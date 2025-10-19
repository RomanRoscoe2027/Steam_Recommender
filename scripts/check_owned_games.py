# scripts/check_owned_games.py
import os
from dotenv import load_dotenv
load_dotenv()  # loads .env at project root
from app.services.steam_client import SteamClient

STEAMID64 = os.getenv("STEAMID64")  # export this or hardcode for a quick test
if not STEAMID64:
    raise SystemExit("Set STEAMID64 in your env (export STEAMID64=17_digit_id)")

client = SteamClient()
games, count = client.owned_games(STEAMID64, include_appinfo=True)
print("game_count:", count)
for g in games[:]:
    print(g["appid"], g.get("name"), g.get("playtime_forever", 0))
