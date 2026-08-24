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
    """
    Smoke-test target: confirms the app is up AND the database is
    reachable, not just that gunicorn is responding. A 200 here with
    database: "healthy" means both are true; anything else means don't
    trust the deploy yet.
    """
    from extensions import db
    try:
        db.session.execute(db.text("SELECT 1"))
        database_status = "healthy"
        status_code = 200
    except Exception as exc:
        current_app.logger.error(f"Health check: database unreachable: {exc}")
        database_status = "unreachable"
        status_code = 503

    return jsonify({"ok": status_code == 200, "database": database_status}), status_code


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
