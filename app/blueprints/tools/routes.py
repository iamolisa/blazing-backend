from flask import Blueprint, jsonify, request
from app.core.leads import create_lead
from app.core.spam import is_honeypot_triggered
from app.core.catalog import get_active_packages
from app.core.financing_ai import get_financing_advice, FinancingAdvisorUnavailable
from app.core.solar_sizing import (
    APPLIANCE_LOADS_WATTS,
    TIME_BLOCKS,
    VALID_AUTONOMY_DAYS,
    SizingValidationError,
    calculate_solar_sizing,
    match_packages,
    build_summary_text,
)
from extensions import limiter

tools_bp = Blueprint("tools", __name__)


@tools_bp.route("/")
def index():
    """Reference data the calculator UI is built from: appliance loads,
    the time-block definitions (labels + max hours), and which autonomy
    options are offered, so the frontend never hardcodes any of this."""
    return jsonify({
        "ok": True,
        "appliance_loads": APPLIANCE_LOADS_WATTS,
        "time_blocks": TIME_BLOCKS,
        "autonomy_days_options": list(VALID_AUTONOMY_DAYS),
    })


@tools_bp.route("/solar-sizing", methods=["POST"])
@limiter.limit("15 per minute")
def solar_sizing():
    """
    Time-of-day aware solar sizing calculator. Takes each appliance's
    quantity and hours-of-use per time block (morning/afternoon/evening/
    night), works out inverter/battery/panel sizing (see
    app/core/solar_sizing.py for the full method), and matches the
    result against the real package catalog:
      - "single"  -> one package already fits well
      - "compare" -> the requirement sits between two tiers; show both
      - "custom"  -> nothing in the catalog covers it; no price, just
                     the exact numbers for a manual quote
    ---
    tags:
      - Tools
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            appliances:
              type: array
              items:
                type: object
                properties:
                  key: {type: string, example: fridge}
                  quantity: {type: integer, example: 1}
                  hours:
                    type: object
                    properties:
                      morning: {type: number}
                      afternoon: {type: number}
                      evening: {type: number}
                      night: {type: number}
            autonomy_days: {type: integer, example: 1}
            battery_type: {type: string, example: tubular}
    responses:
      200:
        description: Sizing result and package match
      422:
        description: Invalid appliance/autonomy/battery input
      429:
        description: Rate limit exceeded
    """
    data = request.get_json(silent=True) or {}

    try:
        result = calculate_solar_sizing(
            appliances=data.get("appliances"),
            autonomy_days=data.get("autonomy_days", 1),
            battery_type=data.get("battery_type", "tubular"),
        )
    except SizingValidationError as exc:
        return jsonify({"ok": False, "error": "validation", "message": str(exc)}), 422

    match = match_packages(result, get_active_packages())
    summary = build_summary_text(result, match)

    return jsonify({
        "ok": True,
        "result": {
            "total_daily_wh": result.total_daily_wh,
            "evening_night_wh": result.evening_night_wh,
            "daytime_wh": result.daytime_wh,
            "peak_block": result.peak_block,
            "peak_block_watts": result.peak_block_watts,
            "recommended_kva": result.recommended_kva,
            "battery_kwh_required": result.battery_kwh_required,
            "battery_ah_required": result.battery_ah_required,
            "panel_watts_required": result.panel_watts_required,
            "panel_count_suggested": result.panel_count_suggested,
            "autonomy_days": result.autonomy_days,
            "battery_type": result.battery_type,
            "block_totals_watts": result.block_totals_watts,
        },
        "match": match,
        "summary_text": summary,
    }), 200


@tools_bp.route("/sizing-result", methods=["POST"])
@limiter.limit("5 per minute")
def sizing_result():
    """
    Stores the calculator's estimate as a lead so the sales team can
    follow up. Accepts an optional 'system_summary' (the multi-line
    text from /solar-sizing's summary_text) for a fuller record than
    the older single 'estimated_kva' field.
    """
    data = request.get_json(silent=True) or request.form
    if is_honeypot_triggered(data):
        return jsonify({"ok": True, "lead_id": None}), 201

    message = data.get("system_summary") or f"Estimated system size: {data.get('estimated_kva', 'n/a')}"
    lead = create_lead(
        {
            "full_name": data.get("full_name", "Website visitor"),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
            "interest": "Solar sizing calculator",
            "message": message,
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
