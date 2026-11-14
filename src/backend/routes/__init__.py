"""Explicitly register implemented blueprints; no service auto-discovery."""

from .health import health_bp
from .pantry import pantry_bp
from .recipes import recipes_bp
from .scans import scans_bp


def register_blueprints(app):
    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(recipes_bp, url_prefix="/api/v1/recipes")
    app.register_blueprint(scans_bp, url_prefix="/api/v1/scans")
    app.register_blueprint(pantry_bp, url_prefix="/api/v1/pantry")
