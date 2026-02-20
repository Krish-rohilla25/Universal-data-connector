"""
Mock data generator.

Generates realistic-looking customer, support-ticket, and analytics records so
that developers can bootstrap the service without needing a real database.
All data is deterministic when you pass a fixed seed, which makes tests easy.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# Friendly names to make mock data look more real
FIRST_NAMES = [
    "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry",
    "Iris", "Jack", "Karen", "Liam", "Mia", "Noah", "Olivia", "Paul",
    "Quinn", "Rachel", "Sam", "Tara",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Martinez",
    "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Lee",
    "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
]
DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "company.io", "corp.net"]

TICKET_SUBJECTS = [
    "Login page not loading",
    "Cannot export to CSV",
    "Billing discrepancy this month",
    "API returning 500 errors",
    "Password reset email not arriving",
    "Dashboard shows wrong date range",
    "Slow response times on search",
    "Feature request: dark mode",
    "Integration with Salesforce failing",
    "Two-factor auth keeps locking account",
]

METRICS = ["daily_active_users", "new_signups", "churn_rate", "revenue_usd"]


def _random_date(days_back: int = 365, rng: random.Random = None) -> datetime:
    rng = rng or random
    return datetime.utcnow() - timedelta(days=rng.randint(0, days_back))


def generate_customers(count: int = 50, seed: int = 42) -> List[Dict[str, Any]]:
    """Return a list of fake CRM customer records."""
    rng = random.Random(seed)
    customers = []
    for i in range(1, count + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        domain = rng.choice(DOMAINS)
        customers.append(
            {
                "customer_id": i,
                "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}@{domain}",
                "plan": rng.choice(["free", "starter", "pro", "enterprise"]),
                "mrr_usd": round(rng.uniform(0, 2000), 2),
                "created_at": _random_date(365, rng).isoformat(),
                "status": rng.choice(["active", "inactive", "churned"]),
            }
        )
    return customers


def generate_support_tickets(count: int = 50, seed: int = 42) -> List[Dict[str, Any]]:
    """Return a list of fake support ticket records."""
    rng = random.Random(seed)
    tickets = []
    for i in range(1, count + 1):
        created = _random_date(60, rng)
        tickets.append(
            {
                "ticket_id": i,
                "customer_id": rng.randint(1, 50),
                "subject": rng.choice(TICKET_SUBJECTS),
                "priority": rng.choice(["low", "medium", "high"]),
                "created_at": created.isoformat(),
                "updated_at": (created + timedelta(hours=rng.randint(1, 48))).isoformat(),
                "status": rng.choice(["open", "in_progress", "closed"]),
                "assigned_agent": rng.choice(["agent_a", "agent_b", "agent_c", None]),
            }
        )
    return tickets


def generate_analytics(days: int = 30, seed: int = 42) -> List[Dict[str, Any]]:
    """Return a list of daily metric records covering the last `days` days."""
    rng = random.Random(seed)
    records = []
    for day_offset in range(days):
        date = (datetime.utcnow() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for metric in METRICS:
            if metric == "daily_active_users":
                value = rng.randint(100, 1000)
            elif metric == "new_signups":
                value = rng.randint(5, 150)
            elif metric == "churn_rate":
                value = round(rng.uniform(0.5, 8.0), 2)
            else:
                value = round(rng.uniform(500, 50000), 2)
            records.append({"metric": metric, "date": date, "value": value})
    return records


def seed_data_files(data_dir: str = "data") -> None:
    """Write generated mock data to the JSON fixture files."""
    p = Path(data_dir)
    p.mkdir(exist_ok=True)

    (p / "customers.json").write_text(
        json.dumps(generate_customers(), indent=2), encoding="utf-8"
    )
    (p / "support_tickets.json").write_text(
        json.dumps(generate_support_tickets(), indent=2), encoding="utf-8"
    )
    (p / "analytics.json").write_text(
        json.dumps(generate_analytics(), indent=2), encoding="utf-8"
    )
    print(f"Mock data written to {p.resolve()}")


if __name__ == "__main__":
    seed_data_files()
