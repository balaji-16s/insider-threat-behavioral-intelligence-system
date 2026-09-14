#!/usr/bin/env python3
"""
Enrich the CERT dataset with the remaining monitored activity types.

The CERT r1 dataset only contains logon / device / http events, so the app
only sees ``login``, ``usb_device`` and ``data_transfer``. This script adds
realistic synthetic events for the other 5 monitored types — ``file_download``,
``file_upload``, ``email``, ``privilege_change`` and ``remote_access`` — so
every module (Activity Logs, anomaly rules, risk models, reports) sees the
full 8-type activity set. CERT events are left untouched.

Usage:
    python scripts/enrich_activity.py
    python scripts/enrich_activity.py --days 30 --events-per-day 4
"""

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import SessionLocal  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.activity_log import ActivityLog, ActivityType  # noqa: E402

# The activity types the CERT r1 release does not contain — the ones this
# script is responsible for. Kept here so callers (e.g. refresh_dataset.py)
# can identify previously enriched rows without duplicating the list.
ENRICHED_TYPES = (
    ActivityType.FILE_DOWNLOAD,
    ActivityType.FILE_UPLOAD,
    ActivityType.EMAIL,
    ActivityType.PRIVILEGE_CHANGE,
    ActivityType.REMOTE_ACCESS,
)

FILE_NAMES = [
    "quarterly_report", "project_plan", "budget_2026", "audit_findings",
    "onboarding_guide", "security_policy", "contract_draft", "meeting_notes",
    "release_notes", "sprint_backlog", "customer_data", "inventory_sheet",
    "resume", "invoice_0421", "vendor_agreement", "architecture_diagram",
]
FILE_EXTS = ["pdf", "xlsx", "docx", "csv", "zip", "pptx"]

EMAIL_DOMAINS = ["company.com", "partner.com", "client.com", "vendor.com"]

REMOTE_PLATFORMS = ["vpn", "remote-desktop", "cloud-portal", "sso-portal"]


def enrich_activity(
    db: Session,
    days: int = 30,
    events_per_day: int = 4,
    end_at: datetime | None = None,
    seed: int = 20260816,
    verbose: bool = True,
) -> int:
    """Synthesize the 5 non-CERT activity types over the last ``days`` days.

    Generates events for every employee, ending at ``end_at`` (defaults to
    now), and returns the number of events inserted. Deterministic for a
    given ``seed`` so re-runs are reproducible.
    """
    rng = random.Random(seed)  # deterministic
    end = end_at or datetime.utcnow()

    employees = db.query(Employee).all()
    if not employees:
        raise RuntimeError("No employees found. Ingest the CERT dataset first.")

    if verbose:
        print(f"Enriching activity for {len(employees)} employees over {days} days...")
    batch: list[ActivityLog] = []
    total = 0

    for idx, emp in enumerate(employees):
        # Slight per-employee variation so volumes look organic.
        per_day = max(1, events_per_day + rng.randint(-1, 2))
        for day_ago in range(days):
            day = end - timedelta(days=day_ago)
            for _ in range(per_day):
                atype = rng.choices(
                    list(ENRICHED_TYPES),
                    weights=[30, 18, 32, 3, 17],
                )[0]

                # Mostly business hours, ~8% off-hours, some late night.
                if rng.random() < 0.08:
                    hour = rng.randint(1, 5)
                else:
                    hour = rng.randint(8, 19)
                occurred = day.replace(
                    hour=hour,
                    minute=rng.randint(0, 59),
                    second=rng.randint(0, 59),
                )
                # Never generate telemetry later than the anchor instant, so
                # the dataset stays anchored to "now" instead of drifting
                # into the future on the most recent day.
                if occurred > end:
                    occurred = end - timedelta(seconds=rng.randint(1, 300))

                details = _details_for(atype, rng)
                batch.append(
                    ActivityLog(
                        employee_id=emp.id,
                        activity_type=atype,
                        source=details.pop("_source", "enriched"),
                        details=details,
                        occurred_at=occurred,
                    )
                )
                total += 1

                if len(batch) >= 20000:
                    db.bulk_save_objects(batch)
                    db.commit()
                    batch = []
                    if verbose:
                        print(f"    {total:>9,} events inserted...")

        if verbose and (idx + 1) % 200 == 0:
            print(f"    {idx + 1}/{len(employees)} employees done")

    if batch:
        db.bulk_save_objects(batch)
        db.commit()

    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich activity logs with the 5 missing activity types.")
    parser.add_argument("--days", type=int, default=30, help="How many days back to synthesize events (default: 30)")
    parser.add_argument("--events-per-day", type=int, default=4,
                        help="Base events per employee per day (default: 4)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        employees = db.query(Employee).count()
        if not employees:
            print("✗ No employees found. Ingest the CERT dataset first.")
            return

        total = enrich_activity(
            db, days=args.days, events_per_day=args.events_per_day
        )

        print("=" * 60)
        print("  ✅ ACTIVITY ENRICHMENT COMPLETE")
        print("=" * 60)
        print(f"  Employees:       {employees}")
        print(f"  New events:      {total:,} ({args.days}-day window)")
        print("  Types added:     file_download, file_upload, email,")
        print("                   privilege_change, remote_access")
        print("  CERT events:     untouched")
        print("\n  Next: run the UEBA pipeline (UEBA Intelligence page) to")
        print("        refresh baselines and risk scores with the new data.")
    finally:
        db.close()


def _details_for(atype: ActivityType, rng: random.Random) -> dict:
    name = rng.choice(FILE_NAMES)
    ext = rng.choice(FILE_EXTS)
    if atype == ActivityType.FILE_DOWNLOAD:
        size_kb = rng.randint(50, 90000)
        # Some large downloads (> 10 MB) to feed the large-file rule.
        if rng.random() < 0.04:
            size_kb = rng.randint(11000, 250000)
        return {
            "_source": rng.choice(["file_server", "cloud_portal", "email_server"]),
            "filename": f"{name}_{rng.randint(1, 999)}.{ext}",
            "size_kb": size_kb,
            "location": rng.choice(["/shared/", "/projects/", "/reports/"]),
        }
    if atype == ActivityType.FILE_UPLOAD:
        return {
            "_source": rng.choice(["file_server", "cloud_portal"]),
            "filename": f"{name}_{rng.randint(1, 999)}.{ext}",
            "size_kb": rng.randint(10, 50000),
            "destination": rng.choice(["shared-drive", "archive", "team-folder"]),
        }
    if atype == ActivityType.EMAIL:
        return {
            "_source": "email_server",
            "recipients": rng.randint(1, 12),
            "has_attachment": rng.random() > 0.6,
            "to_domain": rng.choice(EMAIL_DOMAINS),
            "sensitive": rng.random() < 0.05,
        }
    if atype == ActivityType.PRIVILEGE_CHANGE:
        return {
            "_source": "iam",
            "action": rng.choice(["granted", "elevated", "revoked", "modified"]),
            "privilege": rng.choice(
                ["admin_panel", "source_code", "financial_reports", "cloud_console"]
            ),
            "actor": rng.choice(["self", "manager", "it-admin"]),
        }
    # remote_access
    return {
        "_source": rng.choice(REMOTE_PLATFORMS),
        "method": rng.choice(["mfa", "password", "sso"]),
        "success": rng.random() > 0.03,
        "off_hours": True,
    }


if __name__ == "__main__":
    main()
