from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, ForeignKey, Integer, String, Boolean, BigInteger, Text

db = SQLAlchemy()

class App(db.Model):
    __tablename__ = "apps"
    steam_appid = db.Column(Integer, primary_key=True)
    name = db.Column(String, index=True)
    type = db.Column(String)
    is_free = db.Column(Boolean, default=False)
    metacritic_score = db.Column(Integer)
    recommendations_total = db.Column(Integer)
    #key for popularity reccommending at some point
    release_date_raw = db.Column(String)
    last_fetched_ts = db.Column(BigInteger)
    #don't wanna hammer the API, impoetant for cache

    genres = db.relationship("AppGenre", back_populates="app",
                             cascade="all, delete-orphan")
    categories = db.relationship("AppCategory", back_populates="app",
                                 cascade="all, delete-orphan")
    """ The above two are vital for creating our recceomendations, JSON data
    will likely return some list of categories and genres, cascades allow for auto deletion of childs
    in regards to deleting app, think of as like smart ptr in c++. Important to understand that this
    is for convience, as could all essentially be done through regular sql querying, just have to
    be more precise and its far more annoying, sql alchemy helps manage relationships, instead of 
    total manual control."""

class AppGenre(db.Model):
    """Genre table that connects to parent table app, through foreign key
    steam_appid. Index named idx_genre created just to sift through all genres."""
    __tablename__ = "app_genres"
    steam_appid = db.Column(Integer, ForeignKey("apps.steam_appid", ondelete="CASCADE"), primary_key=True)
    genre = db.Column(String, primary_key=True)
    app = db.relationship("App", back_populates="genres")
    __table_args__ = (Index("idx_genre", "genre"),)

class AppCategory(db.Model):
    """Category table that connects to parent table app, through foreign key
    steam_appid. Index named idx_categpry created just to sift through all cats."""
    __tablename__ = "app_categories"
    steam_appid = db.Column(Integer, ForeignKey("apps.steam_appid", ondelete="CASCADE"), primary_key=True)
    category = db.Column(String, primary_key=True)
    app = db.relationship("App", back_populates="categories")
    __table_args__ = (Index("idx_category", "category"),)


class SteamLink(db.Model):
    __tablename__ = "steam_links"
    user_id = db.Column(Integer, primary_key=True)
    steamid64 = db.Column(String, nullable=False, unique=True)

class OwnedGame(db.Model):
    """Creating table in db from client.owned_games, we need this primarily to use the users
    time playing games, as well as the last time they played said game, to accurately
    suggest games based off their preferences that favors their recent preferences more so."""
    __tablename__ = "owned_games"
    user_id = db.Column(Integer, primary_key=True)
    steam_appid = db.Column(Integer, ForeignKey("apps.steam_appid", ondelete="CASCADE"), primary_key=True)
    playtime_forever = db.Column(Integer, default=0)     
    rtime_last_played = db.Column(BigInteger) 
    __table_args__ = (Index("idx_owned_user", "user_id"),)
