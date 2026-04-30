"""My Pay Phase 2 backend API tests - repay-checkout, payment status,
webhook signature, mark-repaid + credit recycling, ML status, social connect,
extended dashboard summary fields."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"

CREATOR_EMAIL = "creator@mypay.io"
CREATOR_PW = "Creator@123"
ADMIN_EMAIL = "admin@mypay.io"
ADMIN_PW = "Admin@123"

ORIGIN_URL = BASE_URL  # used for stripe success/cancel URL


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def creator_token():
    r = requests.post(f"{API}/auth/login", json={"email": CREATOR_EMAIL, "password": CREATOR_PW}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def h(t):
    return {"Authorization": f"Bearer {t}"}


def _make_disbursed_deal(creator_token, amount=15000):
    """Helper: create a deal, analyze, disburse, return id + summary snapshot."""
    brands = requests.get(f"{API}/brands", headers=h(creator_token), timeout=15).json()
    nike = next(b for b in brands if b["name"] == "Nike")
    r = requests.post(f"{API}/deals", headers=h(creator_token), json={
        "brand_id": nike["id"], "deal_title": f"TEST_P2_{uuid.uuid4().hex[:6]}",
        "deal_amount": amount, "payment_terms_days": 30
    }, timeout=15)
    assert r.status_code == 200, r.text
    deal_id = r.json()["id"]
    # analyze
    a = requests.post(f"{API}/deals/{deal_id}/analyze", headers=h(creator_token), timeout=120)
    assert a.status_code == 200, a.text
    # disburse
    d = requests.post(f"{API}/deals/{deal_id}/advance", headers=h(creator_token), timeout=15)
    assert d.status_code == 200, d.text
    return deal_id, a.json()


# ---------- ML model + analyze.ml ----------
class TestMLStatus:
    def test_ml_status_endpoint(self, creator_token):
        r = requests.get(f"{API}/ml/status", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("available") is True
        assert "n_train" in body and isinstance(body["n_train"], int)
        assert "n_test" in body
        assert "default_rate" in body
        assert "roc_auc" in body and 0.5 <= body["roc_auc"] <= 1.0
        assert "feature_names" in body and isinstance(body["feature_names"], list)

    def test_analyze_includes_ml_block(self, creator_token):
        # Create + analyze a fresh deal and assert risk.ml present
        brands = requests.get(f"{API}/brands", headers=h(creator_token), timeout=15).json()
        nike = next(b for b in brands if b["name"] == "Nike")
        d = requests.post(f"{API}/deals", headers=h(creator_token), json={
            "brand_id": nike["id"], "deal_title": "TEST_P2_ml_block",
            "deal_amount": 8000, "payment_terms_days": 60
        }, timeout=15).json()
        a = requests.post(f"{API}/deals/{d['id']}/analyze", headers=h(creator_token), timeout=120)
        assert a.status_code == 200, a.text
        risk = a.json()["risk"]
        assert "ml" in risk, "risk.ml block missing from analyze response"
        ml = risk["ml"]
        for key in ("default_prob", "survival_prob", "ml_score", "model_auc"):
            assert key in ml, f"ml.{key} missing"
        assert 0 <= ml["default_prob"] <= 1
        assert abs((ml["default_prob"] + ml["survival_prob"]) - 1) < 0.01


# ---------- Dashboard summary new fields ----------
class TestDashboardSummary:
    def test_summary_has_phase2_fields(self, creator_token):
        r = requests.get(f"{API}/dashboard/summary", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        s = r.json()
        for k in ("outstanding", "total_repaid", "lifetime_advanced", "used_pct", "creator_health", "credit_limit", "available"):
            assert k in s, f"missing field: {k}"
        assert isinstance(s["outstanding"], (int, float))
        assert isinstance(s["used_pct"], (int, float))


# ---------- Stripe Checkout flow ----------
class TestRepayCheckout:
    def test_repay_checkout_requires_disbursed(self, creator_token):
        # create new (uploaded) deal — should reject
        brands = requests.get(f"{API}/brands", headers=h(creator_token), timeout=15).json()
        nike = next(b for b in brands if b["name"] == "Nike")
        d = requests.post(f"{API}/deals", headers=h(creator_token), json={
            "brand_id": nike["id"], "deal_title": "TEST_P2_undisbursed",
            "deal_amount": 4000, "payment_terms_days": 30
        }, timeout=15).json()
        r = requests.post(f"{API}/deals/{d['id']}/repay-checkout", headers=h(creator_token),
                          json={"origin_url": ORIGIN_URL}, timeout=20)
        assert r.status_code == 400, r.text

    def test_repay_checkout_creates_session_and_marks_awaiting(self, creator_token):
        deal_id, _ = _make_disbursed_deal(creator_token, amount=12345)
        # create checkout session
        r = requests.post(f"{API}/deals/{deal_id}/repay-checkout", headers=h(creator_token),
                          json={"origin_url": ORIGIN_URL}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "url" in body and "session_id" in body
        assert body["url"].startswith("https://checkout.stripe.com/")
        assert body["session_id"].startswith("cs_test_")
        # Deal status should now be awaiting_payment
        d = requests.get(f"{API}/deals/{deal_id}", headers=h(creator_token), timeout=15).json()
        assert d["status"] == "awaiting_payment"
        assert d.get("last_payment_session") == body["session_id"]
        # store for next test
        pytest.p2_session_id = body["session_id"]
        pytest.p2_deal_id = deal_id

    def test_payment_status_polling(self, creator_token):
        sid = pytest.p2_session_id
        r = requests.get(f"{API}/payments/status/{sid}", headers=h(creator_token), timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "payment_status" in body
        assert "status" in body
        # session was just created and not paid; should be open/unpaid
        # Stripe can return 'pending' briefly after session creation in test mode
        assert body["payment_status"] in ("unpaid", "paid", "no_payment_required", "pending")

    def test_payment_status_unknown_session(self, creator_token):
        r = requests.get(f"{API}/payments/status/cs_test_does_not_exist_xyz", headers=h(creator_token), timeout=15)
        assert r.status_code == 404


# ---------- Stripe webhook signature rejection ----------
class TestStripeWebhook:
    def test_webhook_rejects_invalid_signature(self):
        r = requests.post(f"{API}/webhook/stripe",
                          data=b'{"type":"checkout.session.completed"}',
                          headers={"Stripe-Signature": "t=1,v1=bogus", "Content-Type": "application/json"},
                          timeout=15)
        assert r.status_code in (400, 422), f"expected 400/422, got {r.status_code}: {r.text}"


# ---------- Admin mark-repaid + credit recycling ----------
class TestAdminMarkRepaid:
    def test_mark_repaid_recycles_credit(self, creator_token, admin_token):
        # snapshot summary BEFORE
        before = requests.get(f"{API}/dashboard/summary", headers=h(creator_token), timeout=15).json()
        before_outstanding = before["outstanding"]
        before_repaid = before["total_repaid"]
        before_available = before["available"]

        # create + disburse a fresh deal
        deal_id, analyze = _make_disbursed_deal(creator_token, amount=7000)
        advance = analyze["advance_amount"]

        # outstanding should grow
        mid = requests.get(f"{API}/dashboard/summary", headers=h(creator_token), timeout=15).json()
        assert mid["outstanding"] >= before_outstanding + advance - 0.01

        # admin marks repaid
        r = requests.post(f"{API}/admin/deals/{deal_id}/mark-repaid", headers=h(admin_token), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True and "repaid_at" in body

        # verify deal status now repaid
        d = requests.get(f"{API}/deals/{deal_id}", headers=h(admin_token), timeout=15).json()
        assert d["status"] == "repaid"
        assert d.get("repaid_at")

        # outstanding shrinks; total_repaid grows; available recycles back
        after = requests.get(f"{API}/dashboard/summary", headers=h(creator_token), timeout=15).json()
        assert after["outstanding"] <= mid["outstanding"] - advance + 0.01, \
            f"outstanding did not recycle: before={mid['outstanding']} after={after['outstanding']}"
        assert after["total_repaid"] >= before_repaid + advance - 0.01
        assert after["available"] >= before_available - 0.01  # recycled

    def test_mark_repaid_rejects_non_outstanding(self, admin_token, creator_token):
        # uploaded deal cannot be marked repaid
        brands = requests.get(f"{API}/brands", headers=h(creator_token), timeout=15).json()
        nike = next(b for b in brands if b["name"] == "Nike")
        d = requests.post(f"{API}/deals", headers=h(creator_token), json={
            "brand_id": nike["id"], "deal_title": "TEST_P2_uploaded_repay",
            "deal_amount": 3000, "payment_terms_days": 30
        }, timeout=15).json()
        r = requests.post(f"{API}/admin/deals/{d['id']}/mark-repaid", headers=h(admin_token), timeout=15)
        assert r.status_code == 400

    def test_mark_repaid_creator_forbidden(self, creator_token):
        r = requests.post(f"{API}/admin/deals/anything/mark-repaid", headers=h(creator_token), timeout=15)
        assert r.status_code == 403


# ---------- Social connect placeholder ----------
class TestSocialConnect:
    def test_connect_instagram_returns_pending_meta_review(self, creator_token):
        r = requests.post(f"{API}/creator/social/connect", headers=h(creator_token),
                          json={"platform": "instagram"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("status") == "pending_meta_review"
        assert "message" in body and isinstance(body["message"], str) and len(body["message"]) > 0
        # verify persisted
        p = requests.get(f"{API}/creator/profile", headers=h(creator_token), timeout=15).json()
        assert p.get("provider_connected_requested") is True

    @pytest.mark.parametrize("platform", ["tiktok", "youtube", "x"])
    def test_connect_other_platforms(self, creator_token, platform):
        r = requests.post(f"{API}/creator/social/connect", headers=h(creator_token),
                          json={"platform": platform}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") == "pending_meta_review"
