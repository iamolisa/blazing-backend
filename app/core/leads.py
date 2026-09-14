"""
Business logic for turning a submitted form into a stored Lead.
Isolated from routes so the same logic can be reused by the contact
form, the quote request form, and the sizing/energy tools.
"""
from extensions import db
from app.models import Lead


def create_lead(form_data, source="contact_form"):
    lead = Lead(
        full_name=form_data.get("full_name", "").strip(),
        email=form_data.get("email", "").strip() or None,
        phone=form_data.get("phone", "").strip(),
        city=form_data.get("city", "").strip() or None,
        interest=form_data.get("interest", "").strip() or None,
        message=form_data.get("message", "").strip() or None,
        source=source,
    )
    db.session.add(lead)
    db.session.commit()
    return lead
