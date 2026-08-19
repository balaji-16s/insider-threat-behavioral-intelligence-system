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
- **Statistical / Rule-Based Engine**: Z-score, IQR, off-hours data transfers, USB spikes, privilege escalation
- **🤖 ML Engine (Isolation Forest)**: Unsupervised scikit-learn model trained on 14 behavioral features, persisted to `data/models/`. Scores employees from 0–100 with top deviating factors

### 🎯 Insider Risk Scoring & UEBA Pipeline
- Dynamic 0–100 threat score based on multi-dimensional behavioral deviations
- **One-Click UEBA Pipeline**: Baselines → Anomaly Detection → Threat Assessment → Risk Persistence

### 🚨 Incident Investigation & Automated Mitigation Playbooks
- Automated alert-to-incident escalation workflows
- **Single-Click Mitigation Playbooks**: Lock User Account, Force MFA Challenge, Revoke Active Session

### 📊 SOC Dashboards & Reporting
- Real-time SOC dashboard featuring 30-day activity trends, risk distribution heatmaps, and open incident counters
- PDF and Excel exportable reports for security audits

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

To enrich and ingest dataset:
```bash
python scripts/enrich_activity.py
python scripts/ingest_cert.py --all --clear
```

To seed demo user accounts:
```bash
python scripts/seed_demo_users.py
```

---

## 🔑 Pre-Seeded Demo Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin@itbis.com` | `Password123!` |
| **Security Manager** | `manager@itbis.com` | `Password123!` |
| **SOC Engineer** | `soc@itbis.com` | `Password123!` |
| **Security Analyst** | `analyst@itbis.com` | `Password123!` |

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
├── scripts/
│   ├── ingest_cert.py     # CERT dataset ingestion script
│   ├── seed_demo_users.py # Demo user credentials seeder
│   └── train_ml_model.py  # Isolation Forest ML model trainer
├── docker-compose.yml     # Multi-container orchestration (Backend, Frontend, Postgres, Redis)
└── requirements.txt
```

---

## 🚀 Quick Start Guide

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

Run full automated test suite (46 passing pytest tests):
```bash
venv/bin/python -m pytest
```

---

## ⚠️ Disclaimer

Built for research and educational purposes. Uses simulated activity data from the CMU SEI CERT dataset. Do not deploy for production security decisions without proper validation.
