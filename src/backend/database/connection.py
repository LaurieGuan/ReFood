"""Optional MariaDB connector, imported and connected only on repository calls."""

import os
from urllib.parse import unquote, urlsplit


def connect():
    url = urlsplit(os.environ.get("DATABASE_URL", ""))
    if url.scheme != "mariadb" or not url.hostname or not url.path.strip("/"):
        raise ValueError("DATABASE_URL must use mariadb://user:password@host:port/database")
    if url.query or url.fragment:
        raise ValueError("DATABASE_URL query parameters and fragments are not supported")
    try:
        import mariadb
    except ImportError:
        raise RuntimeError("MariaDB mode requires the optional mariadb connector") from None
    return mariadb.connect(
        host=url.hostname, port=url.port or 3306,
        user=unquote(url.username or ""), password=unquote(url.password or ""),
        database=unquote(url.path.lstrip("/")),
        connect_timeout=5, autocommit=False,
    )
