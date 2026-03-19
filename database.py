"""database.py - Database connection and schema initialization.

Provides get_db() for obtaining a SQLite connection and init_db() for
creating all required tables on first run.  Both functions read the
database path from config.DATABASE so that the test suite can substitute
a temporary file without restarting the interpreter.
"""

import sqlite3
import config  # imported as module so tests can override config.DATABASE


def get_db():
    """Open and return a new SQLite connection with row factory and FK support.

    Returns:
        sqlite3.Connection: An open connection to the application database.
            Callers are responsible for calling .close() when finished.
    """
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row          # rows accessible by column name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all application tables if they do not already exist.

    Tables created:
        users  - registered user accounts
        decks  - flashcard decks owned by users
        cards  - question-answer pairs belonging to decks
    """
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS decks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            description TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS cards (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id    INTEGER NOT NULL,
            question   TEXT    NOT NULL,
            answer     TEXT    NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (deck_id) REFERENCES decks(id)
        );
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at: {config.DATABASE}")
