"""Synthetic default-rate ML model.

Generates 1,000 synthetic historical deals with realistic default outcomes
based on brand tier, creator health, and payment terms, then trains a
Logistic Regression classifier. Model is persisted via ``joblib`` (safer
than raw pickle) and loaded by the risk engine at runtime.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "default_model.joblib"

TIER_DEFAULT_RATE = {
    "fortune500": 0.004,
    "enterprise": 0.018,
    "growth": 0.062,
    "seed": 0.180,
}
TIER_ORD = {"fortune500": 4, "enterprise": 3, "growth": 2, "seed": 1}
TIER_SOLVENCY_MEAN = {"fortune500": 96, "enterprise": 89, "growth": 74, "seed": 55}
TIER_HISTORY_MEAN = {"fortune500": 95, "enterprise": 88, "growth": 76, "seed": 58}


def _sample_one(rng: np.random.Generator) -> dict:
    tier = rng.choice(
        ["fortune500", "enterprise", "growth", "seed"],
        p=[0.18, 0.32, 0.32, 0.18],
    )
    solvency = float(np.clip(rng.normal(TIER_SOLVENCY_MEAN[tier], 3.5), 30, 100))
    history = float(np.clip(rng.normal(TIER_HISTORY_MEAN[tier], 4.0), 25, 100))
    followers = int(10 ** rng.uniform(3.8, 6.4))
    er = float(np.clip(rng.normal(3.8, 1.3), 0.5, 9.5))
    auth = float(np.clip(rng.normal(82, 10), 35, 99))
    terms = int(rng.choice([30, 45, 60, 75, 90]))
    deal_amount = float(np.clip(rng.lognormal(8.6, 0.7), 500, 75000))

    base = TIER_DEFAULT_RATE[tier]
    p_default = (
        base
        + (85 - solvency) * 0.003
        + (85 - history) * 0.004
        + (80 - auth) * 0.0025
        + max(0, terms - 30) * 0.0012
        + (deal_amount / 50000.0) * 0.015
    )
    p_default = float(np.clip(p_default + rng.normal(0, 0.015), 0.001, 0.85))
    defaulted = 1 if rng.random() < p_default else 0

    return {
        "tier_ord": TIER_ORD[tier],
        "solvency": solvency,
        "payment_history": history,
        "followers_log": np.log10(followers),
        "engagement_rate": er,
        "authenticity": auth,
        "payment_terms": terms,
        "deal_amount_log": np.log10(deal_amount),
        "defaulted": defaulted,
    }


def generate_dataset(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Deterministic synthetic dataset using numpy's PRNG (non-cryptographic by design)."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame([_sample_one(rng) for _ in range(n)])


def train_and_persist():
    df = generate_dataset(1000)
    X = df.drop(columns=["defaulted"])
    y = df["defaulted"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=7, stratify=y)

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=400, class_weight="balanced")),
    ])
    pipe.fit(X_tr, y_tr)

    p_te = pipe.predict_proba(X_te)[:, 1]
    try:
        auc = roc_auc_score(y_te, p_te)
    except Exception:
        auc = 0.0

    report = {
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "default_rate": float(y.mean()),
        "roc_auc": float(auc),
        "feature_names": list(X.columns),
    }

    joblib.dump({"model": pipe, "report": report}, MODEL_PATH)
    print(f"Trained on {report['n_train']} deals · AUC {report['roc_auc']:.3f} · saved {MODEL_PATH}")
    return report


if __name__ == "__main__":
    train_and_persist()
