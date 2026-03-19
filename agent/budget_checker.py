import sqlite3
import json
import os
from datetime import date

DB_PATH = "data/transactions.db"
BUDGETS_PATH = "data/budgets.json"

def load_budgets() -> dict:
    """Load budget limits from JSON file."""
    if not os.path.exists(BUDGETS_PATH):
        # Create a default budgets file if none exists
        default_budgets = {
            "Food": 3000,
            "Transport": 2000,
            "Entertainment": 2000,
            "Utilities": 2000,
            "Shopping": 3000,
            "Health": 2000,
            "Other": 1000
        }
        os.makedirs("data", exist_ok=True)
        with open(BUDGETS_PATH, "w") as f:
            json.dump(default_budgets, f, indent=2)
        print(f"Created default budgets at {BUDGETS_PATH}")
        return default_budgets

    with open(BUDGETS_PATH, "r") as f:
        return json.load(f)


def get_monthly_spend(category: str, year: int, month: int) -> float:
    """Get total spending for a category in a given month."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) 
        FROM transactions
        WHERE category = ?
        AND strftime('%Y', date) = ?
        AND strftime('%m', date) = ?
    """, (category, str(year), f"{month:02d}"))
    total = cursor.fetchone()[0]
    conn.close()
    return total


def check_budgets() -> list[dict]:
    """Compare current month spending vs budget limits and return alerts."""
    budgets = load_budgets()
    alerts = []

    today = date.today()
    days_in_month = 30
    day_of_month = today.day
    expected_pct = day_of_month / days_in_month

    for category, limit in budgets.items():
        spent = get_monthly_spend(category, today.year, today.month)
        pct_used = (spent / limit * 100) if limit > 0 else 0
        remaining = limit - spent

        # Determine alert level
        if pct_used >= 90:
            level = "CRITICAL"
        elif pct_used >= 70:
            level = "WARNING"
        else:
            level = "SAFE"

        # Pace check: spending faster than expected?
        pace_warning = (spent / limit) > (expected_pct * 1.2) if limit > 0 else False

        if level != "SAFE" or pace_warning:
            alerts.append({
                "category": category,
                "spent": round(spent, 2),
                "limit": limit,
                "pct_used": round(pct_used, 1),
                "remaining": round(remaining, 2),
                "level": level,
                "pace_warning": pace_warning,
                "days_remaining": days_in_month - day_of_month
            })

    return alerts


def print_budget_report():
    """Print a full budget report to the terminal."""
    budgets = load_budgets()
    today = date.today()

    print(f"\n{'='*55}")
    print(f"  Budget Report — {today.strftime('%B %Y')}  (Day {today.day}/30)")
    print(f"{'='*55}")

    for category, limit in budgets.items():
        spent = get_monthly_spend(category, today.year, today.month)
        pct = (spent / limit * 100) if limit > 0 else 0
        bar_filled = int(pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)

        if pct >= 90:
            status = "!! CRITICAL"
        elif pct >= 70:
            status = "!  WARNING "
        else:
            status = "   OK      "

        print(f"\n  {category:<15} {status}")
        print(f"  [{bar}] {pct:.1f}%")
        print(f"  Rs.{spent:.0f} spent of Rs.{limit} budget  |  Rs.{limit-spent:.0f} remaining")

    print(f"\n{'='*55}\n")
    alerts = check_budgets()
    if alerts:
        print(f"  {len(alerts)} alert(s) need attention!")
    else:
        print("  All budgets on track.")
    print()

