from flask import Blueprint, jsonify, request
from app.core.leads import create_lead
from app.core.spam import is_honeypot_triggered
from app.core.catalog import get_active_packages
from app.core.financing_ai import get_financing_advice, FinancingAdvisorUnavailable
from extensions import limiter

tools_bp = Blueprint("tools", __name__)

# Rough reference loads in watts, used by the sizing calculator on the
# client side (frontend js/calculator.js -> SolarCalculator).
APPLIANCE_LOADS_WATTS = {
    "bulbs": 15,
    "fan": 75,
    "fridge": 150,
    "tv": 120,
    "ac_1hp": 900,
    "ac_1_5hp": 1200,
    "washing_machine": 500,
    "freezer": 200,
    "pumping_machine": 750,
    "iron": 1000,
}


@tools_bp.route("/")
def index():
    return jsonify({"ok": True, "appliance_loads": APPLIANCE_LOADS_WATTS})


@tools_bp.route("/sizing-result", methods=["POST"])
@limiter.limit("5 per minute")
def sizing_result():
    """
    Accepts the calculator's estimated load and stores it as a lead so
    the sales team can follow up, then returns a JSON confirmation.
    Real appliance -> kVA math happens client-side in calculator.js so the
    UI updates instantly as sliders move; this endpoint just captures the lead.
    """
    data = request.get_json(silent=True) or request.form
    if is_honeypot_triggered(data):
        return jsonify({"ok": True, "lead_id": None}), 201
    lead = create_lead(
        {
            "full_name": data.get("full_name", "Website visitor"),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
            "interest": "Solar sizing calculator",
            "message": f"Estimated system size: {data.get('estimated_kva', 'n/a')}",
        },
        source="calculator",
    )
    return jsonify({"ok": True, "lead_id": lead.id}), 201


@tools_bp.route("/financing-advice", methods=["POST"])
@limiter.limit("5 per hour")
def financing_advice():
    """
    Free-text financing/installment advisor. Grounded in real package
    pricing (see app/core/financing_ai.py). The model is never allowed to
    invent a price or promise credit terms the business doesn't offer.

    Rate limited harder than the other public endpoints since each call
    has a real cost against the AI provider, not just server capacity.
    """
    data = request.get_json(silent=True) or request.form
    if is_honeypot_triggered(data):
        return jsonify({"ok": True, "reply": None}), 200

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "validation", "message": "Please describe your budget, timeline, or what you'd like to power."}), 400

    try:
        packages = get_active_packages()
        reply = get_financing_advice(message, packages)
    except FinancingAdvisorUnavailable as exc:
        return jsonify({"ok": False, "error": "advisor_unavailable", "message": str(exc)}), 503

    lead_id = None
    phone = (data.get("phone") or "").strip()
    if phone:
        lead = create_lead(
            {
                "full_name": data.get("full_name", "Website visitor"),
                "phone": phone,
                "email": data.get("email", ""),
                "interest": "Financing / installment advisor",
                "message": message,
            },
            source="financing_advisor",
        )
        lead_id = lead.id

    return jsonify({"ok": True, "reply": reply, "lead_id": lead_id}), 200
