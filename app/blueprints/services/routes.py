from flask import Blueprint, jsonify, abort
from app.core.catalog import get_active_services
from app.models import ServiceItem

services_bp = Blueprint("services", __name__)


@services_bp.route("/")
def index():
    return jsonify({"ok": True, "services": [s.to_dict() for s in get_active_services()]})


@services_bp.route("/<slug>")
def detail(slug):
    service = ServiceItem.query.filter_by(slug=slug, is_active=True).first()
    if not service:
        abort(404)
    related = [s for s in get_active_services() if s.id != service.id][:3]
    return jsonify({
        "ok": True,
        "service": service.to_dict(include_description=True),
        "related": [s.to_dict() for s in related],
    })
