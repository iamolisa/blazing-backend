# Blazing Trail Engineering — Backend (JSON API)

Flask JSON API. Deploy this to **Render**. It has no server-rendered pages —
the frontend (a separate static site) calls it over HTTP/JSON.

- **Financing/installment advisor**: `POST /api/tools/financing-advice` is powered by Groq (free tier — budget-friendly to start with) and grounded in real package pricing pulled from the DB at request time — it cannot invent a price or promise financing terms the business doesn't offer (see `app/core/financing_ai.py` for the guardrails). Requires `GROQ_API_KEY` in the environment; without it, the endpoint returns a clean `503` rather than crashing, and the frontend shows a fallback pointing to the quote form. Rate-limited to 5/hour/IP since each call still has a cost even on a free tier. Get a key from [console.groq.com](https://console.groq.com). `financing_ai.py` is the only file that knows which provider is in use — moving to Anthropic or another provider later is a change in one file, not a rewrite.

## Security

- **Rate limiting** (Flask-Limiter): 200/min default across all API routes, with tighter limits on sensitive ones — admin login (8/min), contact/quote (5/min), calculator lead capture (5/min), testimonial submission (3/hour). In-memory storage by default; if this ever runs across multiple gunicorn workers/instances, set `RATELIMIT_STORAGE_URI` to a Redis URL or limits won't be shared correctly across processes.
- **Security headers** (Flask-Talisman): strict CSP (`default-src 'none'` — this is a JSON-only API, nothing should ever load a script/style/frame from it), `X-Frame-Options: DENY`, HSTS + forced HTTPS in production.
- **Spam protection**: every public write endpoint (contact, quote, calculator lead capture, testimonial submission) checks a hidden honeypot field (`app/core/spam.py`) — real visitors never see or fill it; bots that auto-fill every field trip it and get a normal-looking success response with no record created. This is a first-line filter, not a CAPTCHA — if spam volume becomes a real problem post-launch, add Cloudflare Turnstile or hCaptcha on top.
- **Admin auth**: bearer tokens expire after 12 hours (`TOKEN_TTL_HOURS` in `app/models/user.py`), and changing the admin password immediately invalidates any existing token. Change your password via `/admin/settings.html` once logged in — no more editing `seed.py` by hand.

## Local run

```
pip install -r requirements.txt
flask db upgrade     # applies migrations, creates instance/blazingtrail.db
python seed.py        # populates it with starter content (dev-only, see below)
python run.py          # serves http://localhost:5000, routes under /api/*
```

Seeded admin login: `admin@blazingtrailengineering.com` / `ChangeMe123!`
**Change this immediately via `/admin/settings.html` after your first
login** — there's now a real change-password flow, so there's no reason
to leave the seeded default in place even for a moment longer than it
takes to log in once.

### Database migrations (Flask-Migrate / Alembic)

Schema changes go through migrations, never through `seed.py` or
`db.drop_all()`, once there's real data to protect:

```
flask db migrate -m "Describe the change"   # generates a migration from model changes
flask db upgrade                              # applies pending migrations
```

`seed.py` now refuses to run against anything that looks like Postgres,
and refuses to run when `FLASK_CONFIG=production` — it's a local/dev
convenience script, not a way to reset production. If you find yourself
wanting to re-seed production, that's a sign you need a migration or a
one-off data-fix script instead.

## Deploying to Render

**Faster path:** this repo includes `render.yaml` at the repo root — a
Render Blueprint that provisions the web service and Postgres database
together in one step. In the Render dashboard: New → Blueprint → connect
this repo. It reads `render.yaml` automatically. You'll still need to
fill in `CORS_ORIGINS` and (optionally) `GROQ_API_KEY` manually
afterward — everything else (`SECRET_KEY`, `DATABASE_URL`,
`FLASK_CONFIG`) is wired up for you. The manual steps below are what the
blueprint does under the hood, useful if you want to understand or
customize any of it.

**One thing the blueprint doesn't solve:** Render's free tier spins
services down after periods of inactivity, so the first request after a
quiet stretch can take 30-60 seconds while it wakes back up — noticeable
on a customer's first form submission. Fine for testing, worth upgrading
to a paid instance before pushing this as your real live site.

1. Push this `backend/` folder to its own Git repo (not the combined
   project folder — the frontend deploys separately to Hostinger, not
   through Git). This matters for the Blueprint above too:
   `render.yaml` doesn't set `rootDir`, because it expects this folder
   to be the repo root itself.
2. Create a Render **Postgres** instance first (Render dashboard → New →
   Postgres). Copy its **Internal Database URL** — Render web services in
   the same region can reach it directly, no external network hop needed.
3. New Web Service on Render:
   - **Build command:** `pip install -r requirements.txt && flask db upgrade`
     (runs migrations automatically on every deploy — do not use `python
     seed.py` here, it's local-only and now refuses to run against Postgres)
   - **Start command:** `gunicorn run:app`
4. Environment variables (Render dashboard → Environment):
   - `FLASK_CONFIG=production`
   - `FLASK_APP=app:create_app` (needed for `flask db upgrade` to find the app)
   - `SECRET_KEY=` — generate a real random value (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `CORS_ORIGINS=https://blazingtrailengineering.com,https://www.blazingtrailengineering.com`
     (comma-separated, no spaces; must match your Hostinger domain exactly,
     including https:// and any www. variant you use)
   - `DATABASE_URL=` — the Internal Database URL from step 2. Render hands
     this out as `postgres://...`; the app normalizes that to
     `postgresql://...` automatically, so paste it as-is.
5. **Production will refuse to boot if any of the above are missing or
   left at their defaults** — this is intentional (see `config.py`,
   `ProductionConfig.validate()`). If the service won't start, check the
   Render logs; the error message tells you exactly which env var is
   missing.
6. After first deploy, create the admin user once via Render's Shell tab
   (do **not** run `seed.py` — it only inserts starter content and will
   refuse to run against Postgres anyway):
   ```python
   python -c "
   from app import create_app
   from extensions import db
   from app.models import User
   app = create_app()
   with app.app_context():
       u = User(name='Blazing Trail Admin', email='admin@blazingtrailengineering.com', role='admin')
       u.set_password('REPLACE-WITH-A-REAL-PASSWORD')
       db.session.add(u)
       db.session.commit()
       print('Admin created.')
   "
   ```
   Use a real password here, not `ChangeMe123!` — there's no need to
   create the weak default and change it afterward.

### Database backups

Render's managed Postgres includes automatic daily backups on paid plans
— check your plan's retention window in the Render dashboard (Postgres
instance → Backups) and make sure it actually covers what you need.

For an additional/independent copy, `scripts/backup_db.sh` runs a
`pg_dump` against the **External Database URL** (from the same Render
Postgres dashboard) and gzips it. Run it from your own machine, or wire
it into a scheduler:

```
DATABASE_URL="<external connection string>" ./scripts/backup_db.sh
```

Restore with:
```
gunzip -c backups/blazingtrail_<timestamp>.sql.gz | psql "$DATABASE_URL"
```

If you schedule this via a Render Cron Job instead of a machine with
persistent disk, ship the resulting file somewhere durable (S3, Backblaze,
etc.) before the job's container is torn down — Render's own filesystem
is ephemeral, so a backup that only exists on it isn't actually backed up.

## What changed from the original Flask app

This was originally a server-rendered Flask app (Jinja templates + admin
panel with session-based login). It's been converted to a pure JSON API:

- Every route now returns JSON instead of HTML.
- Admin auth uses a bearer token (`Authorization: Bearer <token>`) instead
  of session cookies, since the frontend lives on a different domain
  (cross-site cookies are unreliable/blocked by default in most browsers).
- CORS is enabled via `flask-cors`, restricted to `CORS_ORIGINS`.
- All Jinja templates and template-only static assets were removed — the
  equivalent UI now lives in the `frontend/` folder as static HTML/JS.

## API reference (quick)

Public (no auth):
- `GET /api/business` — site info for header/footer
- `GET /api/home` — aggregated homepage data
- `GET /api/services/`, `GET /api/services/<slug>`
- `GET /api/products/?category=<slug>&q=<search>`, `GET /api/products/<slug>`
- `GET /api/packages/`
- `GET /api/gallery/?category=<slug>`
- `GET /api/testimonials/`
- `GET /api/tools/`, `POST /api/tools/sizing-result`, `POST /api/tools/financing-advice`
- `POST /api/contact/`, `POST /api/contact/quote`

Admin (`Authorization: Bearer <token>` required, get token from login):
- `POST /api/admin/login`, `POST /api/admin/logout`, `GET /api/admin/me`
- `PATCH /api/admin/me/password` — change your own password (requires `current_password`; invalidates the old token, returns a fresh one)
- `GET /api/admin/dashboard`
- `GET /api/admin/products`, `POST /api/admin/products`,
  `PUT /api/admin/products/<id>`, `DELETE /api/admin/products/<id>`
- `GET /api/admin/categories`
- `GET /api/admin/leads?page=&per_page=&status=`, `PATCH /api/admin/leads/<id>/status`
  (paginated, 25/page by default, max 100/page; optional `status` filter)

## Tests

`python -m pytest test_api.py -v` — 17 tests covering every endpoint,
including admin auth/CRUD, validation, 404s, and CORS headers.
