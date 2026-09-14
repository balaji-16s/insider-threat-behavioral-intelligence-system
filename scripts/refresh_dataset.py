#!/usr/bin/env python3
"""
Dataset Refresh / Re-anchor

Keeps the ingested demo dataset aligned with the analytics lookback windows
so every window contains *all* monitored activity types.

Why this is needed
------------------
1. ``ingest_cert.py`` rebases CERT timestamps so the newest event lands on
   "now" at ingest time. Days later the default 30-day lookback slowly
   empties and the dashboard/anomaly views look stale.
2. ``enrich_activity.py`` only synthesizes the 5 non-CERT activity types
   (file_download, file_upload, email, privilege_change, remote_access) for
   a short recent block, so wider windows see only the 3 CERT types
   (login, data_transfer, usb_device) — and a narrow window can end up
   containing just one threat type.

What this script does (idempotent)
----------------------------------
1. Removes the previously synthesized activity types.
2. Shifts every remaining (CERT) activity timestamp forward by the delta
   needed to land the newest event on "now", and shifts the alert /
   incident / notification timestamps by the same delta so the timeline
   stays consistent.
3. Re-generates the synthesized activity types across ``--days`` ending at
   "now", so all 8 activity types span the whole analysis window.
4. Clears the cached detection/ML result files.
5. Optionally recomputes behavioral baselines + risk scores and retrains
   the Isolation Forest model against the refreshed data.

Usage
-----
    python scripts/refresh_dataset.py                  # re-anchor + spread all 8 types
    python scripts/refresh_dataset.py --dry-run        # report only, change nothing
    python scripts/refresh_dataset.py --days 120       # spread types over 120 days
    python scripts/refresh_dataset.py --no-shift       # only re-spread types
    python scripts/refresh_dataset.py --no-recompute   # data only, no engine re-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, inspect, text  # noqa: E402

from app.db.base import SessionLocal  # noqa: E402
from app.models.activity_log import ActivityLog  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from scripts.enrich_activity import ENRICHED_TYPES, enrich_activity  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Timestamp columns that follow the activity timeline and are not recomputed
# by the engine step, so they are shifted by the same delta as the activity.
SHIFTED_COLUMNS = [
    ("activity_logs", "occurred_at"),
    ("activity_logs", "ingested_at"),
    ("alerts", "created_at"),
    ("alerts", "updated_at"),
    ("incidents", "created_at"),
    ("incidents", "closed_at"),
    ("notifications", "created_at"),
]

CACHE_FILES = ["detection_results.json", "ml_results.json"]


def _synthetic_type_names() -> list[str]:
    """Postgres enum labels for the synthesized types.

    SQLAlchemy's ``Enum`` persists the enum *names* (``EMAIL``), not the
    lowercase values, so raw SQL must compare against ``.name``.
    """
    return [t.name for t in ENRICHED_TYPES]


def _table_count(db, table: str) -> int:
    return db.execute(text(f"SELECT count(*) FROM {table}")).scalar() or 0


def _newest_cert_activity(db) -> datetime | None:
    """Newest timestamp among the CERT (non-synthesized) activity types."""
    return (
        db.query(func.max(ActivityLog.occurred_at))
        .filter(ActivityLog.activity_type.notin_(list(ENRICHED_TYPES)))
        .scalar()
    )


def _delete_synthetic(db) -> int:
    result = db.execute(
        text(
            "DELETE FROM activity_logs WHERE activity_type::text = ANY(:types)"
        ),
        {"types": _synthetic_type_names()},
    )
    db.commit()
    return result.rowcount or 0


def _shift_timeline(
    db, delta: timedelta, anchor: datetime
) -> dict[str, int]:
    """Add ``delta`` to every timeline column so dates stay consistent.

    Only rows anchored to the activity timeline (at or before the newest
    activity timestamp) are moved. Rows already recorded after that point
    belong to "now" and moving them would push them into the future.
    """
    inspector = inspect(db.get_bind())
    shifted: dict[str, int] = {}
    for table, column in SHIFTED_COLUMNS:
        existing_columns = {
            col["name"] for col in inspector.get_columns(table)
        }
        if column not in existing_columns:
            continue  # optional column not present in this schema
        result = db.execute(
            text(
                f"UPDATE {table} SET {column} = {column} + :delta "
                f"WHERE {column} IS NOT NULL AND {column} <= :anchor"
            ),
            {"delta": delta, "anchor": anchor},
        )
        shifted[f"{table}.{column}"] = result.rowcount or 0
    db.commit()
    return shifted


def _pull_back_future_timestamps(db) -> int:
    """Move a timeline column back if its newest row is in the future.

    The whole column is shifted by the overshoot so the newest row lands on
    now while the relative spacing between rows is preserved (a plain clamp
    would collapse every future row onto the same instant).
    """
    inspector = inspect(db.get_bind())
    adjusted = 0
    for table, column in SHIFTED_COLUMNS:
        existing_columns = {
            col["name"] for col in inspector.get_columns(table)
        }
        if column not in existing_columns:
            continue
        overshoot = db.execute(
            text(f"SELECT max({column}) - now() FROM {table}")
        ).scalar()
        if not overshoot or overshoot <= timedelta(0):
            continue
        result = db.execute(
            text(
                f"UPDATE {table} SET {column} = {column} - :overshoot "
                f"WHERE {column} IS NOT NULL"
            ),
            {"overshoot": overshoot},
        )
        adjusted += result.rowcount or 0
    db.commit()
    return adjusted


def _clear_caches() -> list[str]:
    cleared = []
    for name in CACHE_FILES:
        path = DATA_DIR / name
        if path.exists():
            path.unlink()
            cleared.append(name)

    # The peer cohort behind scoring and anomaly thresholds is cached in
    # memory, so drop it too: recomputation must derive thresholds from the
    # refreshed distribution, not the previous one.
    from app.services.threat_detection import invalidate_cohort_cache

    invalidate_cohort_cache()
    return cleared


def _recompute(db, days: int, verbose: bool) -> None:
    """Refresh baselines, risk scores and the ML model against the new data."""
    from app.services.behavioral_profiling import compute_all_baselines
    from app.services.risk_scoring import calculate_risk_scores
    from app.services.ml_anomaly_detection import train_and_save_model

    if verbose:
        print("\n[5/5] Recomputing engines (baselines, risk scores, ML model)...")

    baselines = compute_all_baselines(db, days=max(days, 90))
    if verbose:
        print(f"      baselines recomputed:        {baselines}")

    scoring = calculate_risk_scores(db, days=days)
    if verbose:
        print(
            f"      risk scores recalculated:    {scoring['calculated']} "
            f"(avg {scoring['average_score']})"
        )

    trained = train_and_save_model(db, days=days)
    if verbose:
        print(
            f"      ML model retrained:          {trained.get('samples')} samples"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-anchor the ingested dataset and spread all activity types."
    )
    parser.add_argument(
        "--days", type=int, default=90,
        help="Synthetic types span this many days back from now (default: 90)",
    )
    parser.add_argument(
        "--events-per-day", type=int, default=4,
        help="Base synthesized events per employee per day (default: 4)",
    )
    parser.add_argument(
        "--no-shift", action="store_true",
        help="Skip re-anchoring timestamps; only re-spread the synthesized types",
    )
    parser.add_argument(
        "--no-recompute", action="store_true",
        help="Skip baseline/risk/ML recomputation (data changes only)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without writing anything",
    )
    args = parser.parse_args()

    if args.days < 7:
        parser.error("--days must be at least 7")

    db = SessionLocal()
    try:
        employees = db.query(Employee).count()
        if not employees:
            print("✗ No employees found. Ingest the CERT dataset first:")
            print("    python scripts/ingest_cert.py --ingest --clear")
            return

        now = datetime.utcnow()
        newest_cert = _newest_cert_activity(db)
        delta = (now - newest_cert) if newest_cert else timedelta(0)

        print("=" * 62)
        print("  ITBIS - Dataset Refresh")
        print("=" * 62)
        print(f"  employees:                 {employees}")
        print(f"  activity rows:             {_table_count(db, 'activity_logs'):,}")
        print(f"  newest CERT activity:      {newest_cert}")
        print(f"  now:                       {now}")
        print(f"  shift needed:              {delta}")

        if args.dry_run:
            print("\n  --dry-run: no changes written.")
            return

        print("\n[1/5] Removing previously synthesized activity...")
        removed = _delete_synthetic(db)
        print(f"      removed {removed:,} rows of types {_synthetic_type_names()}")

        if args.no_shift:
            print("\n[2/5] Skipping timestamp re-anchor (--no-shift).")
        elif delta <= timedelta(0):
            print("\n[2/5] Dataset is already anchored to now; no shift needed.")
        else:
            print(f"\n[2/5] Re-anchoring timeline by {delta}...")
            # Rows already newer than the activity timeline are left alone.
            shifted = _shift_timeline(db, delta, newest_cert or now)
            for target, count in shifted.items():
                print(f"      {target:<34} {count:>10,} rows")
            adjusted = _pull_back_future_timestamps(db)
            print(f"      future timestamps pulled back:    {adjusted:>10,} rows")

        print(f"\n[3/5] Synthesizing all activity types across {args.days} days...")
        total = enrich_activity(
            db,
            days=args.days,
            events_per_day=args.events_per_day,
            end_at=now,
            verbose=False,
        )
        print(f"      inserted {total:,} enriched events")

        print("\n[4/5] Clearing cached detection/ML results...")
        cleared = _clear_caches()
        print(f"      cleared: {', '.join(cleared) if cleared else 'nothing to clear'}")

        if args.no_recompute:
            print("\n[5/5] Skipping engine recomputation (--no-recompute).")
        else:
            _recompute(db, days=min(args.days, 30), verbose=True)

        print("\n" + "=" * 62)
        print("  ✅ DATASET REFRESH COMPLETE")
        print("=" * 62)

        rows = (
            db.query(ActivityLog.activity_type, func.count(ActivityLog.id))
            .group_by(ActivityLog.activity_type)
            .all()
        )
        for atype, count in sorted(rows, key=lambda r: -r[1]):
            label = atype.value if hasattr(atype, "value") else str(atype)
            print(f"  {label:<18} {count:>12,}")

        newest = db.query(func.max(ActivityLog.occurred_at)).scalar()
        print(f"\n  newest activity now: {newest}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
