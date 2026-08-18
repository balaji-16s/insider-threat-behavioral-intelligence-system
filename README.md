# 🛡️ Insider Threat Behavioral Intelligence System (ITBIS)

An **AI-powered insider threat detection platform** that continuously monitors employee activities, builds behavioral profiles, detects anomalies with machine learning, scores insider risk, and drives security investigations.

Built with **FastAPI** + **React**, running on the **real CERT Insider Threat Test Dataset** (CMU SEI).

---

## ✨ Features

### 🔐 Authentication & Role-Based Access
- JWT authentication with bcrypt password hashing
- **Google OAuth sign-in** ("Continue with Google") — set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` in `.env`; new Google users are provisioned automatically
- 4 roles: `administrator`, `security_manager`, `soc_engineer`, `security_analyst`
- Role-protected endpoints via dependency injection

### 👤 Employee Identity & Monitoring
- Employee onboarding with department, designation, manager, device info & access privileges
- **8 monitored activity types**: login, file download/upload, data transfer, email, privilege change, remote access, USB device

### 🧠 Behavioral Profiling Engine
- Per-employee behavioral baselines (activity distribution, hourly patterns, off-hours/weekend ratios, burst detection)
- **Peer-group comparison** against department peers

### ⚡ Anomaly Detection (2 Engines)
- **Statistical/rule-based**: Z-score, IQR, off-hours transfers, USB spikes, privilege escalation, large downloads, late-night & weekend patterns
- **🤖 ML (Isolation Forest)**: unsupervised scikit-learn model on 14 behavioral features — **trained once on the dataset** (`python scripts/train_ml_model.py` or the *Retrain Model* button) and persisted to `data/models/`; scoring loads the trained model for inference instead of re-fitting on every run. Scores every employee 0–100 with explainable top deviating factors, plus ground-truth validation against known insider labels

### 🎯 Insider Risk Scoring
- Weighted multi-model threat engine (data exfiltration, off-hours access, privilege abuse, policy violations, behavioral deviation)
- Risk persisted with full breakdowns; org-wide analytics: trend, department breakdown, top contributors

### 🕵️ UEBA Intelligence Pipeline
- One-call pipeline: baselines → anomaly detection → threat assessment → risk persistence
- Consolidated per-employee UEBA profiles

### 🚨 Alerts & Incident Investigation
- Severity levels (informational → critical), alert lifecycle, alert→incident escalation
- Incident timelines with audited actors, status workflows, related-alert resolution

### 📊 Dashboards & Reports
- SOC dashboard (org risk trend, top insider threats, recent alerts, activity trends)
- **13 frontend pages**: Login, Dashboard, Employees, Employee Detail, Activity Logs, UEBA Intelligence, Anomaly Detection (+ML tab), Behavioral Analysis, Alerts, Incidents, Incident Detail, Risk Scores, Anomaly Reports

---

## 🗄️ Real Dataset — CERT Insider Threat Test Dataset (r1)

The platform runs on **real insider-threat data** from the CMU SEI CERT Insider Threat Test Dataset instead of synthetic data:

| Component | Source file | Volume |
|-----------|-------------|--------|
| 1,000 employees | `LDAP/*.csv` | real names, roles, emails |
| Login events | `logon.csv` | 849K |
| USB device events | `device.csv` | 65K |
| Web/network events | `http.csv` | 3.45M |
| **Total real events** | | **4.37M** |

CERT r1 only contains logon/device/http events. Run the enrichment script to add
the other 5 monitored activity types (`file_download`, `file_upload`, `email`,
`privilege_change`, `remote_access`) so all 8 types appear in every module:
```bash
python scripts/enrich_activity.py
```

- **Ground-truth insider labels** saved to `data/cert/insiders.json` for evaluating detection models
- Timestamps are **rebased to the present** so the platform's 30-day analytics windows work with the 2010–2011 data (relative behavior is preserved; use `--no-rebase` to keep original dates)
- Dataset license: free for research/educational use (see `data/cert/license.txt`)

**Ingest the real data:**
```bash
python scripts/ingest_cert.py --all            # download (87 MB) + extract + ingest
python scripts/ingest_cert.py --all --clear    # replace existing data
python scripts/ingest_cert.py --all --max-users 200   # smaller subset
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · FastAPI · SQLAlchemy 2 · Alembic |
| AI/ML | scikit-learn (Isolation Forest) · NumPy |
| Database | PostgreSQL 16 · Redis 7 |
| Auth | JWT (python-jose) · Passlib (bcrypt) |
| Frontend | React 19 · TypeScript · Vite · Tailwind CSS 4 · Recharts · lucide-react |
| Infrastructure | Docker Compose |

---

## 📂 Project Structure

```text
├── app/
│   ├── api/v1/            # Routers: auth, employees, activity_logs, alerts,
│   │                      #   incidents, risk_scores, dashboard, anomaly, reports, ueba
│   ├── core/              # config.py, security.py (JWT/hashing), deps.py (auth/RBAC)
│   ├── db/base.py         # Engine, SessionLocal, Base
│   ├── models/            # 7 tables: User, Employee, ActivityLog, BehavioralBaseline,
│   │                      #   RiskScore, Alert, Incident
│   ├── schemas/           # Pydantic request/response models
│   ├── services/          # auth, behavioral_profiling, anomaly_detection,
│   │                      #   ml_anomaly_detection, threat_detection, risk_scoring,
│   │                      #   ueba, report_service, report_export (PDF/Excel)
│   └── main.py            # FastAPI app entrypoint
├── frontend/src/
│   ├── pages/             # 13 pages (Dashboard … IncidentDetail)
│   ├── api/               # typed API clients
│   ├── components/        # Layout, ProtectedRoute
│   └── context/           # AuthContext
├── scripts/
│   ├── ingest_cert.py     # Real CERT dataset ingestion
│   └── seed_data.py       # Synthetic demo data generator (fallback)
├── alembic/               # DB migrations
├── docker-compose.yml     # PostgreSQL + Redis
└── requirements.txt
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+ · Node 18+ · Docker & Docker Compose

### 2. Environment
```bash
cp .env.example .env
docker compose up -d          # PostgreSQL (:5433) + Redis (:6379)
# Optional: enable Google OAuth by filling in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
# and GOOGLE_REDIRECT_URI (create an OAuth 2.0 Client ID at Google Cloud Console).
```

### 3. Backend
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # create the 7 tables
python scripts/ingest_cert.py --all --clear   # load real CERT data
uvicorn app.main:app --reload                 # http://127.0.0.1:8000/docs
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

### 5. Accounts (Google OAuth only)
There are **no demo credentials** — all accounts sign in with **Continue with Google**.
The first Google sign-in automatically becomes the **Administrator**; later sign-ins
are provisioned as **Security Analysts**. (Roles map to the 3 documented logins:
`administrator`, `security_manager`, `security_analyst` — adjust roles in the DB if needed.)

### 6. First Run Workflow
1. Log in → Dashboard shows org risk posture & top threats
2. **UEBA Intelligence** → *Run Pipeline* to refresh baselines/anomalies/risk
3. **Anomaly Detection → ML Detection tab** → *Run ML Detection* (Isolation Forest)
4. **Risk Scores** → *Recalculate* + explore analytics
5. **Alerts** → escalate to an incident → **Incidents** → investigate via timeline

---

## 🔌 Key API Endpoints

| Area | Endpoints |
|------|-----------|
| Auth | `POST /api/v1/auth/register` · `POST /api/v1/auth/login` · `GET/PUT /api/v1/auth/me` |
| Employees | `GET/POST /api/v1/employees` · `GET/PUT/DELETE /api/v1/employees/{id}` · stats |
| Activity | `GET/POST /api/v1/activity-logs` · `POST /api/v1/activity-logs/bulk` |
| Anomaly | `POST /api/v1/anomaly/detect` · `POST /api/v1/anomaly/ml/detect` · `GET /api/v1/anomaly/ml/results` · `POST /api/v1/anomaly/baselines/compute` · `GET /api/v1/anomaly/threat/top` |
| Risk | `POST /api/v1/risk-scores/calculate` · `GET /api/v1/risk-scores/analytics` · `GET /api/v1/risk-scores/distribution` |
| UEBA | `POST /api/v1/ueba/pipeline` · `GET /api/v1/ueba/overview` · `GET /api/v1/ueba/overview/{employee_id}` |
| Alerts | `GET/POST /api/v1/alerts` · `PATCH /api/v1/alerts/{id}` · `POST /api/v1/alerts/{id}/escalate` |
| Incidents | `GET/POST /api/v1/incidents` · `PATCH /api/v1/incidents/{id}` · `POST /api/v1/incidents/{id}/timeline` · `GET /api/v1/incidents/{id}/related-alerts` |
| Notifications | `GET /api/v1/notifications` · `POST /api/v1/notifications/send` |
| Reports | `GET /api/v1/reports/anomaly` · `GET /api/v1/reports/employee/{employee_id}` · **PDF/Excel export**: `/anomaly/pdf` · `/anomaly/xlsx` · `/employee/{id}/pdf` · `/employee/{id}/xlsx` |
| Dashboard | `GET /api/v1/dashboard/stats` · `GET /api/v1/dashboard/recent-alerts` · `GET /api/v1/dashboard/activity-trends` |

---

## 🧪 Testing

46 automated tests cover the core engine, notifications, and API workflows (run against a dedicated `itbis_test` PostgreSQL database):

*   **Auth & RBAC & Profile** — registration, login, token auth, user profile update (`/auth/me`), role restrictions (403s)
*   **Anomaly detection** — rule-based off-hours exfiltration, quiet-user negatives, threat scoring
*   **Risk scoring** — score persistence, engine-score replacement, analytics
*   **ML engine** — Isolation Forest flags seeded insiders, no-activity exclusion, 0-100 range
*   **Notifications** — multi-channel alert dispatch (email/webhook/in-app) and audit logging
*   **Report export** — valid PDF/Excel magic bytes for org & employee reports
*   **API workflows** — employee CRUD, bulk activity ingestion, alert escalation, dashboard stats


```bash
# requires Docker Compose services running (PostgreSQL :5433)
venv/bin/python -m pytest
```

## 📈 Performance Notes

- The UEBA pipeline (baselines → anomalies → risk scores) is **manual**: click **Run UEBA Pipeline** / **Recalculate Scores** to refresh. Baselines are batched (chunked activity loading + single-SQL department peer stats) so the whole pipeline completes in a few minutes at 1,000 employees / 4.4M+ events
- ML anomaly detection scores 1,000 employees in ~15 seconds using the persisted trained model (no per-run re-fitting); retrain with `python scripts/train_ml_model.py` or the **Retrain Model** button
- Reports, top-threats and risk pages all read the **same persisted risk scores**, so every module shows identical numbers; org reports are cached 60s and export fast

---

## 🔭 Roadmap

- [x] Milestone 1 — Auth, employee mgmt, activity monitoring, real data ingestion
- [x] Milestone 2 — Behavioral profiling, anomaly detection, threat models
- [x] Milestone 3 — Risk scoring, UEBA pipeline, investigation workflows
- [x] **ML anomaly detection (Isolation Forest)**
- [x] PDF/Excel report export (reportlab + openpyxl, download buttons on Anomaly Reports page)
- [x] Automated tests (pytest — 46 tests passing across auth, engines, notifications, exports, API)
- [x] Docker images for full app + CI/CD (GitHub Actions `.github/workflows/ci.yml`)
- [x] Notification & escalation system (email/webhook notification dispatch service)
- [x] User Profile Management API (`GET/PUT /api/v1/auth/me`) & Role-Based Dashboard Views


---

## ⚠️ Disclaimer

Built for research & educational purposes. The CERT dataset contains simulated (realistic but fictional) employee activity. Do not use for production security decisions without proper validation.
