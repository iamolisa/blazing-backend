from flask import Blueprint, jsonify, request
from app.core.leads import create_lead
from app.core.spam import is_honeypot_triggered
from extensions import limiter

contact_bp = Blueprint("contact", __name__)


def _validate(data):
    errors = {}
    if not (data.get("full_name") or "").strip():
        errors["full_name"] = "Full name is required."
    if not (data.get("phone") or "").strip():
        errors["phone"] = "Phone number is required."
    return errors


@contact_bp.route("/", methods=["POST"])
@limiter.limit("5 per minute")
def index():
    data = request.get_json(silent=True) or request.form
    if is_honeypot_triggered(data):
        # Return a normal-looking success without creating a lead. Don't
        # give a bot any signal that it was caught.
        return jsonify({"ok": True, "message": "Thanks. Your message has been received. We'll get back to you shortly."}), 201
    errors = _validate(data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    lead = create_lead(data, source="contact_form")
    return jsonify({
        "ok": True,
        "message": "Thanks. Your message has been received. We'll get back to you shortly.",
        "lead_id": lead.id,
    }), 201


@contact_bp.route("/quote", methods=["POST"])
@limiter.limit("5 per minute")
def quote():
    data = request.get_json(silent=True) or request.form
    if is_honeypot_triggered(data):
        return jsonify({"ok": True, "message": "Quote request received. Our team will reach out with pricing."}), 201
    errors = _validate(data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    lead = create_lead(data, source="quote_form")
    return jsonify({
        "ok": True,
        "message": "Quote request received. Our team will reach out with pricing.",
        "lead_id": lead.id,
    }), 201
