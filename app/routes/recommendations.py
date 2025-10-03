from flask import Blueprint, jsonify, request, current_app
from ..extensions import db
from ..models.game import Game
from ..services.steam_client import SteamClient
from math import log10

bp = Blueprint("recommendations", __name__)

@bp.post("/seed")
def seed():
    """
    Seed a few appids into the DB for dev:
    curl -XPOST :8000/api/seed -H 'Content-Type: application/json' \
         -d '{"appids":[570,440,620]}'
    """
    data = request.get_json(silent=True) or {}
    appids = data.get("appids") or [570, 440, 620]  # Dota2/TF2/Portal2
    client = SteamClient(cache_ttl=current_app.config.get("STEAM_CACHE_TTL_SECONDS", 3600))

    for raw in appids:
        appid = int(raw)
        details = client.app_details(appid).get(str(appid), {}).get("data", {}) or {}
        summary = client.app_reviews_summary(appid).get("query_summary", {}) or {}

        g = Game.query.get(appid) or Game(appid=appid, name=details.get("name", f"App {appid}"))
        g.positive = summary.get("total_positive", 0)
        g.negative = summary.get("total_negative", 0)
        #owners_estimate often unavailable; leave None (we'll improve later)
        db.session.add(g)
    db.session.commit()
    return jsonify({"seeded": len(appids)}), 201

"""Want to test for a lot fo seeds."""
@bp.post("/seed_range")
def seed_range():
    """
    Body JSON (all optional):
    {"start": 1000, "end": 1500, "extra": [570,440,620]}
    """
    payload = request.get_json(silent=True) or {}
    start = int(payload.get("start", 1000))
    end   = int(payload.get("end",   1500))
    extra = payload.get("extra") or [570, 440, 620]
    appids = list(range(start, end)) + extra

    client = SteamClient(cache_ttl=current_app.config.get("STEAM_CACHE_TTL_SECONDS", 3600))
    seeded = 0
    for raw in appids:
        appid = int(raw)
        details = client.app_details(appid).get(str(appid), {}).get("data", {}) or {}
        summary = client.app_reviews_summary(appid).get("query_summary", {}) or {}

        game = Game.query.get(appid) or Game(appid=appid, name=details.get("name", f"App {appid}"))
        game.positive = summary.get("total_positive", 0)
        game.negative = summary.get("total_negative", 0)
        db.session.add(game)
        seeded += 1
    db.session.commit()
    return jsonify({"seeded": seeded, "range": [start, end]}), 201

@bp.route("/recommendations", methods=["GET", "POST"])
def recommendations():
    #built to allow both get and post methods, now we can test and dev debug easier with post method
    if request.method == "GET":
        payload = {
            "limit": request.args.get("limit"),
            "min_reviews": request.args.get("min_reviews"),
            "q": request.args.get("q"),
        }
    elif request.method == "POST": 
        payload = request.get_json(silent=True) or {}

    # normalize inputs with defaults
    limit = max(1, min(int(payload.get("limit") or 10), 100))
    min_reviews = int(payload.get("min_reviews") or 50)
    q = ((payload.get("q") or "")).strip()

    #filter and score
    candidates = Game.query.all()
    if q:
        candidates = [game for game in candidates if q.lower() in game.name.lower()]
    candidates = [game for game in candidates if game.total_reviews >= min_reviews]

    from math import log10
    def score(game: Game) -> float:
        if game.total_reviews == 0: return 0.0
        owners = game.owners_estimate or game.total_reviews
        return game.pos_ratio / (1.0 + log10(max(owners, 1)))

    ranked = sorted(candidates, key=score, reverse=True)[:limit]
    return jsonify([
        {
            "appid": game.appid,
            "name": game.name,
            "pos_ratio": round(game.pos_ratio, 4),
            "total_reviews": game.total_reviews,
            "owners_estimate": game.owners_estimate,
        } for game in ranked
    ])
