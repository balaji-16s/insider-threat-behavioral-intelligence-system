# 🛡️ Insider Threat Behavioral Intelligence System (ITBIS)

An **AI-powered User and Entity Behavior Analytics (UEBA) platform** that continuously monitors employee activities, builds behavioral profiles, detects anomalies with machine learning, scores insider risk, and drives automated security response.

Built with **FastAPI**, **React (Vite)**, **PostgreSQL**, **Redis**, and **Docker**, trained and evaluated on the **CMU SEI CERT Insider Threat Test Dataset**.

---

## ✨ Features & Core Capabilities

### 🔐 Authentication & Role-Based Access Control (RBAC)
- JWT Authentication with bcrypt password hashing
- **Google OAuth 2.0 Integration** ("Continue with Google")
- 4 Role Levels: `administrator`, `security_manager`, `soc_engineer`, `security_analyst`
- Pre-seeded Demo Credentials available for instant SOC testing

### 👤 Employee Identity & Activity Telemetry
- Comprehensive employee onboarding: department, designation, manager, access privileges
- **8 Monitored Activity Types**: Login, File Download, File Upload, Data Transfer, Email, Privilege Escalation, Remote Access, USB Devices

### 🧠 Behavioral Profiling Engine
- Per-employee 30-day behavioral baselines (hourly patterns, off-hours/weekend ratios, burst activity)
- **Department Peer Group Comparison** to spot statistical outliers

### ⚡ Anomaly Detection (Dual-Engine Architecture)
- **Statistical / Rule-Based Engine**: Robust (median/MAD) z-score volume detection, IQR hourly spikes, off-hours data transfers, USB spikes, privilege escalation, large downloads, late-night and weekend access
- **🤖 ML Engine (Isolation Forest)**: Unsupervised scikit-learn model trained on 14 behavioral features, persisted to `data/models/`. Scores employees from 0–100 with top deviating factors

#### Peer-relative thresholds (why scores discriminate)

Every rule and threat factor is evaluated **against the peer distribution**
rather than a fixed event count. A fixed threshold is calibrated for
human-scale activity and saturates on a large dataset: with ~1,000 data
transfers per employee per month, constants like *"score 5 points per
transfer, cap at 40"* max out for everyone simultaneously, collapsing all
employees onto the same score and firing every rule for the entire
organisation.

Instead, a signal's severity is how far it exceeds the cohort **median**,
as a fraction of the median→**p95** distance. A median employee is
unremarkable by definition; the top 5% saturate. Results:

| Metric | Fixed thresholds | Peer-relative |
| :--- | :--- | :--- |
| Risk distribution | 951 medium / 0 critical | 701 low / 287 medium / 14 high |
| Distinct risk scores | ~140 | 452 |
| Large-download rule firing | 100% of employees | 5.1% |
| Off-hours transfer rule firing | 74% of employees | 5.1% |
| Privilege-escalation rule firing | 86% of employees | 6.8% |

This is also **scale-independent**: the same code behaves correctly whether
a window holds a dozen events or several million, so no threshold tuning or
dataset swap is needed as the data grows. Signals that do not vary across
peers (e.g. weekend activity, which every employee exhibits) are
automatically disabled rather than alerting the whole organisation.

When fewer than 20 employees are available the engine falls back to the
original absolute thresholds, since a distribution cannot be estimated from
a handful of samples. Scoring is deterministic — repeated runs on unchanged
data produce byte-identical scores.

### 🎯 Insider Risk Scoring & UEBA Pipeline
- Dynamic 0–100 threat score based on multi-dimensional behavioral deviations
- **One-Click UEBA Pipeline**: Baselines → Anomaly Detection → Threat Assessment → Risk Persistence

### 🚨 Incident Investigation & Automated Mitigation Playbooks
- Automated alert-to-incident escalation workflows
- **Single-Click Mitigation Playbooks**: Lock User Account, Force MFA Challenge, Revoke Active Session

### 📊 SOC Dashboards & Reporting
- Real-time SOC dashboard featuring 30-day activity trends, risk distribution heatmaps, and open incident counters
- PDF and Excel exportable reports for security audits

### 👷 Worker (Employee) Self-Service Portal
- Dedicated `employee` role and a **My Dashboard** page where a worker sees only their own data
- Answers three questions in one view: **what have I done**, **what was flagged against me**, and **what is my risk score and level**
- Shows the risk score against the organisation and the worker's own department (percentile and rank)
- Explains *why* a score is what it is, comparing each signal to the peer median and 95th percentile
- Authorisation is derived from the JWT, so an employee account cannot request another employee's records by editing a URL

---

## 🗄️ Real Dataset — CERT Insider Threat Dataset (r1)

The platform runs on **real insider threat data** from the CMU SEI CERT dataset:

| Component | Source File | Volume |
|-----------|-------------|--------|
| 1,000 Employees | `LDAP/*.csv` | Real names, roles, emails |
| Login Events | `logon.csv` | 849K events |
| USB Device Events | `device.csv` | 65K events |
| Web/Network Events | `http.csv` | 3.45M events |
| **Total Real Telemetry** | | **4.37M Events** |

To ingest the dataset and enrich it with the remaining activity types
(**order matters** — enrichment runs against the ingested employees):
```bash
python scripts/ingest_cert.py --ingest --clear   # load CERT telemetry (clear = fresh start)
python scripts/enrich_activity.py                # add file/email/remote/privilege events
python scripts/seed_demo_users.py                # create the demo logins below
python scripts/refresh_dataset.py                # re-anchor to now + compute baselines/scores/ML
python scripts/seed_worker_users.py              # create the worker portal logins
```

### 🔄 Keeping the Dataset Fresh

Analytics use **relative** lookback windows (30/90/180 days), but the ingested
timestamps are fixed. Left alone, the newest event drifts into the past and the
active window slowly empties — which also skews results, because a half-empty
window makes one rule dominate every employee's anomalies.

Re-anchor everything to "now" whenever the data ages:
```bash
python scripts/refresh_dataset.py                 # re-anchor + spread all 8 activity types
python scripts/refresh_dataset.py --dry-run       # preview the shift, change nothing
python scripts/refresh_dataset.py --days 180      # widen the enriched window
```

It re-anchors activity, alerts, incidents and notifications together, re-spreads
the synthesized activity types so **every window contains all 8 types**, clears
the cached detection/ML results, then recomputes baselines, risk scores and the
ML model. It is idempotent — re-running only shifts by the elapsed time.

---

## 🔑 Pre-Seeded Demo Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin@itbis.com` | `Password123!` |
| **Security Manager** | `manager@itbis.com` | `Password123!` |
| **SOC Engineer** | `soc@itbis.com` | `Password123!` |
| **Security Analyst** | `analyst@itbis.com` | `Password123!` |

### Worker portal logins

Created by `python scripts/seed_worker_users.py`, which links each account
to a real employee at a different risk level so the portal demonstrates
contrast rather than three identical screens:

| Account | Linked to |
| :--- | :--- |
| `worker.high@itbis.com` / `Password123!` | Highest-risk employee |
| `worker.mid@itbis.com` / `Password123!` | Median-risk employee |
| `worker.low@itbis.com` / `Password123!` | Lowest-risk employee |

Worker accounts are redirected to `/my-dashboard` on login and are refused
(HTTP 403) by every analyst and SOC endpoint.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | Python 3.11+ · FastAPI · SQLAlchemy 2 · Alembic |
| **AI / ML Engine** | scikit-learn (Isolation Forest) · NumPy · pandas |
| **Database & Cache** | PostgreSQL 16 · Redis 7 |
| **Auth & Security** | JWT (python-jose) · Passlib (bcrypt) · OAuth2 |
| **Frontend UI** | React 19 · TypeScript · Vite · Tailwind CSS · Recharts |
| **Infrastructure** | Docker · Docker Compose |

---

## 📂 Project Structure

```text
├── app/
│   ├── api/v1/            # API Endpoints: auth, employees, activity_logs, alerts,
│   │                      #   incidents, risk_scores, dashboard, anomaly, ueba
│   ├── core/              # config.py, security.py (JWT/hashing), deps.py (RBAC)
│   ├── db/base.py         # SQLAlchemy Engine & SessionLocal
│   ├── models/            # Database Models: User, Employee, ActivityLog,
│   │                      #   BehavioralBaseline, RiskScore, Alert, Incident
│   ├── schemas/           # Pydantic schemas
│   └── services/          # Profiling, Anomaly Engine, ML Engine, Risk Scoring, UEBA
├── frontend/              # React 19 + Vite SOC Dashboard Application
├── app/services/activity_aggregates.py  # Shared SQL aggregation for the engines
├── scripts/
│   ├── ingest_cert.py     # CERT dataset ingestion script
│   ├── enrich_activity.py # Adds the 5 activity types CERT does not contain
│   ├── refresh_dataset.py # Re-anchors the dataset to "now" and re-spreads types
│   ├── seed_demo_users.py # Demo user credentials seeder
│   └── train_ml_model.py  # Isolation Forest ML model trainer
├── docker-compose.yml     # Multi-container orchestration (Backend, Frontend, Postgres, Redis)
└── requirements.txt
```

---

## 🚀 Quick Start Guide

### 0. Ports and a database gotcha

`.env` points `DATABASE_URL` at **port 5433**, which is the *container's*
port. If you run the backend locally (`uvicorn`) but forget to start
Postgres, every request fails with
`connection to server at "localhost", port 5433 failed: Connection refused`
while `/health` still returns `ok` (it does not touch the database).

Bringing up only the infrastructure avoids clashing with locally running
servers on 8000/5173:

```bash
docker compose up -d postgres redis    # infra only — safe alongside local dev
docker compose stop postgres redis     # pause infra, keep the data volume
```

> Never use `docker compose down -v`: the `-v` deletes the volume, and you
> will have to re-ingest all 5M+ activity rows.

### 1. Launch with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/balaji-16s/insider-threat-behavioral-intelligence-system.git
cd insider-threat-behavioral-intelligence-system

# Start all 4 containers (Backend, Frontend, Postgres, Redis)
docker compose up -d --build
```

- **Frontend Dashboard:** `http://localhost:5173`
- **FastAPI OpenAPI Docs:** `http://localhost:8000/docs`

### 2. Manual Local Setup

```bash
# Backend Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_demo_users.py
uvicorn app.main:app --reload

# Frontend Setup (in a new terminal tab)
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing

Run full automated test suite (47 passing pytest tests):
```bash
venv/bin/python -m pytest
```

---

## ✅ Verifying the Stack Is Running

```bash
# all four containers should be Up (frontend must NOT be restarting)
docker compose ps

# backend API health + interactive docs
curl http://localhost:8000/health          # {"status":"ok"}
curl -I http://localhost:8000/docs        # 200

# frontend (nginx serves the SPA and proxies /api to the backend)
curl -I http://localhost:5173/            # 200
```

| Service | URL |
| :--- | :--- |
| SOC Dashboard | `http://localhost:5173` |
| FastAPI OpenAPI Docs | `http://localhost:8000/docs` |

---

## ⚠️ Known Limitations

These are measured properties of the current dataset, not bugs in the
engines — recorded so results are not over-interpreted.

1. **Ground-truth validation cannot run.** `data/cert/insiders.json` uses
   true CERT user ids (`BBS0039`, `2`), but the ingested `employee_code`
   values were synthesized from names (`BMS0001` = Burton M Stephenson).
   Zero of the 189 insider ids match an employee, so
   `ground_truth.insiders_in_dataset` is always `0` and ML precision is
   never actually measured. Fixing this means re-ingesting with the real
   CERT LDAP user ids, or adding an explicit id mapping.
2. **Two behavioural signals do not vary in this dataset**, so they cannot
   discriminate and are correctly inert: there are no `external` data
   transfers at all, and every employee is active on essentially every
   weekend day.
3. **`volume_anomaly` still fires for ~91% of employees.** This one is
   genuine: daily volumes swing widely (e.g. 243→645 events for a single
   employee within 30 days), so a per-day outlier test legitimately finds
   at least one busy day for most people. It is a data characteristic, not
   a threshold bug.
4. **No employee reaches the CRITICAL risk tier** (top score 78.9 against
   an 80 threshold). The enriched dataset contains no truly extreme
   outlier. Thresholds were left as-is rather than tuned to manufacture a
   critical case.

## ⚠️ Disclaimer

Built for research and educational purposes. Uses simulated activity data from the CMU SEI CERT dataset. Do not deploy for production security decisions without proper validation.
