# services/app_metadata.py
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
import requests
from sqlalchemy.exc import IntegrityError
from ..models.appdetails import db, App, OwnedGame, Genre, Category, AppGenre, AppCategory

# -------- helpers --------

def _safe_get(data: Dict[str, Any], path: Tuple[str, ...], default=None):
    """
    Safely walk through nested dicts to grab information:
    _safe_get(d, ('a','b','c')), d['a']['b']['c'] or default.
    """
    current = data
    for k in path:
        if not isinstance(current, dict) or k not in current:
            return default
        current = current[k]
    return current

def _parse_app_payload(raw: Dict[str, Any], appid: int) -> Optional[Dict[str, Any]]:
    """
    Helper function used to grab all data from api and parsed to be ready to
    place into tables.
    """
    #raw is the entire response json
    block = raw.get(str(appid))
    #first block contains data and success
    if not block or not block.get("success"):
        return None
    data = block.get("data", {})
    steam_appid = data.get("steam_appid")
    name = data.get("name")

    if steam_appid is None or name is None:
        return None

    
    app_type = data.get("type")
    is_free = bool(data.get("is_free", False))
    metacritic_score = _safe_get(data, ("metacritic", "score"))
    #will do this for all dicts containing nested dicts
    if metacritic_score is not None:
        try:
            metacritic_score = int(metacritic_score)
        except (TypeError, ValueError):
            metacritic_score = None

    recommendations_total = _safe_get(data, ("recommendations", "total"))
    if recommendations_total is not None:
        try:
            recommendations_total = int(recommendations_total)
        except (TypeError, ValueError):
            recommendations_total = None
    genres = [game.get("description") for game in data.get("genres", []) if isinstance(game, dict) and game.get("description")]
    categories = [category.get("description") for category in data.get("categories", []) if isinstance(category, dict) and category.get("description")]

    return {
        "appid": int(steam_appid),
        "name": name,
        "type": app_type,
        "is_free": is_free,
        "metacritic_score": metacritic_score,
        "recommendations_total": recommendations_total,
        "genres": genres,
        "categories": categories,
    }

def _request_appdetails(appid: int) -> Optional[Dict[str, Any]]:
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    try:
        request = requests.get(url, timeout=6)
        if request.status_code in (429, 500, 502, 503, 504):
            raise RuntimeError(f"Transient HTTP {request.status_code}")
        request.raise_for_status()
        return request.json()
    except Exception as e:
        print(f"[appdetails] appid={appid} failed: {e}")
    return None

def fetch_app_details(appid: int) -> Optional[Dict[str, Any]]:
    """
    Fetch and parse app metadata from Steam. Returns a normalized dict or None.
    Does NOT touch the database.
    """
    raw = _request_appdetails(appid)
    if not raw:
        return None
    return _parse_app_payload(raw, appid)

def upsert_app_metadata(appid: int) -> Optional[App]:
    """
    Fetch metadata for a single appid and upsert into App / Genre / Category + pivot tables.
    Returns the App instance or none.
    """
    meta = fetch_app_details(appid)
    if not meta:
        return None

    #for apps
    app = App.query.get(meta["appid"])
    if not app:
        app = App(
            appid=meta["appid"],
            name=meta["name"],
            type=meta["type"],
            is_free=meta["is_free"],
            metacritic_score=meta["metacritic_score"],
            recommendations_total=meta["recommendations_total"],
        )
        db.session.add(app)
    else:
        app.name = meta["name"]
        app.type = meta["type"]
        app.is_free = meta["is_free"]
        app.metacritic_score = meta["metacritic_score"]
        app.recommendations_total = meta["recommendations_total"]

    #for genres now
    genre_ids = []
    for gamename in meta["genres"]:
        game = Genre.query.filter_by(name=gamename).first()
        if not game:
            game = Genre(name=gamename)
            db.session.add(game)
            try:
                db.session.flush()  # get g.id
            except IntegrityError:
                db.session.rollback()
                game = Genre.query.filter_by(name=gamename).first()
        genre_ids.append(game.id)

    #for categories
    category_ids = []
    for category_name in meta["categories"]:
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            db.session.add(category)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                category = Category.query.filter_by(name=category_name).first()
        category_ids.append(category.id)

    #pivot inserts
    for gid in genre_ids:
        exists = AppGenre.query.filter_by(appid=app.appid, genre_id=gid).first()
        if not exists:
            db.session.add(AppGenre(appid=app.appid, genre_id=gid))

    for cid in category_ids:
        exists = AppCategory.query.filter_by(appid=app.appid, category_id=cid).first()
        if not exists:
            db.session.add(AppCategory(appid=app.appid, category_id=cid))

    db.session.commit()
    return app

def backfill_metadata_for_user(user_id: int, limit: int = 200) -> int:
    """
    Iterate the user's OwnedGame rows and upsert metadata for any apps missing in App.
    Returns the count of apps successfully (up)inserted/updated.
    """
    count = 0
    # Get appids the user owns
    owned = (
        db.session.query(OwnedGame.appid)
        .filter(OwnedGame.user_id == user_id)
        .limit(limit)
        .all()
    )
    appids = [row[0] for row in owned]


    existing = set(
        a[0] for a in db.session.query(App.appid).filter(App.appid.in_(appids)).all()
    )
    missing = [a for a in appids if a not in existing]

    for appid in missing:
        if upsert_app_metadata(appid):
            count += 1
    return count
