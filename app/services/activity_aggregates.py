"""
Shared Activity Aggregation Layer

Computes compact per-employee activity aggregates in Postgres so the
analytics engines never materialise raw activity rows.

Why this exists
---------------
Every engine (anomaly detection, the five threat models, ML feature
extraction, behavioral baselines) only ever needs *counts* of activity —
how many events per type, per hour, per day. The previous approach loaded
every row into Python as an ORM object, which on the full CERT dataset
means ~1.2M rows per 30-day window (≈10s just to fetch, plus several
seconds of per-row Python work) and each engine paid that cost
independently.

``load_employee_activity`` collapses that into a handful of grouped SQL
queries returning ~70K small rows, giving every engine the same
pre-aggregated view of behavior.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Sequence

from sqlalchemy import Date, Float, Integer, case, cast, func, or_
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog, ActivityType

# Size thresholds (KB) for the "large download" rules and threat models.
LARGE_DOWNLOAD_KB = 10_000
HUGE_DOWNLOAD_KB = 50_000

# Guards against non-numeric size_kb values in arbitrary ingested data.
_NUMERIC_RE = r"^-?[0-9]+(\.[0-9]+)?$"

# Optional aggregation groups. The per-type/hour counts always run (they
# provide ``total_logs`` and every timing signal); the rest are opt-in so an
# engine only pays for the queries it actually consumes.
ALL_SECTIONS = frozenset(
    {
        "daily",
        "pcs",
        "downloads",
        "destinations",
        "devices",
        "off_hours_dates",
    }
)


def _chunks(items: Sequence[Any], size: int) -> list[list[Any]]:
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


@dataclass
class EmployeeActivity:
    """Per-employee activity counts over one lookback window."""

    employee_id: str
    total_logs: int = 0
    # type value -> count, e.g. {"data_transfer": 1234}
    type_counts: Counter[str] = field(default_factory=Counter)
    # hour -> count (all activity types)
    hourly_counts: Counter[int] = field(default_factory=Counter)
    # (type value, hour) -> count
    type_hour_counts: Counter[tuple[str, int]] = field(default_factory=Counter)
    # calendar day -> count
    daily_counts: Counter[date] = field(default_factory=Counter)
    unique_pcs: int = 0
    # file downloads above LARGE_DOWNLOAD_KB: count + total KB
    large_download_count: int = 0
    large_download_kb: float = 0.0
    # file downloads above HUGE_DOWNLOAD_KB: count + total KB
    huge_download_count: int = 0
    huge_download_kb: float = 0.0
    # data transfer destination -> count (e.g. {"external": 4, "usb": 2})
    transfer_destinations: Counter[str] = field(default_factory=Counter)
    usb_devices: list[str] = field(default_factory=list)
    # up to 5 off-hours data-transfer timestamps (for alert evidence)
    off_hours_transfer_dates: list[datetime] = field(default_factory=list)

    # ── Derived signals ─────────────────────────────────────────

    @property
    def off_hours(self) -> int:
        """Events outside 07:00-19:59."""
        return sum(n for h, n in self.hourly_counts.items() if h < 7 or h > 19)

    @property
    def late_night(self) -> int:
        """Events between midnight and 04:59."""
        return sum(n for h, n in self.hourly_counts.items() if h < 5)

    @property
    def weekend_events(self) -> int:
        return sum(n for d, n in self.daily_counts.items() if d.weekday() >= 5)

    @property
    def weekend_days(self) -> int:
        return sum(1 for d in self.daily_counts if d.weekday() >= 5)

    @property
    def unique_hours(self) -> int:
        return len(self.hourly_counts)

    def count_of(self, atype: ActivityType) -> int:
        return self.type_counts.get(atype.value, 0)

    def off_hours_of(self, atype: ActivityType) -> int:
        key = atype.value
        return sum(
            n
            for (atype_key, hour), n in self.type_hour_counts.items()
            if atype_key == key and (hour < 7 or hour > 19)
        )


def load_employee_activity(
    db: Session,
    employee_ids: Iterable[Any],
    cutoff: datetime,
    chunk_size: int = 1000,
    sections: Iterable[str] | None = None,
) -> dict[str, EmployeeActivity]:
    """Return ``{employee_id: EmployeeActivity}`` for the window ``>= cutoff``.

    Only employees with at least one event in the window are returned.
    ``sections`` restricts which optional aggregates are computed (see
    ``ALL_SECTIONS``); pass ``None`` for everything.
    """
    wanted = ALL_SECTIONS if sections is None else frozenset(sections)
    ids = [str(e) for e in employee_ids]
    result: dict[str, EmployeeActivity] = {}

    for chunk in _chunks(ids, chunk_size):
        _accumulate_chunk(db, chunk, cutoff, result, wanted)

    # Alert evidence wants a few concrete off-hours transfer timestamps.
    # Only employees whose rule actually fires (>= 3 such transfers) need
    # them, so this query is restricted to that subset.
    if "off_hours_dates" in wanted:
        qualifying = [
            emp_id
            for emp_id, act in result.items()
            if act.off_hours_of(ActivityType.DATA_TRANSFER) >= 3
        ]
        for chunk in _chunks(qualifying, chunk_size):
            _load_off_hours_transfer_dates(db, chunk, cutoff, result)

    return result


def _accumulate_chunk(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
    sections: frozenset[str] = ALL_SECTIONS,
) -> None:
    """Run the grouped aggregation queries for one chunk of employees.

    The volume/type/hour counts always run; the remaining aggregate groups
    are opt-in via ``sections`` so an engine never pays for columns it does
    not consume.
    """
    _agg_volume(db, employee_ids, cutoff, result)
    if "daily" in sections:
        _agg_daily(db, employee_ids, cutoff, result)
    if "pcs" in sections:
        _agg_pcs(db, employee_ids, cutoff, result)
    if "downloads" in sections:
        _agg_downloads(db, employee_ids, cutoff, result)
    if "destinations" in sections:
        _agg_destinations(db, employee_ids, cutoff, result)
    if "devices" in sections:
        _agg_devices(db, employee_ids, cutoff, result)


def _agg_volume(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
) -> None:
    """Activity type + hour distribution (also provides the total volume)."""
    hour_col = cast(func.date_part("hour", ActivityLog.occurred_at), Integer)
    for emp_id, atype, hour, count in (
        db.query(
            ActivityLog.employee_id,
            ActivityLog.activity_type,
            hour_col,
            func.count(ActivityLog.id),
        )
        .filter(
            ActivityLog.employee_id.in_(employee_ids),
            ActivityLog.occurred_at >= cutoff,
        )
        .group_by(ActivityLog.employee_id, ActivityLog.activity_type, hour_col)
        .all()
    ):
        act = _entry(result, emp_id)
        key = _type_key(atype)
        count = int(count)
        hour = int(hour)
        act.total_logs += count
        act.type_counts[key] += count
        act.hourly_counts[hour] += count
        act.type_hour_counts[(key, hour)] += count


def _agg_daily(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
) -> None:
    """Daily activity counts (volume anomalies, bursts, weekend signals)."""
    day_col = cast(ActivityLog.occurred_at, Date)
    for emp_id, day, count in (
        db.query(
            ActivityLog.employee_id,
            day_col,
            func.count(ActivityLog.id),
        )
        .filter(
            ActivityLog.employee_id.in_(employee_ids),
            ActivityLog.occurred_at >= cutoff,
        )
        .group_by(ActivityLog.employee_id, day_col)
        .all()
    ):
        _entry(result, emp_id).daily_counts[day] += int(count)


def _agg_pcs(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
) -> None:
    """Distinct workstations used."""
    pc_col = ActivityLog.details.op("->>")("pc")
    for emp_id, distinct_pcs in (
        db.query(
            ActivityLog.employee_id,
            func.count(func.distinct(pc_col)),
        )
        .filter(
            ActivityLog.employee_id.in_(employee_ids),
            ActivityLog.occurred_at >= cutoff,
            pc_col.isnot(None),
            pc_col != "",
        )
        .group_by(ActivityLog.employee_id)
        .all()
    ):
        _entry(result, emp_id).unique_pcs = int(distinct_pcs or 0)


def _agg_downloads(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
) -> None:
    """Download sizes split at the two rule thresholds (10 MB / 50 MB)."""
    size_text = ActivityLog.details.op("->>")("size_kb")
    size_kb = case(
        (size_text.op("~")(_NUMERIC_RE), cast(size_text, Float)),
        else_=0.0,
    )
    for emp_id, large_n, large_kb, huge_n, huge_kb in (
        db.query(
            ActivityLog.employee_id,
            func.count().filter(size_kb > LARGE_DOWNLOAD_KB),
            func.coalesce(
                func.sum(size_kb).filter(size_kb > LARGE_DOWNLOAD_KB), 0.0
            ),
            func.count().filter(size_kb > HUGE_DOWNLOAD_KB),
            func.coalesce(
                func.sum(size_kb).filter(size_kb > HUGE_DOWNLOAD_KB), 0.0
            ),
        )
        .filter(
            ActivityLog.employee_id.in_(employee_ids),
            ActivityLog.occurred_at >= cutoff,
            ActivityLog.activity_type == ActivityType.FILE_DOWNLOAD,
        )
        .group_by(ActivityLog.employee_id)
        .all()
    ):
        act = _entry(result, emp_id)
        act.large_download_count = int(large_n or 0)
        act.large_download_kb = float(large_kb or 0.0)
        act.huge_download_count = int(huge_n or 0)
        act.huge_download_kb = float(huge_kb or 0.0)


def _agg_destinations(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
) -> None:
    """Data-transfer destinations (external / removable media)."""
    dest_col = ActivityLog.details.op("->>")("destination")
    for emp_id, destination, count in (
        db.query(
            ActivityLog.employee_id,
            dest_col,
            func.count(ActivityLog.id),
        )
        .filter(
            ActivityLog.employee_id.in_(employee_ids),
            ActivityLog.occurred_at >= cutoff,
            ActivityLog.activity_type == ActivityType.DATA_TRANSFER,
            dest_col.isnot(None),
        )
        .group_by(ActivityLog.employee_id, dest_col)
        .all()
    ):
        _entry(result, emp_id).transfer_destinations[str(destination)] += int(
            count
        )


def _agg_devices(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
) -> None:
    """USB device identifiers (used as alert evidence)."""
    device_col = func.coalesce(
        ActivityLog.details.op("->>")("device"), "unknown"
    )
    for emp_id, devices in (
        db.query(
            ActivityLog.employee_id,
            func.array_agg(func.distinct(device_col)),
        )
        .filter(
            ActivityLog.employee_id.in_(employee_ids),
            ActivityLog.occurred_at >= cutoff,
            ActivityLog.activity_type == ActivityType.USB_DEVICE,
        )
        .group_by(ActivityLog.employee_id)
        .all()
    ):
        act = _entry(result, emp_id)
        act.usb_devices = [str(d) for d in (devices or []) if d is not None]


def _load_off_hours_transfer_dates(
    db: Session,
    employee_ids: list[str],
    cutoff: datetime,
    result: dict[str, EmployeeActivity],
) -> None:
    """Attach up to 5 off-hours transfer timestamps per employee for evidence."""
    hour_expr = func.date_part("hour", ActivityLog.occurred_at)
    for emp_id, dates in (
        db.query(
            ActivityLog.employee_id,
            func.array_agg(ActivityLog.occurred_at),
        )
        .filter(
            ActivityLog.employee_id.in_(employee_ids),
            ActivityLog.occurred_at >= cutoff,
            ActivityLog.activity_type == ActivityType.DATA_TRANSFER,
            or_(hour_expr < 7, hour_expr > 19),
        )
        .group_by(ActivityLog.employee_id)
        .all()
    ):
        act = _entry(result, emp_id)
        # Earliest five, so the evidence shown in the UI is deterministic.
        act.off_hours_transfer_dates = sorted(dates or [])[:5]


def _entry(
    result: dict[str, EmployeeActivity], emp_id: Any
) -> EmployeeActivity:
    key = str(emp_id)
    act = result.get(key)
    if act is None:
        act = EmployeeActivity(employee_id=key)
        result[key] = act
    return act


def _type_key(atype: Any) -> str:
    """Normalise an activity type to the lowercase value used by the engines."""
    return atype.value if hasattr(atype, "value") else str(atype)
