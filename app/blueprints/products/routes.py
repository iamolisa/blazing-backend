from flask import Blueprint, jsonify, request, abort
from app.core.catalog import get_active_products, get_product_categories
from app.models import Product

products_bp = Blueprint("products", __name__)


@products_bp.route("/")
def index():
    category_slug = request.args.get("category")
    search = request.args.get("q")
    products = get_active_products(category_slug=category_slug, search=search)
    return jsonify({
        "ok": True,
        "products": [p.to_dict() for p in products],
        "categories": [c.to_dict() for c in get_product_categories()],
        "active_category": category_slug,
        "search_query": search or "",
    })


@products_bp.route("/<slug>")
def detail(slug):
    product = Product.query.filter_by(slug=slug, is_active=True).first()
    if not product:
        abort(404)
    return jsonify({"ok": True, "product": product.to_dict(include_description=True)})
