"""Create and seed the SQLite database for local development."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


def create_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            signup_date TEXT,
            country TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            event_type TEXT,
            event_time TEXT,
            amount REAL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            order_date TEXT,
            order_value REAL,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    conn.commit()


def seed_data(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute("DELETE FROM events")
    cur.execute("DELETE FROM orders")
    cur.execute("DELETE FROM users")

    users = [
        (1, "Alice", "alice@example.com", "2025-01-10", "US"),
        (2, "Bob", "bob@example.com", "2025-01-15", "US"),
        (3, "Carol", None, "2025-02-01", "CA"),  # intentional null email
        (4, "Dan", "dan@example.com", "2025-02-10", "UK"),
        (5, "Dan", "dan@example.com", "2025-02-10", "UK"),  # intentional duplicate-like row
    ]

    events = [
        (1, 1, "login", "2025-02-11T10:00:00", 0.0),
        (2, 1, "purchase", "2025-02-11T10:10:00", 120.0),
        (3, 2, "login", "2025-02-12T12:00:00", 0.0),
        (4, 3, "purchase", "2025-02-12T12:30:00", 99999.0),  # outlier amount
        (5, 3, "purchase", "2025-02-12T12:30:00", 99999.0),  # intentional duplicate event
    ]

    orders = [
        (101, 1, "2025-02-11", 120.0, "completed"),
        (102, 2, "2025-02-13", 75.5, "completed"),
        (103, 3, "2025-02-13", None, "pending"),  # intentional null order_value
        (104, 4, "2025-02-14", 50.0, "cancelled"),
        (105, 4, "2025-02-14", 50.0, "cancelled"),  # intentional duplicate-like order
    ]

    cur.executemany(
        "INSERT INTO users (user_id, name, email, signup_date, country) VALUES (?, ?, ?, ?, ?)",
        users,
    )
    cur.executemany(
        "INSERT INTO events (event_id, user_id, event_type, event_time, amount) VALUES (?, ?, ?, ?, ?)",
        events,
    )
    cur.executemany(
        "INSERT INTO orders (order_id, user_id, order_date, order_value, status) VALUES (?, ?, ?, ?, ?)",
        orders,
    )

    conn.commit()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        create_tables(conn)
        seed_data(conn)
    print(f"Database created and seeded at: {DB_PATH}")


if __name__ == "__main__":
    main()
