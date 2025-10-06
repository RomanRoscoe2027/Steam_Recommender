from flask import Blueprint, jsonify, request, current_app
from ..extensions import db
from ..models.game import Game
from ..services.steam_client import SteamClient
from math import log10

bp = Blueprint("recommendations", __name__)
#          
@bp.post("/seed")
#user request to seed some appids into the database for development purposes
def seed():

    data = request.get_json(silent=True) or {}
    #grab JSON payload from user request, if none present use empty dict
    #silent true means if JSON is malformed just return None rather than error
    appids = data.get("appids") or [570, 440, 620]  # Dota2/TF2/Portal2
    client = SteamClient(cache_ttl=current_app.config.get("STEAM_CACHE_TTL_SECONDS", 3600))
    #build client from config then grab ttl from config, default to 3600 if not present
    for raw in appids:
        appid = int(raw)
        details = client.app_details(appid).get(str(appid), {}).get("data", {}) or {}
        summary = client.app_reviews_summary(appid).get("query_summary", {}) or {}
        #create a new Game instance or update existing
        game = Game.query.get(appid) or Game(appid=appid, name=details.get("name", f"App {appid}"))
        game.positive = summary.get("total_positive", 0)
        game.negative = summary.get("total_negative", 0)
        #owners_estimate often unavailable; leave None (we'll improve later)
        db.session.add(game)
    db.session.commit()
    return jsonify({"seeded": len(appids)}), 201

""" Big picture: when user submits a POST request to /seed with a list of appids,
    our server will use the SteamClient to fetch details and review summaries for each appid.
    It will then create or update Game records in the database with the fetched data,
    and finally commit the changes to the database. 
"""

@bp.get("/recommendations")
def recommendations():
    """
    Return top N 'hidden gems' using a simple score:
    score = pos_ratio / (1 + log10(popularity_proxy))
    """
    limit = int(request.args.get("limit", 10))
    #default to top 10 if not specified, otherwise grab from user request
    #same process for all below, uses request args to grab query parameters
    min_reviews = int(request.args.get("min_reviews", 50))
    name_query = request.args.get("q")  # optional name filter

    candidates = Game.query.all()
    #get all games from database
    if name_query:
        candidates = [game for game in candidates if name_query.lower() in game.name.lower()]
    candidates = [game for game in candidates if game.total_reviews >= min_reviews]
    #filter candidates by name query and minimum reviews
    def score(game: Game) -> float:
        if game.total_reviews == 0:
            return 0.0
        ratio = game.pos_ratio
        owners = game.owners_estimate or max(game.total_reviews, 1)  # crude popularity proxy
        return ratio / (1.0 + log10(max(owners, 1)))
        #calculate score based on positive review ratio and popularity proxy

    ranked = sorted(candidates, key=score, reverse=True)[:limit]

    #format response through jsonify after sorting and limiting
    return jsonify([
        {
            "appid": game.appid,
            "name": game.name,
            "pos_ratio": round(game.pos_ratio, 4),
            "total_reviews": game.total_reviews,
            "owners_estimate": game.owners_estimate,
        } for game in ranked
    ])
