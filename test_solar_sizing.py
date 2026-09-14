"""
Tests for the time-of-day solar sizing calculator.
Run with: pytest test_solar_sizing.py -v
"""
import json
import pytest
from app import create_app
from app.core.solar_sizing import (
    calculate_solar_sizing,
    match_packages,
    SizingValidationError,
)


# ---- Pure calculation logic (no Flask/DB needed) --------------------------

def test_daytime_only_usage_needs_no_battery():
    appliances = [{"key": "fridge", "quantity": 1, "hours": {"morning": 6, "afternoon": 5, "evening": 0, "night": 0}}]
    result = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    assert result.evening_night_wh == 0
    assert result.battery_kwh_required == 0


def test_evening_and_night_usage_drives_battery_size():
    appliances = [{"key": "bulbs", "quantity": 4, "hours": {"morning": 0, "afternoon": 0, "evening": 4, "night": 8}}]
    result = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    # 4 bulbs x 15W x 12h = 720Wh, all of it evening/night
    assert result.evening_night_wh == 720
    assert result.total_daily_wh == 720


def test_lithium_needs_smaller_battery_than_tubular_for_same_load():
    appliances = [{"key": "fridge", "quantity": 1, "hours": {"morning": 0, "afternoon": 0, "evening": 4, "night": 9}}]
    lithium = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="lithium")
    tubular = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    assert lithium.battery_kwh_required < tubular.battery_kwh_required


def test_more_autonomy_days_scales_battery_linearly():
    appliances = [{"key": "fridge", "quantity": 1, "hours": {"morning": 0, "afternoon": 0, "evening": 4, "night": 9}}]
    one_day = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    two_day = calculate_solar_sizing(appliances, autonomy_days=2, battery_type="tubular")
    assert two_day.battery_kwh_required == pytest.approx(one_day.battery_kwh_required * 2, rel=0.01)


def test_peak_block_is_the_busiest_block_not_the_daily_sum():
    # Everything staggered into a different block -> peak load is just
    # the single biggest appliance, not the sum of all of them.
    appliances = [
        {"key": "iron", "quantity": 1, "hours": {"morning": 1, "afternoon": 0, "evening": 0, "night": 0}},
        {"key": "washing_machine", "quantity": 1, "hours": {"morning": 0, "afternoon": 1, "evening": 0, "night": 0}},
        {"key": "ac_1_5hp", "quantity": 1, "hours": {"morning": 0, "afternoon": 0, "evening": 4, "night": 0}},
    ]
    result = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    assert result.peak_block == "evening"
    assert result.peak_block_watts == 1200  # just the AC, not iron+washer+AC combined


def test_rejects_hours_outside_block_duration():
    with pytest.raises(SizingValidationError):
        calculate_solar_sizing(
            [{"key": "fridge", "quantity": 1, "hours": {"morning": 8}}],  # morning caps at 6
            autonomy_days=1, battery_type="tubular",
        )


def test_rejects_unknown_appliance():
    with pytest.raises(SizingValidationError):
        calculate_solar_sizing(
            [{"key": "space_heater", "quantity": 1, "hours": {"morning": 1}}],
            autonomy_days=1, battery_type="tubular",
        )


def test_rejects_bad_autonomy_days():
    with pytest.raises(SizingValidationError):
        calculate_solar_sizing(
            [{"key": "fridge", "quantity": 1, "hours": {"morning": 1}}],
            autonomy_days=4, battery_type="tubular",
        )


def test_empty_appliance_list_is_rejected():
    with pytest.raises(SizingValidationError):
        calculate_solar_sizing([], autonomy_days=1, battery_type="tubular")


# ---- Package matching -------------------------------------------------

class _FakePackage:
    def __init__(self, name, kva_rating, capacity_label, battery_type,
                 price_with_panel_naira, price_without_panel_naira, panel_spec):
        self.id = name
        self.name = name
        self.slug = name.lower().replace(" ", "-")
        self.tagline = ""
        self.kva_rating = kva_rating
        self.capacity_label = capacity_label
        self.battery_type = battery_type
        self.price_with_panel_naira = price_with_panel_naira
        self.price_without_panel_naira = price_without_panel_naira
        self.panel_spec = panel_spec
        self.includes = "Inverter\nBattery"

    @property
    def includes_list(self):
        return self.includes.split("\n")


TUBULAR_CATALOG = [
    _FakePackage("2.5kVA Tubular", "2.5kVA", "2.5kVA", "Tubular", 1510000, 900000, "4x 330W solar panels"),
    _FakePackage("3.2kVA Tubular", "3.2kVA", "3.2kVA", "Tubular", 1580000, 1000000, "4x 330W solar panels"),
    _FakePackage("4.2kVA Tubular", "4.2kVA", "4.2kVA", "Tubular", 1680000, 1080000, "4x 330W solar panels"),
    _FakePackage("5kVA Tubular", "5kVA", "5kVA", "Tubular", 2650000, 1900000, "5x 600W solar panels"),
]


def test_match_returns_single_when_smallest_tier_already_covers():
    appliances = [{"key": "bulbs", "quantity": 2, "hours": {"morning": 0, "afternoon": 0, "evening": 2, "night": 2}}]
    result = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    match = match_packages(result, TUBULAR_CATALOG)
    assert match["type"] == "single"
    assert match["packages"][0]["name"] == "2.5kVA Tubular"


def test_match_returns_compare_between_two_neighboring_tiers():
    # 3.0kVA required: more than the 2.5kVA tier covers, comfortably
    # within the 3.2kVA tier.
    appliances = [
        {"key": "ac_1hp", "quantity": 2, "hours": {"morning": 0, "afternoon": 0, "evening": 1, "night": 0}},
        {"key": "washing_machine", "quantity": 1, "hours": {"morning": 0, "afternoon": 0, "evening": 1, "night": 0}},
    ]
    result = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    match = match_packages(result, TUBULAR_CATALOG)
    assert match["type"] == "compare"
    assert len(match["packages"]) == 2


def test_match_returns_custom_when_nothing_covers_it():
    appliances = [{"key": "ac_1_5hp", "quantity": 6, "hours": {"morning": 5, "afternoon": 5, "evening": 4, "night": 9}}]
    result = calculate_solar_sizing(appliances, autonomy_days=3, battery_type="tubular")
    match = match_packages(result, TUBULAR_CATALOG)
    assert match["type"] == "custom"
    assert match["packages"] == []


def test_price_range_is_a_spread_not_the_raw_price():
    appliances = [{"key": "bulbs", "quantity": 2, "hours": {"morning": 0, "afternoon": 0, "evening": 2, "night": 2}}]
    result = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    match = match_packages(result, TUBULAR_CATALOG)
    price_range = match["packages"][0]["price_range"]
    assert price_range["low"] < 1510000 < price_range["high"]


def test_tubular_package_with_no_kwh_figure_is_flagged_unconfirmed():
    appliances = [{"key": "bulbs", "quantity": 2, "hours": {"morning": 0, "afternoon": 0, "evening": 2, "night": 2}}]
    result = calculate_solar_sizing(appliances, autonomy_days=1, battery_type="tubular")
    match = match_packages(result, TUBULAR_CATALOG)
    assert match["packages"][0]["battery_capacity_unconfirmed"] is True


# ---- Endpoint (uses the real seeded DB via the app factory) ---------------

@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_solar_sizing_endpoint_happy_path(client):
    payload = {
        "appliances": [
            {"key": "fridge", "quantity": 1, "hours": {"morning": 6, "afternoon": 5, "evening": 4, "night": 9}},
            {"key": "bulbs", "quantity": 4, "hours": {"morning": 0, "afternoon": 0, "evening": 4, "night": 6}},
        ],
        "autonomy_days": 1,
        "battery_type": "tubular",
    }
    resp = client.post("/api/tools/solar-sizing", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["ok"] is True
    assert body["match"]["type"] in ("single", "compare", "custom")
    assert "recommended_kva" in body["result"]


def test_solar_sizing_endpoint_rejects_bad_input(client):
    resp = client.post("/api/tools/solar-sizing", data=json.dumps({"appliances": []}), content_type="application/json")
    assert resp.status_code == 422
    body = json.loads(resp.data)
    assert body["ok"] is False
