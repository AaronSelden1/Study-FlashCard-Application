"""config.py - Configuration settings for the Study Flashcard Application.

All environment-specific settings are defined here so that they can be
imported by app.py, database.py, and the test suite without duplication.
"""

import os

# ---------------------------------------------------------------------------
# Base directory
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Flask secret key
# Used for cryptographically signing session cookies.
# Override via the SECRET_KEY environment variable in production.
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "cmsc495-flashcard-dev-key-2026-change-in-production"
)

# ---------------------------------------------------------------------------
# SQLite database path
# Override via the DATABASE environment variable or directly in the test
# fixture to use a temporary file.
# ---------------------------------------------------------------------------
DATABASE = os.environ.get(
    "DATABASE",
    os.path.join(BASE_DIR, "flashcard.db")
)
