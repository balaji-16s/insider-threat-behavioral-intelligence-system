#!/usr/bin/env python3
"""
ITBIS Synthetic Data Generator

Generates realistic enterprise data for all 7 database tables.

Usage:
    python scripts/seed_data.py           # Generate fresh data
    python scripts/seed_data.py --clear   # Clear all data first
"""

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db.base import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.activity_log import ActivityLog, ActivityType
from app.models.behavioral_baseline import BehavioralBaseline
from app.models.risk_score import RiskScore, RiskLevel
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.incident import Incident, IncidentStatus

# ─── Configuration ────────────────────────────────────────────────

DEPARTMENTS = {
    "Engineering": ["Software Engineer", "Senior Engineer", "Tech Lead", "Engineering Manager"],
    "Product": ["Product Manager", "Product Owner", "Associate PM"],
    "Sales": ["Sales Rep", "Senior Sales Rep", "Account Executive", "Sales Manager"],
    "Marketing": ["Marketing Specialist", "Marketing Manager", "Content Writer"],
    "Finance": ["Accountant", "Financial Analyst", "Finance Manager"],
    "HR": ["HR Coordinator", "HR Manager", "Recruiter"],
    "Legal": ["Legal Counsel", "Compliance Officer"],
    "IT Security": ["Security Analyst", "SOC Engineer", "Security Architect"],
    "Operations": ["Operations Analyst", "Operations Manager"],
    "Executive": ["CEO", "CTO", "COO"],
}

ACTIVITY_TYPES = [
    ActivityType.LOGIN, ActivityType.FILE_DOWNLOAD, ActivityType.FILE_UPLOAD,
    ActivityType.EMAIL, ActivityType.DATA_TRANSFER, ActivityType.PRIVILEGE_CHANGE,
    ActivityType.REMOTE_ACCESS, ActivityType.USB_DEVICE,
]

SOURCES = ["workstation", "laptop", "vpn", "cloud_portal", "email_server", "file_server"]

FIRST_NAMES = ["Alice","Bob","Charlie","Diana","Edward","Fiona","George","Helen","Ivan","Julia",
    "Kevin","Laura","Mike","Nina","Oscar","Patricia","Quinn","Rachel","Sam","Tina",
    "Uma","Victor","Wendy","Xavier","Yara","Zack","Aaron","Bella","Carlos","Daisy",
    "Eli","Faith","Gavin","Hannah","Isaac","Jade","Kai","Liam","Maya","Noah",
    "Olivia","Paul","Rose","Steve","Tracy","Violet","Will","Zoe"]

LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Wilson","Anderson","Thomas","Taylor",
    "Moore","Jackson","Martin","Lee","Perez","Thompson","White","Harris","Sanchez",
    "Clark","Ramirez","Lewis","Robinson","Walker","Young","Allen","King","Wright",
    "Scott","Torres","Nguyen","Hill","Flores","Green","Adams","Nelson","Baker","Hall"]


def main():
    print("\n" + "=" * 60)
    print("  ITBIS - Synthetic Data Generator")
    print("=" * 60)

    clear = "--clear" in sys.argv

    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        print("\n✓ Database tables ready")

        existing_emps = db.query(Employee).count()
        if existing_emps > 0 and not clear:
            print(f"\n⚠ Database already has {existing_emps} employees. Use --clear to regenerate.")
            print("  Skipping. Existing data is fine for the UI.")
            return

        if clear and existing_emps > 0:
            print("\n  Clearing existing data...")
            db.query(Incident).delete()
            db.query(Alert).delete()
            db.query(RiskScore).delete()
            db.query(BehavioralBaseline).delete()
            db.query(ActivityLog).delete()
            db.query(Employee).delete()
            db.commit()
            print("  ✓ Cleared")

        # ─── 1. Users ───────────────────────────────────────────
        # No demo credentials are seeded anymore. Accounts are created via
        # Google OAuth (the first sign-in becomes the administrator).
        print("\n[1/6] Users: skipped — log in via Google OAuth (first user becomes admin)")

        # ─── 2. Generate Employees ──────────────────────────────
        print("\n[2/6] Generating employees...")
        dept_list = list(DEPARTMENTS.keys())
        employees = []
        for i in range(40):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            dept = random.choice(dept_list)
            emp = Employee(
                employee_code=f"EMP{1001 + i:04d}",
                full_name=f"{first} {last}",
                department=dept,
                designation=random.choice(DEPARTMENTS[dept]),
                manager_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                device_info={
                    "os": random.choice(["Windows 11", "macOS 14", "Ubuntu 22.04"]),
                    "hostname": f"{first.lower()}-{random.choice(['laptop', 'desktop'])}",
                },
                access_privileges=random.sample(
                    ["vpn_access", "admin_panel", "source_code", "financial_reports",
                     "employee_data", "client_data", "cloud_console", "file_server"],
                    k=random.randint(1, 5)),
            )
            employees.append(emp)
        db.add_all(employees)
        db.commit()
        for e in employees:
            db.refresh(e)
        print(f"  ✓ {len(employees)} employees created")

        # ─── 3. Generate Activity Logs ──────────────────────────
        print("\n[3/6] Generating activity logs...")
        now = datetime.utcnow()
        all_logs = []
        high_risk_indices = {3, 7, 15, 22, 31}  # indices that will have more suspicious activity

        for idx, emp in enumerate(employees):
            is_high_risk = idx in high_risk_indices
            for day_ago in range(30):
                day = now - timedelta(days=day_ago)
                day_start = day.replace(hour=8, minute=0, second=0, microsecond=0)
                
                num_logs = random.randint(3, 8)
                if is_high_risk:
                    num_logs += random.randint(1, 4)

                for _ in range(num_logs):
                    # Weighted activity type selection
                    at = random.choices(ACTIVITY_TYPES, weights=[
                        30, 15, 10, 20, 5, 2, 8, 10
                    ])[0]
                    
                    # High risk employees have more data transfers and USB events
                    if is_high_risk and random.random() < 0.15:
                        at = random.choice([ActivityType.DATA_TRANSFER, ActivityType.USB_DEVICE])

                    # Activity time using ABSOLUTE hours (not relative to day_start)
                    if random.random() < 0.08:
                        hour = random.randint(1, 5)  # off-hours (1-5 AM)
                    else:
                        hour = random.randint(8, 18)  # business hours (8 AM - 6 PM)
                    
                    occurred = day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

                    details = {}
                    if at == ActivityType.LOGIN:
                        details = {"method": random.choice(["password", "sso", "mfa"]), "success": True}
                    elif at in (ActivityType.FILE_DOWNLOAD, ActivityType.FILE_UPLOAD):
                        details = {"filename": f"doc_{random.randint(1,999)}.pdf", "size_kb": random.randint(10, 50000)}
                    elif at == ActivityType.EMAIL:
                        details = {"recipients": random.randint(1, 10), "has_attachment": random.random() > 0.6}
                    elif at == ActivityType.DATA_TRANSFER:
                        details = {"bytes": random.randint(1000, 50000000), "destination": random.choice(["usb", "cloud", "external"])}
                    elif at == ActivityType.USB_DEVICE:
                        details = {"device": f"USB-{random.randint(1000,9999)}", "action": "connect"}

                    all_logs.append(ActivityLog(
                        employee_id=emp.id,
                        activity_type=at,
                        source=random.choice(SOURCES),
                        details=details,
                        occurred_at=occurred,
                    ))

            if (idx + 1) % 10 == 0:
                print(f"    Planning logs for {idx + 1}/{len(employees)} employees...")

        # Bulk insert in batches
        batch_size = 2000
        for i in range(0, len(all_logs), batch_size):
            db.bulk_save_objects(all_logs[i:i + batch_size])
            db.commit()
        print(f"  ✓ {len(all_logs)} activity logs created")

        # ─── 4. Generate Behavioral Baselines ───────────────────
        print("\n[4/6] Generating behavioral baselines...")
        baselines = []
        for emp in employees:
            emp_logs = [l for l in all_logs if l.employee_id == emp.id]
            type_counts = {}
            for at in ACTIVITY_TYPES:
                type_counts[at.value] = len([l for l in emp_logs if l.activity_type == at])
            
            off_hours = len([l for l in emp_logs if l.occurred_at.hour < 7 or l.occurred_at.hour > 20])
            data_xfers = type_counts.get("data_transfer", 0)
            usb_count = type_counts.get("usb_device", 0)
            
            baselines.append(BehavioralBaseline(
                employee_id=emp.id,
                baseline_data={
                    "total_logs": len(emp_logs),
                    "daily_avg": round(len(emp_logs) / 30, 1),
                    "activity_distribution": type_counts,
                    "off_hours_activity": off_hours,
                    "data_transfer_freq": data_xfers,
                    "usb_usage_freq": usb_count,
                }))
        db.bulk_save_objects(baselines)
        db.commit()
        print(f"  ✓ {len(baselines)} baselines created")

        # ─── 5. Generate Risk Scores ────────────────────────────
        print("\n[5/6] Generating risk scores...")
        risk_scores = []
        for idx, emp in enumerate(employees):
            is_high_risk = idx in high_risk_indices
            emp_logs = [l for l in all_logs if l.employee_id == emp.id]
            
            for day_ago in range(0, 30, 5):
                day = now - timedelta(days=day_ago)
                recent = [l for l in emp_logs if l.occurred_at > day - timedelta(days=5)]
                
                off_hours = len([l for l in recent if l.occurred_at.hour < 7 or l.occurred_at.hour > 20])
                data_xfers = len([l for l in recent if l.activity_type == ActivityType.DATA_TRANSFER])
                usb = len([l for l in recent if l.activity_type == ActivityType.USB_DEVICE])
                
                base = random.uniform(50, 90) if is_high_risk else random.uniform(5, 35)
                score = min(100, max(0, base + off_hours * 2 + data_xfers * 4 + usb * 3))
                
                if is_high_risk and random.random() < 0.3:
                    score += random.uniform(10, 25)  # spike
                score = min(100, score)
                
                risk_scores.append(RiskScore(
                    employee_id=emp.id,
                    score=round(score, 1),
                    risk_level=(RiskLevel.CRITICAL if score >= 80 else RiskLevel.HIGH if score >= 60 
                                else RiskLevel.MEDIUM if score >= 30 else RiskLevel.LOW),
                    breakdown={
                        "off_hours": off_hours, "data_transfers": data_xfers,
                        "usb_events": usb, "base_score": round(base, 1),
                    },
                    calculated_at=day,
                ))
        db.bulk_save_objects(risk_scores)
        db.commit()
        print(f"  ✓ {len(risk_scores)} risk scores created")

        # ─── 6. Generate Alerts & Incidents ─────────────────────
        print("\n[6/6] Generating alerts and incidents...")
        alerts = []
        for idx in high_risk_indices:
            if idx >= len(employees):
                continue
            emp = employees[idx]
            
            scenarios = [
                ("Unusual Data Transfer Activity", AlertSeverity.HIGH, "data_exfiltration",
                 f"Employee {emp.full_name} performed excessive data transfers."),
                ("Excessive Off-Hours Access", AlertSeverity.MEDIUM, "off_hours_access",
                 f"Employee frequently accessing systems outside business hours."),
            ]
            if random.random() < 0.6:
                scenarios.append(
                    ("USB Device Policy Violation", AlertSeverity.MEDIUM, "policy_violation",
                     f"Employee connected unauthorized USB devices.")
                )
            
            for title, severity, anomaly_type, desc in scenarios:
                alert = Alert(
                    employee_id=emp.id, title=title, description=desc,
                    severity=severity, status=AlertStatus.OPEN,
                    anomaly_type=anomaly_type,
                    evidence={"detected_by": "automated_analysis"},
                    created_at=now - timedelta(days=random.randint(1, 14)),
                )
                alerts.append(alert)

        # Add a few random alerts
        for _ in range(5):
            emp = random.choice(employees)
            alerts.append(Alert(
                employee_id=emp.id,
                title=random.choice(["Failed Login Attempts", "New Device Registration", "Large Download Detected"]),
                description="Anomalous activity detected by monitoring system.",
                severity=random.choice(list(AlertSeverity)),
                status=random.choice([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
                anomaly_type=random.choice(["authentication", "device", "data_access"]),
                evidence={},
                created_at=now - timedelta(days=random.randint(1, 7)),
            ))

        db.add_all(alerts)
        db.commit()
        for a in alerts:
            db.refresh(a)
        print(f"  ✓ {len(alerts)} alerts created")

        # Create incidents from some alerts
        incidents = []
        for i, alert in enumerate(alerts[:6]):
            incidents.append(Incident(
                employee_id=alert.employee_id,
                title=f"Investigation: {alert.title}",
                status=list(IncidentStatus)[i % 4],
                related_alert_ids=[str(alert.id)],
                timeline=[{"event": "Alert generated", "timestamp": alert.created_at.isoformat()}],
                created_at=alert.created_at,
            ))
        db.add_all(incidents)
        db.commit()
        print(f"  ✓ {len(incidents)} incidents created")

        # ─── Summary ────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  ✅ DATA GENERATION COMPLETE!")
        print("=" * 60)
        print(f"  Employees:       {len(employees)}")
        print(f"  Activity Logs:   {len(all_logs)}")
        print(f"  Risk Scores:     {len(risk_scores)}")
        print(f"  Alerts:          {len(alerts)}")
        print(f"  Incidents:       {len(incidents)}")
        print(f"  Users:           Google OAuth only (first sign-in becomes admin)")
        print(f"\n  Start: uvicorn app.main:app --reload")
        print(f"  Frontend: cd frontend && npm run dev")

    finally:
        db.close()


if __name__ == "__main__":
    main()
