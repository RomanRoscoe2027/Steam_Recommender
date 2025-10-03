import os  

class BaseConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///./data.db")  # Database connection string, defaults to local SQLite if not set
    SQLALCHEMY_TRACK_MODIFICATIONS = False  
    STEAM_API_KEY = os.getenv("STEAM_API_KEY", "")  # Steam API key, fetched from environment or left empty
    STEAM_CACHE_TTL_SECONDS = int(os.getenv("STEAM_CACHE_TTL_SECONDS", "3600"))  # Time-to-live for Steam API cache, in seconds

class DevConfig(BaseConfig):
    DEBUG = True  

def get_config(env: str):
    return DevConfig  