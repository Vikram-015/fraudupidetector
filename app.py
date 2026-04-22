"""
app.py
------
Flask backend for the Hybrid UPI Fraud Detection System.

Routes
------
/                  → redirect to /login or /dashboard
/signup, /login    → auth (email + password, hashed)
/logout
/profile           → set/update behavior profile
/emi               → manage EMIs
/special           → manage special/recurring transactions
/send              → simulate "Send Money"
/random            → generate a random transaction (for demos)
/otp/<txn_id>      → OTP verification (simulated)
/dashboard         → history, risk levels, spending patterns
/confirm/<txn_id>  → "This was me"  (adaptive learning kicks in here)
/report/<txn_id>   → "Report fraud"
"""

from __future__ import annotations

import random
from datetime import datetime
from functools import wraps

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import database as db
import fraud_engine as fe

app = Flask(__name__)
app.secret_key = "change-me-in-production"  # demo only

db.init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def current_user():
    return db.fetch_one("SELECT * FROM users WHERE id = ?", (session["user_id"],))


def user_profile_dict():
    u = current_user()
    return {
        "avg_amount":     u["avg_amount"],
        "avg_daily_txns": u["avg_daily_txns"],
        "account_type":   u["account_type"],
    }


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        name  = request.form.get("full_name", "").strip()
        pw    = request.form["password"]

        if db.fetch_one("SELECT 1 FROM users WHERE email = ?", (email,)):
            flash("Email already registered", "error")
            return redirect(url_for("signup"))

        uid = db.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
            (email, generate_password_hash(pw), name),
        )
        session["user_id"] = uid
        flash("Account created — please set up your behavior profile.", "ok")
        return redirect(url_for("profile"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw    = request.form["password"]
        user  = db.fetch_one("SELECT * FROM users WHERE email = ?", (email,))
        if user and check_password_hash(user["password_hash"], pw):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Profile / EMI / Special
# ---------------------------------------------------------------------------
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        db.execute(
            """UPDATE users 
               SET account_type = ?, avg_amount = ?, avg_daily_txns = ?
               WHERE id = ?""",
            (
                request.form.get('account_type'),
                float(request.form.get('avg_amount')),
                float(request.form.get('avg_daily_txns')),
                session['user_id']
            )
        )

        flash("Profile updated successfully", "ok")
        return redirect(url_for('dashboard'))

    return render_template('profile.html', user=current_user())


@app.route("/emi", methods=["GET", "POST"])
@login_required
def emi():
    if request.method == "POST":
        db.execute(
            "INSERT INTO emis (user_id, name, amount, week) VALUES (?,?,?,?)",
            (session["user_id"],
             request.form["name"],
             float(request.form["amount"]),
             int(request.form["week"])),
        )
        flash("EMI added", "ok")
        return redirect(url_for("emi"))

    emis = db.fetch_all("SELECT * FROM emis WHERE user_id = ?",
                        (session["user_id"],))
    return render_template("emi.html", emis=emis)


@app.route("/special", methods=["GET", "POST"])
@login_required
def special():
    if request.method == "POST":
        db.execute(
            """INSERT INTO special_txns (user_id, name, amount, frequency_months)
               VALUES (?,?,?,?)""",
            (session["user_id"],
             request.form["name"],
             float(request.form["amount"]),
             int(request.form["frequency_months"])),
        )
        flash("Special transaction saved", "ok")
        return redirect(url_for("special"))

    rows = db.fetch_all("SELECT * FROM special_txns WHERE user_id = ?",
                        (session["user_id"],))
    return render_template("special.html", specials=rows)


# ---------------------------------------------------------------------------
# Send money (the heart of the demo)
# ---------------------------------------------------------------------------
def _evaluate_and_store(receiver: str, amount: float):
    """Run hybrid engine, persist transaction, return the new row id + result."""
    uid = session["user_id"]
    profile = user_profile_dict()
    emis = [dict(r) for r in db.fetch_all(
        "SELECT * FROM emis WHERE user_id = ?", (uid,))]
    specials = [dict(r) for r in db.fetch_all(
        "SELECT * FROM special_txns WHERE user_id = ?", (uid,))]

    result = fe.evaluate(amount, profile, emis, specials)

    txn_id = db.execute(
        """INSERT INTO transactions
           (user_id, receiver, amount, risk_score, risk_class, action, note)
           VALUES (?,?,?,?,?,?,?)""",
        (uid, receiver, amount, result["risk_score"],
         result["risk_class"], result["action"], result["note"]),
    )
    return txn_id, result


@app.route("/send", methods=["GET", "POST"])
@login_required
def send():
    if request.method == "POST":
        receiver = request.form["receiver"].strip()
        amount   = float(request.form["amount"])
        txn_id, result = _evaluate_and_store(receiver, amount)

        # Route based on action
        if result["action"] == "otp":
            return redirect(url_for("otp", txn_id=txn_id))
        if result["action"] == "block":
            flash(f"❌ {result['note']}", "error")
            return redirect(url_for("dashboard"))

        flash(f"✅ {result['note']} (₹{amount:.0f} → {receiver})",
              "ok" if result["action"] == "allow" else "warn")
        return redirect(url_for("dashboard"))

    return render_template("send_money.html")


@app.route("/random")
@login_required
def random_txn():
    """Demo helper: generate a single random transaction."""
    receiver = random.choice(["alice@upi", "bob@upi", "store@upi", "unknown@xyz"])
    # 70% normal, 30% suspicious-or-worse
    amount = random.choice([
        random.randint(100, 1500),    # normal-ish
        random.randint(100, 1500),
        random.randint(8000, 50000),  # potentially fraud
    ])
    txn_id, result = _evaluate_and_store(receiver, amount)
    flash(f"Random txn ₹{amount} → {receiver} : {result['risk_class']} "
          f"({result['note']})",
          "ok" if result["action"] == "allow" else "warn")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# OTP simulation
# ---------------------------------------------------------------------------
@app.route("/otp/<int:txn_id>", methods=["GET", "POST"])
@login_required
def otp(txn_id):
    txn = db.fetch_one("SELECT * FROM transactions WHERE id = ? AND user_id = ?",
                       (txn_id, session["user_id"]))
    if not txn:
        return redirect(url_for("dashboard"))

    # In a real system the OTP would be sent by SMS — here it's hardcoded.
    DEMO_OTP = "1234"

    if request.method == "POST":
        if request.form["otp"] == DEMO_OTP:
            db.execute("UPDATE transactions SET action = 'allow', note = ?, "
                       "confirmed = 1 WHERE id = ?",
                       ("Verified by OTP & approved", txn_id))
            flash("✅ Transaction verified and approved", "ok")
        else:
            db.execute("UPDATE transactions SET action = 'block', note = ? "
                       "WHERE id = ?",
                       ("Blocked: wrong OTP", txn_id))
            flash("❌ Wrong OTP — transaction blocked", "error")
        return redirect(url_for("dashboard"))

    return render_template("otp.html", txn=txn, demo_otp=DEMO_OTP)


# ---------------------------------------------------------------------------
# Confirm / Report   (+ adaptive learning)
# ---------------------------------------------------------------------------
@app.route("/confirm/<int:txn_id>")
@login_required
def confirm(txn_id):
    txn = db.fetch_one("SELECT * FROM transactions WHERE id = ? AND user_id = ?",
                       (txn_id, session["user_id"]))
    if txn:
        db.execute("UPDATE transactions SET confirmed = 1 WHERE id = ?", (txn_id,))
        # Adaptive learning: nudge avg_amount toward this confirmed amount
        prof = user_profile_dict()
        new_prof = fe.update_profile(prof, txn["amount"])
        db.execute("UPDATE users SET avg_amount = ? WHERE id = ?",
                   (new_prof["avg_amount"], session["user_id"]))
        flash("Marked as legitimate. Behavior profile updated.", "ok")
    return redirect(url_for("dashboard"))


@app.route("/report/<int:txn_id>")
@login_required
def report(txn_id):
    db.execute("UPDATE transactions SET reported = 1, action = 'block', "
               "risk_class = 'Fraud', note = ? WHERE id = ? AND user_id = ?",
               ("Reported by user as fraud", txn_id, session["user_id"]))
    flash("Reported as fraud. Thanks — we’ll learn from this.", "warn")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    all_txns = db.fetch_all(
    "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC",
    (uid,)
)

    recent_txns = all_txns[:3]  # only last 3

# Spending pattern
    pattern = {"Normal": 0, "Suspicious": 0, "High Risk": 0, "Fraud": 0}

    for t in all_txns:   # ✅ FIXED HERE
        pattern[t["risk_class"]] = pattern.get(t["risk_class"], 0) + t["amount"]

    return render_template(
       "dashboard.html",
        user=current_user(),
        txns=recent_txns,
        all_txns=all_txns,
        pattern=pattern
)



# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
