import os
from dotenv import load_dotenv
load_dotenv()  # loads .env at project root

from app import create_app
from app.services.steam_client import SteamClient
from app.services.owned_games_sync import upsert_owned_games_only
STEAMID64 = os.getenv("STEAMID64")  # export this or hardcode for a quick test
USER_ID = int(os.getenv("TEST_USER_ID", "1"))  # pick a user id for local testing
if not STEAMID64:
    raise SystemExit("Set STEAMID64 in your env (export STEAMID64=17_digit_id)")

def main():
    client = SteamClient()
    games, count = client.owned_games(STEAMID64, include_appinfo=True)
    print("game_count:", count)
    for g in games[:10]:  # limit print noise
        print(g["appid"], g.get("name"), g.get("playtime_forever", 0))

    # write to DB (inside app context)
    app = create_app()
    with app.app_context():
        stats = upsert_owned_games_only(USER_ID, games)
        print("sync stats:", stats)

if __name__ == "__main__":
    main()
