"""
Centralized Flask extension instances so blueprints/models can import
them without triggering circular imports with the app factory.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

db = SQLAlchemy()
cors = CORS()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    # Generous baseline so normal browsing/admin dashboard use never
    # trips it. This exists to stop scripted abuse, not to throttle
    # real traffic. Sensitive routes (login, contact, quote,
    # testimonials, calculator) set tighter limits at the route.
    default_limits=["200 per minute"],
)
talisman = Talisman()
