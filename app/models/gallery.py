from datetime import datetime
from extensions import db


class GalleryItem(db.Model):
    __tablename__ = "gallery_items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(60), default="solar")  # solar | panels | plc | backup
    location = db.Column(db.String(120))
    image_url = db.Column(db.String(400))
    kva_rating = db.Column(db.String(40))
    is_featured = db.Column(db.Boolean, default=False)
    # Detail-page copy: a short sell paragraph plus newline-separated
    # highlight bullets (same "\n".split() convention as Package.includes).
    description = db.Column(db.Text)
    highlights = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<GalleryItem {self.title}>"

    def to_dict(self, include_description=False):
        data = {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "location": self.location,
            "image_url": self.image_url,
            "kva_rating": self.kva_rating,
            "is_featured": self.is_featured,
        }
        if include_description:
            data["description"] = self.description
            data["highlights"] = [h for h in (self.highlights or "").split("\n") if h]
        return data
