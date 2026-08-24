"""
Service layer: query helpers shared by blueprints. Keeping this logic out
of routes.py makes it reusable (e.g. by the admin blueprint and, later,
a JSON API) and easier to unit test in isolation from Flask request context.
"""
from app.models import Product, Category, ServiceItem, Package, GalleryItem, Testimonial


def get_featured_products(limit=6):
    return (
        Product.query.filter_by(is_active=True, is_featured=True)
        .order_by(Product.id.desc())
        .limit(limit)
        .all()
    )


def get_active_products(category_slug=None, search=None):
    query = Product.query.filter_by(is_active=True)
    if category_slug:
        query = query.join(Category).filter(Category.slug == category_slug)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    return query.order_by(Product.name.asc()).all()


def get_product_categories():
    return Category.query.filter_by(kind="product").order_by(Category.name.asc()).all()


def get_active_services(limit=None):
    query = ServiceItem.query.filter_by(is_active=True).order_by(ServiceItem.order.asc())
    return query.limit(limit).all() if limit else query.all()


def get_active_packages():
    return Package.query.filter_by(is_active=True).order_by(Package.order.asc()).all()


def get_gallery_items(category=None):
    query = GalleryItem.query
    if category and category != "all":
        query = query.filter_by(category=category)
    return query.order_by(GalleryItem.created_at.desc()).all()


def get_gallery_item(item_id):
    return GalleryItem.query.get(item_id)


def get_related_gallery_items(item, limit=3):
    return (
        GalleryItem.query.filter(GalleryItem.category == item.category, GalleryItem.id != item.id)
        .order_by(GalleryItem.created_at.desc())
        .limit(limit)
        .all()
    )


def get_featured_testimonials(limit=6):
    approved = Testimonial.query.filter_by(status="approved")
    featured = approved.filter_by(is_featured=True).order_by(Testimonial.sort_rank.asc()).limit(limit).all()
    return featured or approved.order_by(Testimonial.sort_rank.asc()).limit(limit).all()


def get_approved_testimonials():
    return Testimonial.query.filter_by(status="approved").order_by(Testimonial.sort_rank.asc()).all()


def get_dashboard_stats():
    return {
        "products": Product.query.count(),
        "services": ServiceItem.query.count(),
        "packages": Package.query.count(),
        "gallery": GalleryItem.query.count(),
        "testimonials": Testimonial.query.count(),
        "pending_testimonials": Testimonial.query.filter_by(status="pending").count(),
    }
