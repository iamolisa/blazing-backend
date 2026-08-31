from datetime import datetime
from flask import Blueprint, jsonify, current_app
from app.core.catalog import (
    get_featured_products,
    get_active_services,
    get_active_packages,
    get_featured_testimonials,
    get_gallery_items,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/health")
def health():
    return jsonify({'status': 'ok'})


@main_bp.route("/business")
def business():
    """Shared site/business info the frontend renders in header/footer/meta."""
    cfg = current_app.config
    return jsonify({
        "ok": True,
        "business_name": cfg["BUSINESS_NAME"],
        "business_tagline": cfg["BUSINESS_TAGLINE"],
        "business_phone": cfg["BUSINESS_PHONE"],
        "business_phone_secondary": cfg["BUSINESS_PHONE_SECONDARY"],
        "business_whatsapp": cfg["BUSINESS_WHATSAPP"],
        "business_email": cfg["BUSINESS_EMAIL"],
        "business_address": cfg["BUSINESS_ADDRESS"],
        "current_year": datetime.utcnow().year,
    })


@main_bp.route("/home")
def home():
    return jsonify({
        "ok": True,
        "featured_products": [p.to_dict() for p in get_featured_products(limit=6)],
        "services": [s.to_dict() for s in get_active_services(limit=8)],
        "packages": [p.to_dict() for p in get_active_packages()],
        "testimonials": [t.to_dict() for t in get_featured_testimonials(limit=3)],
        "gallery_items": [g.to_dict() for g in get_gallery_items()[:6]],
    })
