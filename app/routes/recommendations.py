from flask import Blueprint, jsonify, request, current_app
from ..extensions import db
from ..models.appdetails import App
from ..services.steam_client import SteamClient
from math import log10

bp = Blueprint("recommendations", __name__)
         
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
        
        game = App.query.get(appid) or App(appid=appid, name=details.get("name", f"App {appid}"))
        game.positive = summary.get("total_positive", 0)
        game.negative = summary.get("total_negative", 0)

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

    candidates = App.query.all() 
    #get all games from database
    if name_query:
        candidates = [game for game in candidates if name_query.lower() in (game.name or "").lower()]
    candidates = [game for game in candidates if ((game.positive or 0) + (game.negative or 0)) >= min_reviews]
    #filter candidates by name query and minimum reviews

    def total_reviews(game: App) -> int:
        #return total reviews as int
        return int(game.positive or 0) + int(game.negative or 0)

    def pos_ratio(game: App) -> float:
        #return positive review ratio as float
        t = total_reviews(game)
        return (float(game.positive) / t) if t else 0.0

    def popularity_proxy(game: App) -> int:
        """
        Replacement for owners_estimate (often unavailable). Prefer storefront
        recommendations_total if cached on App; otherwise fall back to total_reviews.
        """
        val = getattr(game, "recommendations_total", None)
        if val is None:
            val = total_reviews(game)
        return max(int(val or 0), 1)

    def score(game: App) -> float:
        if total_reviews(game) == 0:
            return 0.0
        ratio = pos_ratio(game)
        owners = popularity_proxy(game)  #crude popularity
        return ratio / (1.0 + log10(max(owners, 1)))
        #calculate score based on positive review ratio and popularity

    ranked = sorted(candidates, key=score, reverse=True)[:limit]

    #format response through jsonify after sorting and limiting
    return jsonify([
        {
            "appid": app.appid,  
            "name": app.name,
            "pos_ratio": round(pos_ratio(app), 4),
            "total_reviews": total_reviews(app),
            "owners_estimate": popularity_proxy(app),  # keep key name if you want to avoid breaking clients
        } for app in ranked
    ])
