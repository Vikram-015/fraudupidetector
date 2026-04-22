"""
fraud_engine.py
---------------
Hybrid Fraud Detection Engine.

Combines four signals:
  1. Rule-based deviation check (amount / frequency / time)
  2. EMI logic (amount + expected week of month)
  3. Special-transaction logic (rare recurring txns)
  4. Random Forest ML prediction

Returns: dict with risk_score, risk_class, action, note.
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path





_FEATURES = ["amount", "hour", "day_of_week", "week_of_month",
             "amount_deviation", "freq_deviation"]

MODEL_PATH = Path(__file__).parent / "data" / "model.pkl"
_model = None  # lazy-loaded


def _load_model():
    """Load the trained Random Forest from disk (cached)."""
    global _model
    if _model is None and MODEL_PATH.exists():
       
     return _model


# ---------------------------------------------------------------------------
# 1. EMI logic
# ---------------------------------------------------------------------------
def check_emi(amount: float, now: datetime, emis: list[dict]) -> str | None:
    """
    Returns a human-readable EMI message or None.

    Matching rules:
      - amount within ±5% AND week matches      → "Possible EMI deducted, please cross-verify"
      - amount within ±5% AND week mismatch     → "Unusual EMI timing"
      - week matches AND amount differs >5%     → "Incorrect EMI amount"
    """
    week_of_month = (now.day - 1) // 7 + 1  # 1..5

    for emi in emis:
        amt_match = abs(amount - emi["amount"]) / emi["amount"] <= 0.05
        week_match = emi["week"] == week_of_month

        if amt_match and week_match:
            return f"Possible EMI deducted ({emi['name']}), please cross-verify"
        if amt_match and not week_match:
            return f"Unusual EMI timing for {emi['name']}"
        if week_match and not amt_match:
            return f"Incorrect EMI amount for {emi['name']}"
    return None


# ---------------------------------------------------------------------------
# 2. Special transactions logic
# ---------------------------------------------------------------------------
def check_special(amount: float, specials: list[dict]) -> str | None:
    """If amount roughly matches a known rare/recurring txn, mark it safe."""
    for s in specials:
        if abs(amount - s["amount"]) / s["amount"] <= 0.10:
            return f"Recognised recurring payment: {s['name']}"
    return None


# ---------------------------------------------------------------------------
# 3. Rule-based deviation
# ---------------------------------------------------------------------------
def deviation_score(amount: float, avg_amount: float) -> float:
    """Risk score = (amount - avg) / avg.  Clamped to >=0."""
    if avg_amount <= 0:
        return 0.0
    return max(0.0, (amount - avg_amount) / avg_amount)


def classify(score: float) -> tuple[str, str]:
    """Map numeric deviation score → (class, action)."""
    if score <= 1:
        return "Normal", "allow"
    if score <= 3:
        return "Suspicious", "warn"
    if score <= 6:
        return "High Risk", "otp"
    return "Fraud", "block"


# ---------------------------------------------------------------------------
# 4. ML prediction
# ---------------------------------------------------------------------------
def ml_predict(amount: float, profile: dict, now: datetime) -> float:
    """
    Returns probability of fraud from Random Forest, or 0.0 if model not trained.
    Features must match train_model.py exactly.
    """
    model = _load_model()
    if model is None:
        return 0.0

    avg = profile["avg_amount"] or 1.0
    row = [amount, avg_amount, avg_txns]([[
        amount,
        now.hour,
        now.weekday(),
        (now.day - 1) // 7 + 1,
        (amount - avg) / avg,
        0.0,  # freq_deviation (simplified — recompute on adaptive learning)
    ]], columns=_FEATURES)
    return float(model.predict_proba(row)[0][1])


# ---------------------------------------------------------------------------
# Hybrid decision
# ---------------------------------------------------------------------------
def evaluate(amount: float, profile: dict, emis: list[dict],
             specials: list[dict], now: datetime | None = None) -> dict:
    """
    Main entry point. Returns:
        {
          "risk_score": float,
          "risk_class": "Normal|Suspicious|High Risk|Fraud",
          "action":     "allow|warn|otp|block",
          "note":       str
        }
    """
    now = now or datetime.now()

    # 1. EMI shortcut — always inform the user, never auto-block
    emi_note = check_emi(amount, now, emis)
    if emi_note:
        return {
            "risk_score": 0.0,
            "risk_class": "Normal",
            "action": "warn",
            "note": emi_note,
        }

    # 2. Recognised recurring payment → allow
    spc_note = check_special(amount, specials)
    if spc_note:
        return {
            "risk_score": 0.0,
            "risk_class": "Normal",
            "action": "allow",
            "note": spc_note,
        }

    # 3. Rule-based deviation
    dev = deviation_score(amount, profile["avg_amount"])

    # 4. ML probability
    ml_p = ml_predict(amount, profile, now)

    # Hybrid score: weighted blend (rule 60% + ML 40%, ML scaled to 0..10)
    hybrid = 0.6 * dev + 0.4 * (ml_p * 10)

    risk_class, action = classify(hybrid)

    # Late-night transactions add extra suspicion
    if now.hour < 5 and risk_class == "Normal":
        risk_class, action = "Suspicious", "warn"

    note = {
        "allow": "Transaction Successful",
        "warn":  "Unusual Activity Detected — please review",
        "otp":   "High Risk Transaction — OTP verification required",
        "block": "Transaction Blocked — looks fraudulent",
    }[action]

    return {
        "risk_score": round(hybrid, 2),
        "risk_class": risk_class,
        "action": action,
        "note": note,
    }


# ---------------------------------------------------------------------------
# Adaptive learning
# ---------------------------------------------------------------------------
def update_profile(profile: dict, new_amount: float, alpha: float = 0.1) -> dict:
    """
    Exponential moving average of avg_amount.
    Called after a user CONFIRMS a transaction was legitimate.
    """
    new_avg = (1 - alpha) * profile["avg_amount"] + alpha * new_amount
    profile["avg_amount"] = round(new_avg, 2)
    return profile
