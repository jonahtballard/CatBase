from flask import Flask
from flask_cors import CORS
import os

# Use RELATIVE imports so we don't clash with the third-party "routes" package
from .routes.analytics import analytics_bp
from .routes.meta import meta_bp
from .routes.subjects import subjects_bp
from .routes.terms import terms_bp
from .routes.instructors import instructors_bp
from .routes.meetings import meetings_bp
from .routes.sections import sections_bp
from .routes.courses import courses_bp  # optional if you prefer sections-only

def create_app():
    app = Flask(__name__)

    # ---- CORS ----
    # Prefer a specific origin for dev; override with FRONTEND_ORIGIN env var
    default_origin = "http://localhost:5173"  # or http://localhost:3000 if you use CRA
    frontend_origin = os.getenv("FRONTEND_ORIGIN", default_origin)
    CORS(app, resources={r"/api/*": {"origins": [frontend_origin]}})

    # ---- Blueprints ----
    app.register_blueprint(meta_bp,        url_prefix="/api")
    app.register_blueprint(subjects_bp,    url_prefix="/api")
    app.register_blueprint(terms_bp,       url_prefix="/api")
    app.register_blueprint(instructors_bp, url_prefix="/api")
    app.register_blueprint(meetings_bp,    url_prefix="/api")
    app.register_blueprint(sections_bp,    url_prefix="/api")
    app.register_blueprint(courses_bp,     url_prefix="/api")  # comment out if not needed
    app.register_blueprint(analytics_bp, url_prefix="/api")


    # Simple root to prove the server is alive
    @app.get("/")
    def root():
        return {"ok": True, "service": "CatBase API", "docs": "/api/health"}

    return app

if __name__ == "__main__":
    app = create_app()
    # Use port 5001 to avoid conflicts; change if you prefer
    app.run(host="127.0.0.1", port=5001, debug=True)
