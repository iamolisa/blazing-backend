"""
Sync the admin account to whatever ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD
currently say, reading both from the environment rather than ever having
them typed or hardcoded anywhere.

Designed to run automatically on every deploy (see the buildCommand in
render.yaml) rather than needing a Render Shell tab, which isn't
available on the free plan. That means it has to be safe to run
unattended, every single time code is pushed or any env var changes -
not just when the admin password specifically changed. So it only ever
touches the database when something is actually out of sync:

  - no admin with this email yet       -> create it
  - admin exists, password matches     -> do nothing
  - admin exists, password differs     -> update it (this is what makes
                                           changing ADMIN_SEED_PASSWORD in
                                           Render's dashboard and letting
                                           it redeploy actually take effect,
                                           with no extra step)

Also deliberately non-fatal if the env vars aren't set, or look invalid -
it prints a warning and exits 0 rather than failing the build, so a typo
in ADMIN_SEED_PASSWORD or forgetting to set it yet can't block an
unrelated deploy from going out. ProductionConfig.validate() in config.py
is the actual hard gate for settings that must never be wrong
(SECRET_KEY, DATABASE_URL, CORS_ORIGINS); this script is a convenience,
not a security boundary.

Works against any database (local SQLite or production Postgres), unlike
seed.py, which refuses to touch Postgres on purpose.
"""
from app import create_app
from extensions import db
from app.models import User

app = create_app()

EMAIL = app.config.get("ADMIN_SEED_EMAIL")
PASSWORD = app.config.get("ADMIN_SEED_PASSWORD")

if not EMAIL or not PASSWORD:
    print("create_admin.py: ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD not set - skipping.")
elif len(PASSWORD) < 10:
    print("create_admin.py: ADMIN_SEED_PASSWORD is under 10 characters - skipping.")
else:
    with app.app_context():
        user = User.query.filter_by(email=EMAIL.strip().lower()).first()

        if not user:
            user = User(name="Admin", email=EMAIL.strip().lower(), role="admin")
            user.set_password(PASSWORD)
            db.session.add(user)
            db.session.commit()
            print(f"create_admin.py: created admin {EMAIL}")
        elif not user.check_password(PASSWORD):
            user.set_password(PASSWORD)  # also clears their current token - see User.set_password
            db.session.commit()
            print(f"create_admin.py: ADMIN_SEED_PASSWORD changed - updated {EMAIL}")
        else:
            print(f"create_admin.py: {EMAIL} already up to date - nothing to do.")
