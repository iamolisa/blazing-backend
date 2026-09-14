"""
Solar sizing calculator: turns a list of appliances (with how many hours
each one runs in different parts of the day) into a recommended inverter,
battery bank and panel array, then matches that recommendation against
the real package catalog.

Why time-of-day matters (read before changing the formulas)
-------------------------------------------------------------------------
A calculator that just sums every appliance's wattage assumes everything
in the house runs at the exact same moment, which produces a system far
bigger than most clients actually need. Two numbers matter more than a
single "total watts" figure:

1. Total daily energy (Wh/day) - how much the panels have to generate
   and/or the battery has to store across a full day. This is a sum of
   every appliance-hour, regardless of when it happens.
2. Evening/night energy (Wh/day) - the portion of that total that falls
   outside daylight hours. Panels aren't generating then, so this slice
   has to come entirely out of the battery. It is the real driver of
   battery bank size, not the daily total.

Time blocks (kept intentionally simple for a rough sizing tool):
    morning    06:00-12:00  (6h)  -\\_ daytime, solar generating directly
    afternoon  12:00-17:00  (5h)  -/
    evening    17:00-21:00  (4h)  -\\_ battery-dependent, no generation
    night      21:00-06:00  (9h)  -/
"""
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------

# Rough reference running-loads in watts. Shown to the client as the
# starting point for each appliance row; they only choose quantity and
# hours, not wattage, to keep the form simple.
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

# (label, max hours available in that block, is it a daytime/solar block)
TIME_BLOCKS = {
    "morning": {"label": "Morning (6am-12pm)", "max_hours": 6, "daytime": True},
    "afternoon": {"label": "Afternoon (12-5pm)", "max_hours": 5, "daytime": True},
    "evening": {"label": "Evening (5-9pm)", "max_hours": 4, "daytime": False},
    "night": {"label": "Night (9pm-6am)", "max_hours": 9, "daytime": False},
}

DAYTIME_BLOCKS = [b for b, cfg in TIME_BLOCKS.items() if cfg["daytime"]]
NIGHT_BLOCKS = [b for b, cfg in TIME_BLOCKS.items() if not cfg["daytime"]]

# Nigeria (Lagos/Ogun/Imo) average, per the business's own guidance.
# Real output varies with weather and season; a full engineering
# assessment always confirms the final number.
PEAK_SUN_HOURS = 6

# Accounts for inverter conversion loss, wiring loss, panel soiling/temp
# derating, etc. 75-80% is the normal planning range; 0.78 is a single
# reasonable middle value for a rough estimate.
SYSTEM_EFFICIENCY = 0.78

# Standard safety/surge margin applied to the single busiest time block
# when sizing the inverter (matches prior calculator behaviour).
INVERTER_SURGE_FACTOR = 1.3

# Depth of discharge by battery chemistry. Tubular batteries degrade
# quickly past ~50% discharge; lithium tolerates much deeper cycling.
DEPTH_OF_DISCHARGE = {
    "lithium": 0.90,
    "tubular": 0.50,
}

BATTERY_BANK_VOLTAGE = 48  # assumed system voltage for the Ah figure
REFERENCE_PANEL_WATTS = 350  # used only for the "x panels" display figure

VALID_AUTONOMY_DAYS = (1, 2, 3)
MAX_QUANTITY_PER_APPLIANCE = 30

# A stored package price is a single number, but material costs and the
# exchange rate move, so nothing on the site should read as a locked-in
# quote. Every price shown is stretched into a range instead.
PRICE_RANGE_SPREAD = 0.08


class SizingValidationError(ValueError):
    """Raised on bad input from the client. Routes.py turns this into a
    422 with the message intact, rather than a generic 400."""
    pass


@dataclass
class SizingResult:
    total_daily_wh: float
    evening_night_wh: float
    daytime_wh: float
    peak_block: str
    peak_block_watts: float
    recommended_kva: float
    battery_wh_required: float
    battery_kwh_required: float
    battery_ah_required: float
    panel_watts_required: float
    panel_count_suggested: int
    autonomy_days: int
    battery_type: str
    block_totals_watts: dict = field(default_factory=dict)


# ---------------------------------------------------------------------
# Step 1-2: validate and normalize the raw appliance input
# ---------------------------------------------------------------------

def _validate_appliances(appliances):
    if not isinstance(appliances, list) or not appliances:
        raise SizingValidationError("Add at least one appliance to calculate a system size.")

    cleaned = []
    for row in appliances:
        key = (row or {}).get("key")
        if key not in APPLIANCE_LOADS_WATTS:
            raise SizingValidationError(f"Unknown appliance: {key!r}.")

        try:
            quantity = int(row.get("quantity", 0))
        except (TypeError, ValueError):
            raise SizingValidationError(f"{key}: quantity must be a whole number.")
        if quantity < 0 or quantity > MAX_QUANTITY_PER_APPLIANCE:
            raise SizingValidationError(f"{key}: quantity must be between 0 and {MAX_QUANTITY_PER_APPLIANCE}.")

        hours = {}
        raw_hours = row.get("hours") or {}
        for block, cfg in TIME_BLOCKS.items():
            try:
                value = float(raw_hours.get(block, 0) or 0)
            except (TypeError, ValueError):
                raise SizingValidationError(f"{key}: {block} hours must be a number.")
            if value < 0 or value > cfg["max_hours"]:
                raise SizingValidationError(
                    f"{key}: {block} hours must be between 0 and {cfg['max_hours']}."
                )
            hours[block] = value

        if quantity > 0 and sum(hours.values()) == 0:
            # Quantity with no usage hours contributes nothing and is
            # almost certainly a user just leaving the row in a default
            # state, not an intentional "runs zero hours a day" input.
            continue

        cleaned.append({"key": key, "quantity": quantity, "hours": hours})

    if not cleaned:
        raise SizingValidationError("Add at least one appliance with a quantity and some hours of use.")
    return cleaned


def _validate_autonomy_days(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise SizingValidationError("Autonomy days must be 1, 2 or 3.")
    if value not in VALID_AUTONOMY_DAYS:
        raise SizingValidationError("Autonomy days must be 1, 2 or 3.")
    return value


def _validate_battery_type(value):
    value = (value or "tubular").strip().lower()
    if value not in DEPTH_OF_DISCHARGE:
        raise SizingValidationError("Battery type must be 'lithium' or 'tubular'.")
    return value


# ---------------------------------------------------------------------
# Step 3-7: the actual calculation
# ---------------------------------------------------------------------

def calculate_solar_sizing(appliances, autonomy_days, battery_type):
    """Pure function: appliance usage in -> sizing numbers out. No DB
    access here, so this is trivially unit-testable on its own."""
    appliances = _validate_appliances(appliances)
    autonomy_days = _validate_autonomy_days(autonomy_days)
    battery_type = _validate_battery_type(battery_type)

    total_daily_wh = 0.0
    evening_night_wh = 0.0
    block_totals_watts = {block: 0.0 for block in TIME_BLOCKS}

    for row in appliances:
        watts = APPLIANCE_LOADS_WATTS[row["key"]]
        qty = row["quantity"]
        running_watts = watts * qty

        for block, hrs in row["hours"].items():
            total_daily_wh += running_watts * hrs
            if block in NIGHT_BLOCKS:
                evening_night_wh += running_watts * hrs
            # Peak load: an appliance counts toward a block's peak if it
            # runs *any* hours in that block, since within that window it
            # could plausibly overlap with everything else tagged to the
            # same block. This is deliberately the worst case within a
            # block, not across the whole day.
            if hrs > 0:
                block_totals_watts[block] += running_watts

    daytime_wh = total_daily_wh - evening_night_wh
    peak_block = max(block_totals_watts, key=block_totals_watts.get)
    peak_block_watts = block_totals_watts[peak_block]

    recommended_va = peak_block_watts * INVERTER_SURGE_FACTOR
    recommended_kva = max(recommended_va / 1000, 0.5)

    raw_battery_wh = evening_night_wh * autonomy_days
    dod = DEPTH_OF_DISCHARGE[battery_type]
    battery_wh_required = raw_battery_wh / dod if dod else raw_battery_wh
    battery_kwh_required = battery_wh_required / 1000
    battery_ah_required = battery_wh_required / BATTERY_BANK_VOLTAGE

    panel_watts_required = total_daily_wh / (PEAK_SUN_HOURS * SYSTEM_EFFICIENCY) if total_daily_wh else 0
    panel_count_suggested = max(2, int(-(-panel_watts_required // REFERENCE_PANEL_WATTS))) if panel_watts_required else 2

    return SizingResult(
        total_daily_wh=round(total_daily_wh, 1),
        evening_night_wh=round(evening_night_wh, 1),
        daytime_wh=round(daytime_wh, 1),
        peak_block=peak_block,
        peak_block_watts=round(peak_block_watts, 1),
        recommended_kva=round(recommended_kva, 1),
        battery_wh_required=round(battery_wh_required, 1),
        battery_kwh_required=round(battery_kwh_required, 2),
        battery_ah_required=round(battery_ah_required, 1),
        panel_watts_required=round(panel_watts_required, 1),
        panel_count_suggested=panel_count_suggested,
        autonomy_days=autonomy_days,
        battery_type=battery_type,
        block_totals_watts={k: round(v, 1) for k, v in block_totals_watts.items()},
    )


# ---------------------------------------------------------------------
# Step 8: match the result against the real package catalog
# ---------------------------------------------------------------------

_KVA_RE = re.compile(r"([\d.]+)\s*kVA", re.IGNORECASE)
_BATTERY_KWH_RE = re.compile(r"([\d.]+)\s*kWh", re.IGNORECASE)
_PANEL_SPEC_RE = re.compile(r"(\d+)\s*[x\u00d7]\s*(\d+)\s*W", re.IGNORECASE)


def _parse_kva(package):
    match = _KVA_RE.search(package.kva_rating or "")
    return float(match.group(1)) if match else None


def _parse_battery_kwh(package):
    # capacity_label looks like "3.2kVA - 2.5kWh"; tubular tiers often
    # omit the kWh half entirely, in which case this returns None and
    # that package is treated as "battery capacity unconfirmed" rather
    # than assumed to pass or fail the requirement.
    match = _BATTERY_KWH_RE.search(package.capacity_label or "")
    return float(match.group(1)) if match else None


def _parse_panel_watts(package):
    match = _PANEL_SPEC_RE.search(package.panel_spec or "")
    if not match:
        return None
    count, watts = int(match.group(1)), int(match.group(2))
    return count * watts


def _price_range(amount):
    if not amount:
        return None
    low = round(amount * (1 - PRICE_RANGE_SPREAD) / 10000) * 10000
    high = round(amount * (1 + PRICE_RANGE_SPREAD) / 10000) * 10000
    return {"low": int(low), "high": int(high)}


def _package_summary(package, result):
    price_source = package.price_with_panel_naira or package.price_without_panel_naira
    battery_kwh = _parse_battery_kwh(package)
    return {
        "id": package.id,
        "name": package.name,
        "slug": package.slug,
        "tagline": package.tagline,
        "kva_rating": package.kva_rating,
        "capacity_label": package.capacity_label,
        "battery_type": package.battery_type,
        "panel_spec": package.panel_spec,
        "includes": package.includes_list,
        "price_range": _price_range(price_source),
        "price_includes_panels": bool(package.price_with_panel_naira),
        "battery_capacity_unconfirmed": battery_kwh is None,
    }


def match_packages(result: SizingResult, packages):
    """
    packages: active Package rows (already filtered to is_active=True).
    Only compares against packages of the requested battery chemistry,
    since a lithium requirement can't fairly be met by a tubular tier
    or vice versa.

    Returns one of three shapes:
      {"type": "single",  "packages": [pkg]}
      {"type": "compare", "packages": [smaller_that_falls_short, best_fit]}
      {"type": "custom",  "packages": []}
    """
    same_chemistry = [p for p in packages if (p.battery_type or "").strip().lower() == result.battery_type]
    parsed = []
    for p in same_chemistry:
        kva = _parse_kva(p)
        if kva is None:
            continue  # can't evaluate a package with no readable kVA figure
        parsed.append({
            "package": p,
            "kva": kva,
            "battery_kwh": _parse_battery_kwh(p),
            "panel_watts": _parse_panel_watts(p),
        })
    parsed.sort(key=lambda row: row["kva"])

    def covers(row):
        if row["kva"] < result.recommended_kva:
            return False
        if row["battery_kwh"] is not None and row["battery_kwh"] < result.battery_kwh_required:
            return False
        if row["panel_watts"] is not None and row["panel_watts"] < result.panel_watts_required:
            return False
        return True

    covering = [row for row in parsed if covers(row)]

    if not covering:
        return {"type": "custom", "packages": []}

    best_fit = covering[0]
    idx = parsed.index(best_fit)

    if idx > 0:
        neighbor = parsed[idx - 1]
        return {
            "type": "compare",
            "packages": [
                _package_summary(neighbor["package"], result),
                _package_summary(best_fit["package"], result),
            ],
        }

    return {"type": "single", "packages": [_package_summary(best_fit["package"], result)]}


# ---------------------------------------------------------------------
# Human-readable summary, reused for both the lead record and the
# WhatsApp deep link the frontend builds.
# ---------------------------------------------------------------------

def build_summary_text(result: SizingResult, match):
    lines = [
        f"Solar sizing estimate from the website calculator:",
        f"- Inverter: ~{result.recommended_kva:g}kVA",
        f"- Battery: ~{result.battery_kwh_required:g}kWh ({result.battery_type}, {result.autonomy_days}-day autonomy)",
        f"- Panels: ~{result.panel_watts_required:g}W ({result.panel_count_suggested}x {REFERENCE_PANEL_WATTS}W)",
        f"- Daily use: {result.total_daily_wh/1000:.1f}kWh, evening/night: {result.evening_night_wh/1000:.1f}kWh",
    ]
    if match["type"] == "single":
        pkg = match["packages"][0]
        pr = pkg["price_range"]
        price_txt = f"₦{pr['low']:,}-₦{pr['high']:,}" if pr else "request quote"
        lines.append(f"Closest package: {pkg['name']} ({price_txt})")
    elif match["type"] == "compare":
        names = " / ".join(p["name"] for p in match["packages"])
        lines.append(f"Between two packages: {names}")
    else:
        lines.append("This needs a custom-engineered system beyond our standard packages.")
    return "\n".join(lines)
