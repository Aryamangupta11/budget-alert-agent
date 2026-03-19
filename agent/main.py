import click
import json
import os
from dotenv import load_dotenv

load_dotenv()

@click.group()
def cli():
    """Budget Alert Agent — tracks your spending and alerts you."""
    pass


@cli.command()
@click.argument("csv_file")
def ingest(csv_file):
    """Load transactions from a CSV file."""
    from agent.ingester import load_transactions
    transactions = load_transactions(csv_file)
    if transactions:
        click.echo(f"\nLoaded {len(transactions)} transactions successfully.")
    else:
        click.echo("No transactions loaded. Check your CSV file.")


@cli.command()
def categorize():
    """Categorize all uncategorized transactions using Claude."""
    from agent.categorizer import run_categorization
    run_categorization()


@cli.command()
def report():
    """Show full budget report for current month."""
    from agent.budget_checker import print_budget_report
    print_budget_report()


@cli.command()
def check():
    """Run budget check and show Claude-generated alerts."""
    from agent.budget_checker import check_budgets
    from agent.advisor import generate_all_alerts, print_alerts

    click.echo("\nChecking budgets...")
    alerts = check_budgets()

    if not alerts:
        click.echo("All budgets on track — no alerts!")
        return

    click.echo(f"Found {len(alerts)} alert(s). Generating messages...\n")
    alerts_with_messages = generate_all_alerts(alerts)
    print_alerts(alerts_with_messages)


@cli.command()
def run_all():
    """Full pipeline — ingest, categorize, check and alert."""
    from agent.ingester import load_transactions
    from agent.categorizer import run_categorization
    from agent.budget_checker import check_budgets, print_budget_report
    from agent.advisor import generate_all_alerts, print_alerts

    click.echo("\n--- Step 1: Loading transactions ---")
    load_transactions("tests/sample_transactions.csv")

    click.echo("\n--- Step 2: Categorizing ---")
    run_categorization()

    click.echo("\n--- Step 3: Budget Report ---")
    print_budget_report()

    click.echo("\n--- Step 4: Generating Alerts ---")
    alerts = check_budgets()
    if alerts:
        alerts_with_messages = generate_all_alerts(alerts)
        print_alerts(alerts_with_messages)
    else:
        click.echo("All budgets on track!")


if __name__ == "__main__":
    cli()