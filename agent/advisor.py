import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

def generate_alert_message(alert: dict) -> str:
    """Ask Claude to write a friendly, actionable alert message."""

    prompt = f"""
    Write a short, friendly budget alert message in 2-3 sentences.

    Data:
    - Category: {alert['category']}
    - Spent: Rs.{alert['spent']} of Rs.{alert['limit']} budget ({alert['pct_used']}%)
    - Days remaining this month: {alert['days_remaining']}
    - Remaining budget: Rs.{alert['remaining']}
    - Alert level: {alert['level']}
    - Spending too fast: {alert['pace_warning']}

    Rules:
    - Be direct and helpful
    - Give one specific actionable tip
    - Use Rs. for currency
    - Do not use markdown or bullet points
    - Keep it under 3 sentences
    """

    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


def generate_all_alerts(alerts: list[dict]) -> list[dict]:
    """Generate Claude messages for all alerts."""
    results = []

    for alert in alerts:
        print(f"Generating message for {alert['category']}...")
        message = generate_alert_message(alert)
        results.append({
            **alert,
            "message": message
        })

    return results


def print_alerts(alerts: list[dict]):
    """Print all alerts with Claude-generated messages."""
    if not alerts:
        print("\nNo alerts — all budgets on track!")
        return

    print(f"\n{'='*55}")
    print(f"  Budget Alerts ({len(alerts)} found)")
    print(f"{'='*55}\n")

    for alert in alerts:
        level = alert['level']
        if level == "CRITICAL":
            prefix = "!! CRITICAL"
        elif level == "WARNING":
            prefix = "!  WARNING "
        else:
            prefix = "   PACE    "

        print(f"  [{prefix}] {alert['category']}")
        print(f"  Rs.{alert['spent']} / Rs.{alert['limit']} ({alert['pct_used']}%)")
        print(f"  {alert['days_remaining']} days remaining | Rs.{alert['remaining']} left")
        print(f"\n  Claude says:")
        print(f"  {alert['message']}")
        print(f"\n  {'-'*50}\n")

