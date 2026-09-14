from extensions import db


class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), nullable=False)
    client_role = db.Column(db.String(160))  # e.g. "Facility Manager, Lekki"
    quote = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)
    is_featured = db.Column(db.Boolean, default=False)

    # Provenance + moderation, so new submissions (via a future public form)
    # land as "pending" and only show on the site once approved from the
    # admin dashboard. Existing Google reviews are seeded as "approved".
    source = db.Column(db.String(60), default="Website")  # "Google Review" | "Website"
    reviewer_meta = db.Column(db.String(160))  # e.g. "Local Guide · 32 reviews · 3 photos"
    review_date_label = db.Column(db.String(60))  # e.g. "6 months ago" (as given by the source)
    sort_rank = db.Column(db.Integer, default=0)  # lower = newer; controls display order
    owner_reply = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="approved")  # "pending" | "approved"

    def __repr__(self):
        return f"<Testimonial {self.client_name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "client_name": self.client_name,
            "client_role": self.client_role,
            "quote": self.quote,
            "rating": self.rating,
            "is_featured": self.is_featured,
            "source": self.source,
            "reviewer_meta": self.reviewer_meta,
            "review_date_label": self.review_date_label,
            "owner_reply": self.owner_reply,
            "status": self.status,
        }
