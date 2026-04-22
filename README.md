# Hybrid ML-Based UPI Fraud Detection System with Behavioral Analysis

A beginner-friendly **Flask + Machine Learning** project that simulates a UPI
environment and detects fraudulent transactions using a **hybrid engine**
(rule-based logic + Random Forest ML model + EMI logic + special-transaction
logic + adaptive learning).

> ⚠️ This is an **educational simulation**. No real banking/UPI APIs are used.

---

## 1. Features

- ✅ Gmail-style **Login / Signup** (email + password, hashed)
- ✅ **User Behavior Profiling** (account type, avg amount, avg daily txns)
- ✅ **EMI handling** (amount + expected week of month)
- ✅ **Special transactions** (fees, insurance, rare monthly/quarterly payments)
- ✅ **Send Money** simulator + **Random transaction generator**
- ✅ **Hybrid Fraud Detection**: Rules + Random Forest ML model
- ✅ **Risk Score** → Normal / Suspicious / High Risk / Fraud
- ✅ **Smart notifications** (Allow / Warn / OTP / Block)
- ✅ **OTP simulation** for verification
- ✅ **Dashboard** with history, risk levels, spending patterns
- ✅ **Adaptive learning** (profile updates after each confirmed transaction)

---

## 2. Quick Start

```bash
# 1. Create venv (optional but recommended)
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Train the ML model (creates data/model.pkl)
python train_model.py

# 4. Run the Flask app
python app.py

# 5. Open in browser
# http://127.0.0.1:5000
```

Default flow: **Signup → Set Behavior Profile → Add EMI/Special Txns → Send Money → Dashboard**

---

## 3. Project Structure

```
upi_fraud/
├── app.py                  # Flask backend (routes + hybrid engine)
├── fraud_engine.py         # Rule-based + ML + EMI + special logic
├── train_model.py          # Trains Random Forest on sample data
├── database.py             # SQLite schema + helpers
├── requirements.txt
├── README.md
├── data/
│   ├── sample_transactions.csv   # Training dataset
│   └── model.pkl                 # Generated after training
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   ├── profile.html
│   ├── dashboard.html
│   ├── send_money.html
│   ├── emi.html
│   ├── special.html
│   └── otp.html
├── static/
│   ├── style.css
│   └── app.js
└── docs/
    ├── architecture.txt    # System architecture (text diagram)
    ├── flowchart.txt       # Fraud detection flowchart
    └── viva.md             # Short viva explanation
```

---

## 4. Hybrid Decision Engine (summary)

```
final_decision = combine(
    rule_based_check(txn, profile),     # threshold + deviation
    ml_model.predict(features),          # Random Forest
    emi_check(txn, user_emis),           # EMI matching
    special_check(txn, user_specials)    # rare-txn pattern
)
→ Risk Score → {Normal, Suspicious, High Risk, Fraud}
→ Action → {Allow, Warn, OTP, Block}
```

See `docs/flowchart.txt` and `docs/architecture.txt`.

---

## 5. Risk Score Formula

```
deviation = (txn_amount - avg_amount) / avg_amount
```

| Score range          | Class       | Action     |
|----------------------|-------------|------------|
| deviation ≤ 1        | Normal      | Allow      |
| 1 < deviation ≤ 3    | Suspicious  | Warn       |
| 3 < deviation ≤ 6    | High Risk   | OTP verify |
| deviation > 6 or ML=fraud | Fraud  | Block      |

---

## 6. Sample Dataset

`data/sample_transactions.csv` — 1,000 synthetic rows with columns:
`amount, hour, day_of_week, week_of_month, amount_deviation, freq_deviation, is_fraud`

Used by `train_model.py` to fit a Random Forest classifier.

---

## 7. Viva (1-minute pitch)

See `docs/viva.md`.
