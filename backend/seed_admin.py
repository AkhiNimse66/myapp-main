#!/usr/bin/env python3
"""
seed_admin.py — One-time admin account setup for Athanni.

Run once from the backend/ directory:

    cd ~/Desktop/myapp-main/backend
    python seed_admin.py

Creates admin@athanni.co.in (or override via env vars below).
Idempotent — safe to run multiple times, skips if account already exists.

Override defaults with environment variables before running:
    ADMIN_EMAIL=ops@yourcompany.com ADMIN_PASSWORD=strongpassword python seed_admin.py
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── Load .env from the backend/ directory (same folder as this script) ──────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            os.environ.setdefault(_key.strip(), _val.strip())

# ── Config — override via env vars if needed ─────────────────────────────────
MONGO_URL      = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME        = os.environ.get("DB_NAME", "athanni_dev")
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL", "admin@athanni.co.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "athanni-admin-2024")
ADMIN_NAME     = os.environ.get("ADMIN_NAME", "Athanni Admin")


def _hash(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def main() -> None:
    try:
        import pymongo
    except ImportError:
        print("❌  pymongo not installed.  Run: pip install pymongo --break-system-packages")
        sys.exit(1)

    try:
        import bcrypt  # noqa: F401
    except ImportError:
        print("❌  bcrypt not installed.  Run: pip install bcrypt --break-system-packages")
        sys.exit(1)

    print(f"⟳  Connecting to {MONGO_URL} / {DB_NAME} …")
    try:
        client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=5_000)
        client.server_info()          # raises if MongoDB is not reachable
    except Exception as exc:
        print(f"❌  Could not connect to MongoDB: {exc}")
        print("    Is MongoDB running?  Start it with:")
        print("      brew services start mongodb-community")
        print("    or: docker run -d -p 27017:27017 --name athanni-mongo mongo:7")
        sys.exit(1)

    users = client[DB_NAME]["users"]

    # ── Idempotency check ────────────────────────────────────────────────────
    existing = users.find_one({"email": ADMIN_EMAIL.lower()})
    if existing:
        print(f"✓  Admin account already exists — nothing to do.")
        print(f"   Email : {ADMIN_EMAIL}")
        print(f"   Role  : {existing.get('role')}")
        print(f"   Status: {existing.get('status')}")
        print()
        print("   Log in at → http://localhost:3000/login")
        return

    # ── Create admin user ────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id":            str(uuid.uuid4()),
        "email":         ADMIN_EMAIL.lower().strip(),
        "password_hash": _hash(ADMIN_PASSWORD),
        "name":          ADMIN_NAME,
        "role":          "admin",
        "status":        "active",
        "kyc_status":    "verified",   # admin is always KYC-verified
        "created_at":    now,
        "updated_at":    now,
    }
    users.insert_one(doc)
    doc.pop("_id", None)

    print()
    print("✅  Admin account created.")
    print()
    print(f"   Email    : {ADMIN_EMAIL}")
    print(f"   Password : {ADMIN_PASSWORD}")
    print(f"   Role     : admin")
    print()
    print("   ⚠️  Save these credentials — this script won't show the password again.")
    print("   Log in at → http://localhost:3000/login")
    print()


if __name__ == "__main__":
    main()
