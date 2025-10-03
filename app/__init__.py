from flask import Flask, jsonify 
from .config import get_config
from .extensions import db

from .routes.recommendations import bp as recs_bp
# Initialize flask application, allows app/ to be a package imported

from .models.game import Game 
#initially wasn't being imported, needs db/metadata
def create_app(env: str = "dev") -> Flask:
    app = Flask(__name__)  #Create the WSGI app object
    app.config.from_object(get_config(env))
    db.init_app(app)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    app.register_blueprint(recs_bp, url_prefix="/api")

    #dev-only: create tables on startup (use Alembic later)

    with app.app_context():
        db.create_all()

    return app