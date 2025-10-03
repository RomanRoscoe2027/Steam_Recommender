import time, requests
from typing import Any, Dict, Optional

class SteamClient:
    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[float, Any]] = {}

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        key = f"{url}|{params}"
        now = time.time()
        if key in self._cache:
            ts, data = self._cache[key]
            if now - ts < self.cache_ttl:
                return data
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        self._cache[key] = (now, data)
        return data

    def app_details(self, appid: int) -> dict:
        url = "https://store.steampowered.com/api/appdetails"
        return self._get(url, {"appids": appid})

    def app_reviews_summary(self, appid: int) -> dict:
        url = f"https://store.steampowered.com/appreviews/{appid}"
        return self._get(url, {"json": 1, "purchase_type": "all", "filter": "summary"})
