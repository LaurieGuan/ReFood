"""Explicitly register implemented blueprints; no service auto-discovery."""

from .health import health_bp


def register_blueprints(app):
    # Future resource blueprints belong here with /api/v1/<resource> prefixes.
    app.register_blueprint(health_bp, url_prefix="/api/v1")
