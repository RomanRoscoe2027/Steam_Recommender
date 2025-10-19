# app/services/owned_sync.py
from ..models.appdetails import db, App, OwnedGame

def upsert_owned_games_only(user_id: int, games: list[dict]) -> dict:
    #load once: all rows for this user → O(1) lookups in the loop
    existing_by_appid = {}
    for row in OwnedGame.query.filter_by(user_id=user_id).all():
        existing_by_appid[row.appid] = row
    #create a dict of all ownedgame rows for user-
    seen = set()
    created = updated = 0

    for g in games:
        appid = g.get("appid")
        if appid is None:
            continue
        seen.add(appid)
        
        if App.query.get(appid) is None:
            db.session.add(App(appid=appid))  
            #FK parent
        
        row = existing_by_appid.get(appid)
        #lookups in O(1) time cuz of dict,essentially one query over n+1 queries
        if row is None:
            row = OwnedGame(user_id=user_id, appid=appid)
            db.session.add(row)
            created += 1
        else:
            updated += 1

        row.playtime_forever  = int(g.get("playtime_forever") or 0)
        rlp = g.get("rtime_last_played")
        row.rtime_last_played = int(rlp) if rlp is not None else None
    db.session.commit()
    return {"created": created, "updated": updated, "total_incoming": len(games)}
