"""
train_model.py
--------------
1. Generates a synthetic dataset (data/sample_transactions.csv) if missing.
2. Trains a Random Forest classifier on it.
3. Saves model to data/model.pkl.

Run once before starting the app:
    python train_model.py
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "sample_transactions.csv"
MODEL_PATH = DATA_DIR / "model.pkl"

FEATURES = ["amount", "hour", "day_of_week", "week_of_month",
            "amount_deviation", "freq_deviation"]


def generate_dataset(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Synthetic mix of normal and fraudulent UPI-like transactions."""
    rng = np.random.default_rng(seed)

    # 85% normal, 15% fraud
    n_normal = int(n * 0.85)
    n_fraud = n - n_normal

    normal = pd.DataFrame({
        "amount":            rng.normal(900, 200, n_normal).clip(50, 3000),
        "hour":              rng.integers(7, 22, n_normal),
        "day_of_week":       rng.integers(0, 7, n_normal),
        "week_of_month":     rng.integers(1, 5, n_normal),
        "amount_deviation":  rng.normal(0.1, 0.3, n_normal).clip(-1, 1.5),
        "freq_deviation":    rng.normal(0.0, 0.3, n_normal),
        "is_fraud":          0,
    })

    fraud = pd.DataFrame({
        "amount":            rng.normal(15000, 8000, n_fraud).clip(2000, 80000),
        "hour":              rng.choice([0, 1, 2, 3, 4, 23], n_fraud),  # odd hours
        "day_of_week":       rng.integers(0, 7, n_fraud),
        "week_of_month":     rng.integers(1, 5, n_fraud),
        "amount_deviation":  rng.normal(8, 4, n_fraud).clip(2, 50),
        "freq_deviation":    rng.normal(3, 2, n_fraud).clip(0, 10),
        "is_fraud":          1,
    })

    df = pd.concat([normal, fraud], ignore_index=True).sample(frac=1, random_state=seed)
    df.to_csv(CSV_PATH, index=False)
    print(f"✅ Wrote {len(df)} rows to {CSV_PATH}")
    return df


def train():
    df = generate_dataset() if not CSV_PATH.exists() else pd.read_csv(CSV_PATH)

    X = df[FEATURES]
    y = df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=200, max_depth=8, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    print("\n=== Test set performance ===")
    print(classification_report(y_test, model.predict(X_test),
                                target_names=["normal", "fraud"]))

    joblib.dump(model, MODEL_PATH)
    print(f"✅ Saved model → {MODEL_PATH}")


if __name__ == "__main__":
    # Always regenerate so users can rerun easily
    generate_dataset()
    train()
