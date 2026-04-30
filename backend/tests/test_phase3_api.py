"""Phase 3 backend tests for My Pay.

Coverage:
- POST /api/contracts/upload + GET /api/contracts/{id}/download (auth-protected)
- POST /api/deals with contract_file_id link -> contract_storage_path/size persist
- GET /api/storage/status
- POST /api/deals/{id}/advance writes disbursement_confirmation email (status='mocked')
- POST /api/admin/deals/{id}/mark-repaid -> repayment_received email + deals_labeled(default_label=0)
- POST /api/admin/deals/{id}/mark-default -> deals_labeled(default_label=1)
- POST /api/admin/maturity-sweep -> {ok, reminders_sent, outstanding_count}
- GET /api/admin/emails (403 for creator, 200 for admin)
- GET /api/admin/ml/drift -> {global_psi, verdict, features[], ...}
- POST /api/admin/ml/retrain -> {ok, report{n_train, n_test, roc_auc, n_production}}
"""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Frontend env has the public URL; fallback to internal for local runs
    BASE_URL = "http://localhost:8001"
API = f"{BASE_URL}/api"

CREATOR = {"email": "creator@mypay.io", "password": "Creator@123"}
ADMIN = {"email": "admin@mypay.io", "password": "Admin@123"}


# --------- Shared fixtures ---------
@pytest.fixture(scope="session")
def s():
    return requests.Session()


def _login(session, creds):
    r = session.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login {creds['email']} failed: {r.status_code} {r.text[:200]}"
    body = r.json()
    return body.get("access_token") or body["token"]


@pytest.fixture(scope="session")
def creator_token(s):
    return _login(s, CREATOR)


@pytest.fixture(scope="session")
def admin_token(s):
    return _login(s, ADMIN)


@pytest.fixture(scope="session")
def creator_h(creator_token):
    return {"Authorization": f"Bearer {creator_token}"}


@pytest.fixture(scope="session")
def admin_h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def brand_id(s, creator_h):
    r = s.get(f"{API}/brands", headers=creator_h, timeout=30)
    assert r.status_code == 200
    brands = r.json()
    assert brands, "no brands seeded"
    # Prefer a fortune500 brand for predictable scoring
    for b in brands:
        if b.get("tier") == "fortune500":
            return b["id"]
    return brands[0]["id"]


# --------- 1. Storage status ---------
def test_storage_status(s, creator_h):
    r = s.get(f"{API}/storage/status", headers=creator_h, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("app_name") == "mypay"
    assert body.get("available") is True, f"storage unavailable: {body}"


# --------- 2. Contract upload/download ---------
@pytest.fixture(scope="session")
def uploaded_contract(s, creator_h):
    content = b"%PDF-1.4\n%TEST_P3 contract bytes\n"
    files = {"file": ("TEST_P3_contract.pdf", io.BytesIO(content), "application/pdf")}
    r = s.post(f"{API}/contracts/upload", headers=creator_h, files=files, timeout=60)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert "id" in body and "storage_path" in body
    assert body["size"] == len(content)
    assert body["content_type"] in ("application/pdf", "application/octet-stream")
    return {"body": body, "content": content}


def test_contract_upload_returns_metadata(uploaded_contract):
    body = uploaded_contract["body"]
    assert body["id"]
    assert body["storage_path"]
    assert body["size"] > 0


def test_contract_download_with_header(s, creator_h, uploaded_contract):
    cid = uploaded_contract["body"]["id"]
    r = s.get(f"{API}/contracts/{cid}/download", headers=creator_h, timeout=60)
    assert r.status_code == 200, r.text[:300]
    assert r.content == uploaded_contract["content"]
    assert r.headers.get("content-type", "").startswith("application/pdf") or "pdf" in r.headers.get("content-type", "")


def test_contract_download_with_auth_query(s, creator_token, uploaded_contract):
    cid = uploaded_contract["body"]["id"]
    # No header — use ?auth=
    r = requests.get(f"{API}/contracts/{cid}/download", params={"auth": creator_token}, timeout=60)
    assert r.status_code == 200
    assert r.content == uploaded_contract["content"]


def test_contract_download_forbidden_for_other_user(s, uploaded_contract):
    # Admin is NOT the owner — but admins are allowed by design. Test a fresh creator.
    # Register a second creator
    sess = requests.Session()
    email = f"TEST_p3_other_{int(time.time())}@mypay.io"
    r = sess.post(f"{API}/auth/register", json={
        "email": email, "password": "Passw0rd!", "full_name": "Other P3", "role": "creator", "handle": "@other_p3"
    }, timeout=30)
    assert r.status_code == 200, r.text
    token = r.json().get("access_token") or r.json()["token"]
    cid = uploaded_contract["body"]["id"]
    r2 = requests.get(f"{API}/contracts/{cid}/download",
                      headers={"Authorization": f"Bearer {token}"}, timeout=30)
    assert r2.status_code == 403, f"expected 403 for foreign creator, got {r2.status_code}"


def test_contract_download_404_for_missing(s, creator_h):
    r = s.get(f"{API}/contracts/does-not-exist-xyz/download", headers=creator_h, timeout=30)
    assert r.status_code == 404


# --------- 3. Deal linked to contract_file_id ---------
@pytest.fixture(scope="session")
def linked_deal(s, creator_h, brand_id, uploaded_contract):
    cid = uploaded_contract["body"]["id"]
    payload = {
        "brand_id": brand_id,
        "deal_title": "TEST_P3 linked-contract deal",
        "deal_amount": 15000,
        "payment_terms_days": 30,
        "contract_text": "TEST P3 contract clauses",
        "contract_file_id": cid,
    }
    r = s.post(f"{API}/deals", headers=creator_h, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_deal_persists_storage_path_and_size(linked_deal, uploaded_contract):
    assert linked_deal.get("contract_file_id") == uploaded_contract["body"]["id"]
    assert linked_deal.get("contract_storage_path") == uploaded_contract["body"]["storage_path"]
    assert linked_deal.get("contract_file_size") == uploaded_contract["body"]["size"]


# --------- 4. Advance triggers email (mocked) ---------
def test_advance_triggers_mocked_email(s, creator_h, admin_h, linked_deal):
    deal_id = linked_deal["id"]
    # Must analyze first (moves to 'scored')
    ra = s.post(f"{API}/deals/{deal_id}/analyze", headers=creator_h, timeout=90)
    assert ra.status_code == 200, ra.text[:300]

    rb = s.post(f"{API}/deals/{deal_id}/advance", headers=creator_h, timeout=30)
    assert rb.status_code == 200, rb.text
    assert rb.json().get("disbursed_at")

    # Allow async write
    time.sleep(0.5)
    # Read email log via admin
    logs = s.get(f"{API}/admin/emails", headers=admin_h, timeout=30).json()
    found = [e for e in logs if e.get("template") == "disbursement_confirmation"
             and e.get("to") == CREATOR["email"]]
    assert found, "disbursement_confirmation email not logged"
    latest = found[0]
    assert latest.get("status") == "mocked", f"expected 'mocked', got {latest.get('status')}"
    assert latest.get("provider") == "mock"


# --------- 5. Admin emails endpoint access ---------
def test_admin_emails_forbidden_for_creator(s, creator_h):
    r = s.get(f"{API}/admin/emails", headers=creator_h, timeout=30)
    assert r.status_code == 403


def test_admin_emails_sorted_desc(s, admin_h):
    r = s.get(f"{API}/admin/emails", headers=admin_h, timeout=30)
    assert r.status_code == 200
    logs = r.json()
    assert isinstance(logs, list)
    if len(logs) >= 2:
        # created_at should be descending
        ts = [e.get("created_at") for e in logs if e.get("created_at")]
        assert ts == sorted(ts, reverse=True)


# --------- 6. Maturity sweep ---------
def test_maturity_sweep(s, admin_h):
    r = s.post(f"{API}/admin/maturity-sweep", headers=admin_h, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert "reminders_sent" in body
    assert "outstanding_count" in body
    assert isinstance(body["reminders_sent"], int)
    assert isinstance(body["outstanding_count"], int)


# --------- 7. Mark repaid: email + label 0 ---------
def test_mark_repaid_labels_and_emails(s, creator_h, admin_h, brand_id):
    # Fresh disbursed deal to avoid polluting linked_deal tests
    dcreate = s.post(f"{API}/deals", headers=creator_h, json={
        "brand_id": brand_id, "deal_title": "TEST_P3 repaid flow", "deal_amount": 8000,
        "payment_terms_days": 30, "contract_text": "clauses"
    }, timeout=30).json()
    did = dcreate["id"]
    assert s.post(f"{API}/deals/{did}/analyze", headers=creator_h, timeout=90).status_code == 200
    assert s.post(f"{API}/deals/{did}/advance", headers=creator_h, timeout=30).status_code == 200

    r = s.post(f"{API}/admin/deals/{did}/mark-repaid", headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    time.sleep(0.5)

    logs = s.get(f"{API}/admin/emails", headers=admin_h, timeout=30).json()
    found = [e for e in logs if e.get("template") == "repayment_received"]
    assert found, "repayment_received email not logged"
    assert found[0].get("status") == "mocked"

    # Verify deals_labeled row exists with default_label=0 via drift endpoint side-effect check:
    # We don't have a direct listing endpoint, but retrain.n_production should increment.
    r2 = s.post(f"{API}/admin/ml/retrain", headers=admin_h, timeout=90)
    assert r2.status_code == 200
    rep = r2.json().get("report", {})
    assert rep.get("n_production", 0) >= 1, f"expected labeled prod row, got report={rep}"


# --------- 8. Mark default: label 1 ---------
def test_mark_default_labels(s, creator_h, admin_h, brand_id):
    dcreate = s.post(f"{API}/deals", headers=creator_h, json={
        "brand_id": brand_id, "deal_title": "TEST_P3 default flow", "deal_amount": 9000,
        "payment_terms_days": 30, "contract_text": "clauses"
    }, timeout=30).json()
    did = dcreate["id"]
    assert s.post(f"{API}/deals/{did}/analyze", headers=creator_h, timeout=90).status_code == 200
    assert s.post(f"{API}/deals/{did}/advance", headers=creator_h, timeout=30).status_code == 200

    r = s.post(f"{API}/admin/deals/{did}/mark-default", headers=admin_h, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True

    # Now the retrain report should include a label=1 contribution; at least n_production increments
    r2 = s.post(f"{API}/admin/ml/retrain", headers=admin_h, timeout=90).json()
    rep = r2.get("report", {})
    assert rep.get("n_production", 0) >= 2


# --------- 9. Drift ---------
def test_drift_report(s, admin_h):
    r = s.get(f"{API}/admin/ml/drift", headers=admin_h, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "global_psi" in body
    assert body.get("verdict") in ("stable", "watch", "drift", "insufficient_data")
    assert isinstance(body.get("features"), list)
    assert body.get("n_training") >= 1
    assert "message" in body


# --------- 10. Retrain ---------
def test_retrain(s, admin_h):
    r = s.post(f"{API}/admin/ml/retrain", headers=admin_h, timeout=90)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    rep = body.get("report", {})
    for k in ("n_train", "n_test", "roc_auc", "n_production"):
        assert k in rep, f"missing {k} in retrain report"
    assert 0.0 <= rep["roc_auc"] <= 1.0
