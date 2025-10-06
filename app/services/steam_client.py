import time, requests
#time for caching, requests for HTTP requests
from typing import Any, Dict, Optional
#type hints, any for any type, json can be whatever
#dict only imported for type hints
class SteamClient:
    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[float, Any]] = {}
        #type hinting for cache, key is str, value is tuple of (timestamp, data)
        #important for catching errors in development, any is for JSON payload, float for timestamp

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        
        key = f"{url}|{params}"
        #create a unique cache key based on URL and parameters
        now = time.time()
        #grab current time - float
        
        if key in self._cache:
            timestamp, data = self._cache[key]
            #retrieve cached entry, remember tho data is a JSON payload, can be anything as a tuple
            if now - timestamp < self.cache_ttl:
                #if key exists and entry is fresh return data - cache hit, return data
                #from RAM rather than network, far in quit bursts that acknowledge ttl
                return data
        
        #cache miss or stale entry, make network request
        response_object = requests.get(url, params=params)
        #call get func from requests library, pass url and params
            #essentially calls out to someone elses API and gets a response object
        response_object.raise_for_status()
            #built in func to raise an error if status code is not 200
        data = response_object.json()
        #JSON response and store in cache and return the data
        self._cache[key] = (now, data)
        return data


    #below functions are specific to Steam API, but return JSON data using our get method

    def app_details(self, appid: int) -> dict:
        url = "https://store.steampowered.com/api/appdetails"
        return self._get(url, {"appids": appid})

    def app_reviews_summary(self, appid: int) -> dict:
        url = f"https://store.steampowered.com/appreviews/{appid}"
        return self._get(url, {"json": 1, "purchase_type": "all", "filter": "summary"})#cur
