from extensions import db


class Package(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    tagline = db.Column(db.String(200))
    kva_rating = db.Column(db.String(40))  # e.g. "3.2kVA"
    capacity_label = db.Column(db.String(60))  # e.g. "3.2kVA · 2.5kWh"
    battery_type = db.Column(db.String(40))  # "Lithium" | "Tubular"

    # Client prices systems two ways: inverter+battery only, or bundled
    # with solar panels. The frontend renders a toggle to switch between
    # these instantly rather than showing two separate cards per system.
    price_with_panel_naira = db.Column(db.Integer, nullable=True)
    price_without_panel_naira = db.Column(db.Integer, nullable=True)
    panel_spec = db.Column(db.String(120), nullable=True)  # e.g. "4× 330W solar panels"

    includes = db.Column(db.Text)  # newline-separated list, rendered in template
    best_for = db.Column(db.String(160))
    is_popular = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)

    @property
    def includes_list(self):
        return [line.strip() for line in (self.includes or "").split("\n") if line.strip()]

    def _format(self, amount):
        if amount:
            return f"₦{amount:,.0f}".replace(".0", "")
        return "Request quote"

    @property
    def formatted_price_with_panel(self):
        return self._format(self.price_with_panel_naira)

    @property
    def formatted_price_without_panel(self):
        return self._format(self.price_without_panel_naira)

    def __repr__(self):
        return f"<Package {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "tagline": self.tagline,
            "kva_rating": self.kva_rating,
            "capacity_label": self.capacity_label,
            "battery_type": self.battery_type,
            "price_with_panel_naira": self.price_with_panel_naira,
            "price_without_panel_naira": self.price_without_panel_naira,
            "formatted_price_with_panel": self.formatted_price_with_panel,
            "formatted_price_without_panel": self.formatted_price_without_panel,
            "panel_spec": self.panel_spec,
            "includes": self.includes_list,
            "best_for": self.best_for,
            "is_popular": self.is_popular,
            "is_active": self.is_active,
            "order": self.order,
        }
