"""Explicit local demo identities, not authentication."""
from flask import request
from werkzeug.exceptions import BadRequest


def demo_user_id():
    user_id = request.headers.get("X-Demo-User-Id", "demo_user").strip()
    if user_id not in {"alice", "bob", "demo_user", "shop_demo"}:
        raise BadRequest("X-Demo-User-Id must be alice, bob, demo_user or shop_demo")
    return user_id
