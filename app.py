from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

DB_PATH = "purchases.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
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

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO purchases (date, description, amount, who) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d"), description, amount, who),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT date, description, amount, who FROM purchases ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    purchases = [
        {
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

    return render_template(
        "index.html",
        purchases=purchases,
        joe_independent=joe_independent,
        kath_independent=kath_independent,
        joint_total=joint_total,
        joe_owes=joe_owes,
        kath_owes=kath_owes
    )

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