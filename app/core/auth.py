"""
Simple bearer-token auth for the admin JSON API.

The frontend (Hostinger, a different domain) can't reliably rely on
cross-site session cookies, so the admin login endpoint issues an opaque
token that the frontend stores (e.g. in memory / localStorage) and sends
back as `Authorization: Bearer <token>` on every admin request.
"""
from functools import wraps
from flask import request, jsonify, g
from app.models import User


def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):].strip()
    if not token:
        return None
    user = User.query.filter_by(api_token=token).first()
    if not user or not user.token_is_valid():
        return None
    return user


def token_required(view_fn):
    @wraps(view_fn)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"ok": False, "error": "unauthorized", "message": "Sign in required."}), 401
        if user.role not in ("admin", "editor"):
            return jsonify({"ok": False, "error": "forbidden", "message": "You don't have access to this."}), 403
        g.current_user = user
        return view_fn(*args, **kwargs)
    return wrapped
