from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, date
import sqlite3
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)

DB_PATH = "purchases.db"
EXPIRY_DATE = date(2025, 12, 28)


def get_db_connection():
    """
    Return a database connection.
    - If DATABASE_URL is set (e.g. on Render), use PostgreSQL.
    - Otherwise, use local SQLite so development still works.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Postgres connection with dict-style rows
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        # Local SQLite for development
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """Create the purchases table in whichever database we're using."""
    db_url = os.environ.get("DATABASE_URL")
    conn = get_db_connection()
    cur = conn.cursor()
    if db_url:
        # Postgres: use SERIAL for auto-incrementing id
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                who TEXT NOT NULL
            )
            """
        )
    else:
        # SQLite: use INTEGER PRIMARY KEY AUTOINCREMENT
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                who TEXT NOT NULL
            )
            """
        )
    conn.commit()
    conn.close()


# Ensure database exists when app starts
init_db()


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount_str = request.form.get("amount", "0").strip()
        who = request.form.get("who", "joint")

        if not description or not amount_str:
            return redirect(url_for("index"))

        try:
            amount = float(amount_str)
        except ValueError:
            return redirect(url_for("index"))

        db_url = os.environ.get("DATABASE_URL")
        conn = get_db_connection()
        cur = conn.cursor()
        if db_url:
            # Postgres uses %s placeholders
            cur.execute(
                "INSERT INTO purchases (date, description, amount, who) VALUES (%s, %s, %s, %s)",
                (datetime.now().strftime("%Y-%m-%d"), description, amount, who),
            )
        else:
            # SQLite uses ? placeholders
            cur.execute(
                "INSERT INTO purchases (date, description, amount, who) VALUES (?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d"), description, amount, who),
            )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, description, amount, who FROM purchases ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    purchases = [
        {
            "id": row["id"],
            "date": row["date"],
            "description": row["description"],
            "amount": row["amount"],
            "who": row["who"],
        }
        for row in rows
    ]

    joe_independent = sum(p["amount"] for p in purchases if p["who"] == "joe")
    kath_independent = sum(p["amount"] for p in purchases if p["who"] == "kath")
    joint_total = sum(p["amount"] for p in purchases if p["who"] == "joint")

    joe_owes = joe_independent + joint_total / 2
    kath_owes = kath_independent + joint_total / 2

    # Calculate a warning message with a live countdown until the free database tier expiry
    today = date.today()
    days_left = (EXPIRY_DATE - today).days
    if days_left > 0:
        expiry_warning = (
            f"Heads up: the free database tier expires in {days_left} day"
            f"{'s' if days_left != 1 else ''} on 28 December 2025. "
            "Consider upgrading or exporting your data so you don't lose access."
        )
    elif days_left == 0:
        expiry_warning = (
            "Heads up: the free database tier expires today (28 December 2025). "
            "After today you may lose access unless you upgrade or export your data."
        )
    else:
        expiry_warning = (
            "Heads up: the free database tier expiry date (28 December 2025) has passed. "
            "If the database becomes paused, you may need to upgrade or export your data."
        )

    return render_template(
        "index.html",
        purchases=purchases,
        joe_independent=joe_independent,
        kath_independent=kath_independent,
        joint_total=joint_total,
        joe_owes=joe_owes,
        kath_owes=kath_owes,
        expiry_warning=expiry_warning,
    )


@app.post("/delete/<int:purchase_id>")
def delete_purchase(purchase_id):
    """Delete a single purchase row and return to the main page."""
    db_url = os.environ.get("DATABASE_URL")
    conn = get_db_connection()
    cur = conn.cursor()
    if db_url:
        cur.execute("DELETE FROM purchases WHERE id = %s", (purchase_id,))
    else:
        cur.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.post("/clear")
def clear_purchases():
    """Delete all rows from the purchases table and return to the main page."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM purchases")
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)