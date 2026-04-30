"""My Pay backend API tests - auth, brands, deals, AI analysis, admin."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"

CREATOR_EMAIL = "creator@mypay.io"
CREATOR_PW = "Creator@123"
ADMIN_EMAIL = "admin@mypay.io"
ADMIN_PW = "Admin@123"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def creator_token():
    r = requests.post(f"{API}/auth/login", json={"email": CREATOR_EMAIL, "password": CREATOR_PW}, timeout=15)
    assert r.status_code == 200, f"creator login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def h(t):
    return {"Authorization": f"Bearer {t}"}


# ---------- Auth ----------
class TestAuth:
    def test_register_new_creator(self):
        email = f"TEST_{uuid.uuid4().hex[:8]}@mypay.io"
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Test@1234", "full_name": "Test Creator",
            "handle": "@testc", "role": "creator"
        }, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "token" in body and "user" in body
        assert body["user"]["email"] == email
        assert body["user"]["role"] == "creator"
        assert "id" in body["user"]

    def test_login_creator(self):
        r = requests.post(f"{API}/auth/login", json={"email": CREATOR_EMAIL, "password": CREATOR_PW}, timeout=15)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_admin(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=15)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": CREATOR_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_me_endpoint(self, creator_token):
        r = requests.get(f"{API}/auth/me", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == CREATOR_EMAIL

    def test_me_unauth(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code in (401, 403)


# ---------- Brands ----------
class TestBrands:
    def test_list_brands(self, creator_token):
        r = requests.get(f"{API}/brands", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        brands = r.json()
        assert isinstance(brands, list)
        assert len(brands) == 20
        names = [b["name"] for b in brands]
        assert "Nike" in names
        # no _id leak
        for b in brands:
            assert "_id" not in b
            assert "id" in b


# ---------- Deals ----------
class TestDeals:
    def _get_nike(self, token):
        brands = requests.get(f"{API}/brands", headers=h(token), timeout=15).json()
        return next(b for b in brands if b["name"] == "Nike")

    def test_create_deal_no_id_leak(self, creator_token):
        nike = self._get_nike(creator_token)
        r = requests.post(f"{API}/deals", headers=h(creator_token), json={
            "brand_id": nike["id"], "deal_title": "TEST Nike Summer Campaign",
            "deal_amount": 25000, "payment_terms_days": 45
        }, timeout=15)
        assert r.status_code == 200, r.text
        deal = r.json()
        assert "id" in deal
        assert "_id" not in deal
        assert deal["status"] == "uploaded"
        assert deal["brand_name"] == "Nike"
        pytest.deal_id = deal["id"]

    def test_list_creator_deals_only_theirs(self, creator_token):
        r = requests.get(f"{API}/deals", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        deals = r.json()
        assert isinstance(deals, list)
        assert any(d["id"] == pytest.deal_id for d in deals)
        for d in deals:
            assert "_id" not in d

    def test_analyze_deal_ai(self, creator_token):
        r = requests.post(f"{API}/deals/{pytest.deal_id}/analyze", headers=h(creator_token), timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "ai_analysis" in body
        assert "risk" in body
        assert "advance_amount" in body
        assert "discount_fee" in body
        risk = body["risk"]
        # Nike fortune500 AAA with demo creator at 45 days -> risk_score >= 85, advance 90-95
        assert risk["risk_score"] >= 85, f"expected >=85, got {risk['risk_score']}"
        assert 90 <= risk["advance_rate"] <= 95
        pytest.risk_score = risk["risk_score"]

    def test_get_deal_detail(self, creator_token):
        r = requests.get(f"{API}/deals/{pytest.deal_id}", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        deal = r.json()
        assert deal["id"] == pytest.deal_id
        assert deal["status"] == "scored"
        assert "_id" not in deal

    def test_advance_requires_scored(self, creator_token):
        # Create an unscored deal and attempt to disburse (should 400)
        nike = self._get_nike(creator_token)
        r = requests.post(f"{API}/deals", headers=h(creator_token), json={
            "brand_id": nike["id"], "deal_title": "TEST Pre-score Deal",
            "deal_amount": 5000, "payment_terms_days": 30
        }, timeout=15).json()
        adv = requests.post(f"{API}/deals/{r['id']}/advance", headers=h(creator_token), timeout=15)
        assert adv.status_code == 400

    def test_disburse_scored_deal(self, creator_token):
        r = requests.post(f"{API}/deals/{pytest.deal_id}/advance", headers=h(creator_token), timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        # verify persisted
        d = requests.get(f"{API}/deals/{pytest.deal_id}", headers=h(creator_token), timeout=15).json()
        assert d["status"] == "disbursed"


# ---------- Dashboard + profile ----------
class TestDashboard:
    def test_summary(self, creator_token):
        r = requests.get(f"{API}/dashboard/summary", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        s = r.json()
        assert "credit_limit" in s
        assert "total_advanced" in s
        assert "creator_health" in s
        assert s["creator_health"]["followers"] > 0

    def test_get_profile(self, creator_token):
        r = requests.get(f"{API}/creator/profile", headers=h(creator_token), timeout=15)
        assert r.status_code == 200
        p = r.json()
        assert p.get("handle") == "@avastone"

    def test_update_profile(self, creator_token):
        r = requests.put(f"{API}/creator/profile", headers=h(creator_token), json={
            "handle": "@avastone", "platform": "instagram",
            "followers": 500000, "engagement_rate": 5.0, "authenticity_score": 93.0
        }, timeout=15)
        assert r.status_code == 200
        # verify persistence
        g = requests.get(f"{API}/creator/profile", headers=h(creator_token), timeout=15).json()
        assert g["followers"] == 500000
        assert g["engagement_rate"] == 5.0


# ---------- Admin ----------
class TestAdmin:
    def test_admin_list_deals(self, admin_token):
        r = requests.get(f"{API}/admin/deals", headers=h(admin_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_stats(self, admin_token):
        r = requests.get(f"{API}/admin/stats", headers=h(admin_token), timeout=15)
        assert r.status_code == 200
        s = r.json()
        assert "total_deals" in s and "total_volume" in s

    def test_creator_cannot_access_admin(self, creator_token):
        r = requests.get(f"{API}/admin/deals", headers=h(creator_token), timeout=15)
        assert r.status_code == 403
        r2 = requests.get(f"{API}/admin/stats", headers=h(creator_token), timeout=15)
        assert r2.status_code == 403

    def test_admin_override(self, admin_token):
        # Use previously-scored deal
        r = requests.post(f"{API}/admin/deals/{pytest.deal_id}/override", headers=h(admin_token), json={
            "advance_rate": 92.0, "discount_fee_rate": 3.0, "notes": "TEST override"
        }, timeout=15)
        assert r.status_code == 200
        # admin can fetch any deal
        d = requests.get(f"{API}/deals/{pytest.deal_id}", headers=h(admin_token), timeout=15).json()
        assert d["admin_override"]["advance_rate"] == 92.0
