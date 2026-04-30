# How to run My Pay locally

## Prerequisites — install once

### MongoDB (pick one)

**Option A — Homebrew (Mac)**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Option B — Docker (any OS, easiest)**
```bash
docker run -d -p 27017:27017 --name mypay-mongo mongo:7
```

**Option C — Windows**
Download from https://www.mongodb.com/try/download/community
Install as a service — it starts automatically.

---

## Start everything (after MongoDB is running)

Open a terminal in the `myapp-main/` folder and run:

```bash
bash start.sh
```

This will:
1. Create a Python virtual environment and install dependencies
2. Start the FastAPI backend on port 8000
3. Seed the 5 demo brands (Gymshark, Nykaa, boAt, Mamaearth, Sugar Cosmetics)
4. Install npm packages and start the React frontend on port 3000

**First run takes ~2 minutes** (installing packages). After that it starts in seconds.

---

## Manual startup (if you prefer two terminals)

**Terminal 1 — Backend**
```bash
cd myapp-main/backend
python3 -m venv .venv          # first time only
source .venv/bin/activate      # Mac/Linux
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt  # first time only
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
cd myapp-main/frontend
npm install    # first time only
npm start
```

---

## URLs

| Service   | URL                          |
|-----------|------------------------------|
| App       | http://localhost:3000        |
| API       | http://localhost:8000        |
| API docs  | http://localhost:8000/docs   |

---

## Test the full flow

1. **Register** at http://localhost:3000/register
   - Fill name, handle (@yourhandle), email, password
   - Lands on dashboard with ₹50,000 starter credit limit

2. **Seed demo brands** (one-time, if start.sh didn't do it)
   ```bash
   curl -X POST http://localhost:8000/api/brands/seed
   ```

3. **Update your profile** at http://localhost:3000/profile
   - Enter followers: 300000, engagement: 4.5, authenticity: 85
   - Watch the credit preview update live
   - Click Save — limit jumps to ₹10L (Premium tier)

4. **Submit a deal** at http://localhost:3000/deals/new
   - Select Nykaa from the brand dropdown
   - Enter amount: 100000, terms: Net 60
   - Click Submit — auto-runs underwriting
   - Deal detail page shows risk score, advance amount (₹80,000), fee (₹3,000)

5. **Accept the advance** on the deal detail page
   - Click "Accept & Receive ₹80,000"
   - Status changes to Disbursed

6. **Check dashboard** — credit used updates, pipeline shows 1 disbursed deal

---

## Run unit tests
```bash
cd myapp-main/backend
source .venv/bin/activate
python -m pytest app/tests/unit/ -v
# Expected: 35 passed
```

---

## Troubleshooting

**"Connection refused" on port 27017** — MongoDB isn't running.
Start it: `brew services start mongodb-community` or `docker start mypay-mongo`

**"Module not found" errors** — Dependencies not installed.
Run: `pip install -r requirements.txt --break-system-packages`

**Frontend blank page** — Check browser console. Usually means
REACT_APP_BACKEND_URL isn't set. Confirm `frontend/.env` exists with:
`REACT_APP_BACKEND_URL=http://localhost:8000`

**"Login failed"** — Backend not running or CORS issue.
Check terminal 1 for errors. Confirm backend is on port 8000.
