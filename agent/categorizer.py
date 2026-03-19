import json
import sqlite3
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/transactions.db"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

CATEGORIES = ["Food", "Transport", "Entertainment",
               "Utilities", "Shopping", "Health", "Other"]

def categorize_transactions(transactions: list[dict]) -> list[dict]:
    """Use Claude via OpenRouter to categorize transactions."""

    if not transactions:
        print("No transactions to categorize.")
        return []

    prompt = f"""
    Categorize each transaction into exactly one of these categories: {', '.join(CATEGORIES)}.

    Transactions:
    {json.dumps(transactions, indent=2)}

    Return ONLY a valid JSON array. Each object must have all original fields 
    plus a new "category" field. No explanation, no markdown, no code blocks, just raw JSON.
    """

    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message.content

    # Strip markdown code blocks if model added them
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    result = json.loads(text)
    print(f"Categorized {len(result)} transactions.")
    return result


def save_categories(transactions: list[dict]):
    """Update the category field in the database."""
    conn = sqlite3.connect(DB_PATH)

    for tx in transactions:
        conn.execute("""
            UPDATE transactions 
            SET category = ?
            WHERE date = ? AND description = ? AND amount = ?
        """, (tx["category"], tx["date"], tx["description"], tx["amount"]))

    conn.commit()
    conn.close()
    print("Categories saved to database.")


def run_categorization():
    """Load uncategorized transactions, categorize them, save back."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT date, description, amount 
        FROM transactions 
        WHERE category = 'Uncategorized'
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("All transactions already categorized.")
        return

    transactions = [
        {"date": r[0], "description": r[1], "amount": r[2]}
        for r in rows
    ]

    print(f"Sending {len(transactions)} transactions to Claude via OpenRouter...")
    categorized = categorize_transactions(transactions)
    save_categories(categorized)

    print("\n--- Categorization Result ---")
    for tx in categorized:
        print(f"  {tx['date']} | {tx['description'][:30]:<30} | Rs.{tx['amount']} -> {tx['category']}")
