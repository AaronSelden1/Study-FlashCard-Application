"""app.py - Main Flask application for the Study Flashcard Application.

Routes
------
Public:
    GET  /                              Home / landing page
    GET  /register                      Registration form
    POST /register                      Submit new account
    GET  /login                         Login form
    POST /login                         Submit credentials
    GET  /logout                        End session

Authenticated (login required):
    GET  /dashboard                     User deck list
    POST /deck/create                   Create new deck
    GET  /deck/<deck_id>                View deck and cards
    GET  /deck/<deck_id>/edit           Edit deck form
    POST /deck/<deck_id>/edit           Submit deck edits
    POST /deck/<deck_id>/delete         Delete deck
    POST /deck/<deck_id>/card/add       Add card to deck
    GET  /deck/<deck_id>/card/<cid>/edit    Edit card form
    POST /deck/<deck_id>/card/<cid>/edit    Submit card edits
    POST /deck/<deck_id>/card/<cid>/delete  Delete card
    GET  /study/<deck_id>               Study mode
    POST /study/<deck_id>/result        Progress summary
"""

import functools
import os

from flask import (Flask, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import config
from database import get_db, init_db

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ---------------------------------------------------------------------------
# Helper: login_required decorator
# ---------------------------------------------------------------------------
def login_required(view):
    """Redirect unauthenticated users to the login page.

    Wraps a view function so that any request without an active session
    is redirected to /login with an informational flash message.

    Args:
        view (function): The Flask view function to protect.

    Returns:
        function: The wrapped view function.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


# ---------------------------------------------------------------------------
# Helper: ownership guard
# ---------------------------------------------------------------------------
def get_deck_or_abort(deck_id):
    """Return the deck if it belongs to the logged-in user, else None.

    Args:
        deck_id (int): Primary key of the deck to retrieve.

    Returns:
        sqlite3.Row or None: The deck row, or None if not found / not owned.
    """
    db = get_db()
    deck = db.execute(
        "SELECT * FROM decks WHERE id = ? AND user_id = ?",
        (deck_id, session["user_id"])
    ).fetchone()
    db.close()
    return deck


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """Render the public home / landing page."""
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user account registration.

    GET  - Render the registration form.
    POST - Validate input; on success, create account and redirect to login.

    Validation rules:
        - All fields (username, email, password) must be non-empty.
        - Username must be unique; duplicate returns 'Username is already taken.'
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()

        if existing:
            db.close()
            flash("Username is already taken.", "danger")
            return render_template("register.html")

        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        db.commit()
        user_id = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()["id"]
        db.close()

        # Auto-login the newly registered user
        session.clear()
        session["user_id"] = user_id
        session["username"] = username
        flash("Account created successfully. Welcome!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login.

    GET  - Render the login form.
    POST - Validate credentials; on success, establish session and redirect
           to dashboard.  On failure, display 'Invalid username or password.'
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("All fields are required.", "danger")
            return render_template("login.html")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear the user session and redirect to the home page."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    """Render the authenticated user's deck list with card counts.

    Each deck entry includes the card count and the mastery percentage stored
    in the session from the most recent study session for that deck.
    """
    db = get_db()
    rows = db.execute(
        "SELECT * FROM decks WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    decks = []
    for row in rows:
        card_count = db.execute(
            "SELECT COUNT(*) FROM cards WHERE deck_id = ?", (row["id"],)
        ).fetchone()[0]
        decks.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "card_count": card_count,
            "mastery": session.get(f"mastery_{row['id']}", 0),
        })

    db.close()
    return render_template("dashboard.html", decks=decks)


# ---------------------------------------------------------------------------
# Deck CRUD routes
# ---------------------------------------------------------------------------
@app.route("/deck/create", methods=["POST"])
@login_required
def create_deck():
    """Create a new flashcard deck for the logged-in user.

    Expects POST fields: name (required), description (optional).
    On success, redirects to the dashboard.
    """
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Deck name is required.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()
    db.execute(
        "INSERT INTO decks (user_id, name, description) VALUES (?, ?, ?)",
        (session["user_id"], name, description)
    )
    db.commit()
    db.close()
    flash("Deck created successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/deck/<int:deck_id>")
@login_required
def view_deck(deck_id):
    """Render the deck detail page with all associated cards.

    Args:
        deck_id (int): Primary key of the deck to display.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()
    cards = db.execute(
        "SELECT * FROM cards WHERE deck_id = ? ORDER BY created_at ASC",
        (deck_id,)
    ).fetchall()
    db.close()
    return render_template("deck.html", deck=deck, cards=cards)


@app.route("/deck/<int:deck_id>/edit", methods=["GET", "POST"])
@login_required
def edit_deck(deck_id):
    """Render and process the deck edit form.

    GET  - Display the edit form pre-filled with current values.
    POST - Validate and apply the updated name and description.

    Args:
        deck_id (int): Primary key of the deck to edit.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Deck name is required.", "danger")
            return render_template("edit_deck.html", deck=deck)

        db = get_db()
        db.execute(
            "UPDATE decks SET name = ?, description = ? WHERE id = ?",
            (name, description, deck_id)
        )
        db.commit()
        db.close()
        flash("Deck updated successfully.", "success")
        return redirect(url_for("view_deck", deck_id=deck_id))

    return render_template("edit_deck.html", deck=deck)


@app.route("/deck/<int:deck_id>/delete", methods=["POST"])
@login_required
def delete_deck(deck_id):
    """Delete a deck and all of its cards permanently.

    Args:
        deck_id (int): Primary key of the deck to delete.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()
    db.execute("DELETE FROM cards WHERE deck_id = ?", (deck_id,))
    db.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
    db.commit()
    db.close()
    flash("Deck deleted successfully.", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Card CRUD routes
# ---------------------------------------------------------------------------
@app.route("/deck/<int:deck_id>/card/add", methods=["POST"])
@login_required
def add_card(deck_id):
    """Add a new question-answer card to the specified deck.

    Both the question and answer fields are required.  An empty field
    returns: 'Both question and answer fields are required.'

    Args:
        deck_id (int): Primary key of the parent deck.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if not question or not answer:
        flash("Both question and answer fields are required.", "danger")
        return redirect(url_for("view_deck", deck_id=deck_id))

    db = get_db()
    db.execute(
        "INSERT INTO cards (deck_id, question, answer) VALUES (?, ?, ?)",
        (deck_id, question, answer)
    )
    db.commit()
    db.close()
    flash("Card added successfully.", "success")
    return redirect(url_for("view_deck", deck_id=deck_id))


@app.route("/deck/<int:deck_id>/card/<int:card_id>/edit", methods=["GET", "POST"])
@login_required
def edit_card(deck_id, card_id):
    """Render and process the card edit form.

    GET  - Display the edit form pre-filled with current question and answer.
    POST - Validate and apply the updated question and answer.

    Args:
        deck_id (int): Primary key of the parent deck.
        card_id (int): Primary key of the card to edit.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()
    card = db.execute(
        "SELECT * FROM cards WHERE id = ? AND deck_id = ?", (card_id, deck_id)
    ).fetchone()
    db.close()

    if card is None:
        flash("Card not found.", "danger")
        return redirect(url_for("view_deck", deck_id=deck_id))

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()

        if not question or not answer:
            flash("Both question and answer fields are required.", "danger")
            return render_template("edit_card.html", deck=deck, card=card)

        db = get_db()
        db.execute(
            "UPDATE cards SET question = ?, answer = ? WHERE id = ?",
            (question, answer, card_id)
        )
        db.commit()
        db.close()
        flash("Card updated successfully.", "success")
        return redirect(url_for("view_deck", deck_id=deck_id))

    return render_template("edit_card.html", deck=deck, card=card)


@app.route("/deck/<int:deck_id>/card/<int:card_id>/delete", methods=["POST"])
@login_required
def delete_card(deck_id, card_id):
    """Remove a single card from a deck.

    Args:
        deck_id (int): Primary key of the parent deck.
        card_id (int): Primary key of the card to delete.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()
    db.execute(
        "DELETE FROM cards WHERE id = ? AND deck_id = ?", (card_id, deck_id)
    )
    db.commit()
    db.close()
    flash("Card deleted successfully.", "success")
    return redirect(url_for("view_deck", deck_id=deck_id))


# ---------------------------------------------------------------------------
# Study mode routes
# ---------------------------------------------------------------------------
@app.route("/study/<int:deck_id>")
@login_required
def study(deck_id):
    """Render the study mode page for the specified deck.

    Presents all cards for self-assessment.  The user marks each card as
    'Got It' or 'Try Again' and submits the form to the result route.
    Full card-flip animation will be added in Phase II.

    Args:
        deck_id (int): Primary key of the deck to study.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()
    cards = db.execute(
        "SELECT * FROM cards WHERE deck_id = ? ORDER BY RANDOM()",
        (deck_id,)
    ).fetchall()
    db.close()

    if not cards:
        flash("This deck has no cards to study. Add some cards first.", "warning")
        return redirect(url_for("view_deck", deck_id=deck_id))

    cards = [dict(row) for row in cards]

    return render_template("study.html", deck=deck, cards=cards)

   


@app.route("/study/<int:deck_id>/result", methods=["POST"])
@login_required
def study_result(deck_id):
    """Calculate and display the study session progress summary.

    Receives a list of card IDs marked as 'Got It' via POST, computes the
    mastery percentage, persists it to the session, and renders the summary.

    Mastery % = (cards marked Got It / total cards) x 100, rounded to
    the nearest whole number.

    Args:
        deck_id (int): Primary key of the studied deck.
    """
    deck = get_deck_or_abort(deck_id)
    if deck is None:
        flash("Deck not found.", "danger")
        return redirect(url_for("dashboard"))

    db = get_db()
    total = db.execute(
        "SELECT COUNT(*) FROM cards WHERE deck_id = ?", (deck_id,)
    ).fetchone()[0]
    db.close()

    got_it_ids = request.form.getlist("got_it")
    got_it = len(got_it_ids)
    mastery = round((got_it / total * 100) if total > 0 else 0)

    # Persist mastery percentage in session for dashboard display
    session[f"mastery_{deck_id}"] = mastery
    session.modified = True

    return render_template(
        "progress.html",
        deck=deck,
        got_it=got_it,
        total=total,
        mastery=mastery
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    """Render a friendly 404 page for missing routes or resources."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    """Render a friendly 500 page for unhandled server errors."""
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.path.exists(config.DATABASE):
        init_db()
        print("Database initialised.")
    app.run(debug=True)
