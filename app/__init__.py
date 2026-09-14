import os
from flask import Flask, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter.util import get_remote_address
from config import config_map
from extensions import db, cors, migrate, limiter, talisman
from app.logging_config import configure_logging


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_CONFIG", "development")

    config_class = config_map[config_name]
    if hasattr(config_class, "validate"):
        config_class.validate()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Render (like most PaaS) terminates TLS at a reverse proxy and talks
    # to gunicorn over plain HTTP, setting X-Forwarded-Proto/-For. Without
    # this, Flask/Talisman think every request is insecure and either
    # loop-redirect or misreport scheme in generated URLs.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Security headers. This is a JSON-only API (no HTML/JS/CSS served
    # from here), so the CSP can be maximally strict. There's nothing on
    # this origin that should ever load a script, style, or frame.
    talisman.init_app(
        app,
        force_https=config_name == "production",
        strict_transport_security=config_name == "production",
        content_security_policy={
            "default-src": "'none'",
            "frame-ancestors": "'none'",
        },
        frame_options="DENY",
        referrer_policy="strict-origin-when-cross-origin",
        session_cookie_secure=config_name == "production",
    )

    # Frontend (Hostinger) and backend (Render) live on different domains,
    # so CORS must explicitly allow the configured frontend origin(s).
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
    )

    register_blueprints(app)
    register_error_handlers(app)

    return app


def register_blueprints(app):
    from app.blueprints.main.routes import main_bp
    from app.blueprints.services.routes import services_bp
    from app.blueprints.products.routes import products_bp
    from app.blueprints.packages.routes import packages_bp
    from app.blueprints.gallery.routes import gallery_bp
    from app.blueprints.testimonials.routes import testimonials_bp
    from app.blueprints.tools.routes import tools_bp
    from app.blueprints.contact.routes import contact_bp
    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(main_bp, url_prefix="/api")
    app.register_blueprint(services_bp, url_prefix="/api/services")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(packages_bp, url_prefix="/api/packages")
    app.register_blueprint(gallery_bp, url_prefix="/api/gallery")
    app.register_blueprint(testimonials_bp, url_prefix="/api/testimonials")
    app.register_blueprint(tools_bp, url_prefix="/api/tools")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"ok": False, "error": "not_found", "message": "Resource not found."}), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error(f"Unhandled server error: {error}", exc_info=True)
        return jsonify({"ok": False, "error": "server_error", "message": "Something went wrong on our end."}), 500

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"ok": False, "error": "bad_request", "message": str(error)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        app.logger.warning(f"Authorization failure (401): {request.method} {request.path} from {get_remote_address()}")
        return jsonify({"ok": False, "error": "unauthorized", "message": "Sign in required."}), 401

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f"Authorization failure (403): {request.method} {request.path} from {get_remote_address()}")
        return jsonify({"ok": False, "error": "forbidden", "message": "You don't have access to this."}), 403

    @app.errorhandler(429)
    def rate_limited(error):
        app.logger.warning(f"Rate limit hit: {request.method} {request.path} from {get_remote_address()}")
        return jsonify({
            "ok": False, "error": "rate_limited",
            "message": "Too many requests, please wait a moment and try again.",
        }), 429
