#!/usr/bin/env python3
"""
Create demo worker (employee portal) accounts.

The portal is only meaningful with sample logins, so this links a
``UserRole.EMPLOYEE`` account to real employees drawn from the dataset:
the highest-risk employee, a mid-risk one, and a low-risk one. That makes
the dashboard demonstrate genuine contrast instead of three identical
screens.

Run after the dataset is ingested and risk scores have been calculated
(``scripts/refresh_dataset.py`` does both), so the accounts land on
employees that actually have behaviour to show.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func

from app.core.security import hash_password
from app.db.base import SessionLocal
from app.models.employee import Employee
from app.models.risk_score import RiskScore
from app.models.user import User, UserRole

PASSWORD = "Password123!"

# Which positions in the risk ranking get a demo account (0 = highest risk).
PICKS = {
    "worker.high@itbis.com": 0,
    "worker.mid@itbis.com": 0.5,
    "worker.low@itbis.com": -1,
}


def _email_slug(full_name: str) -> str:
    """Build a readable, unique-ish local part from an employee name."""
    return re.sub(r"[^a-z0-9.]+", ".", full_name.lower()).strip(".")


def _ranked_employees(db) -> list[tuple[Employee, float]]:
    """All scored employees ordered from highest to lowest risk."""
    latest = (
        db.query(RiskScore.employee_id, func.max(RiskScore.score).label("score"))
        .group_by(RiskScore.employee_id)
        .subquery()
    )
    rows = (
        db.query(Employee, latest.c.score)
        .join(latest, latest.c.employee_id == Employee.id)
        .order_by(latest.c.score.desc())
        .all()
    )
    return [(emp, float(score or 0)) for emp, score in rows]


def seed_worker_users() -> None:
    db = SessionLocal()
    try:
        ranked = _ranked_employees(db)
        if not ranked:
            print(
                "No risk scores found. Run the UEBA pipeline first:\n"
                "  python scripts/refresh_dataset.py"
            )
            return

        print(f"Seeding worker portal accounts across {len(ranked)} scored employees...")

        for email, position in PICKS.items():
            index = (
                len(ranked) - 1
                if position < 0
                else min(len(ranked) - 1, int(len(ranked) * position))
            )
            employee, score = ranked[index]

            user = db.query(User).filter(User.email == email).first()
            if user is None:
                user = User(
                    full_name=employee.full_name,
                    email=email,
                    hashed_password=hash_password(PASSWORD),
                    role=UserRole.EMPLOYEE,
                    is_active=True,
                )
                db.add(user)
                action = "Created"
            else:
                user.hashed_password = hash_password(PASSWORD)
                user.role = UserRole.EMPLOYEE
                user.full_name = employee.full_name
                action = "Updated"

            # Point the login at whichever employee currently holds this
            # risk position, so re-running keeps the demo meaningful.
            user.employee_id = employee.id
            db.commit()

            print(
                f"  ✓ {action} {email} ({PASSWORD})\n"
                f"      -> {employee.full_name} "
                f"({employee.department or 'n/a'}), risk {score:.1f}"
            )

        print("\nWorker portal accounts ready.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_worker_users()
