from flask import Blueprint

# Import blueprints from submodules
from .health import health_bp
from .subjects import subjects_bp
from .terms import terms_bp
from .instructors import instructors_bp
from .meetings import meetings_bp
from .sections import sections_bp
from .courses import courses_bp

# Master API blueprint
api_bp = Blueprint("api", __name__)
api_bp.register_blueprint(health_bp, url_prefix="/api")
api_bp.register_blueprint(subjects_bp, url_prefix="/api")
api_bp.register_blueprint(terms_bp, url_prefix="/api")
api_bp.register_blueprint(instructors_bp, url_prefix="/api")
api_bp.register_blueprint(meetings_bp, url_prefix="/api")
api_bp.register_blueprint(sections_bp, url_prefix="/api")
api_bp.register_blueprint(courses_bp, url_prefix="/api")
