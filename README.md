# SpendSight — UPI Spending Analyser

> "Your bank statement, but actually readable."

A behavioural finance tool that takes your UPI/bank CSV and returns
a full spending dashboard — categories, trends, merchants, subscriptions.

## Project Structure

```
spendsight/
├── data/
│   ├── generate_transactions.py   # Synthetic data generator
│   └── sample_transactions.csv   # Pre-generated sample
├── src/
│   ├── parser/
│   │   └── analyser.py            # CSV parser + categoriser + insights
│   └── api/
│       └── main.py                # FastAPI backend
├── frontend/
│   └── index.html                 # Full UI (served by FastAPI)
├── requirements.txt
└── README.md
```

## Quickstart

```bash
# 1. Create and activate venv
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Install
pip install -r requirements.txt

# 3. Generate sample data (already included in zip)
python data/generate_transactions.py

# 4. Start API + open browser
uvicorn src.api.main:app --reload & start http://localhost:8000/app
```

## How data is acquired

| Method | Description | Status |
|--------|-------------|--------|
| CSV upload | User downloads from Paytm/BHIM, uploads here | ✅ v1 (this build) |
| RBI Account Aggregator | One-tap consent via Setu/Finvu AA API | 🔜 v2 production |

## CSV format supported

Any CSV with these columns (flexible column name matching):
- `date` — transaction date
- `amount` — transaction amount
- `description` or `narration` — transaction text
- `type` — debit / credit (optional, inferred if missing)
- `merchant` — merchant name (optional, inferred from description)
