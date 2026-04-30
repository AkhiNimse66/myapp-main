"""ML-backed default probability service.

Loads the serialised LogisticRegression model at startup (or trains on first
call). Falls back silently to the heuristic if the model is unavailable.
Uses ``joblib`` instead of raw ``pickle`` to avoid the arbitrary-code-execution
surface from pickle deserialisation.
"""
from __future__ import annotations
import logging
from typing import Optional

import numpy as np
import joblib

from ml_trainer import MODEL_PATH, TIER_ORD

logger = logging.getLogger("mypay.ml")
_MODEL = None
_REPORT: Optional[dict] = None


def _load_from_disk() -> None:
    global _MODEL, _REPORT
    if not MODEL_PATH.exists():
        return
    try:
        pkg = joblib.load(MODEL_PATH)
        _MODEL = pkg.get("model")
        _REPORT = pkg.get("report")
        if _MODEL is not None and _REPORT is not None:
            logger.info(f"ML model loaded · AUC {_REPORT.get('roc_auc'):.3f}")
    except Exception as e:
        logger.warning(f"Failed loading ML model from {MODEL_PATH}: {e}")


def _ensure_loaded() -> None:
    if _MODEL is not None:
        return
    if not MODEL_PATH.exists():
        try:
            from ml_trainer import train_and_persist
            train_and_persist()
        except Exception as e:
            logger.warning(f"ML training failed: {e}")
            return
    _load_from_disk()


def predict_default_prob(*, brand: dict, social: dict, deal_amount: float, payment_terms_days: int):
    _ensure_loaded()
    if _MODEL is None or _REPORT is None:
        return None
    followers = (social or {}).get("followers", 50000) or 50000
    feats = np.array([[
        TIER_ORD.get(brand.get("tier", "growth"), 2),
        brand.get("solvency_score", 70),
        brand.get("payment_history_score", 70),
        np.log10(max(1, followers)),
        (social or {}).get("engagement_rate", 3.0) or 3.0,
        (social or {}).get("authenticity_score", 75) or 75,
        payment_terms_days,
        np.log10(max(1, deal_amount)),
    ]])
    try:
        p = float(_MODEL.predict_proba(feats)[0, 1])
        return {
            "default_prob": round(p, 4),
            "survival_prob": round(1 - p, 4),
            "ml_score": round((1 - p) * 100, 1),
            "model_auc": round(_REPORT.get("roc_auc", 0), 3),
        }
    except Exception as e:
        logger.warning(f"ML predict failed: {e}")
        return None


def model_report():
    _ensure_loaded()
    return _REPORT


def reset():
    """Force reload on next access (used after retraining)."""
    global _MODEL, _REPORT
    _MODEL, _REPORT = None, None
