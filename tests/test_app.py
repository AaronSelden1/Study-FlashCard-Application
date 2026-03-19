"""
test_app.py - Unit tests for the Study Flashcard Application.

Test Classes
------------
TestRegistration   : User registration (success, duplicate username, missing fields)
TestAuthentication : Login (valid, invalid password, invalid username), logout
TestAccessControl  : Protected routes redirect unauthenticated users
TestDeckCRUD       : Create, read, edit, delete decks
TestCardCRUD       : Add, edit, delete cards within a deck
TestDataIsolation  : Users cannot access another user's decks or cards

Run with:
    pytest tests/ -v
"""

import os
import tempfile
import pytest

import config          # imported so tests can monkey-patch config.DATABASE
import database
from app import app as flask_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """
    Fixture: configure app for testing with an isolated temporary database.

    Steps
    -----
    1. Create a temporary SQLite file.
    2. Override config.DATABASE so database.get_db() and init_db() use it.
    3. Initialise the schema.
    4. Yield a Flask test client.
    5. Restore the original DATABASE path and remove the temp file.
    """
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)                          # close OS file descriptor; SQLite opens its own

    original_db = config.DATABASE
    config.DATABASE = db_path                # monkey-patch before init_db()
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    flask_app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.app_context():
        database.init_db()

    with flask_app.test_client() as test_client:
        yield test_client

    # Teardown
    config.DATABASE = original_db
    try:
        os.unlink(db_path)
    except OSError:
        pass


# ── Helper functions ───────────────────────────────────────────────────────────

def register(client, username, password):
    """POST to /register and return the response."""
    return client.post(
        "/register",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def login(client, username, password):
    """POST to /login and return the response."""
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def logout(client):
    """GET /logout and return the response."""
    return client.get("/logout", follow_redirects=True)


def create_deck(client, name, description=""):
    """POST to /deck/create and return the response."""
    return client.post(
        "/deck/create",
        data={"name": name, "description": description},
        follow_redirects=True,
    )


def add_card(client, deck_id, question, answer):
    """POST to /deck/<deck_id>/card/add and return the response."""
    return client.post(
        f"/deck/{deck_id}/card/add",
        data={"question": question, "answer": answer},
        follow_redirects=True,
    )


# ── TestRegistration ───────────────────────────────────────────────────────────

class TestRegistration:
    """Tests for the /register route."""

    def test_register_success(self, client):
        """A new user with valid credentials is registered and redirected."""
        response = register(client, "alice", "password123")
        assert response.status_code == 200
        # After successful registration the user lands on the dashboard
        assert b"Dashboard" in response.data or b"dashboard" in response.data.lower()

    def test_register_duplicate_username(self, client):
        """Registering with an existing username shows an error message."""
        register(client, "alice", "password123")
        logout(client)
        response = register(client, "alice", "differentpass")
        assert b"Username is already taken." in response.data

    def test_register_missing_username(self, client):
        """Submitting the register form with no username triggers validation."""
        response = register(client, "", "password123")
        assert b"All fields are required." in response.data

    def test_register_missing_password(self, client):
        """Submitting the register form with no password triggers validation."""
        response = register(client, "bob", "")
        assert b"All fields are required." in response.data

    def test_register_missing_both_fields(self, client):
        """Submitting empty register form triggers validation."""
        response = register(client, "", "")
        assert b"All fields are required." in response.data


# ── TestAuthentication ─────────────────────────────────────────────────────────

class TestAuthentication:
    """Tests for /login and /logout routes."""

    def test_login_valid_credentials(self, client):
        """A registered user can log in with correct credentials."""
        register(client, "alice", "password123")
        logout(client)
        response = login(client, "alice", "password123")
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"dashboard" in response.data.lower()

    def test_login_wrong_password(self, client):
        """Login with an incorrect password shows an error."""
        register(client, "alice", "password123")
        logout(client)
        response = login(client, "alice", "wrongpass")
        assert b"Invalid username or password." in response.data

    def test_login_unknown_username(self, client):
        """Login with a username that does not exist shows an error."""
        response = login(client, "nobody", "password123")
        assert b"Invalid username or password." in response.data

    def test_login_missing_fields(self, client):
        """Login with empty credentials triggers validation."""
        response = login(client, "", "")
        assert b"All fields are required." in response.data

    def test_logout_redirects_to_home(self, client):
        """Logging out redirects to the home/login page."""
        register(client, "alice", "password123")
        response = logout(client)
        assert response.status_code == 200
        # After logout the user is no longer on the dashboard
        assert b"Please log in" in response.data or b"Login" in response.data or b"login" in response.data.lower()

    def test_session_cleared_after_logout(self, client):
        """After logout, accessing /dashboard redirects to login."""
        register(client, "alice", "password123")
        logout(client)
        response = client.get("/dashboard", follow_redirects=True)
        assert b"Please log in to access this page." in response.data or b"login" in response.data.lower()


# ── TestAccessControl ──────────────────────────────────────────────────────────

class TestAccessControl:
    """Tests that unauthenticated access to protected routes is blocked."""

    # Routes that accept GET (or GET+POST)
    GET_ROUTES = [
        "/dashboard",
        "/deck/1",
        "/deck/1/edit",
        "/deck/1/card/1/edit",
        "/study/1",
    ]
    # Routes that only accept POST
    POST_ROUTES = [
        "/deck/create",
        "/deck/1/delete",
        "/deck/1/card/add",
        "/deck/1/card/1/delete",
        "/study/1/result",
    ]

    def test_protected_get_routes_redirect_to_login(self, client):
        """GET-accessible protected routes redirect unauthenticated users."""
        for route in self.GET_ROUTES:
            response = client.get(route, follow_redirects=True)
            assert b"Please log in to access this page." in response.data, (
                f"Route {route!r} did not block unauthenticated GET access"
            )

    def test_protected_post_routes_redirect_to_login(self, client):
        """POST-only protected routes redirect unauthenticated users."""
        for route in self.POST_ROUTES:
            response = client.post(route, data={}, follow_redirects=True)
            assert b"Please log in to access this page." in response.data, (
                f"Route {route!r} did not block unauthenticated POST access"
            )


# ── TestDeckCRUD ───────────────────────────────────────────────────────────────

class TestDeckCRUD:
    """Tests for deck create, read, edit, and delete operations."""

    def test_create_deck_success(self, client):
        """An authenticated user can create a deck."""
        register(client, "alice", "password123")
        response = create_deck(client, "Python Basics", "Core Python concepts")
        assert response.status_code == 200
        assert b"Python Basics" in response.data

    def test_create_deck_missing_name(self, client):
        """Creating a deck without a name shows a validation error."""
        register(client, "alice", "password123")
        response = create_deck(client, "")
        assert b"Deck name is required." in response.data

    def test_view_deck(self, client):
        """A created deck is visible when its page is accessed."""
        register(client, "alice", "password123")
        create_deck(client, "Biology 101")
        response = client.get("/deck/1", follow_redirects=True)
        assert response.status_code == 200
        assert b"Biology 101" in response.data

    def test_edit_deck(self, client):
        """An authenticated user can rename their deck."""
        register(client, "alice", "password123")
        create_deck(client, "Old Name")
        response = client.post(
            "/deck/1/edit",
            data={"name": "New Name", "description": ""},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"New Name" in response.data

    def test_delete_deck(self, client):
        """An authenticated user can delete their deck."""
        register(client, "alice", "password123")
        create_deck(client, "Temp Deck")
        response = client.post("/deck/1/delete", follow_redirects=True)
        assert response.status_code == 200
        # Deck should no longer appear on the dashboard
        assert b"Temp Deck" not in response.data

    def test_deck_appears_on_dashboard(self, client):
        """Created decks appear on the user's dashboard."""
        register(client, "alice", "password123")
        create_deck(client, "My Flashcards")
        response = client.get("/dashboard")
        assert b"My Flashcards" in response.data

    def test_create_deck_unauthenticated(self, client):
        """Unauthenticated deck creation is rejected."""
        response = client.post(
            "/deck/create",
            data={"name": "Sneaky Deck"},
            follow_redirects=True,
        )
        assert b"Please log in to access this page." in response.data


# ── TestCardCRUD ───────────────────────────────────────────────────────────────

class TestCardCRUD:
    """Tests for card add, edit, and delete operations within a deck."""

    def test_add_card_success(self, client):
        """A card with valid question and answer is added to the deck."""
        register(client, "alice", "password123")
        create_deck(client, "Chemistry")
        response = add_card(client, 1, "What is H2O?", "Water")
        assert response.status_code == 200
        assert b"What is H2O?" in response.data

    def test_add_card_missing_question(self, client):
        """Adding a card with no question shows a validation error."""
        register(client, "alice", "password123")
        create_deck(client, "Chemistry")
        response = add_card(client, 1, "", "Water")
        assert b"Both question and answer fields are required." in response.data

    def test_add_card_missing_answer(self, client):
        """Adding a card with no answer shows a validation error."""
        register(client, "alice", "password123")
        create_deck(client, "Chemistry")
        response = add_card(client, 1, "What is H2O?", "")
        assert b"Both question and answer fields are required." in response.data

    def test_add_card_missing_both_fields(self, client):
        """Adding a card with both fields empty shows a validation error."""
        register(client, "alice", "password123")
        create_deck(client, "Chemistry")
        response = add_card(client, 1, "", "")
        assert b"Both question and answer fields are required." in response.data

    def test_edit_card(self, client):
        """A card's question and answer can be updated."""
        register(client, "alice", "password123")
        create_deck(client, "Chemistry")
        add_card(client, 1, "Old Question", "Old Answer")
        response = client.post(
            "/deck/1/card/1/edit",
            data={"question": "New Question", "answer": "New Answer"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"New Question" in response.data

    def test_delete_card(self, client):
        """A card can be deleted from a deck."""
        register(client, "alice", "password123")
        create_deck(client, "Chemistry")
        add_card(client, 1, "What is H2O?", "Water")
        response = client.post("/deck/1/card/1/delete", follow_redirects=True)
        assert response.status_code == 200
        assert b"What is H2O?" not in response.data

    def test_multiple_cards_in_deck(self, client):
        """Multiple cards can coexist in the same deck."""
        register(client, "alice", "password123")
        create_deck(client, "Mixed Bag")
        add_card(client, 1, "Question A", "Answer A")
        add_card(client, 1, "Question B", "Answer B")
        response = client.get("/deck/1")
        assert b"Question A" in response.data
        assert b"Question B" in response.data


# ── TestDataIsolation ──────────────────────────────────────────────────────────

class TestDataIsolation:
    """Tests that users cannot access or modify each other's data."""

    def _setup_alice_deck(self, client):
        """Register alice, create a deck with one card, then log out."""
        register(client, "alice", "pass_alice")
        create_deck(client, "AliceDeck")
        add_card(client, 1, "AliceQuestion", "AliceAnswer")
        logout(client)

    def test_user_cannot_view_other_users_deck(self, client):
        """User bob cannot access alice's deck page."""
        self._setup_alice_deck(client)
        register(client, "bob", "pass_bob")
        response = client.get("/deck/1", follow_redirects=True)
        # Should 404 or redirect to dashboard, not show alice's deck
        assert b"AliceDeck" not in response.data or response.status_code == 404

    def test_user_cannot_add_card_to_other_users_deck(self, client):
        """User bob cannot add a card to alice's deck."""
        self._setup_alice_deck(client)
        register(client, "bob", "pass_bob")
        response = add_card(client, 1, "BobQuestion", "BobAnswer")
        assert b"BobQuestion" not in response.data or response.status_code == 404

    def test_user_cannot_edit_other_users_deck(self, client):
        """User bob cannot edit alice's deck."""
        self._setup_alice_deck(client)
        register(client, "bob", "pass_bob")
        response = client.post(
            "/deck/1/edit",
            data={"name": "HijackedDeck", "description": ""},
            follow_redirects=True,
        )
        # Must NOT succeed; alice's deck should not be renamed
        assert b"HijackedDeck" not in response.data or response.status_code == 404

    def test_user_cannot_delete_other_users_deck(self, client):
        """User bob cannot delete alice's deck."""
        self._setup_alice_deck(client)
        register(client, "bob", "pass_bob")
        response = client.post("/deck/1/delete", follow_redirects=True)
        # Verify alice's deck is still there when alice logs back in
        logout(client)
        login(client, "alice", "pass_alice")
        dash = client.get("/dashboard")
        assert b"AliceDeck" in dash.data

    def test_dashboard_shows_only_own_decks(self, client):
        """Each user's dashboard only shows their own decks."""
        register(client, "alice", "pass_alice")
        create_deck(client, "Alice Deck")
        logout(client)

        register(client, "bob", "pass_bob")
        create_deck(client, "Bob Deck")

        response = client.get("/dashboard")
        assert b"Bob Deck" in response.data
        assert b"Alice Deck" not in response.data
