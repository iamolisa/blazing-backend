import secrets
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

# How long an admin bearer token stays valid before requiring re-login.
# Kept short-ish since the token sits in localStorage (readable by any JS
# on the page, unlike an HttpOnly cookie). See DEPLOY.md for the tradeoffs
# of this cross-domain auth approach.
TOKEN_TTL_HOURS = 12


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="admin")  # admin | editor
    # Bearer token for the JSON API (frontend lives on a different domain,
    # so we avoid cross-site session cookies and use a simple token instead).
    api_token = db.Column(db.String(64), unique=True, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)
        # A password change invalidates any existing session. The old
        # token (e.g. one that leaked) stops working immediately.
        self.api_token = None
        self.token_expires_at = None

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def generate_api_token(self):
        self.api_token = secrets.token_hex(32)
        self.token_expires_at = datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
        return self.api_token

    def token_is_valid(self):
        if not self.api_token or not self.token_expires_at:
            return False
        return datetime.utcnow() < self.token_expires_at

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}

    def __repr__(self):
        return f"<User {self.email}>"
