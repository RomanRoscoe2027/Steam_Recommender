from flask import Flask, jsonify 

# Initialize flask application, allows app/ to be a package imported

def create_app(env: str = "dev") -> Flask:
    app = Flask(__name__)  #Create the WSGI app object

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    return app