import schedule
import time
import os
from dotenv import load_dotenv

load_dotenv()

def run_daily_check():
    """Run the full budget check pipeline."""
    print("\nRunning scheduled budget check...")

    from agent.budget_checker import check_budgets, print_budget_report
    from agent.advisor import generate_all_alerts, print_alerts

    print_budget_report()

    alerts = check_budgets()
    if alerts:
        alerts_with_messages = generate_all_alerts(alerts)
        print_alerts(alerts_with_messages)
    else:
        print("All budgets on track!")


def start_scheduler(run_at: str = "09:00"):
    """Start the daily scheduler."""
    print(f"Scheduler started — will check budgets daily at {run_at}")
    print("Press Ctrl+C to stop.\n")

    schedule.every().day.at(run_at).do(run_daily_check)

    # Also run immediately on start
    run_daily_check()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    start_scheduler()
