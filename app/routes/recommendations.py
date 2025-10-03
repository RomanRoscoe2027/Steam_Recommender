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

@bp.get("/recommendations")
def recommendations():
    """
    Return top N 'hidden gems' using a simple score:
    score = pos_ratio / (1 + log10(popularity_proxy))
    """
    limit = int(request.args.get("limit", 10))
    min_reviews = int(request.args.get("min_reviews", 50))
    name_query = request.args.get("q")  # optional name filter

    candidates = Game.query.all()
    if name_query:
        candidates = [game for game in candidates if name_query.lower() in game.name.lower()]
    candidates = [game for game in candidates if game.total_reviews >= min_reviews]

    def score(game: Game) -> float:
        if game.total_reviews == 0:
            return 0.0
        ratio = game.pos_ratio
        owners = game.owners_estimate or max(game.total_reviews, 1)  # crude popularity proxy
        return ratio / (1.0 + log10(max(owners, 1)))

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
