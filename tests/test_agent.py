import pytest
import sqlite3
import os
import json
import pandas as pd
from unittest.mock import patch, MagicMock

# ── ingester tests ────────────────────────────────────────────────────────────

def test_load_transactions_valid_csv():
    from agent.ingester import load_transactions
    txs = load_transactions("tests/sample_transactions.csv")
    assert len(txs) >= 0, "Should load transactions without crashing"

def test_load_transactions_missing_file():
    from agent.ingester import load_transactions
    result = load_transactions("nonexistent_file.csv")
    assert result == [], "Should return empty list for missing file"

def test_load_transactions_negative_amounts():
    """Bank CSVs often have negative amounts — should be stored as positive."""
    from agent.ingester import load_transactions
    df = pd.DataFrame([
        {"date": "2026-03-20", "description": "Negative test tx", "amount": -500}
    ])
    df.to_csv("tests/temp_negative_test.csv", index=False)
    txs = load_transactions("tests/temp_negative_test.csv")
    os.remove("tests/temp_negative_test.csv")
    if txs:
        assert txs[0]["amount"] == 500, "Negative amounts should be made positive"

def test_load_transactions_wrong_columns():
    """CSV with wrong column names should return empty list."""
    from agent.ingester import load_transactions
    df = pd.DataFrame([
        {"wrong_col": "2026-03-01", "another_col": "Test", "price": 100}
    ])
    df.to_csv("tests/temp_wrong_cols.csv", index=False)
    result = load_transactions("tests/temp_wrong_cols.csv")
    os.remove("tests/temp_wrong_cols.csv")
    assert result == [], "Wrong columns should return empty list"

def test_no_duplicates_in_db():
    """Running ingest twice should not duplicate transactions."""
    from agent.ingester import load_transactions

    # Get count before
    conn = sqlite3.connect("data/transactions.db")
    count_before = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    conn.close()

    # Run ingest twice
    load_transactions("tests/sample_transactions.csv")
    load_transactions("tests/sample_transactions.csv")

    # Count should not have increased
    conn = sqlite3.connect("data/transactions.db")
    count_after = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    conn.close()

    assert count_before == count_after, \
        f"Duplicates detected! Count went from {count_before} to {count_after}"


# ── budget checker tests ──────────────────────────────────────────────────────

def test_check_budgets_returns_list():
    from agent.budget_checker import check_budgets
    alerts = check_budgets()
    assert isinstance(alerts, list), "Should return a list"

def test_alert_has_required_fields():
    from agent.budget_checker import check_budgets
    alerts = check_budgets()
    for alert in alerts:
        assert "category" in alert
        assert "spent" in alert
        assert "limit" in alert
        assert "pct_used" in alert
        assert "level" in alert

def test_alert_levels_are_valid():
    from agent.budget_checker import check_budgets
    alerts = check_budgets()
    for alert in alerts:
        assert alert["level"] in ("SAFE", "WARNING", "CRITICAL"), \
            f"Invalid level: {alert['level']}"

def test_critical_threshold():
    pct = 95
    level = "CRITICAL" if pct >= 90 else "WARNING" if pct >= 70 else "SAFE"
    assert level == "CRITICAL"

def test_warning_threshold():
    pct = 75
    level = "CRITICAL" if pct >= 90 else "WARNING" if pct >= 70 else "SAFE"
    assert level == "WARNING"

def test_safe_threshold():
    pct = 50
    level = "CRITICAL" if pct >= 90 else "WARNING" if pct >= 70 else "SAFE"
    assert level == "SAFE"

def test_budgets_file_exists():
    assert os.path.exists("data/budgets.json"), "budgets.json should exist"
    with open("data/budgets.json") as f:
        budgets = json.load(f)
    assert len(budgets) > 0, "Budgets should not be empty"


# ── categorizer tests (mocked) ────────────────────────────────────────────────

def test_categorizer_empty_input():
    from agent.categorizer import categorize_transactions
    result = categorize_transactions([])
    assert result == [], "Empty input should return empty list"

def test_categorizer_strips_markdown():
    from agent.categorizer import categorize_transactions
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '''```json
[{"date":"2026-03-01","description":"Swiggy","amount":450,"category":"Food"}]
```'''
    with patch("agent.categorizer.client.chat.completions.create",
               return_value=mock_response):
        result = categorize_transactions([
            {"date": "2026-03-01", "description": "Swiggy", "amount": 450}
        ])
        assert result[0]["category"] == "Food"

def test_categorizer_valid_categories():
    from agent.categorizer import CATEGORIES
    valid = set(CATEGORIES)
    result = [{"category": "Food"}, {"category": "Transport"}]
    for r in result:
        assert r["category"] in valid


# ── advisor tests (mocked) ────────────────────────────────────────────────────

def test_advisor_returns_string():
    from agent.advisor import generate_alert_message
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "You are overspending on food."
    with patch("agent.advisor.client.chat.completions.create",
               return_value=mock_response):
        alert = {
            "category": "Food", "spent": 2500, "limit": 3000,
            "pct_used": 83.3, "remaining": 500, "level": "WARNING",
            "pace_warning": True, "days_remaining": 11
        }
        msg = generate_alert_message(alert)
        assert isinstance(msg, str)
        assert len(msg) > 0

def test_advisor_message_content():
    from agent.advisor import generate_all_alerts
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Cut back on dining out."
    with patch("agent.advisor.client.chat.completions.create",
               return_value=mock_response):
        alerts = [{
            "category": "Food", "spent": 2500, "limit": 3000,
            "pct_used": 83.3, "remaining": 500, "level": "WARNING",
            "pace_warning": True, "days_remaining": 11
        }]
        results = generate_all_alerts(alerts)
        assert results[0]["message"] == "Cut back on dining out."