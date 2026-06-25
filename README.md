# QueueStorm Ticket Classifier

bKash / SUST CSE Carnival 2026 — Codex Community Hackathon Mock Preliminary

A stateless REST API that classifies customer support tickets for a digital finance company.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/sort-ticket` | Classify a customer ticket |

## Run Locally

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Test it:
```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","channel":"app","locale":"en","message":"I sent 5000 taka to a wrong number, please help"}'
```

## Deploy on Render (Free)

1. Push this repo to GitHub (make it public)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Set these fields:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Click Deploy
6. Your HTTPS URL is shown at the top of the Render dashboard

No environment variables required (rule-based, no API keys).

## How It Works

Rule-based keyword classification — no LLM, no GPU, no external APIs.

- Scans message text for keywords in each category
- Picks the category with the most keyword matches
- Derives severity and department from case type
- Flags `human_review_required = true` for phishing or critical severity

## LLM Used

No — fully rule-based solution.
