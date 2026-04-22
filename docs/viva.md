# Viva — 1-minute pitch

**Project:** Hybrid Machine-Learning–Based UPI Fraud Detection System with
Behavioral Analysis.

**Problem.** UPI fraud is rising because pure rule-based systems either flag
legitimate large payments (false positives) or miss subtle anomalies
(false negatives).

**My approach — Hybrid Engine.** I combine four signals:

1. **Behavioral baseline** per user (account type, average amount, average
   daily transaction count).
2. **Rule-based deviation:** `risk = (amount − avg) / avg`.
3. **Random Forest ML model** trained on a synthetic dataset of 1,000
   transactions with features `amount, hour, day_of_week, week_of_month,
   amount_deviation, freq_deviation`.
4. **Domain logic:** EMI matcher (amount + expected week of month) and
   special/recurring transactions (fees, insurance) so genuine large payments
   aren’t flagged.

The hybrid score is `0.6 × rule_deviation + 0.4 × (ml_prob × 10)`, mapped to
**Normal / Suspicious / High Risk / Fraud**, which decides the action:
**Allow / Warn / OTP verify / Block**.

**Adaptive learning.** When a user confirms a transaction was theirs, I
update their `avg_amount` with an exponential moving average — the model
gradually learns each user’s real behavior.

**Stack.** Flask (backend), SQLite (users, EMIs, special txns,
transactions), scikit-learn Random Forest (model.pkl), HTML/CSS/JS frontend
with a Gmail-style login.

**No real banking APIs** — every transaction is simulated internally, which
makes it safe to demo and easy for others to run locally with one command.

**Why hybrid?** Rules are explainable but rigid; ML is flexible but a black
box. Combining them gives both the **interpretability** of rules and the
**generalization** of ML, plus the user-aware behavioral context that
generic models lack.
