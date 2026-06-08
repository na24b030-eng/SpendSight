"""
SpendSight FastAPI backend.

POST /upload      → parse CSV, return full insights JSON
GET  /sample      → return insights from synthetic sample data
GET  /health      → health check

Run: uvicorn src.api.main:app --reload
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from src.parser.analyser import parse_csv, compute_insights
from data.generate_transactions import generate

ROOT = Path(__file__).parent.parent.parent
FRONTEND_DIR = ROOT / "frontend"
SAMPLE_CSV = ROOT / "data" / "sample_transactions.csv"

app = FastAPI(title="SpendSight API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "SpendSight API. Visit /app for the dashboard, /docs for Swagger."}


@app.get("/sample")
def get_sample():
    """Return insights from synthetic sample data."""
    # Generate fresh if not exists
    if not SAMPLE_CSV.exists():
        generate(n_months=6, output_path=SAMPLE_CSV)

    content = SAMPLE_CSV.read_text(encoding="utf-8")
    transactions = parse_csv(content)
    if not transactions:
        raise HTTPException(status_code=500, detail="Failed to parse sample data")

    insights = compute_insights(transactions)
    return JSONResponse(content=insights)


@app.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    """Parse uploaded CSV and return full insights."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported in v1.")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Could not decode file. Please save as UTF-8 CSV.")

    transactions = parse_csv(text)
    if not transactions:
        raise HTTPException(
            status_code=422,
            detail="No transactions found. Check that your CSV has: date, amount, description columns."
        )

    insights = compute_insights(transactions)
    return JSONResponse(content=insights)
