"""
File-based logging, in addition to Flask's default stderr output.

Before this existed, the app had exactly one logging call in the entire
codebase (an error-path log in the financing advisor). Login attempts,
admin actions (create/edit/delete on products, testimonials, leads),
password changes, and authorization failures weren't being recorded
anywhere durable. There was no audit trail to check if something went
wrong or someone needed to know who changed what. This closes that gap.

Two files:
- logs/app.log    : INFO and above: normal operational + audit events.
- logs/errors.log : ERROR and above: just the things that need attention.

Never log passwords, tokens, or full request bodies. See call sites in
the blueprints for what specifically gets logged (email + action, never
credentials).
"""
import logging
import logging.handlers
import os


def configure_logging(app):
    log_dir = os.path.join(app.instance_path, "..", "logs")
    log_dir = os.path.abspath(log_dir)
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=5 * 1024 * 1024, backupCount=5
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)

    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "errors.log"), maxBytes=5 * 1024 * 1024, backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)

    app.logger.info("Application started")
