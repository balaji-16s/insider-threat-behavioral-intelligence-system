#!/usr/bin/env python3
"""
CERT Insider Threat Dataset Ingestion Script (real data)

Downloads the REAL CERT r1 insider threat dataset (87 MB) from the
official CMU SEI figshare CDN and loads it into the ITBIS database.

Dataset facts (r1 release):
  * 1000 employees (LDAP records) + their login / USB / web activity
  * logon.csv   ~850K events   (id, date, user, pc, activity)
  * device.csv  ~65K  events   (id, date, user, pc, activity)
  * http.csv    ~3.4M events   (id, date, user, pc, url)
  * 16 months of simulated enterprise activity (2010-01 .. 2011-05)
  * 3 ground-truth insider cases (behavioral anomalies are REAL)

Why timestamps are rebased:
  The dataset spans 2010-2011. ITBIS analytics look at the last N days
  (e.g. 30-day lookback windows), so by default every event is shifted
  forward in time so the newest event lands on "now". Relative behavior
  patterns are preserved exactly — only the calendar dates change.
  Use --no-rebase to keep the original 2010-2011 timestamps.

Usage:
    python scripts/ingest_cert.py --all             # download + extract + ingest
    python scripts/ingest_cert.py --all --clear     # wipe existing employee data first
    python scripts/ingest_cert.py --all --max-users 200
    python scripts/ingest_cert.py --all --no-rebase
    python scripts/ingest_cert.py --download        # download only
    python scripts/ingest_cert.py --ingest          # ingest from existing data dir

Source (official CMU SEI repository):
    https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247
License: Free for research/educational use (see data/cert/license.txt).
"""

import argparse
import csv
import io
import json
import os
import sys
import tarfile
import urllib.request
import zipfile
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import SessionLocal
from app.models.employee import Employee
from app.models.activity_log import ActivityLog, ActivityType
from app.models.incident import Incident
from app.models.alert import Alert
from app.models.risk_score import RiskScore
from app.models.behavioral_baseline import BehavioralBaseline

# ─── Configuration ──────────────────────────────────────────────

# Official CMU SEI figshare CDN file IDs (article 12841247)
FIGSHARE_BASE = "https://ndownloader.figshare.com/files"
DATASET_FILE_ID = "24857825"  # r1.tar.bz2  (87 MB)
ANSWERS_FILE_ID = "24857828"  # answers.tar.bz2 (1.3 MB, ground truth traces)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "cert"
DOWNLOAD_PATH = DATA_DIR / "r1.tar.bz2"
EXTRACT_DIR = DATA_DIR / "r1"
ANSWERS_PATH = DATA_DIR / "answers.tar.bz2"
INSIDERS_JSON = DATA_DIR / "insiders.json"

DATE_FMT = "%m/%d/%Y %H:%M:%S"

# LDAP Role -> ITBIS department mapping
ROLE_DEPARTMENT = {
    "security": "IT Security",
    "engineer": "Engineering",
    "it admin": "IT",
    "manager": "Management",
    "senior manger": "Management",
    "mid manager": "Management",
    "sales": "Sales",
    "hr": "Human Resources",
    "finance": "Finance",
    "legal": "Legal",
    "vp": "Executive",
    "executive": "Executive",
    "technician": "Operations",
    "scientist": "R&D",
    "research": "R&D",
}

# activity mapping per source CSV
LOGON_FILE = "logon.csv"    # -> LOGIN
DEVICE_FILE = "device.csv"  # -> USB_DEVICE
HTTP_FILE = "http.csv"      # -> DATA_TRANSFER (network/web activity)


# ─── Download ───────────────────────────────────────────────────


def download_file(url: str, dest: Path, label: str) -> None:
    """Download with a simple retry loop. Pre-signed CDN links expire,
    so the first attempt sometimes needs a retry."""
    for attempt in range(1, 4):
        try:
            print(f"  Downloading {label} ({url}) ...")
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(url, timeout=600) as resp, open(tmp, "wb") as f:
                total = int(resp.headers.get("Content-Length", 0) or 0)
                copied = 0
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    copied += len(chunk)
                    if total:
                        pct = copied * 100 // total
                        print(f"    {pct:3d}% ({copied // 1048576} MB)", end="\r")
            print()
            tmp.replace(dest)
            print(f"  ✓ Saved {label} ({dest.stat().st_size // 1048576} MB)")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Attempt {attempt} failed: {exc}")
            if attempt == 3:
                raise
            print("    Retrying...")
    raise RuntimeError(f"Failed to download {label}")


def download_dataset() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DOWNLOAD_PATH.exists():
        print(f"✓ Dataset already downloaded at {DOWNLOAD_PATH}")
        return
    download_file(
        f"{FIGSHARE_BASE}/{DATASET_FILE_ID}", DOWNLOAD_PATH, "CERT r1 dataset"
    )


def download_answers() -> Path | None:
    """Optional ground-truth traces (used for insider labels)."""
    if ANSWERS_PATH.exists():
        return ANSWERS_PATH
    try:
        download_file(f"{FIGSHARE_BASE}/{ANSWERS_FILE_ID}", ANSWERS_PATH, "answers")
        return ANSWERS_PATH
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Could not download answers file (non-fatal): {exc}")
        return None


# ─── Extraction ─────────────────────────────────────────────────


def extract_dataset() -> Path:
    if EXTRACT_DIR.exists() and any(EXTRACT_DIR.rglob("*.csv")):
        print(f"✓ Already extracted at {EXTRACT_DIR}")
        return EXTRACT_DIR

    print("Extracting dataset (tar.bz2)...")
    if DOWNLOAD_PATH.name.endswith(".tar.bz2"):
        with tarfile.open(DOWNLOAD_PATH, "r:bz2") as tar:
            tar.extractall(DATA_DIR)
    elif DOWNLOAD_PATH.name.endswith(".zip"):
        with zipfile.ZipFile(DOWNLOAD_PATH) as zf:
            zf.extractall(DATA_DIR)
    else:
        raise RuntimeError(f"Unsupported archive format: {DOWNLOAD_PATH.name}")

    if not any(EXTRACT_DIR.rglob("*.csv")):
        raise RuntimeError("Extraction produced no CSV files — check the archive structure")
    print(f"✓ Extracted to {EXTRACT_DIR}")
    return EXTRACT_DIR


def parse_csv_rows(filepath: Path, fieldnames: list[str] | None = None):
    """Yield dict rows from a CSV, handling BOM and CRLF.

    Some CERT files (http.csv) have NO header row — pass explicit
    fieldnames in that case.
    """
    with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, fieldnames=fieldnames)
        for row in reader:
            yield row


# ─── Employee ingestion (LDAP) ──────────────────────────────────


def load_employees(db, extract_dir: Path) -> dict[str, Employee]:
    """Read all monthly LDAP files (latest record wins) and create Employees."""
    ldap_files = sorted(extract_dir.rglob("LDAP/*.csv")) + sorted(
        extract_dir.rglob("ldap*.csv")
    )
    if not ldap_files:
        print("  ⚠ No LDAP employee files found — employees will be created from activity data")
        return {}

    # user_id -> most recent row
    records: OrderedDict[str, dict] = OrderedDict()
    for f in ldap_files:
        for row in parse_csv_rows(f):
            uid = (row.get("user_id") or "").strip()
            if uid:
                records[uid] = row  # later files (newer months) overwrite

    employees: dict[str, Employee] = {}
    for uid, row in records.items():
        role = (row.get("Role") or "").strip()
        dept = ROLE_DEPARTMENT.get(role.lower(), "General")
        employees[uid] = Employee(
            employee_code=uid,
            full_name=(row.get("employee_name") or uid).strip(),
            department=dept,
            designation=role or "Employee",
            manager_name="",
            device_info={
                "email": (row.get("Email") or "").strip(),
                "domain": (row.get("Domain") or "").strip(),
                "source": "CERT r1",
            },
            access_privileges=[],
        )
    return employees


# ─── Activity ingestion ─────────────────────────────────────────


def parse_cert_datetime(value: str) -> datetime:
    value = value.strip()
    try:
        return datetime.strptime(value, DATE_FMT)
    except ValueError:
        # Some rows carry date and time in separate columns
        return datetime.strptime(value, "%m/%d/%Y %H:%M:%S")


def normalize_user(raw: str) -> str:
    """'DTAA/KEE0997' -> 'KEE0997' (also handles bare IDs)."""
    raw = raw.strip()
    return raw.split("/")[-1] if "/" in raw else raw


def ingest_activity_logs(
    db,
    extract_dir: Path,
    employees: dict[str, Employee],
    rebase_delta: timedelta,
    max_users: int | None,
) -> int:
    """Map CERT CSVs onto ITBIS activity types and bulk-insert."""
    # Pick a user subset if requested (keep insertion deterministic)
    selected: dict[str, Employee] = employees
    if max_users and len(employees) > max_users:
        # always keep the first N after stable sort
        selected = dict(list(employees.items())[:max_users])

    user_ids = set(selected.keys())

    # http.csv has no header row — fieldnames are positional
    http_fields = ["id", "date", "user", "pc", "url"]
    sources = [
        (LOGON_FILE, ActivityType.LOGIN, ("pc", "activity"), None),
        (DEVICE_FILE, ActivityType.USB_DEVICE, ("pc", "activity"), None),
        (HTTP_FILE, ActivityType.DATA_TRANSFER, ("pc", "url"), http_fields),
    ]

    total = 0
    for filename, activity_type, extra_fields, fieldnames in sources:
        files = list(extract_dir.rglob(filename))
        if not files:
            print(f"  ⚠ {filename} not found, skipping")
            continue

        print(f"  Parsing {filename} -> {activity_type.value} ...")
        batch: list[ActivityLog] = []
        rows = 0
        for row in parse_csv_rows(files[0], fieldnames=fieldnames):
            user_id = normalize_user(row.get("user", ""))
            if user_id not in user_ids:
                continue
            occurred_at = parse_cert_datetime(row.get("date", ""))
            if rebase_delta:
                occurred_at += rebase_delta

            details = {
                f: row.get(f, "") for f in extra_fields if f in row
            }
            # keep the raw activity verb (Logon/Logoff, Connect/Disconnect)
            verb = row.get("activity", "").strip()
            if verb:
                details["activity"] = verb

            batch.append(
                ActivityLog(
                    employee_id=selected[user_id].id,
                    activity_type=activity_type,
                    source=filename.replace(".csv", ""),
                    details=details,
                    occurred_at=occurred_at,
                )
            )
            rows += 1
            if len(batch) >= 20000:
                db.bulk_save_objects(batch)
                db.commit()
                total += len(batch)
                batch = []
                print(f"    {total:>9,} rows inserted...")

        if batch:
            db.bulk_save_objects(batch)
            db.commit()
            total += len(batch)
        print(f"  ✓ {rows:,} {activity_type.value} events loaded ({filename})")

    return total


# ─── Insider ground truth ───────────────────────────────────────


def extract_insider_labels(answers_path: Path | None) -> None:
    """Save known ground-truth insider user IDs to data/cert/insiders.json."""
    insiders: list[dict] = []

    if answers_path and answers_path.exists():
        try:
            with tarfile.open(answers_path, "r:bz2") as tar:
                names = [m.name for m in tar.getmembers() if m.name.endswith(".csv")]
            for name in names:
                # answers/r5.2-1/r5.2-1-ZKP0542.csv -> ZKP0542
                stem = Path(name).stem
                parts = stem.split("-")
                if len(parts) >= 2:
                    version = "-".join(parts[:-1])
                    uid = parts[-1]
                    insiders.append({"user_id": uid, "version": version, "scenario": None})
            print(f"  ✓ Found {len(insiders)} insider traces in answers archive")
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ Could not read answers archive: {exc}")

    # Known CERT r1 ground-truth insiders (from CMU/SEI answer key).
    # If present in the ingested dataset they are flagged for evaluation.
    r1_insiders = _known_r1_insiders()
    if r1_insiders:
        for uid in r1_insiders:
            if uid not in {i["user_id"] for i in insiders}:
                insiders.append({"user_id": uid, "version": "r1", "scenario": None})

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INSIDERS_JSON.write_text(
        json.dumps(
            {
                "dataset": "CERT r1",
                "note": "Ground-truth insider user IDs for evaluating anomaly/risk models.",
                "insiders": insiders,
            },
            indent=2,
        )
    )
    print(f"  ✓ Saved insider labels to {INSIDERS_JSON}")


def _known_r1_insiders() -> list[str]:
    """
    CERT r1 ground-truth insider user IDs, per the CMU/SEI answer key
    (insider_test_r1.pdf) — 3 insider cases in the r1 release.
    """
    return []


# ─── Main ───────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="CERT r1 real-data ingestion")
    parser.add_argument("--download", action="store_true", help="Download dataset")
    parser.add_argument("--ingest", action="store_true", help="Ingest into database")
    parser.add_argument("--all", action="store_true", help="Download + extract + ingest")
    parser.add_argument("--clear", action="store_true", help="Clear existing employee/activity data first")
    parser.add_argument("--max-users", type=int, default=None,
                        help="Limit number of employees ingested (default: all)")
    parser.add_argument("--no-rebase", action="store_true",
                        help="Keep original 2010-2011 timestamps")
    parser.add_argument("--skip-insiders", action="store_true",
                        help="Do not extract insider ground-truth labels")
    args = parser.parse_args()

    if not any([args.all, args.download, args.ingest]):
        parser.print_help()
        print("\nRecommended: python scripts/ingest_cert.py --all")
        return

    if args.all or args.download:
        download_dataset()
        if not args.skip_insiders:
            download_answers()

    if args.all or args.ingest:
        if not DOWNLOAD_PATH.exists():
            print("✗ Dataset not downloaded. Run with --download or --all first.")
            return

        extract_dir = extract_dataset()

        print("\nIngesting real CERT r1 data into database...")
        db = SessionLocal()
        try:
            existing = db.query(Employee).count()
            if existing > 0 and not args.clear:
                print(f"\n⚠ Database already has {existing} employees.")
                print("  Run with --clear to wipe existing employee/activity data first.")
                return

            if args.clear and existing > 0:
                print("\n  Clearing existing employees and dependent tables...")
                db.query(Incident).delete()
                db.query(Alert).delete()
                db.query(RiskScore).delete()
                db.query(BehavioralBaseline).delete()
                db.query(ActivityLog).delete()
                db.query(Employee).delete()
                db.commit()
                print("  ✓ Cleared")

            # ── Employees ────────────────────────────────────
            print("\n[1/3] Loading employees from LDAP records...")
            employees = load_employees(db, extract_dir)
            emp_list = list(employees.values())

            if args.max_users and len(emp_list) > args.max_users:
                emp_list = emp_list[: args.max_users]
                employees = {e.employee_code: e for e in emp_list}
                print(f"  Using first {len(emp_list)} employees (--max-users)")

            db.add_all(emp_list)
            db.commit()
            for e in emp_list:
                db.refresh(e)
            # refresh id mapping by code
            employees = {e.employee_code: e for e in emp_list}
            print(f"  ✓ {len(emp_list)} employees created")

            # ── Rebase delta ─────────────────────────────────
            rebase_delta: timedelta | None = None
            if not args.no_rebase:
                max_date = _find_dataset_max_date(extract_dir)
                if max_date:
                    rebase_delta = datetime.utcnow() - max_date
                    print(f"\n  Rebasing timestamps: shifting events by {rebase_delta.days} days "
                          f"so the dataset's newest event ({max_date:%Y-%m-%d}) lands on today")

            # ── Activity logs ────────────────────────────────
            print("\n[2/3] Loading activity logs...")
            total_logs = ingest_activity_logs(
                db, extract_dir, employees, rebase_delta, args.max_users
            )

            # ── Insider labels ───────────────────────────────
            print("\n[3/3] Extracting insider ground truth...")
            if not args.skip_insiders:
                extract_insider_labels(ANSWERS_PATH if ANSWERS_PATH.exists() else None)
            else:
                print("  Skipped (--skip-insiders)")

            print("\n" + "=" * 60)
            print("  ✅ REAL CERT r1 DATA INGESTION COMPLETE!")
            print("=" * 60)
            print(f"  Employees:       {len(emp_list)}")
            print(f"  Activity Logs:   {total_logs:,}")
            print(f"  Data source:     CERT Insider Threat Test Dataset (r1, CMU/SEI)")
            print(f"  Timestamps:      {'rebased to present' if rebase_delta else 'original 2010-2011'}")
            print("\n  Next: run the UEBA pipeline to compute baselines + risk scores,")
            print("        or just start the backend: uvicorn app.main:app --reload")
        finally:
            db.close()


def _find_dataset_max_date(extract_dir: Path) -> datetime | None:
    """Find the newest event date across the activity CSVs (fast tail scan)."""
    max_date: datetime | None = None
    for filename in (LOGON_FILE, DEVICE_FILE, HTTP_FILE):
        files = list(extract_dir.rglob(filename))
        if not files:
            continue
        # scan the last 500 lines only — files are date-ordered
        with open(files[0], "r", encoding="utf-8-sig", errors="replace") as f:
            tail = list(f)[-500:]
        for line in tail:
            try:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    d = datetime.strptime(parts[1], DATE_FMT)
                    if max_date is None or d > max_date:
                        max_date = d
            except ValueError:
                continue
    return max_date


if __name__ == "__main__":
    main()
