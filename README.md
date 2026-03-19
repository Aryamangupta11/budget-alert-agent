# Budget Alert Agent

An AI-powered personal budget tracking agent that monitors your spending,
categorizes transactions using Claude, and fires smart alerts before you overspend.

## Problem it solves

People discover they've overspent only at the end of the month — too late to fix it.
This agent monitors your transactions daily, categorizes them automatically using Claude AI,
and alerts you with actionable advice the moment a budget category hits 70% or above.

## Features

- AI transaction categorization using Claude via OpenRouter
- Real-time budget tracking per category
- Smart alerts at WARNING (70%) and CRITICAL (90%) thresholds
- Pace detection — alerts if spending faster than expected
- Streamlit dashboard with charts and AI-generated advice
- CSV upload directly from the browser
- CLI for terminal usage
- Daily scheduler for automatic checks
- Duplicate transaction protection
- Graceful error handling for bad CSV files, missing DB, wrong API keys

## Tech Stack

| Layer       | Technology              |
|-------------|-------------------------|
| Language    | Python 3.11             |
| AI Model    | Claude via OpenRouter   |
| Database    | SQLite                  |
| UI          | Streamlit + Plotly      |
| CLI         | Click                   |
| Scheduler   | APScheduler             |
| Testing     | pytest (17 tests)       |

## Project Structure
```
budget-alert-agent/
├── agent/
│   ├── __init__.py
│   ├── ingester.py        # CSV → SQLite with duplicate protection
│   ├── categorizer.py     # Claude transaction labelling
│   ├── budget_checker.py  # Spend vs limits logic
│   ├── advisor.py         # Claude alert messages
│   ├── main.py            # CLI entry point
│   └── scheduler.py       # Daily auto-run
├── data/
│   └── budgets.json       # Your budget limits
├── tests/
│   ├── sample_transactions.csv
│   └── test_agent.py      # 17 pytest tests
├── benchmarks/
│   └── compare_cursor.md  # Scoring and comparison
├── app.py                 # Streamlit dashboard
├── .cursorrules           # Cursor AI config
├── .env.example           # Environment variables template
├── .gitignore
└── README.md
```

## Setup

1. Clone the repository
```bash
git clone https://github.com/Aryamangupta11/budget-alert-agent
cd budget-alert-agent
```

2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

3. Install dependencies
```bash
pip install anthropic python-dotenv click pandas sendgrid twilio apscheduler streamlit plotly openai schedule pytest
```

4. Set up environment variables
```bash
cp .env.example .env
# Add your OpenRouter API key to .env
```

5. Initialize database and load sample data
```bash
python -m agent.main ingest tests/sample_transactions.csv
python -m agent.main categorize
```

6. Run the dashboard
```bash
streamlit run app.py
```

## CLI Usage
```bash
# Load transactions from CSV
python -m agent.main ingest your_bank_statement.csv

# Categorize transactions using Claude
python -m agent.main categorize

# View budget report
python -m agent.main report

# Run full pipeline
python -m agent.main run-all
```

## Run Tests
```bash
python -m pytest tests/test_agent.py -v
```

17 tests covering ingester, budget checker, categorizer and advisor modules.

## Environment Variables
```
OPENROUTER_API_KEY=your_openrouter_key_here
```

Get a free key at openrouter.ai

## Bugs Found and Fixed

| Bug | Fix |
|-----|-----|
| Duplicate transactions on re-ingest | UNIQUE constraint + INSERT OR IGNORE |
| Crash when DB deleted | os.path.exists check + try/except |
| Wrong CSV columns showed fake success | Column validation with red error message |
| Empty CSV showed fake success | Warning message instead |
| Raw API traceback on wrong key | try/except with clean error message |
| JSON parse error crash | try/except on json.loads |
| Empty description rows inserted | Skip if description is empty or nan |

## Performance Score

**Score: 8,965 / 10,000**
```
Score = (Categorization_accuracy × 0.35 +
         Alert_precision        × 0.30 +
         Alert_recall           × 0.20 +
         Latency_score          × 0.15) × 10,000

= (0.93 × 0.35) + (0.89 × 0.30) + (0.95 × 0.20) + (0.76 × 0.15)
= 0.3255 + 0.267 + 0.190 + 0.114
= 0.8965 × 10,000
= 8,965
```

## License

MIT


