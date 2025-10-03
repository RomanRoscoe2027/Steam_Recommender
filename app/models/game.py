from datetime import datetime
from ..extensions import db

class Game(db.Model):
    __tablename__ = "games"
    appid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, index=True)
    positive = db.Column(db.Integer, default=0)
    negative = db.Column(db.Integer, default=0)
    owners_estimate = db.Column(db.Integer, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total_reviews(self) -> int:
        return (self.positive or 0) + (self.negative or 0)

    @property
    def pos_ratio(self) -> float:
        t = self.total_reviews
        return (self.positive / t) if t else 0.0
