import pandas as pd
import sqlite3
import os
from datetime import datetime

DB_PATH = "data/transactions.db"

def init_db():
    """Create the transactions table if it doesn't exist."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'Uncategorized'
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized.")

def load_transactions(csv_file: str) -> list[dict]:
    """Load transactions from a CSV file into the database."""

    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        return []

    df = pd.read_csv(csv_file)

    # Normalize column names to lowercase
    df.columns = [col.strip().lower() for col in df.columns]

    # Check required columns exist
    required = {"date", "description", "amount"}
    if not required.issubset(set(df.columns)):
        print(f"Error: CSV must have columns: {required}")
        print(f"Found columns: {set(df.columns)}")
        return []

    init_db()
    conn = sqlite3.connect(DB_PATH)

    inserted = 0
    skipped = 0
    transactions = []

    for _, row in df.iterrows():
        try:
            date = pd.to_datetime(row["date"]).strftime("%Y-%m-%d")
            description = str(row["description"]).strip()
            amount = abs(float(row["amount"]))

            

            if not description or description.lower() == "nan":
                print(f"  Skipping row — empty description on {date}")
                continue

            existing = conn.execute("""
                SELECT COUNT(*) FROM transactions
                WHERE date = ? AND description = ? AND amount = ?
            """, (date, description, amount)).fetchone()[0]

            

            if existing == 0:
                conn.execute("""
                    INSERT OR IGNORE INTO transactions (date, description, amount)
                    VALUES (?, ?, ?)
                """, (date, description, amount))
                transactions.append({
                    "date": date,
                    "description": description,
                    "amount": amount
                })
                inserted += 1
            else:
                print(f"  Skipping duplicate: {description} on {date}")
                skipped += 1

        except Exception as e:
            print(f"Skipping row due to error: {e}")
            continue

    conn.commit()
    conn.close()

    print(f"Successfully loaded {inserted} transactions. ({skipped} duplicates skipped)")
    return transactions


def get_all_transactions() -> list[dict]:
    """Fetch all transactions from the database."""
    if not os.path.exists(DB_PATH):
        print("No database found. Run ingest first.")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT date, description, amount, category FROM transactions ORDER BY date DESC"
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {"date": r[0], "description": r[1], "amount": r[2], "category": r[3]}
        for r in rows
    ]