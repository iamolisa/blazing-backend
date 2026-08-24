from flask import Blueprint, jsonify
from app.core.catalog import get_approved_testimonials
from app.core.spam import is_honeypot_triggered
from extensions import limiter

testimonials_bp = Blueprint("testimonials", __name__)


@testimonials_bp.route("/")
def index():
    return jsonify({"ok": True, "testimonials": [t.to_dict() for t in get_approved_testimonials()]})


@testimonials_bp.route("/", methods=["POST"])
@limiter.limit("3 per hour")
def submit():
    """Public submission endpoint. Lands as 'pending' until an admin
    approves it from the dashboard."""
    from flask import request
    from extensions import db
    from app.models import Testimonial

    data = request.get_json(silent=True) or request.form

    if is_honeypot_triggered(data):
        return jsonify({"ok": True, "message": "Thanks. Your testimonial will appear once reviewed."}), 201

    name = (data.get("client_name") or "").strip()
    quote = (data.get("quote") or "").strip()
    if not name or not quote:
        return jsonify({"ok": False, "error": "validation", "message": "Name and testimonial text are required."}), 400
    if len(quote) > 2000:
        return jsonify({"ok": False, "error": "validation", "message": "Testimonial is too long. Please keep it under 2000 characters."}), 400

    try:
        rating = max(1, min(int(data.get("rating", 5) or 5), 5))
    except (TypeError, ValueError):
        rating = 5

    testimonial = Testimonial(
        client_name=name,
        client_role=data.get("client_role"),
        quote=quote,
        rating=rating,
        source="Website",
        status="pending",
    )
    db.session.add(testimonial)
    db.session.commit()
    return jsonify({"ok": True, "message": "Thanks. Your testimonial will appear once reviewed."}), 201
