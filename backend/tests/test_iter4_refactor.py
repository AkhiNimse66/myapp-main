"""Iteration-4 refactor regression tests.

Focuses on the refactor checklist:
 (1) No banned imports (`import random`, `import pickle`) in backend Python sources.
 (2) ML default model still loads from default_model.joblib and /api/ml/status exposes model_auc.
 (3) /api/deals/{id}/analyze returns risk.ml with {default_prob, survival_prob, ml_score, model_auc}.
 (4) All 6 advance-rate ladder branches map to correct score ranges (via risk_engine directly).
 (5) /api/admin/ml/drift and /api/admin/ml/retrain still return expected payloads.
 (6) Contract download supports header auth, query auth, rejects missing/invalid token + foreign creator + missing contract.
"""
import io
import os
import re
import subprocess
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"

CREATOR = {"email": "creator@mypay.io", "password": "Creator@123"}
ADMIN = {"email": "admin@mypay.io", "password": "Admin@123"}

BACKEND_DIR = Path("/app/backend")


# -------------------- helpers / fixtures --------------------
def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    body = r.json()
    return body.get("token") or body.get("access_token"), body["user"]


@pytest.fixture(scope="module")
def creator_ctx():
    tok, usr = _login(CREATOR)
    return {"token": tok, "user": usr, "h": {"Authorization": f"Bearer {tok}"}}


@pytest.fixture(scope="module")
def admin_ctx():
    tok, usr = _login(ADMIN)
    return {"token": tok, "user": usr, "h": {"Authorization": f"Bearer {tok}"}}


# ---------- (1) banned imports grep ----------
class TestBannedImports:
    def test_no_import_random_or_pickle(self):
        """Security: must not have `import random` or `import pickle` statements."""
        py_files = [p for p in BACKEND_DIR.rglob("*.py")
                    if "__pycache__" not in p.parts and "tests" not in p.parts]
        assert len(py_files) > 0, "no backend python files scanned"
        banned_re = re.compile(
            r"^\s*(import\s+(random|pickle)(\s|$|,)|from\s+(random|pickle)\s+import\s)",
            re.MULTILINE,
        )
        offenders = []
        for p in py_files:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for m in banned_re.finditer(txt):
                offenders.append(f"{p.relative_to(BACKEND_DIR)}: {m.group(0).strip()}")
        assert not offenders, f"banned imports still present: {offenders}"

    def test_legacy_pkl_deleted_joblib_present(self):
        assert (BACKEND_DIR / "default_model.joblib").exists(), "default_model.joblib missing"
        # legacy pickle may or may not exist; if present it should at least be <100KB (tiny legacy)
        # Spec says it was deleted -> assert absence.
        assert not (BACKEND_DIR / "default_model.pkl").exists(), "legacy pickle should be deleted"


# ---------- (2) ML status ----------
class TestMLStatus:
    def test_ml_status_ok_with_auc(self, creator_ctx):
        r = requests.get(f"{API}/ml/status", headers=creator_ctx["h"], timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("available") is True, f"model not available: {body}"
        auc = body.get("roc_auc") or body.get("model_auc") or body.get("auc")
        assert auc is not None, f"no AUC field in ml/status: {body}"
        assert 0.5 < float(auc) < 1.0, f"AUC out of range: {auc}"
        # Phase-3 feature-names contract still preserved after refactor
        assert "feature_names" in body and len(body["feature_names"]) >= 8


# ---------- (3) analyze returns risk.ml block ----------
class TestAnalyzeMLBlock:
    def _create_and_analyze(self, creator_ctx, brand_id, amount):
        body = {
            "brand_id": brand_id,
            "deal_title": "TEST_iter4_ml_block",
            "deal_amount": float(amount),
            "payment_terms_days": 45,
            "contract_text": "One post, two stories on instagram. Payment net 45.",
        }
        r = requests.post(f"{API}/deals", json=body, headers=creator_ctx["h"], timeout=20)
        assert r.status_code in (200, 201), r.text
        deal_id = r.json()["id"]
        r2 = requests.post(f"{API}/deals/{deal_id}/analyze", headers=creator_ctx["h"], timeout=60)
        assert r2.status_code == 200, r2.text
        return r2.json(), deal_id

    def test_analyze_has_ml_subblock(self, creator_ctx):
        brands = requests.get(f"{API}/brands", headers=creator_ctx["h"], timeout=15).json()
        assert brands, "no brands seeded"
        data, _ = self._create_and_analyze(creator_ctx, brands[0]["id"], 10000)
        risk = data.get("risk") or data
        ml = risk.get("ml") or data.get("ml")
        assert ml is not None, f"no risk.ml subblock in {data}"
        for k in ("default_prob", "survival_prob", "ml_score", "model_auc"):
            assert k in ml, f"missing key '{k}' in risk.ml: {ml}"
        # sanity ranges
        assert 0 <= ml["default_prob"] <= 1
        assert 0 <= ml["survival_prob"] <= 1
        assert 0 <= ml["ml_score"] <= 100


# ---------- (4) advance-rate ladder (tested via risk_engine directly) ----------
class TestAdvanceLadder:
    """Directly exercise risk_engine.compute_risk_score -> ladder mapping."""

    @pytest.mark.parametrize("score,expected_rate_pct", [
        (95, 95.0),   # >=90
        (85, 90.0),   # 80-89
        (75, 85.0),   # 70-79
        (65, 80.0),   # 60-69
        (55, 75.0),   # 50-59
        (45, 70.0),   # <50 (floor)
        (20, 70.0),   # deep-low also floor
    ])
    def test_ladder_branch(self, score, expected_rate_pct):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from risk_engine import _lookup_advance_terms  # helper extracted in refactor

        terms = _lookup_advance_terms(score)
        # helper returns tuple (advance_pct, fee_pct); also tolerate dict form
        rate = terms[0] if isinstance(terms, (tuple, list)) else (
            terms.get("advance_rate") or terms.get("advance_pct"))
        assert abs(rate - expected_rate_pct) < 1e-6, f"score={score} -> rate={rate}, expected {expected_rate_pct}"


# ---------- (5) drift + retrain ----------
class TestDriftRetrain:
    def test_drift_report(self, admin_ctx):
        r = requests.get(f"{API}/admin/ml/drift", headers=admin_ctx["h"], timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "verdict" in body
        assert "features" in body or body.get("verdict") == "insufficient_data"

    def test_retrain_roundtrip(self, admin_ctx):
        r = requests.post(f"{API}/admin/ml/retrain", headers=admin_ctx["h"], timeout=120)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        report = body.get("report") or body
        assert "roc_auc" in report or "auc" in report
        assert "n_train" in report or "n_test" in report


# ---------- (6) contract download auth paths ----------
class TestContractDownloadAuth:
    @pytest.fixture(scope="class")
    def uploaded(self, creator_ctx):
        files = {"file": ("iter4_contract.pdf", io.BytesIO(b"%PDF-1.4\niter4 test\n%%EOF"), "application/pdf")}
        r = requests.post(f"{API}/contracts/upload", files=files, headers=creator_ctx["h"], timeout=30)
        assert r.status_code == 200, r.text
        return r.json()  # expects {id, ...}

    def test_download_with_bearer(self, creator_ctx, uploaded):
        cid = uploaded["id"]
        r = requests.get(f"{API}/contracts/{cid}/download", headers=creator_ctx["h"], timeout=30, allow_redirects=False)
        assert r.status_code in (200, 302, 307), r.status_code

    def test_download_with_query_token(self, creator_ctx, uploaded):
        cid = uploaded["id"]
        r = requests.get(f"{API}/contracts/{cid}/download?auth={creator_ctx['token']}", timeout=30, allow_redirects=False)
        assert r.status_code in (200, 302, 307), r.status_code

    def test_download_missing_token_401(self, uploaded):
        cid = uploaded["id"]
        r = requests.get(f"{API}/contracts/{cid}/download", timeout=20, allow_redirects=False)
        assert r.status_code == 401, f"expected 401, got {r.status_code}"

    def test_download_invalid_token_401(self, uploaded):
        cid = uploaded["id"]
        r = requests.get(f"{API}/contracts/{cid}/download?auth=not-a-jwt", timeout=20, allow_redirects=False)
        assert r.status_code == 401, f"expected 401, got {r.status_code}"

    def test_download_foreign_creator_403(self, creator_ctx, uploaded):
        # Register a fresh creator and attempt to fetch the first creator's contract
        import uuid
        other = {"email": f"iter4_other_{uuid.uuid4().hex[:8]}@mypay.io", "password": "Other@123", "full_name": "Other Creator"}
        rr = requests.post(f"{API}/auth/register", json=other, timeout=30)
        assert rr.status_code in (200, 201), rr.text
        tok = rr.json().get("token") or rr.json().get("access_token")
        assert tok
        cid = uploaded["id"]
        r = requests.get(f"{API}/contracts/{cid}/download",
                         headers={"Authorization": f"Bearer {tok}"}, timeout=20, allow_redirects=False)
        assert r.status_code == 403, f"expected 403 for foreign creator, got {r.status_code}: {r.text[:200]}"

    def test_download_missing_contract_404(self, creator_ctx):
        r = requests.get(f"{API}/contracts/00000000-0000-0000-0000-000000000000/download",
                         headers=creator_ctx["h"], timeout=20, allow_redirects=False)
        assert r.status_code == 404, f"expected 404, got {r.status_code}"
