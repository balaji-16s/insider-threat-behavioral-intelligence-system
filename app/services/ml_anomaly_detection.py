"""
ML-Powered Anomaly Detection (Isolation Forest)

Trains an unsupervised Isolation Forest model on per-employee behavioral
feature vectors to identify statistically unusual insider behavior that
simple rule-based checks might miss.

This is the AI/ML layer of the platform: it complements the statistical
and rule-based engine in ``anomaly_detection.py`` with a genuine
unsupervised machine-learning model (scikit-learn).

The model is trained once on the ingested dataset (see
``scripts/train_ml_model.py`` or ``POST /api/v1/anomaly/ml/train``) and
persisted to ``data/models/``. Scoring then loads the trained model for
inference instead of re-fitting on every run, which keeps whole-org
detection fast on the large CERT dataset.

Features are extracted from the last ``days`` of activity for every
employee (volume, timing, device, and baseline-deviation signals), then
an Isolation Forest flags the most anomalous employees. Each result
includes an explainable breakdown of the top deviating features.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityType
from app.models.behavioral_baseline import BehavioralBaseline
from app.models.employee import Employee
from app.services.activity_aggregates import (
    EmployeeActivity,
    load_employee_activity,
)

MODEL_NAME = "Isolation Forest"
MODEL_VERSION = "v1"

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RESULTS_CACHE = DATA_DIR / "ml_results.json"
INSIDERS_JSON = DATA_DIR / "cert" / "insiders.json"

# Persisted trained model: produced by scripts/train_ml_model.py (or the
# /anomaly/ml/train endpoint) and loaded for inference at scoring time.
MODEL_DIR = DATA_DIR / "models"
MODEL_PATH = MODEL_DIR / "isolation_forest.joblib"
MODEL_META_PATH = MODEL_DIR / "isolation_forest_meta.json"

# Feature vector columns (order matters — keep in sync with _extract_features)
FEATURES = [
    "total_logs",
    "daily_avg",
    "login_count",
    "data_transfer_count",
    "usb_count",
    "off_hours_pct",
    "late_night_count",
    "weekend_pct",
    "unique_pcs",
    "unique_hours",
    "daily_std",
    "data_transfer_off_hours_pct",
    "avg_data_per_day",
    "baseline_deviation",
]


# ── Public API ──────────────────────────────────────────────────


def run_ml_anomaly_detection(
    db: Session,
    days: int = 30,
    contamination: float = 0.05,
    retrain: bool = False,
) -> dict[str, Any]:
    """
    Run the ML anomaly detection pipeline for all employees.

    Scores with the persisted trained model (see ``scripts/train_ml_model.py``);
    the model is only re-fitted when ``retrain`` is set, none is saved yet,
    or the caller requests a different contamination.

    Returns scored results (0-100 risk), isolation-forest outlier flags,
    per-employee explainability, and a ground-truth validation summary.
    """
    employees = db.query(Employee).all()
    records, no_activity = _build_feature_records(db, employees, days)

    if not records:
        return {
            "model": MODEL_NAME,
            "version": MODEL_VERSION,
            "contamination": contamination,
            "lookback_days": days,
            "scanned_employees": 0,
            "employees_no_activity": no_activity,
            "outliers_detected": 0,
            "average_ml_score": 0.0,
            "top_flagged": [],
            "ground_truth": None,
            "model_trained_at": None,
            "generated_at": datetime.utcnow().isoformat(),
            "message": "No employees to analyze",
        }

    X = np.array(
        [[r["features"][f] for f in FEATURES] for r in records], dtype=float
    )
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    model, meta = None, None
    if not retrain:
        model, meta = load_trained_model()
        if meta is not None and abs(
            meta.get("contamination", -1.0) - contamination
        ) > 1e-6:
            model, meta = None, None  # trained for a different contamination
        elif model is not None and _is_stale_model(model, X, contamination):
            # The persisted model was fitted on a different activity window:
            # re-using it flags almost every employee as an outlier with
            # identical scores, so refit on the current window instead.
            model, meta = None, None
    if model is None:
        model, meta = _fit_and_save_model(
            X, records, days, contamination, no_activity
        )

    predictions = model.predict(X)  # -1 = outlier, 1 = inlier
    raw_scores = model.decision_function(X)
    ml_scores = _normalize_scores(raw_scores)

    items: list[dict[str, Any]] = []
    for rec, pred, score in zip(records, predictions, ml_scores):
        is_outlier = pred == -1
        items.append(
            {
                "employee_id": rec["employee_id"],
                "employee_code": rec["employee_code"],
                "employee_name": rec["employee_name"],
                "department": rec["department"],
                "designation": rec["designation"],
                "ml_score": round(float(score), 1),
                "is_outlier": bool(is_outlier),
                "severity": _severity(float(score), is_outlier),
                "top_factors": _top_deviating_features(
                    rec["features"], X, FEATURES
                ),
                "features": rec["features"],
            }
        )

    items.sort(key=lambda i: i["ml_score"], reverse=True)
    outliers = [i for i in items if i["is_outlier"]]

    result: dict[str, Any] = {
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "contamination": contamination,
        "lookback_days": days,
        "scanned_employees": len(items),
        "employees_no_activity": no_activity,
        "outliers_detected": len(outliers),
        "average_ml_score": round(
            mean(i["ml_score"] for i in items), 1
        ),
        "top_flagged": items[:25],
        "ground_truth": _ground_truth_check(items),
        "model_trained_at": (meta or {}).get("trained_at"),
        "generated_at": datetime.utcnow().isoformat(),
        "message": (
            f"Isolation Forest flagged {len(outliers)}/{len(items)} employees "
            f"as behavioral outliers (contamination={contamination})"
        )
        + (
            f"; {no_activity} employees with no activity in the window were excluded"
            if no_activity
            else ""
        ),
    }

    _cache_result(result)
    return result


def train_and_save_model(
    db: Session,
    days: int = 30,
    contamination: float = 0.05,
    max_users: int | None = None,
) -> dict[str, Any]:
    """
    Train the Isolation Forest on the current dataset and persist it.

    Offline-training entry point used by ``scripts/train_ml_model.py`` and
    the ``POST /api/v1/anomaly/ml/train`` endpoint. After this runs,
    ``run_ml_anomaly_detection`` scores with the saved model instead of
    re-fitting on every call.
    """
    employees = db.query(Employee).all()
    if max_users:
        employees = employees[:max_users]

    records, no_activity = _build_feature_records(db, employees, days)
    if not records:
        return {
            "trained": False,
            "reason": "No employees with activity in the lookback window",
            "samples": 0,
            "no_activity": no_activity,
        }

    X = np.array(
        [[r["features"][f] for f in FEATURES] for r in records], dtype=float
    )
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    model, meta = _fit_and_save_model(
        X, records, days, contamination, no_activity
    )

    return {
        "trained": True,
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "contamination": contamination,
        "lookback_days": days,
        "samples": len(records),
        "no_activity": no_activity,
        "trained_at": meta["trained_at"],
        "model_path": str(MODEL_PATH),
    }


def _build_feature_records(
    db: Session,
    employees: list[Employee],
    days: int,
) -> tuple[list[dict[str, Any]], int]:
    """
    Load activity for all employees (chunked ``IN(...)`` queries, memory
    bounded) and extract feature vectors.

    Returns ``(records, no_activity)`` where each record carries the
    employee metadata plus their feature vector.
    """
    baselines = {
        b.employee_id: b.baseline_data or {}
        for b in db.query(BehavioralBaseline).all()
    }
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Aggregate in SQL instead of materialising every activity row: the
    # features are all counts, and a 30-day CERT window is ~1.2M rows as
    # ORM objects versus ~70K aggregate rows here.
    activity = load_employee_activity(
        db, [e.id for e in employees], cutoff, sections={"daily", "pcs"}
    )

    records: list[dict[str, Any]] = []
    no_activity = 0
    for emp in employees:
        acts = activity.get(str(emp.id))
        feats = (
            _extract_features(acts, days, baselines.get(emp.id, {}))
            if acts is not None
            else None
        )
        if feats is None:
            # No behavioral data in the window — nothing to judge, so
            # exclude from model scoring to avoid all-zero false positives.
            no_activity += 1
            continue
        records.append(
            {
                "employee_id": str(emp.id),
                "employee_code": emp.employee_code,
                "employee_name": emp.full_name,
                "department": emp.department,
                "designation": emp.designation,
                "features": feats,
            }
        )
    return records, no_activity


def _fit_and_save_model(
    X: np.ndarray,
    records: list[dict[str, Any]],
    days: int,
    contamination: float,
    no_activity: int,
) -> tuple[Any, dict[str, Any]]:
    """Fit a fresh Isolation Forest on ``X`` and persist it to disk."""
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)
    meta = _save_model(model, {
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "contamination": contamination,
        "lookback_days": days,
        "trained_at": datetime.utcnow().isoformat(),
        "feature_names": FEATURES,
        "samples": len(records),
        "employees_no_activity": no_activity,
    })
    return model, meta


def load_trained_model() -> tuple[Any, dict[str, Any] | None]:
    """Load the persisted trained model + metadata, or ``(None, None)``."""
    if not MODEL_PATH.exists() or not MODEL_META_PATH.exists():
        return None, None
    try:
        model = joblib.load(MODEL_PATH)
        meta = json.loads(MODEL_META_PATH.read_text())
        return model, meta
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None


def _is_stale_model(
    model: Any, X: np.ndarray, contamination: float
) -> bool:
    """Detect a persisted model that no longer matches the current window.

    An Isolation Forest fitted on a different activity window (or a
    different scale of features) will flag a large majority of employees
    as outliers, producing a useless "everyone is critical" result. When
    the flagged share far exceeds the requested contamination rate, the
    model is treated as stale and refitted.
    """
    if len(X) == 0:
        return False
    flagged = int((model.predict(X) == -1).sum())
    # Allow generous slack (3x contamination, at least 25%) so a genuine
    # distribution shift does not cause an unnecessary refit.
    max_expected_ratio = max(contamination * 3, 0.25)
    return (flagged / len(X)) > max_expected_ratio


def _save_model(
    model: Any, meta: dict[str, Any]
) -> dict[str, Any]:
    """Persist a fitted model + metadata to ``data/models`` (best-effort)."""
    try:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        MODEL_META_PATH.write_text(json.dumps(meta, indent=2))
    except OSError:
        pass  # persistence is best-effort; scoring still works in-memory
    return meta


def get_cached_ml_results() -> dict[str, Any] | None:
    """Return the most recent ML detection run (None if never run)."""
    if not RESULTS_CACHE.exists():
        return None
    try:
        return json.loads(RESULTS_CACHE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


# ── Feature engineering ─────────────────────────────────────────


def _extract_features(
    activity: EmployeeActivity | None,
    days: int,
    baseline: dict[str, Any],
) -> dict[str, float] | None:
    """Build a behavioral feature vector for one employee over the window.

    ``activity`` must already be scoped to the employee and the lookback
    window (callers aggregate it in SQL once and share it).
    """
    if activity is None or not activity.total_logs:
        return None

    n = activity.total_logs
    xfer_total = activity.count_of(ActivityType.DATA_TRANSFER)

    # Deviation from the stored behavioral baseline (if available)
    baseline_deviation = 0.0
    b_daily_avg = baseline.get("daily_avg") or 0
    if b_daily_avg and n:
        recent_avg = n / max(days, 1)
        baseline_deviation = abs(recent_avg - b_daily_avg) / max(b_daily_avg, 0.1)

    counts = list(activity.daily_counts.values())
    return {
        "total_logs": float(n),
        "daily_avg": round(n / max(days, 1), 3),
        "login_count": float(activity.count_of(ActivityType.LOGIN)),
        "data_transfer_count": float(xfer_total),
        "usb_count": float(activity.count_of(ActivityType.USB_DEVICE)),
        "off_hours_pct": round(activity.off_hours / n * 100, 3),
        "late_night_count": float(activity.late_night),
        "weekend_pct": round(activity.weekend_events / n * 100, 3),
        "unique_pcs": float(activity.unique_pcs),
        "unique_hours": float(activity.unique_hours),
        "daily_std": round(stdev(counts), 3) if len(counts) > 1 else 0.0,
        "data_transfer_off_hours_pct": round(
            activity.off_hours_of(ActivityType.DATA_TRANSFER)
            / max(xfer_total, 1)
            * 100,
            3,
        ),
        "avg_data_per_day": round(xfer_total / max(days, 1), 3),
        "baseline_deviation": round(baseline_deviation, 3),
    }


# ── Scoring & explainability ────────────────────────────────────


def _normalize_scores(raw: np.ndarray) -> np.ndarray:
    """Map Isolation Forest decision scores onto a 0-100 risk scale.

    Lower decision values = more anomalous, so 0 = most anomalous.
    """
    max_d = float(raw.max())
    min_d = float(raw.min())
    if max_d > min_d:
        norm = (raw - min_d) / (max_d - min_d)
        return 100.0 * (1.0 - norm)
    return np.full_like(raw, 50.0, dtype=float)


def _severity(score: float, is_outlier: bool) -> str:
    if not is_outlier:
        return "low"
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    return "medium"


def _top_deviating_features(
    features: dict[str, float], X: np.ndarray, feature_names: list[str]
) -> list[dict[str, Any]]:
    """Explain why an employee is unusual — top 3 features vs. org median."""
    medians = np.median(X, axis=0)
    # Median absolute deviation (robust spread)
    mads = np.median(np.abs(X - medians), axis=0)
    mads = np.where(mads < 1e-9, 1.0, mads)

    current = np.array([features[f] for f in feature_names], dtype=float)
    deviations = np.abs(current - medians) / mads

    ranked = sorted(
        zip(feature_names, current, medians, deviations),
        key=lambda t: t[3],
        reverse=True,
    )
    top = []
    for name, value, med, dev in ranked[:3]:
        if dev >= 2.0:  # only report features that truly stand out
            top.append(
                {
                    "feature": name,
                    "value": round(float(value), 2),
                    "median": round(float(med), 2),
                    "deviation": round(float(dev), 1),
                }
            )
    return top


# ── Ground-truth validation ─────────────────────────────────────


def _ground_truth_check(
    items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Compare flagged employees against known insider labels.

    Labels come from data/cert/insiders.json (ground-truth user IDs).
    Only counts insiders actually present in the ingested dataset.
    """
    if not INSIDERS_JSON.exists():
        return None
    try:
        data = json.loads(INSIDERS_JSON.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    known_insiders = {
        i["user_id"] for i in data.get("insiders", []) if i.get("user_id")
    }
    if not known_insiders:
        return None

    by_code = {i["employee_code"]: i for i in items if i.get("employee_code")}
    present = [uid for uid in known_insiders if uid in by_code]
    if not present:
        return {
            "total_insiders": len(known_insiders),
            "insiders_in_dataset": 0,
            "found_in_outliers": 0,
            "found_in_top20": 0,
            "hit_rate_top20": None,
            "note": "No ground-truth insider IDs matched the ingested employees",
        }

    outliers = {i["employee_code"] for i in items if i["is_outlier"]}
    top20 = {i["employee_code"] for i in items[:20]}
    found_out = [uid for uid in present if uid in outliers]
    found_top = [uid for uid in present if uid in top20]

    return {
        "total_insiders": len(known_insiders),
        "insiders_in_dataset": len(present),
        "found_in_outliers": len(found_out),
        "found_in_top20": len(found_top),
        "hit_rate_top20": round(len(found_top) / len(present), 2),
        "detected_insiders": found_top,
    }


# ── Result cache ────────────────────────────────────────────────


def _cache_result(result: dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_CACHE.write_text(json.dumps(result, indent=2))
    except OSError:
        pass  # cache is best-effort
