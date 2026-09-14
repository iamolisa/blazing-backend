from flask import Blueprint, jsonify
from app.core.catalog import get_active_packages

packages_bp = Blueprint("packages", __name__)


@packages_bp.route("/")
def index():
    return jsonify({"ok": True, "packages": [p.to_dict() for p in get_active_packages()]})
