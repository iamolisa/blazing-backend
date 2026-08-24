"""
End-to-end smoke tests for the JSON API. Run with:  pytest test_api.py -v
Uses the seeded dev sqlite db (run `python seed.py` first) so real data
is exercised, matching what the frontend will actually see.
"""
import json
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def get_json(resp):
    return json.loads(resp.data)


# ---- Public read endpoints -------------------------------------------------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = get_json(r)
    assert body["ok"] is True
    assert body["database"] == "healthy"


def test_business_info(client):
    r = client.get("/api/business")
    assert r.status_code == 200
    data = get_json(r)
    assert data["ok"] is True
    assert data["business_name"] == "Blazing Trail Engineering"
    assert "business_whatsapp" in data


def test_home(client):
    r = client.get("/api/home")
    assert r.status_code == 200
    data = get_json(r)
    assert data["ok"] is True
    for key in ["featured_products", "services", "packages", "testimonials", "gallery_items"]:
        assert key in data
        assert isinstance(data[key], list)


def test_services_index_and_detail(client):
    r = client.get("/api/services/")
    assert r.status_code == 200
    services = get_json(r)["services"]
    assert len(services) > 0
    slug = services[0]["slug"]

    r2 = client.get(f"/api/services/{slug}")
    assert r2.status_code == 200
    detail = get_json(r2)
    assert detail["service"]["slug"] == slug
    assert "description" in detail["service"]
    assert "related" in detail

    r3 = client.get("/api/services/does-not-exist")
    assert r3.status_code == 404


def test_products_index_filter_and_detail(client):
    r = client.get("/api/products/")
    assert r.status_code == 200
    body = get_json(r)
    assert len(body["products"]) > 0
    assert len(body["categories"]) > 0
    slug = body["products"][0]["slug"]
    cat_slug = body["categories"][0]["slug"]

    r2 = client.get(f"/api/products/?category={cat_slug}")
    assert r2.status_code == 200
    filtered = get_json(r2)["products"]
    assert all(p["category"]["slug"] == cat_slug for p in filtered)

    r3 = client.get("/api/products/?q=solar")
    assert r3.status_code == 200

    r4 = client.get(f"/api/products/{slug}")
    assert r4.status_code == 200
    assert get_json(r4)["product"]["slug"] == slug

    r5 = client.get("/api/products/not-a-real-slug")
    assert r5.status_code == 404


def test_packages(client):
    r = client.get("/api/packages/")
    assert r.status_code == 200
    packages = get_json(r)["packages"]
    assert len(packages) > 0
    assert "formatted_price_with_panel" in packages[0]
    assert "formatted_price_without_panel" in packages[0]
    assert "includes" in packages[0]


def test_gallery(client):
    r = client.get("/api/gallery/")
    assert r.status_code == 200
    assert "items" in get_json(r)

    r2 = client.get("/api/gallery/?category=solar")
    assert r2.status_code == 200
    body = get_json(r2)
    assert all(i["category"] == "solar" for i in body["items"])


def test_testimonials(client):
    r = client.get("/api/testimonials/")
    assert r.status_code == 200
    assert "testimonials" in get_json(r)


def test_tools_index(client):
    r = client.get("/api/tools/")
    assert r.status_code == 200
    loads = get_json(r)["appliance_loads"]
    assert loads["fridge"] == 150


def test_tools_sizing_result_creates_lead(client):
    r = client.post("/api/tools/sizing-result", json={
        "full_name": "Test Visitor",
        "phone": "08000000000",
        "estimated_kva": "5kVA",
    })
    assert r.status_code == 201
    body = get_json(r)
    assert body["ok"] is True
    assert "lead_id" in body


def test_financing_advice_without_api_key_returns_clean_503(client):
    # No GROQ_API_KEY is set in the test/dev environment. This must
    # fail cleanly (503 + explanatory message), never a 500/stack trace.
    r = client.post("/api/tools/financing-advice", json={"message": "I want a 5kVA system over 6 months"})
    assert r.status_code == 503
    body = get_json(r)
    assert body["ok"] is False
    assert body["error"] == "advisor_unavailable"


def test_financing_advice_empty_message_is_rejected(client):
    r = client.post("/api/tools/financing-advice", json={"message": ""})
    assert r.status_code == 400
    assert get_json(r)["ok"] is False


def test_financing_advice_honeypot_short_circuits(client):
    r = client.post("/api/tools/financing-advice", json={"message": "test", "website": "http://spam.example"})
    assert r.status_code == 200
    body = get_json(r)
    assert body["ok"] is True
    assert body["reply"] is None


def test_financing_prompt_only_uses_real_package_data():
    """The advisor must never be able to invent a price. The prompt it
    sends to the model can only contain figures pulled from the DB."""
    from app.core.financing_ai import _format_packages_for_prompt

    class FakePackage:
        name = "Test 3kVA System"
        kva_rating = "3kVA"
        battery_type = "Lithium"
        price_with_panel_naira = 1_500_000
        price_without_panel_naira = 900_000

    prompt_fragment = _format_packages_for_prompt([FakePackage()])
    assert "1,500,000" in prompt_fragment
    assert "900,000" in prompt_fragment
    assert "Test 3kVA System" in prompt_fragment


# ---- Contact / quote forms --------------------------------------------------

def test_contact_form_valid(client):
    r = client.post("/api/contact/", json={
        "full_name": "Jane Doe",
        "phone": "08011112222",
        "email": "jane@example.com",
        "message": "Interested in solar for my shop.",
    })
    assert r.status_code == 201
    assert get_json(r)["ok"] is True


def test_contact_form_missing_fields(client):
    r = client.post("/api/contact/", json={"full_name": ""})
    assert r.status_code == 400
    body = get_json(r)
    assert body["ok"] is False
    assert "full_name" in body["errors"]
    assert "phone" in body["errors"]


def test_quote_form_valid(client):
    r = client.post("/api/contact/quote", json={
        "full_name": "Chidi Okafor",
        "phone": "08033334444",
        "interest": "3.5kVA package",
    })
    assert r.status_code == 201


# ---- Admin: auth + CRUD -----------------------------------------------------

def test_admin_login_wrong_password(client):
    r = client.post("/api/admin/login", json={
        "email": "admin@blazingtrailengineering.com",
        "password": "wrong",
    })
    assert r.status_code == 401


def test_admin_requires_token(client):
    r = client.get("/api/admin/dashboard")
    assert r.status_code == 401

    r2 = client.get("/api/admin/dashboard", headers={"Authorization": "Bearer not-a-real-token"})
    assert r2.status_code == 401


def test_admin_full_flow(client):
    # Login
    r = client.post("/api/admin/login", json={
        "email": "admin@blazingtrailengineering.com",
        "password": "ChangeMe123!",
    })
    assert r.status_code == 200
    token = get_json(r)["token"]
    assert token
    headers = {"Authorization": f"Bearer {token}"}

    # /me
    r_me = client.get("/api/admin/me", headers=headers)
    assert r_me.status_code == 200
    assert get_json(r_me)["user"]["email"] == "admin@blazingtrailengineering.com"

    # Dashboard
    r_dash = client.get("/api/admin/dashboard", headers=headers)
    assert r_dash.status_code == 200
    stats = get_json(r_dash)["stats"]
    assert "products" in stats

    # Categories (for the product form dropdown)
    r_cats = client.get("/api/admin/categories", headers=headers)
    assert r_cats.status_code == 200
    cat_id = get_json(r_cats)["categories"][0]["id"]

    # Create product
    r_create = client.post("/api/admin/products", headers=headers, json={
        "name": "Test Panel 400W",
        "slug": "test-panel-400w",
        "short_description": "A test panel.",
        "price_naira": 150000,
        "category_id": cat_id,
        "is_featured": True,
    })
    assert r_create.status_code == 201
    new_product = get_json(r_create)["product"]
    assert new_product["slug"] == "test-panel-400w"
    product_id = new_product["id"]

    # It should now show up in the public products list
    r_public = client.get("/api/products/test-panel-400w")
    assert r_public.status_code == 200

    # Edit product
    r_edit = client.put(f"/api/admin/products/{product_id}", headers=headers, json={
        "name": "Test Panel 450W",
        "slug": "test-panel-400w",
        "price_naira": 160000,
        "is_active": True,
    })
    assert r_edit.status_code == 200
    assert get_json(r_edit)["product"]["name"] == "Test Panel 450W"

    # Leads list
    r_leads = client.get("/api/admin/leads", headers=headers)
    assert r_leads.status_code == 200
    leads = get_json(r_leads)["leads"]
    assert len(leads) > 0
    lead_id = leads[0]["id"]

    # Update lead status
    r_status = client.patch(f"/api/admin/leads/{lead_id}/status", headers=headers, json={"status": "contacted"})
    assert r_status.status_code == 200
    assert get_json(r_status)["lead"]["status"] == "contacted"

    # Delete the lead (fulfills the NDPA deletion right promised in privacy.html)
    r_lead_delete = client.delete(f"/api/admin/leads/{lead_id}", headers=headers)
    assert r_lead_delete.status_code == 200
    r_leads_after = client.get("/api/admin/leads?per_page=100", headers=headers)
    remaining_ids = [l["id"] for l in get_json(r_leads_after)["leads"]]
    assert lead_id not in remaining_ids

    # Delete product
    r_delete = client.delete(f"/api/admin/products/{product_id}", headers=headers)
    assert r_delete.status_code == 200

    r_gone = client.get("/api/products/test-panel-400w")
    assert r_gone.status_code == 404

    # Logout invalidates the token
    r_logout = client.post("/api/admin/logout", headers=headers)
    assert r_logout.status_code == 200

    r_after_logout = client.get("/api/admin/dashboard", headers=headers)
    assert r_after_logout.status_code == 401


# ---- Error handlers ----------------------------------------------------------

def test_404_json(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    body = get_json(r)
    assert body["ok"] is False


def test_cors_header_present(client):
    r = client.get("/api/business", headers={"Origin": "https://blazingtrailengineering.com"})
    assert r.status_code == 200
    assert "Access-Control-Allow-Origin" in r.headers
