"""Lazy SQLAlchemy engines; constructing the Flask app never touches this layer."""
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


@lru_cache(maxsize=8)
def _engine(url):
    parsed = make_url(url)
    if parsed.drivername in ("mariadb", "mysql"):
        parsed = parsed.set(drivername="mysql+pymysql")
    options = {"connect_timeout": 5} if parsed.drivername == "mysql+pymysql" else {}
    return create_engine(parsed, pool_pre_ping=True, connect_args=options)


def get_engine(url=None):
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("Set DATABASE_URL to use durable storage")
    return _engine(url)


def initialize_database():
    from .orm_models import Base
    Base.metadata.create_all(get_engine())


if __name__ == "__main__":
    initialize_database()
