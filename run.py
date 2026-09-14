"""
Local development entry point.

    python run.py

For production, use a WSGI server instead, e.g.:

    gunicorn "run:app"
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, port=5000, use_reloader=debug)
