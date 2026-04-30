"""ML drift monitoring via Population Stability Index (PSI).

Compares feature distributions between the synthetic training set and a
candidate production set (``deals_labeled`` MongoDB collection, when
populated). Returns per-feature PSI scores and a global drift verdict.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import joblib

from ml_trainer import generate_dataset, MODEL_PATH, TIER_ORD

logger = logging.getLogger("mypay.drift")


def _psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index."""
    if len(actual) == 0:
        return 0.0
    edges = np.quantile(expected, np.linspace(0, 1, bins + 1))
    edges[0] = -np.inf
    edges[-1] = np.inf
    edges = np.unique(edges)
    exp_counts, _ = np.histogram(expected, bins=edges)
    act_counts, _ = np.histogram(actual, bins=edges)
    exp_pct = np.where(exp_counts == 0, 1e-4, exp_counts) / max(1, exp_counts.sum())
    act_pct = np.where(act_counts == 0, 1e-4, act_counts) / max(1, act_counts.sum())
    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def _verdict(psi: float) -> str:
    if psi < 0.1:
        return "stable"
    if psi < 0.25:
        return "watch"
    return "drift"


def _deal_to_features(deal: Dict, brand: Dict, social: Dict) -> Dict:
    followers = (social or {}).get("followers", 50000) or 50000
    return {
        "tier_ord": TIER_ORD.get((brand or {}).get("tier", "growth"), 2),
        "solvency": (brand or {}).get("solvency_score", 70),
        "payment_history": (brand or {}).get("payment_history_score", 70),
        "followers_log": float(np.log10(max(1, followers))),
        "engagement_rate": (social or {}).get("engagement_rate", 3.0) or 3.0,
        "authenticity": (social or {}).get("authenticity_score", 75) or 75,
        "payment_terms": deal.get("payment_terms_days", 60),
        "deal_amount_log": float(np.log10(max(1, deal.get("deal_amount", 1000)))),
    }


async def _production_feature_frame(db, min_status: bool = True) -> Optional[pd.DataFrame]:
    query = {"risk": {"$ne": None}} if min_status else {}
    deals = await db.deals.find(query, {"_id": 0}).to_list(5000)
    if not deals:
        return None
    brands_by_id = {b["id"]: b async for b in db.brands.find({}, {"_id": 0})}
    socials_by_user = {s["user_id"]: s async for s in db.social_profiles.find({}, {"_id": 0})}
    rows = [
        _deal_to_features(d, brands_by_id.get(d.get("brand_id"), {}), socials_by_user.get(d.get("user_id"), {}))
        for d in deals
    ]
    return pd.DataFrame(rows)


async def compute_drift_report(db) -> Dict:
    baseline = generate_dataset(1000, seed=42)
    feature_names = [c for c in baseline.columns if c != "defaulted"]

    live = await _production_feature_frame(db)
    if live is None:
        return _empty_drift(feature_names, len(baseline))

    feats: List[Dict] = []
    psis: List[float] = []
    for f in feature_names:
        psi = _psi(baseline[f].values, live[f].values)
        feats.append({
            "name": f,
            "psi": round(psi, 4),
            "verdict": _verdict(psi),
            "training_mean": round(float(baseline[f].mean()), 3),
            "production_mean": round(float(live[f].mean()), 3),
        })
        psis.append(psi)

    global_psi = float(np.mean(psis))
    return {
        "n_production": int(len(live)),
        "n_training": int(len(baseline)),
        "global_psi": round(global_psi, 4),
        "verdict": _verdict(global_psi),
        "features": feats,
        "message": _drift_message(_verdict(global_psi)),
    }


def _empty_drift(feature_names: List[str], n_training: int) -> Dict:
    return {
        "n_production": 0,
        "n_training": int(n_training),
        "global_psi": 0.0,
        "verdict": "insufficient_data",
        "features": [{"name": f, "psi": 0.0, "verdict": "insufficient_data"} for f in feature_names],
        "message": "No production deals with risk scores yet. Drift monitoring activates once you accumulate scored deals.",
    }


def _drift_message(verdict: str) -> str:
    return {
        "stable": "Distributions align with training data.",
        "watch": "Mild drift detected — monitor weekly, no retrain required.",
        "drift": "Significant drift — consider retraining on recent production data.",
    }.get(verdict, "")


async def _labeled_production_frame(db) -> List[Dict]:
    labeled = await db.deals_labeled.find({"default_label": {"$in": [0, 1]}}, {"_id": 0}).to_list(20000)
    if not labeled:
        return []
    brands_by_id = {b["id"]: b async for b in db.brands.find({}, {"_id": 0})}
    socials_by_user = {s["user_id"]: s async for s in db.social_profiles.find({}, {"_id": 0})}
    out = []
    for d in labeled:
        feats = _deal_to_features(d, brands_by_id.get(d.get("brand_id"), {}), socials_by_user.get(d.get("user_id"), {}))
        feats["defaulted"] = int(d["default_label"])
        out.append(feats)
    return out


def _build_training_frame(synth_df: pd.DataFrame, prod_rows: List[Dict], sample_weight: float):
    synth_weight = 1 - sample_weight if prod_rows else 1.0
    rows = []
    weights = []
    for _, r in synth_df.iterrows():
        rows.append(r.to_dict())
        weights.append(synth_weight)
    for r in prod_rows:
        rows.append(r)
        weights.append(sample_weight)
    df = pd.DataFrame(rows)
    X = df.drop(columns=["defaulted"])
    y = df["defaulted"]
    return X, y, np.array(weights)


def _fit_pipeline(X, y, w):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score

    X_tr, X_te, y_tr, y_te, w_tr, _ = train_test_split(X, y, w, test_size=0.2, random_state=7, stratify=y)
    pipe = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=400, class_weight="balanced"))])
    pipe.fit(X_tr, y_tr, clf__sample_weight=w_tr)
    try:
        auc = float(roc_auc_score(y_te, pipe.predict_proba(X_te)[:, 1]))
    except Exception:
        auc = 0.0
    return pipe, int(len(X_tr)), int(len(X_te)), auc


async def retrain_from_production(db, sample_weight: float = 0.7) -> Dict:
    """Retrain blending synthetic baseline with labelled production rows."""
    synth = generate_dataset(1000, seed=42)
    prod_rows = await _labeled_production_frame(db)
    X, y, w = _build_training_frame(synth, prod_rows, sample_weight)
    pipe, n_train, n_test, auc = _fit_pipeline(X, y, w)

    report = {
        "n_train": n_train,
        "n_test": n_test,
        "n_production": len(prod_rows),
        "default_rate": float(y.mean()),
        "roc_auc": auc,
        "feature_names": list(X.columns),
    }
    joblib.dump({"model": pipe, "report": report}, MODEL_PATH)

    # Force reload in-process
    try:
        import ml_service
        ml_service.reset()
    except Exception:
        pass

    logger.info(f"Retrained · AUC {auc:.3f} · prod_rows={len(prod_rows)}")
    return report
