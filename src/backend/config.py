"""Read environment settings when the application is constructed."""

import os


def load_config():
    return {
        "CORS_ORIGINS": [
            origin.strip()
            for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ],
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
    }
