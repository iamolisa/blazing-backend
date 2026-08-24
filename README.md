# Blazing Trail Engineering — Backend

Flask JSON API backend for Blazing Trail Engineering's website (solar,
industrial electrical panels, PLC automation). The frontend is a
separate static site (in the sibling `frontend/` folder in this
project, deployed independently to Hostinger) that talks to this API —
this is not a server-rendered Flask app with Jinja templates.

## What's actually built and working

- **JSON API** covering: business info, services (index + detail),
  products (catalog with category filter + search + detail), packages &
  pricing, project gallery (filterable), testimonials (public read +
  public submission with moderation queue), sizing tools, contact form,
  quote requests, and a full admin API.
- **Real, working solar sizing calculator logic** — actual wattage
  arithmetic against a reference appliance-load table, sizing inverter
  kVA, battery bank Ah, and panel count from real inputs (frontend does
  the live calculation; this API captures the resulting lead).
- **Financing/installment advisor** — `POST /api/tools/financing-advice`,
  powered by Groq, grounded in real package pricing pulled from the DB
  at request time so it can't invent numbers. See "AI-powered tools"
  below.
- **Admin API** (`/api/admin/*`) — bearer-token auth (12-hour expiry,
  invalidated on password change or logout), dashboard stats, full
  product CRUD, testimonial moderation CRUD, and a paginated leads inbox
  with status updates and deletion (the deletion endpoint exists
  specifically to fulfill the data-deletion right promised in the
  Privacy Policy — not just for tidiness).
- **Database-backed content** via SQLAlchemy, with real Flask-Migrate
  (Alembic) migrations — schema changes go through `flask db migrate` /
  `flask db upgrade`, not by dropping and recreating tables. `seed.py` is
  a local-dev-only convenience script and refuses to run against
  anything that looks like Postgres or against `FLASK_CONFIG=production`.
- **Security**: rate limiting (Flask-Limiter) on every sensitive
  endpoint, security headers (Flask-Talisman — strict CSP, HSTS, frame
  denial), honeypot spam protection on every public write endpoint,
  audit logging (`logs/app.log`/`logs/errors.log`) for logins, admin
  actions, and authorization failures, and a production boot-guard that
  refuses to start with a default secret key, SQLite, or wide-open CORS.
- **Automated tests** — `pytest test_api.py`, 22 passing, covering every
  route including auth flow, rate limiting behavior, honeypot behavior,
  and the health check.
- **Lead capture** — contact form, quote form, sizing calculator, and
  the financing advisor (when a phone number is given) all write real
  rows to the `leads` table, visible and manageable in the admin
  dashboard.

## Deliberately stubbed / needs your input

- **Package prices** (`seed.py`) are real, taken from the business's price
  list — 14 systems, each priced with and/or without solar panels. Every
  package now has at least one confirmed price (verified directly against
  the seeded data, not assumed).
- **Testimonials** are real — 22 Google reviews with actual owner replies,
  seeded with an approve/pending workflow. New public submissions land as
  "pending" until approved from `/admin/testimonials.html`.
- **Gallery photos** are real project photos (`frontend/images/gallery/`,
  optimized to WebP).
- **Team/management bios** on the About page are placeholder cards — real
  bios/photos need to be supplied.
- **Interactive map** on the homepage is a real, working Google Maps embed
  (no API key needed) — but `BUSINESS_ADDRESS` in `config.py` is still
  just `"Lagos, Nigeria"`, so it currently pins the whole city rather than
  the actual office. Update that one value once the real address is
  confirmed.
- **Full e-commerce (cart/checkout/payment)** was intentionally left out
  per the questionnaire answer ("full ecommerce sounds nice but cost") —
  the products catalog is browse + "Request a Quote" only, matching the
  "both fixed packages and custom quotes" answer given.
- Company registration/certification badges, manufacturer partner logos,
  and social media links are placeholders — mentioned as available but no
  files were supplied yet.

### Database migrations

Schema changes go through Flask-Migrate (Alembic): `flask db migrate -m
"description"` then `flask db upgrade`. This replaced an earlier
drop-and-recreate approach that would have been unsafe against real
production data — `seed.py` is now local-dev-only and refuses to run
against Postgres or `FLASK_CONFIG=production` (see its own docstring).

## Project structure

```
backend/
├── run.py                   # dev server entry point
├── seed.py                  # local-dev-only starter content (refuses to run against Postgres/production)
├── config.py                 # environment-based config classes + production boot-guard
├── extensions.py             # db, cors, migrate, limiter, talisman singletons
├── requirements.txt
├── render.yaml                # Render Blueprint — this folder is the repo root for that deploy
├── test_api.py                # pytest suite, 22 tests
├── migrations/                 # Flask-Migrate/Alembic, do not hand-edit
├── scripts/backup_db.sh        # pg_dump backup script for production Postgres
├── app/
│   ├── __init__.py             # app factory — extensions, security headers, logging, blueprints
│   ├── logging_config.py        # file-based audit/error logging (logs/app.log, logs/errors.log)
│   ├── models/                   # SQLAlchemy models
│   ├── core/                      # business logic, isolated from Flask routes:
│   │   ├── catalog.py, leads.py, auth.py, spam.py, financing_ai.py (Groq client)
│   └── blueprints/                # one folder per route group, mounted under /api/*
│       ├── main/ services/ products/ packages/ gallery/
│       ├── testimonials/ tools/ contact/ admin/
```

There's no `templates/` or `static/` folder here — this API returns JSON
only. The actual HTML/CSS/JS live in the sibling `frontend/` folder and
are deployed separately.

## Running it locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env         # edit SECRET_KEY for anything beyond local dev
flask db upgrade              # applies migrations, creates instance/blazingtrail.db
python3 seed.py                # populates it with starter content (local dev only)
python3 run.py                  # http://127.0.0.1:5000
```

Admin login: `admin@blazingtrailengineering.com` / `ChangeMe123!` — **change
this immediately via `/admin/settings.html` after your first login** —
there's a real change-password flow now, not just re-seeding.

## Deploying

See `DEPLOY.md` for the full walkthrough (Render + Postgres, environment
variables, the `render.yaml` Blueprint, security headers, rate limiting,
backups). Short version: don't run `run.py` in production — use
`gunicorn run:app` — and the app will refuse to boot in production with a
default secret key, SQLite, or wide-open CORS, on purpose.

## AI-powered tools (Energy Analyzer, Financing Calculator)

**Financing/installment advisor — built.** `POST /api/tools/financing-advice`,
see `app/core/financing_ai.py`. Runs on Groq (free tier, budget-friendly
to start with) and is grounded in real package pricing pulled from the
DB at request time, so it can't invent a price or promise financing
terms the business doesn't actually offer. Needs `GROQ_API_KEY` set to
work — without it, the endpoint returns a clean "not configured" message
rather than crashing. Get a free key at console.groq.com. Swapping to
Anthropic or another provider later is a change contained entirely to
`financing_ai.py`, not a rewrite — nothing else in the app knows or
cares which provider is behind it.

**Energy Analyzer (photo-upload bill/meter reading estimator) — not
built.** This was in the original questionnaire's feature list but
hasn't been wired up. To add it, follow the same pattern as the
financing advisor:

1. Add a route in `app/blueprints/tools/routes.py` that accepts an
   uploaded image (`request.files`), sends it to an AI provider that
   supports image input, and returns an estimated consumption/system-size
   recommendation.
2. Keep the provider-specific client code isolated in its own
   `app/core/` module (mirroring `financing_ai.py`) rather than inline in
   the route — that's what makes providers swappable later.
3. Note this one needs actual file upload handling (size limits,
   content-type validation, no permanent storage of the image unless
   there's a real reason to keep it) — nothing in this codebase currently
   handles file uploads at all, so that part is new, not reused.

## Known limitations worth knowing about

- This has been tested end-to-end at the API level (pytest suite, plus
  extensive manual curl-based testing of auth flows, rate limiting,
  honeypot behavior, and the admin CRUD endpoints throughout
  development), but not in a live browser against the deployed frontend
  — give real device/browser testing a pass before launch (see
  frontend's own testing notes).
- CSRF isn't a concern here the way it would be for a server-rendered
  app with session cookies — this API uses bearer tokens sent via an
  `Authorization` header, which aren't automatically attached by the
  browser the way cookies are, so the usual CSRF attack vector doesn't
  apply the same way. `Flask-WTF`/CSRF tokens were never wired in
  because they're the wrong tool for this auth model, not an oversight.
- Free-tier hosting caveats: Render's free web service spins down after
  inactivity (cold-start delay on the first request after a quiet
  period); Groq's free tier has its own rate/quota limits worth checking
  against expected traffic before launch.
