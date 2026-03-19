# CMSC 495 Capstone – Study Flashcard Application

**Course**: UMGC CMSC 495 – Current Trends and Projects in Computer Science  
**Group**: Group 2  
**Project Lead**: Deen Ojo  
**Phase**: I – Core Functionality

---

## Overview

A web-based flashcard study tool built with Python/Flask and SQLite.  
Users can register, create flash-card decks, add question/answer cards, and self-assess their mastery in study mode.

---

## Technology Stack

| Component | Version |
|-----------|---------|
| Python    | 3.13.x  |
| Flask     | 3.0.3   |
| Werkzeug  | 3.0.3   |
| SQLite    | (bundled with Python) |
| pytest    | 8.1.1   |

---

## Project Structure

```
CMSC495_FlashcardApp/
├── app.py            # Flask application – routes and business logic
├── config.py         # Configuration (SECRET_KEY, DATABASE path)
├── database.py       # Database helpers (get_db, init_db)
├── requirements.txt  # Pinned Python dependencies
├── static/
│   └── style.css     # Application stylesheet
├── templates/        # Jinja2 HTML templates
│   ├── base.html
│   ├── home.html
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── deck.html
│   ├── edit_deck.html
│   ├── edit_card.html
│   ├── study.html
│   ├── progress.html
│   ├── 404.html
│   └── 500.html
└── tests/
    ├── __init__.py
    └── test_app.py   # pytest unit tests
```

---

## Setup Instructions

### 1. Clone / navigate to the project directory

```
cd C:\Users\olait\Documents\CMSC495_FlashcardApp
```

### 2. (Recommended) Create and activate a virtual environment

```
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

Dependency versions:
- `Flask==3.0.3`
- `Werkzeug==3.0.3`
- `pytest==8.1.1`

### 4. Initialise the database

```
python database.py
```

This creates `flashcards.db` in the project root with the Users, Decks, and Cards tables.

---

## Running the Application

```
python app.py
```

Open your browser at **http://127.0.0.1:5000**.

To enable debug mode set the environment variable before running:

```
$env:FLASK_DEBUG = "1"   # PowerShell
python app.py
```

---

## Running Tests

```
pytest tests/ -v
```

All tests use an isolated temporary SQLite database; the production database is never touched.

### Test Cases

| Class | Test | Description |
|-------|------|-------------|
| TestRegistration | test_register_success | Valid credentials create an account |
| TestRegistration | test_register_duplicate_username | Duplicate username returns error |
| TestRegistration | test_register_missing_username | Empty username returns validation error |
| TestRegistration | test_register_missing_password | Empty password returns validation error |
| TestRegistration | test_register_missing_both_fields | Both fields empty returns validation error |
| TestAuthentication | test_login_valid_credentials | Correct credentials log the user in |
| TestAuthentication | test_login_wrong_password | Wrong password returns error |
| TestAuthentication | test_login_unknown_username | Unknown user returns error |
| TestAuthentication | test_login_missing_fields | Empty fields return validation error |
| TestAuthentication | test_logout_redirects_to_home | Logout clears session and redirects |
| TestAuthentication | test_session_cleared_after_logout | Dashboard inaccessible after logout |
| TestAccessControl | test_protected_routes_redirect_to_login | All protected routes block unauthenticated requests |
| TestDeckCRUD | test_create_deck_success | Deck creation succeeds with valid name |
| TestDeckCRUD | test_create_deck_missing_name | Empty deck name returns error |
| TestDeckCRUD | test_view_deck | Deck page shows deck name |
| TestDeckCRUD | test_edit_deck | Deck can be renamed |
| TestDeckCRUD | test_delete_deck | Deck is removed after deletion |
| TestDeckCRUD | test_deck_appears_on_dashboard | Deck is listed on dashboard |
| TestDeckCRUD | test_create_deck_unauthenticated | Unauthenticated creation is blocked |
| TestCardCRUD | test_add_card_success | Card is added with valid fields |
| TestCardCRUD | test_add_card_missing_question | Missing question returns error |
| TestCardCRUD | test_add_card_missing_answer | Missing answer returns error |
| TestCardCRUD | test_add_card_missing_both_fields | Both fields empty returns error |
| TestCardCRUD | test_edit_card | Card question/answer can be updated |
| TestCardCRUD | test_delete_card | Card is removed after deletion |
| TestCardCRUD | test_multiple_cards_in_deck | Multiple cards coexist in one deck |
| TestDataIsolation | test_user_cannot_view_other_users_deck | Cross-user deck access blocked |
| TestDataIsolation | test_user_cannot_add_card_to_other_users_deck | Cross-user card add blocked |
| TestDataIsolation | test_user_cannot_edit_other_users_deck | Cross-user deck edit blocked |
| TestDataIsolation | test_user_cannot_delete_other_users_deck | Cross-user deck delete blocked |
| TestDataIsolation | test_dashboard_shows_only_own_decks | Dashboard only shows user's own decks |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key-change-in-prod` | Flask session secret |
| `DATABASE` | `flashcards.db` (project root) | SQLite database file path |

Set these in your shell before running for production use.

---

## Notes

- Phase I uses form-based self-assessment for study mode (checkbox per card).  
- Phase II will add card-flip animation and enhanced progress tracking.
