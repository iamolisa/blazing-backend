from flask import Blueprint, jsonify, request, abort
from app.core.catalog import get_gallery_items, get_gallery_item, get_related_gallery_items

gallery_bp = Blueprint("gallery", __name__)


@gallery_bp.route("/")
def index():
    category = request.args.get("category", "all")
    return jsonify({
        "ok": True,
        "items": [g.to_dict() for g in get_gallery_items(category)],
        "active_category": category,
    })


@gallery_bp.route("/<int:item_id>")
def detail(item_id):
    item = get_gallery_item(item_id)
    if not item:
        abort(404)
    related = get_related_gallery_items(item)
    return jsonify({
        "ok": True,
        "item": item.to_dict(include_description=True),
        "related": [g.to_dict() for g in related],
    })
