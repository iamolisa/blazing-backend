from extensions import db


class ServiceItem(db.Model):
    __tablename__ = "service_items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    summary = db.Column(db.String(240))
    description = db.Column(db.Text)
    icon = db.Column(db.String(60), default="bolt")
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<ServiceItem {self.title}>"

    def to_dict(self, include_description=False):
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "summary": self.summary,
            "icon": self.icon,
            "order": self.order,
            "is_active": self.is_active,
        }
        if include_description:
            data["description"] = self.description
        return data
