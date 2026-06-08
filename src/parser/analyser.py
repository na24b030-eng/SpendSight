"""
Transaction parser and auto-categoriser.

Handles:
  - CSV from our synthetic generator (and real Paytm/BHIM exports)
  - Keyword-based merchant categorisation
  - Subscription detection (recurring same-merchant charges)
  - Monthly aggregation for trend charts
"""

import re
import csv
import io
from collections import defaultdict
from datetime import datetime
from typing import Optional


# ── Category keyword map ──────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "swiggy", "zomato", "blinkit", "zepto", "bigbasket",
        "dominos", "mcdonald", "kfc", "pizza", "burger", "cafe",
        "starbucks", "haldiram", "restaurant", "food", "dining",
        "dunzo", "grofers", "instamart", "fresh",
    ],
    "Transport": [
        "ola", "uber", "rapido", "irctc", "makemytrip", "redbus",
        "metro", "indigo", "spicejet", "airindia", "goibibo",
        "yatra", "cleartrip", "airlines", "railway", "bus", "cab",
    ],
    "Subscriptions": [
        "netflix", "spotify", "amazon prime", "hotstar", "youtube",
        "notion", "linkedin", "adobe", "microsoft", "apple",
        "primevideo", "jiosaavn", "gaana", "zee5", "sonyliv",
        "auto-debit", "subscription", "renewal",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "nykaa", "ajio", "meesho",
        "croma", "reliance", "tata cliq", "snapdeal", "shopsy",
        "decathlon", "ikea", "h&m",
    ],
    "Utilities": [
        "electricity", "bescom", "bses", "airtel", "jio", "vi ",
        "vodafone", "bsnl", "water", "bwssb", "gas", "lpg",
        "maintenance", "society", "property tax", "bbmp",
        "broadband", "recharge", "bill",
    ],
    "Health": [
        "pharmeasy", "1mg", "apollo", "medplus", "netmeds",
        "healthifyme", "cult.fit", "cure.fit", "lal pathlabs",
        "thyrocare", "hospital", "clinic", "pharmacy", "medical",
        "insurance",
    ],
    "Finance": [
        "sip", "mutual fund", "zerodha", "groww", "kite", "nps",
        "lic", "hdfc life", "icici pru", "ppf", "rd ", "fd ",
        "investment", "insurance premium", "loan emi",
    ],
    "Entertainment": [
        "bookmyshow", "pvr", "inox", "steam", "playstation",
        "xbox", "gaming", "movie", "concert", "event",
    ],
    "Transfers": [
        "transfer", "neft", "imps", "upi", "split", "lent",
        "borrowed", "sent to", "paid to",
    ],
}

INCOME_KEYWORDS = ["salary", "credit", "refund", "cashback", "received", "income"]


def categorise(description: str, merchant: str = "") -> str:
    text = (description + " " + merchant).lower()

    # Check income first
    if any(k in text for k in INCOME_KEYWORDS):
        return "Income"

    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return cat

    return "Other"


def parse_csv(content: str) -> list[dict]:
    """
    Parse CSV content. Tries our format first, then generic fallback.
    Returns list of normalised transaction dicts.
    """
    reader = csv.DictReader(io.StringIO(content.strip()))
    headers = [h.lower().strip() for h in (reader.fieldnames or [])]

    transactions = []
    for row in reader:
        row = {k.lower().strip(): v.strip() for k, v in row.items()}

        # Amount
        amt_raw = row.get("amount", row.get("amt", row.get("debit", "0")))
        try:
            amount = abs(float(re.sub(r"[^\d.]", "", amt_raw or "0")))
        except ValueError:
            amount = 0.0

        # Date
        date_raw = row.get("date", row.get("transaction date", row.get("txn date", "")))
        try:
            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y"]:
                try:
                    parsed_date = datetime.strptime(date_raw, fmt)
                    break
                except ValueError:
                    continue
            else:
                parsed_date = datetime.today()
        except Exception:
            parsed_date = datetime.today()

        # Type
        txn_type = row.get("type", "debit").lower()
        if "credit" in txn_type or amount < 0:
            txn_type = "credit"
        else:
            txn_type = "debit"

        # Description / merchant
        desc = row.get("description", row.get("narration", row.get("details", "")))
        merchant = row.get("merchant", row.get("payee", row.get("to", desc[:30])))

        # Category
        category = row.get("category", "")
        if not category:
            category = categorise(desc, merchant)

        if amount > 0:
            transactions.append({
                "date": parsed_date.strftime("%Y-%m-%d"),
                "month": parsed_date.strftime("%b %Y"),
                "month_sort": parsed_date.strftime("%Y-%m"),
                "description": desc,
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "type": txn_type,
                "balance": float(re.sub(r"[^\d.]", "", row.get("balance", "0") or "0") or 0),
                "upi_ref": row.get("upi_ref", row.get("ref", "")),
            })

    return sorted(transactions, key=lambda x: x["date"], reverse=True)


def detect_subscriptions(transactions: list[dict]) -> list[dict]:
    """
    Finds recurring charges: same merchant appearing monthly with similar amount.
    Returns list of suspected subscriptions with monthly_cost.
    """
    debits = [t for t in transactions if t["type"] == "debit"]

    merchant_months = defaultdict(lambda: defaultdict(list))
    for t in debits:
        merchant_months[t["merchant"]][t["month_sort"]].append(t["amount"])

    subscriptions = []
    for merchant, months in merchant_months.items():
        if len(months) >= 2:
            amounts = [sum(v) / len(v) for v in months.values()]
            avg = sum(amounts) / len(amounts)
            variance = sum((a - avg) ** 2 for a in amounts) / len(amounts)
            cv = (variance ** 0.5) / avg if avg > 0 else 1

            # Low coefficient of variation = consistent charge = likely subscription
            if cv < 0.15 and avg < 3000:
                subscriptions.append({
                    "merchant": merchant,
                    "monthly_cost": round(avg, 2),
                    "annual_cost": round(avg * 12, 2),
                    "months_seen": len(months),
                    "category": next(
                        (t["category"] for t in debits if t["merchant"] == merchant),
                        "Subscriptions"
                    ),
                })

    return sorted(subscriptions, key=lambda x: x["monthly_cost"], reverse=True)


def compute_insights(transactions: list[dict]) -> dict:
    """
    Computes all analytics needed by the frontend in one pass.
    """
    debits = [t for t in transactions if t["type"] == "debit"]
    credits = [t for t in transactions if t["type"] == "credit"]

    total_spent = round(sum(t["amount"] for t in debits), 2)
    total_income = round(sum(t["amount"] for t in credits), 2)

    # Spend by category
    cat_spend = defaultdict(float)
    for t in debits:
        cat_spend[t["category"]] += t["amount"]
    spend_by_category = [
        {"category": k, "amount": round(v, 2), "pct": round(v / total_spent * 100, 1) if total_spent else 0}
        for k, v in sorted(cat_spend.items(), key=lambda x: -x[1])
        if k != "Income"
    ]

    # Monthly trend
    monthly = defaultdict(lambda: {"spent": 0.0, "income": 0.0, "month_sort": ""})
    for t in transactions:
        k = t["month"]
        monthly[k]["month_sort"] = t["month_sort"]
        if t["type"] == "debit":
            monthly[k]["spent"] += t["amount"]
        else:
            monthly[k]["income"] += t["amount"]

    monthly_trend = [
        {"month": k, "month_sort": v["month_sort"], "spent": round(v["spent"], 2), "income": round(v["income"], 2)}
        for k, v in monthly.items()
    ]
    monthly_trend.sort(key=lambda x: x["month_sort"])

    # Top merchants
    merch_spend = defaultdict(float)
    for t in debits:
        merch_spend[t["merchant"]] += t["amount"]
    top_merchants = [
        {"merchant": k, "amount": round(v, 2)}
        for k, v in sorted(merch_spend.items(), key=lambda x: -x[1])[:10]
    ]

    # Subscriptions
    subscriptions = detect_subscriptions(transactions)
    total_sub_monthly = round(sum(s["monthly_cost"] for s in subscriptions), 2)

    # Largest single transactions
    largest = sorted(debits, key=lambda x: -x["amount"])[:5]

    # Avg daily spend
    dates = sorted(set(t["date"] for t in debits))
    avg_daily = round(total_spent / len(dates), 2) if dates else 0

    # Savings rate
    savings_rate = round((total_income - total_spent) / total_income * 100, 1) if total_income else 0

    return {
        "summary": {
            "total_spent": total_spent,
            "total_income": total_income,
            "net": round(total_income - total_spent, 2),
            "avg_daily_spend": avg_daily,
            "savings_rate": savings_rate,
            "n_transactions": len(transactions),
            "months_covered": len(monthly),
        },
        "spend_by_category": spend_by_category,
        "monthly_trend": monthly_trend,
        "top_merchants": top_merchants,
        "subscriptions": subscriptions,
        "subscription_monthly_total": total_sub_monthly,
        "largest_transactions": [
            {k: v for k, v in t.items()} for t in largest
        ],
        "transactions": transactions,
    }
