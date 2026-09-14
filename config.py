"""
Configuration classes for Blazing Trail Engineering.

Set FLASK_ENV / FLASK_CONFIG to switch between configs. Real deployments
should set SECRET_KEY and DATABASE_URL via environment variables rather
than relying on the defaults below.
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _normalized_database_url():
    """Render (and most managed Postgres providers) hand out a DATABASE_URL
    that starts with 'postgres://'. SQLAlchemy 1.4+/2.x only recognizes the
    'postgresql://' scheme, so without this the app fails to boot in
    production with a cryptic dialect error."""
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url or f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'blazingtrail.db')}"


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = _normalized_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Business info, served to the frontend via GET /api/business
    BUSINESS_NAME = "Blazing Trail Engineering"
    BUSINESS_TAGLINE = "Powering your world with reliable solutions"
    BUSINESS_PHONE = "+234 808 557 8080"
    BUSINESS_PHONE_SECONDARY = "+234 810 869 0802"
    BUSINESS_WHATSAPP = "2348085578080"
    BUSINESS_EMAIL = "info@blazingtrailengineering.com"
    # TODO: replace with the real street address once you have one you
    # want public. The homepage Google Maps embed (index.html / home.js)
    # is built from this value. Right now it can only center on "Lagos,
    # Nigeria" generally, not drop a pin on your actual office/yard.
    BUSINESS_ADDRESS = "Lagos, Nigeria"

    # Comma-separated list of allowed frontend origins for CORS, e.g.
    # "https://blazingtrailengineering.com,https://www.blazingtrailengineering.com"
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # Flask-Limiter storage. In-memory is fine for a single Render web
    # service instance/worker. If this ever scales to multiple gunicorn
    # workers or instances, in-memory counters are per-process and won't
    # be shared. Set RATELIMIT_STORAGE_URI to a Redis URL at that point
    # (e.g. Render's managed Redis) or limits become inconsistent across
    # workers.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # Name of the hidden honeypot field every public form includes. Real
    # visitors never see or fill it (CSS-hidden, not display:none since some
    # bots skip display:none fields); bots that auto-fill every field trip
    # it. Submissions with this field non-empty are silently dropped
    # (return a normal-looking success response, don't create a record) so
    # the bot doesn't learn to look for a different signal.
    HONEYPOT_FIELD_NAME = "website"

    # Financing/installment AI advisor (see app/core/financing_ai.py). Not
    # set locally by default. The feature degrades to a clear "not
    # configured yet" message rather than crashing when this is empty.
    #
    # Using Groq (free tier) rather than a paid provider. Swap-friendly
    # by design: financing_ai.py is the only file that knows which
    # provider is in use, so moving to Anthropic or another provider
    # later is a change in one file, not a rewrite.
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    # openai/gpt-oss-20b: fast, cheap, sized right for a short advisory
    # reply, not the biggest model on Groq, but this task doesn't need
    # it. Groq deprecates/renames models periodically; check
    # console.groq.com/docs/models if this stops working.
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False

    @classmethod
    def validate(cls):
        """Called once at startup (see app/__init__.py). Refuses to boot
        with settings that would silently leave production insecure,
        better to crash on deploy than to find out via a leaked DB or an
        open CORS policy."""
        problems = []
        if cls.SECRET_KEY == "dev-key-change-me-in-production":
            problems.append("SECRET_KEY is still the default. Set a real one in the environment.")
        if cls.SQLALCHEMY_DATABASE_URI.startswith("sqlite:"):
            problems.append("DATABASE_URL is not set. Production must not run on SQLite (Render's disk is ephemeral).")
        if cls.CORS_ORIGINS == ["*"]:
            problems.append("CORS_ORIGINS is not set. Refusing to run production wide open. Set it to your real frontend domain(s).")
        if problems:
            raise RuntimeError(
                "Refusing to start in production due to unsafe configuration:\n- " + "\n- ".join(problems)
            )


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
