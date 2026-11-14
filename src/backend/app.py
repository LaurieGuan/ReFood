"""REFOOD Flask entry point; no database or provider initialization."""

from flask import Flask
from flask_cors import CORS

from config import load_config
from routes import register_blueprints
from routes.errors import register_error_handlers


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if test_config is not None:
        app.config.update(test_config)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    register_error_handlers(app)
    register_blueprints(app)
    return app


if __name__ == "__main__":
    create_app().run()
