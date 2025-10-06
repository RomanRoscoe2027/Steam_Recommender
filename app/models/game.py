from datetime import datetime
from ..extensions import db

class Game(db.Model):
    #create a ORM model, representing a game in the database
    __tablename__ = "GAMES"
    appid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True)
    positive = db.Column(db.Integer, default=0)
    negative = db.Column(db.Integer, default=0)
    players = db.Column(db.Integer, nullable=True)
    #will need total players from a third party so fine to be null for now
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total_reviews(self) -> int:
        return (self.positive or 0) + (self.negative or 0)
        #return total reviews as int
    @property
    def pos_ratio(self) -> float:
        total_reviews = self.total_reviews
        return (self.positive / total_reviews) if total_reviews else 0.0
        #return positive review ratio as float    