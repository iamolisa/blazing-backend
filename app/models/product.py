from datetime import datetime
from extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    kind = db.Column(db.String(20), nullable=False, default="product")  # product | service
    icon = db.Column(db.String(60), default="bolt")

    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "kind": self.kind,
            "icon": self.icon,
        }


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    short_description = db.Column(db.String(240))
    description = db.Column(db.Text)
    spec_summary = db.Column(db.String(120))  # e.g. "5.5kVA / 48V"
    image_url = db.Column(db.String(400))
    price_naira = db.Column(db.Integer, nullable=True)  # null = "request quote"
    is_featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Product {self.name}>"

    @property
    def formatted_price(self):
        if self.price_naira:
            return f"₦{self.price_naira:,.0f}".replace(".0", "")
        return "Request quote"

    def to_dict(self, include_description=False):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "short_description": self.short_description,
            "spec_summary": self.spec_summary,
            "image_url": self.image_url,
            "price_naira": self.price_naira,
            "formatted_price": self.formatted_price,
            "is_featured": self.is_featured,
            "is_active": self.is_active,
            "category": self.category.to_dict() if self.category else None,
            "category_id": self.category_id,
        }
        if include_description:
            data["description"] = self.description
        return data
