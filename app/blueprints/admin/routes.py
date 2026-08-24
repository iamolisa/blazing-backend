from flask import Blueprint, jsonify, request, g, current_app
from extensions import db, limiter
from app.models import User, Product, Category, Lead, Testimonial
from app.core.catalog import get_dashboard_stats
from app.core.auth import token_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/login", methods=["POST"])
@limiter.limit("8 per minute")
def login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        current_app.logger.warning(f"Failed admin login attempt for email: {email}")
        return jsonify({"ok": False, "error": "invalid_credentials", "message": "Invalid email or password."}), 401

    token = user.generate_api_token()
    db.session.commit()
    current_app.logger.info(f"Admin login: {user.email}")
    return jsonify({"ok": True, "token": token, "user": user.to_dict()})


@admin_bp.route("/logout", methods=["POST"])
@token_required
def logout():
    email = g.current_user.email
    g.current_user.api_token = None
    g.current_user.token_expires_at = None
    db.session.commit()
    current_app.logger.info(f"Admin logout: {email}")
    return jsonify({"ok": True, "message": "Signed out."})


@admin_bp.route("/me/password", methods=["PATCH", "POST"])
@token_required
def change_password():
    data = request.get_json(silent=True) or request.form
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not g.current_user.check_password(current_password):
        current_app.logger.warning(f"Failed password-change attempt (wrong current password): {g.current_user.email}")
        return jsonify({"ok": False, "error": "invalid_credentials", "message": "Current password is incorrect."}), 401

    if len(new_password) < 10:
        return jsonify({
            "ok": False, "error": "validation",
            "message": "New password must be at least 10 characters.",
        }), 422

    g.current_user.set_password(new_password)  # also clears the token, see User.set_password
    db.session.commit()

    # Issue a fresh token so the admin isn't logged out mid-session after
    # changing their own password, while any other leaked/old token is
    # now dead.
    token = g.current_user.generate_api_token()
    db.session.commit()
    current_app.logger.info(f"Password changed: {g.current_user.email}")
    return jsonify({"ok": True, "message": "Password updated.", "token": token})


@admin_bp.route("/me")
@token_required
def me():
    return jsonify({"ok": True, "user": g.current_user.to_dict()})


@admin_bp.route("/dashboard")
@token_required
def dashboard():
    recent_leads = Lead.query.order_by(Lead.created_at.desc()).limit(8).all()
    return jsonify({
        "ok": True,
        "stats": get_dashboard_stats(),
        "recent_leads": [l.to_dict() for l in recent_leads],
    })


@admin_bp.route("/products")
@token_required
def products():
    items = Product.query.order_by(Product.id.desc()).all()
    return jsonify({"ok": True, "products": [p.to_dict(include_description=True) for p in items]})


def _apply_product_form(product, form):
    product.name = form["name"]
    product.slug = form["slug"]
    product.short_description = form.get("short_description")
    product.description = form.get("description")
    product.spec_summary = form.get("spec_summary")
    product.price_naira = int(form["price_naira"]) if form.get("price_naira") else None
    product.image_url = form.get("image_url") or None
    product.is_featured = bool(form.get("is_featured"))
    product.category_id = form.get("category_id") or None


@admin_bp.route("/products", methods=["POST"])
@token_required
def product_new():
    form = request.get_json(silent=True) or request.form
    if not form.get("name") or not form.get("slug"):
        return jsonify({"ok": False, "error": "validation", "message": "name and slug are required."}), 400

    product = Product(is_active=True)
    _apply_product_form(product, form)
    db.session.add(product)
    db.session.commit()
    current_app.logger.info(f"Product created: '{product.name}' (id={product.id}) by {g.current_user.email}")
    return jsonify({"ok": True, "product": product.to_dict(include_description=True)}), 201


@admin_bp.route("/products/<int:product_id>", methods=["PUT", "PATCH"])
@token_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    form = request.get_json(silent=True) or request.form
    _apply_product_form(product, form)
    if "is_active" in form:
        product.is_active = bool(form.get("is_active"))
    db.session.commit()
    current_app.logger.info(f"Product updated: '{product.name}' (id={product.id}) by {g.current_user.email}")
    return jsonify({"ok": True, "product": product.to_dict(include_description=True)})


@admin_bp.route("/products/<int:product_id>", methods=["DELETE"])
@token_required
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    current_app.logger.info(f"Product deleted: '{name}' (id={product_id}) by {g.current_user.email}")
    return jsonify({"ok": True, "message": "Product deleted."})


@admin_bp.route("/categories")
@token_required
def categories():
    items = Category.query.filter_by(kind="product").order_by(Category.name.asc()).all()
    return jsonify({"ok": True, "categories": [c.to_dict() for c in items]})


@admin_bp.route("/leads")
@token_required
def leads():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 25)), 1), 100)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "validation", "message": "page and per_page must be numbers."}), 400

    query = Lead.query.order_by(Lead.created_at.desc())
    status = request.args.get("status")
    if status:
        query = query.filter(Lead.status == status)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "ok": True,
        "leads": [l.to_dict() for l in paginated.items],
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "total_pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    })


@admin_bp.route("/leads/<int:lead_id>/status", methods=["PATCH", "POST"])
@token_required
def lead_status(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    data = request.get_json(silent=True) or request.form
    old_status = lead.status
    lead.status = data.get("status", lead.status)
    db.session.commit()
    current_app.logger.info(f"Lead #{lead_id} status: {old_status} -> {lead.status} by {g.current_user.email}")
    return jsonify({"ok": True, "lead": lead.to_dict()})


@admin_bp.route("/leads/<int:lead_id>", methods=["DELETE"])
@token_required
def lead_delete(lead_id):
    """
    Deletes a lead's personal data entirely. This is what actually
    fulfills a data-deletion request under the Privacy Policy (see
    privacy.html "Your rights under the NDPA"). Before this endpoint
    existed, honoring that request meant a manual database edit with no
    audit trail; this gives it a real, logged path.
    """
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    current_app.logger.info(f"Lead #{lead_id} deleted by {g.current_user.email}")
    return jsonify({"ok": True, "message": "Lead deleted."})


@admin_bp.route("/testimonials")
@token_required
def testimonials():
    """All testimonials (pending + approved), newest-first by sort_rank
    then id, so newly-submitted ones surface at the top for review."""
    items = Testimonial.query.order_by(Testimonial.sort_rank.asc(), Testimonial.id.desc()).all()
    return jsonify({"ok": True, "testimonials": [t.to_dict() for t in items]})


@admin_bp.route("/testimonials", methods=["POST"])
@token_required
def testimonial_new():
    form = request.get_json(silent=True) or request.form
    if not form.get("client_name") or not form.get("quote"):
        return jsonify({"ok": False, "error": "validation", "message": "client_name and quote are required."}), 400
    try:
        rating = max(1, min(int(form.get("rating", 5) or 5), 5))
    except (TypeError, ValueError):
        rating = 5
    testimonial = Testimonial(
        client_name=form["client_name"],
        client_role=form.get("client_role"),
        quote=form["quote"],
        rating=rating,
        source=form.get("source", "Website"),
        status=form.get("status", "approved"),
        is_featured=bool(form.get("is_featured")),
    )
    db.session.add(testimonial)
    db.session.commit()
    current_app.logger.info(f"Testimonial created: '{testimonial.client_name}' (id={testimonial.id}) by {g.current_user.email}")
    return jsonify({"ok": True, "testimonial": testimonial.to_dict()}), 201


@admin_bp.route("/testimonials/<int:testimonial_id>", methods=["PUT", "PATCH"])
@token_required
def testimonial_edit(testimonial_id):
    """Handles approve/reject (status), writing or editing an owner reply,
    toggling featured, and general edits, all through one endpoint since
    the admin UI does all of this from a single row."""
    testimonial = Testimonial.query.get_or_404(testimonial_id)
    form = request.get_json(silent=True) or request.form
    old_status = testimonial.status
    for field in ("client_name", "client_role", "quote", "status", "owner_reply"):
        if field in form:
            setattr(testimonial, field, form[field])
    if "rating" in form:
        try:
            testimonial.rating = max(1, min(int(form["rating"]), 5))
        except (TypeError, ValueError):
            pass
    if "is_featured" in form:
        testimonial.is_featured = bool(form["is_featured"])
    db.session.commit()
    if "status" in form and form["status"] != old_status:
        current_app.logger.info(f"Testimonial #{testimonial_id} status: {old_status} -> {testimonial.status} by {g.current_user.email}")
    return jsonify({"ok": True, "testimonial": testimonial.to_dict()})


@admin_bp.route("/testimonials/<int:testimonial_id>", methods=["DELETE"])
@token_required
def testimonial_delete(testimonial_id):
    testimonial = Testimonial.query.get_or_404(testimonial_id)
    name = testimonial.client_name
    db.session.delete(testimonial)
    db.session.commit()
    current_app.logger.info(f"Testimonial deleted: '{name}' (id={testimonial_id}) by {g.current_user.email}")
    return jsonify({"ok": True, "message": "Testimonial deleted."})
