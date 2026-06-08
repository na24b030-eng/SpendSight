"""
Generates realistic synthetic UPI transaction CSV.
Mimics the export format of Paytm / BHIM statements.

Output columns:
  date, time, description, merchant, amount, type (debit/credit), balance, upi_ref
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

MERCHANTS = {
    "Food & Dining": [
        ("Swiggy", 180, 650),
        ("Zomato", 200, 700),
        ("Blinkit", 150, 900),
        ("McDonald's", 200, 500),
        ("Cafe Coffee Day", 120, 300),
        ("Domino's Pizza", 250, 600),
        ("Haldiram's", 100, 400),
        ("Starbucks", 300, 600),
        ("Zepto", 200, 1200),
        ("BigBasket", 400, 2000),
    ],
    "Transport": [
        ("Ola", 80, 400),
        ("Uber", 100, 500),
        ("Rapido", 40, 200),
        ("IRCTC", 300, 2500),
        ("MakeMyTrip", 1500, 8000),
        ("RedBus", 400, 1200),
        ("Metro Card Recharge", 200, 500),
        ("IndiGo Airlines", 2000, 12000),
    ],
    "Subscriptions": [
        ("Netflix", 149, 649),
        ("Spotify", 59, 119),
        ("Amazon Prime", 179, 179),
        ("Hotstar", 299, 299),
        ("YouTube Premium", 139, 139),
        ("Notion", 160, 160),
        ("LinkedIn Premium", 1600, 1600),
        ("Adobe Creative", 1675, 1675),
    ],
    "Shopping": [
        ("Amazon", 300, 5000),
        ("Flipkart", 400, 4000),
        ("Myntra", 500, 3000),
        ("Nykaa", 300, 2000),
        ("AJIO", 600, 2500),
        ("Meesho", 200, 1500),
        ("Croma", 1000, 15000),
    ],
    "Utilities": [
        ("BESCOM Electricity", 800, 3000),
        ("Airtel Postpaid", 399, 999),
        ("Jio Recharge", 239, 999),
        ("BWSSB Water Bill", 200, 600),
        ("BBMP Property Tax", 1000, 8000),
        ("LPG Cylinder", 800, 950),
        ("Society Maintenance", 1500, 4000),
    ],
    "Health": [
        ("PharmEasy", 200, 1500),
        ("1mg", 150, 1200),
        ("Apollo Pharmacy", 300, 2000),
        ("Cult.fit", 2000, 2000),
        ("Dr. Lal PathLabs", 500, 3000),
        ("HealthifyMe", 999, 999),
    ],
    "Finance": [
        ("SBI Mutual Fund SIP", 500, 2000),
        ("Zerodha Kite", 500, 5000),
        ("LIC Premium", 1000, 3000),
        ("HDFC Life Insurance", 500, 2000),
        ("Groww SIP", 1000, 5000),
        ("NPS Contribution", 500, 2000),
    ],
    "Entertainment": [
        ("BookMyShow", 200, 800),
        ("PVR Cinemas", 300, 1200),
        ("INOX", 250, 1000),
        ("Steam", 100, 3000),
    ],
    "Transfers": [
        ("UPI Transfer", 100, 2000),
        ("NEFT Transfer", 200, 3000),
        ("Split Bill", 50, 800),
    ],
}

CREDITS = [
    ("Salary Credit", 40000, 90000),
    ("Freelance Payment", 5000, 30000),
    ("Refund", 100, 3000),
    ("Cashback", 10, 200),
    ("UPI Received", 200, 5000),
]

UPI_IDS = [
    "swiggy@icici", "zomato@paytm", "uber@yesbank", "netflix@kotak",
    "amazon@apl", "flipkart@yes", "ola@okaxis", "irctc@sbi",
    "jio@paytm", "hdfc@upi", "user@oksbi", "friend@okhdfc"
]


def rand_upi_ref():
    return "".join([str(random.randint(0, 9)) for _ in range(12)])


def generate(n_months=6, output_path=None):
    rows = []
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30 * n_months)
    balance = 45000.0
    current = start_date

    # Salary on 1st of each month
    salary_dates = set()
    d = start_date.replace(day=1)
    while d <= end_date:
        salary_dates.add(d.strftime("%Y-%m-%d"))
        # move to next month
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)

    # Fixed subscriptions: same day every month
    sub_day = random.randint(5, 10)
    chosen_subs = random.sample(MERCHANTS["Subscriptions"], 4)

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        time_str = f"{random.randint(8,22):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"

        # Salary credit
        if date_str in salary_dates:
            amt = round(random.uniform(50000, 75000), 2)
            balance += amt
            rows.append({
                "date": date_str, "time": time_str,
                "description": "SALARY CREDIT - EMPLOYER",
                "merchant": "Salary Credit",
                "category": "Income",
                "amount": amt, "type": "credit",
                "balance": round(balance, 2),
                "upi_ref": rand_upi_ref(),
            })

        # Subscriptions on sub_day
        if current.day == sub_day:
            for name, lo, hi in chosen_subs:
                amt = round(random.uniform(lo, hi) if lo != hi else lo, 2)
                balance -= amt
                rows.append({
                    "date": date_str, "time": f"{random.randint(0,6):02d}:{random.randint(0,59):02d}:00",
                    "description": f"AUTO-DEBIT {name.upper()}",
                    "merchant": name,
                    "category": "Subscriptions",
                    "amount": amt, "type": "debit",
                    "balance": round(balance, 2),
                    "upi_ref": rand_upi_ref(),
                })

        # Random daily transactions
        n_today = random.choices([0, 1, 2, 3, 4], weights=[0.1, 0.3, 0.3, 0.2, 0.1])[0]
        for _ in range(n_today):
            cat = random.choice([c for c in MERCHANTS if c != "Subscriptions"])
            name, lo, hi = random.choice(MERCHANTS[cat])
            amt = round(random.uniform(lo, hi), 2)
            balance -= amt
            rows.append({
                "date": date_str, "time": time_str,
                "description": f"UPI/{name.replace(' ', '_').upper()}/{rand_upi_ref()[:6]}",
                "merchant": name,
                "category": cat,
                "amount": amt, "type": "debit",
                "balance": round(balance, 2),
                "upi_ref": rand_upi_ref(),
            })

        # Occasional credit (refund / received)
        if random.random() < 0.06:
            name, lo, hi = random.choice(CREDITS[1:])
            amt = round(random.uniform(lo, hi), 2)
            balance += amt
            rows.append({
                "date": date_str, "time": time_str,
                "description": name.upper(),
                "merchant": name,
                "category": "Income",
                "amount": amt, "type": "credit",
                "balance": round(balance, 2),
                "upi_ref": rand_upi_ref(),
            })

        current += timedelta(days=1)

    rows.sort(key=lambda r: (r["date"], r["time"]))

    if output_path is None:
        output_path = Path(__file__).parent / "sample_transactions.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","time","description","merchant","category","amount","type","balance","upi_ref"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} transactions → {output_path}")
    return rows


if __name__ == "__main__":
    generate()
