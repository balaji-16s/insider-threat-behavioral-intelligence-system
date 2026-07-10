# Insider Threat Behavioral Intelligence System (ITBIS)

A security platform built with **FastAPI** designed to monitor, log, and analyze employee activities for insider threat behavior, detect anomalies, calculate risk scores, and manage security incidents.

---

## 🚀 Project Overview

ITBIS allows security operations center (SOC) analysts and administrators to monitor behavioral baselines, track activity logs, trigger real-time alerts, and manage incident lifecycles. 

---

## 🛠️ Tech Stack

*   **Framework:** FastAPI (Python 3.11+)
*   **Database:** PostgreSQL (v16)
*   **ORM:** SQLAlchemy (v2.0+)
*   **Database Migrations:** Alembic
*   **Cache / Key-Value Store:** Redis (v7)
*   **Authentication & Security:** JWT (Jose), Passlib (Bcrypt) for password hashing, and Role-Based Access Control (RBAC)
*   **Infrastructure:** Docker Compose

---

## 📈 Current Project Progress & Features

The project is structured into modular layers (routers, schemas, models, services) and currently has the following foundations implemented:

### 1. Core API & Skeleton Setup
*   **FastAPI Application Entry Point (`app/main.py`):** Configured with system settings and routing.
*   **Health Check Endpoint:** `/health` endpoint to verify application status.
*   **Config Management (`app/core/config.py`):** Structured configuration loading using Pydantic Settings from a `.env` file.

### 2. Database Architecture (SQLAlchemy Models)
We have fully defined and mapped the **7 Core Database Tables** in SQLAlchemy (`app/models/`):
*   **`User`**: Admin and analyst accounts who manage the platform. Includes Role-Based Access Control (RBAC) with defined roles:
    *   `administrator`
    *   `security_manager`
    *   `soc_engineer`
    *   `security_analyst`
*   **`Employee`**: Monitored corporate employees, including metadata like department, designation, manager details, and JSON-based fields for device info and access privileges.
*   **`ActivityLog`**: Logs monitoring employee actions such as `login`, `file_download`, `file_upload`, `data_transfer`, `email`, `privilege_change`, `remote_access`, and `usb_device`.
*   **`BehavioralBaseline`**: JSON-based profile representing baseline behavioral metrics for employees. Used for deviation analysis.
*   **`RiskScore`**: Dynamic risk score values and detailed breakdowns calculated for employees over time.
*   **`Alert`**: System-generated alerts triggered by anomalous activity with tracking states (`open`, `acknowledged`, `resolved`, `dismissed`) and severity levels (`informational`, `low`, `medium`, `high`, `critical`).
*   **`Incident`**: Escalated security incident cases linked to employees and assigned to analysts with investigation timelines and status.

### 3. User Authentication & Authorization
*   **Secure Password Hashing:** Implemented with `passlib` using the Bcrypt algorithm.
*   **JSON Web Tokens (JWT):** Access token generation, expiration handling, and decoding utilities using `python-jose`.
*   **API v1 Auth Endpoints (`app/api/v1/auth.py`):**
    *   `POST /api/v1/auth/register`: Signup endpoint to register platform users.
    *   `POST /api/v1/auth/login`: Authenticates users and issues Bearer access tokens.
*   **Dependency Injection & Role-Based Security (`app/core/deps.py`):**
    *   `get_current_user`: Secures endpoints and retrieves authenticated user context.
    *   `require_role(...)`: Simple middleware/decorator to restrict route access by role (e.g. administrator or security manager).

### 4. Infrastructure & Migrations
*   **Docker Compose Setup (`docker-compose.yml`):** Preconfigured to spin up local instances of:
    *   PostgreSQL database on port `5433`
    *   Redis container on port `6379`
*   **Alembic Migrations:** Alembic configuration and initial migration scripts are set up under `/alembic` to automatically provision the database tables.

---

## 📂 Directory Structure

```text
├── alembic/                # Alembic database migration scripts
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── auth.py     # Auth API endpoints (register, login)
│   ├── core/
│   │   ├── config.py       # Configuration and Environment loading
│   │   ├── deps.py         # Dependencies (auth, role checks, get_db)
│   │   └── security.py     # JWT & Password utility functions
│   ├── db/
│   │   └── base.py         # DB Engine, SessionLocal, Base model
│   ├── models/             # SQLAlchemy Models (User, Employee, ActivityLog, etc.)
│   ├── schemas/            # Pydantic Schemas for validation and serialization
│   │   └── user.py         # User & Token schemas
│   ├── services/           # Business logic layer
│   │   └── auth_service.py # Authentication database services
│   └── main.py             # FastAPI App initialisation
├── docker-compose.yml      # Local DB & Redis service configuration
├── requirements.txt        # Python dependency packages
├── .env.example            # Environment variables template
└── .gitignore              # Files ignored by git
```

---

## 🛠️ Getting Started Locally

### 1. Prerequisites
*   Python 3.11 or higher
*   Docker & Docker Compose

### 2. Environment Setup
Clone the template env file and configure your local settings:
```bash
cp .env.example .env
```

### 3. Run External Services
Start the database and caching services using Docker Compose:
```bash
docker compose up -d
```

### 4. Setup Virtual Environment & Install Dependencies
Create a virtual environment and install the required Python packages:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Run Database Migrations
Provision the PostgreSQL database with the Alembic migration history:
```bash
alembic upgrade head
```

### 6. Run the Application
Start the FastAPI development server:
```bash
uvicorn app.main:app --reload
```

The application will be live at `http://127.0.0.1:8000`. You can access the auto-generated API documentation at `http://127.0.0.1:8000/docs`.
