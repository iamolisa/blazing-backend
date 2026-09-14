from datetime import datetime
from extensions import db


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(160))
    phone = db.Column(db.String(40), nullable=False)
    city = db.Column(db.String(80))
    interest = db.Column(db.String(120))  # e.g. "Solar installation", "PLC automation"
    message = db.Column(db.Text)
    source = db.Column(db.String(60), default="contact_form")  # contact_form | quote_form | calculator
    status = db.Column(db.String(30), default="new")  # new | contacted | quoted | won | lost
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Lead {self.full_name} ({self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "city": self.city,
            "interest": self.interest,
            "message": self.message,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
