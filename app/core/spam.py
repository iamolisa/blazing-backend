"""
Lightweight first-line spam defense for public, unauthenticated write
endpoints (contact form, quote form, testimonial submission, calculator
lead capture).

Two layers, deliberately simple:
1. A honeypot field: every public form includes a hidden input a real
   visitor never sees or fills. Bots that auto-fill every field trip it.
2. Rate limiting (applied separately, via Flask-Limiter, at the route).

This is not a replacement for a CAPTCHA/challenge service (Cloudflare
Turnstile, hCaptcha) if spam volume becomes a real problem post-launch.
it's a cheap filter that stops unsophisticated bots without adding a
third-party script or a site key to manage. Upgrade path noted in
DEPLOY.md if it's ever not enough.
"""
from flask import current_app


def is_honeypot_triggered(data):
    """True if the hidden honeypot field was filled in. A strong signal
    the submission came from a bot, not a real visitor."""
    field_name = current_app.config["HONEYPOT_FIELD_NAME"]
    return bool((data.get(field_name) or "").strip())
