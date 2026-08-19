# Insider Threat Intelligence & UEBA System — Master Video Speech Script

---

## 📋 Script Structure Overview

This master script provides a comprehensive word-for-word spoken transcript divided into two parts:
- **PART A: Slide-by-Slide Presentation Speech (Slides 1 – 14)**
- **PART B: Live System Demonstration Speech (Module-by-Module Breakdown)**

---

# PART A: Slide-by-Slide Presentation Speech

---

### 🟢 SLIDE 1: Title & Cover
**Visual:** Slide 1 — *Insider Threat Behavioral Intelligence System (AI-POWERED ENTERPRISE SECURITY PLATFORM)*

**🎙️ Spoken Speech:**
> *"Good morning, everyone, and welcome to our presentation on the **Insider Threat Behavioral Intelligence System** — an advanced, AI-powered User and Entity Behavior Analytics platform.
> 
> In modern enterprise security, malicious or compromised insiders pose one of the most dangerous vectors because they already operate within trusted network perimeters using legitimate credentials. Traditional security tools fail to distinguish between normal employee activities and malicious insider behavior. 
> 
> Our platform bridges this gap by continuously streaming user activity telemetry, computing 30-day statistical baselines, running machine learning anomaly detection models, and triggering automated mitigation playbooks in real time. Over the next few minutes, we will walk through the architecture, core capabilities, live application demonstration, and technical implementation."*

---

### 🟢 SLIDE 2: Technology Stack & Core Components
**Visual:** Slide 2 — *Technology Stack & Architecture Baseline* (4 Category Cards)

**🎙️ Spoken Speech:**
> *"Moving to Slide 2, let me introduce our core technology stack and infrastructure choices.
> 
> First, on the backend, we leverage **FastAPI**, an asynchronous Python framework that delivers ultra-high throughput for processing incoming security event logs. It handles OAuth2 and JWT-based Role-Based Access Control, while managing live WebSocket alert streams.
> 
> Second, our **UEBA Machine Learning Engine** combines an Isolation Forest model for multi-dimensional outlier detection with a statistical Z-score calculator across 30-day user baselines to output dynamic risk scores from 0 to 100.
> 
> Third, our frontend is built using **React powered by Vite**, offering a high-performance Security Operations Center dashboard with interactive risk heatmaps and real-time alert feeds.
> 
> Finally, our data layer utilizes **PostgreSQL** for persistent audit records and baselines, **Redis** for in-memory caching and Pub/Sub messaging, all containerized seamlessly using **Docker** and **Alembic** database migrations."*

---

### 🟢 SLIDE 3: Core Capabilities & Features
**Visual:** Slide 3 — *Core System Capabilities & Features* (4 Horizontal Cards)

**🎙️ Spoken Speech:**
> *"On Slide 3, we highlight the four pillar capabilities that define our system.
> 
> 1. **Real-Time Telemetry Ingestion:** The system continuously captures authentication events, resource access logs, data transfer sizes, and IP geolocations across all enterprise endpoints.
> 2. **Isolation Forest Anomaly Engine:** Unlike legacy rule engines, our ML model detects subtle multi-dimensional behavioral anomalies without requiring pre-labeled attack data or static signatures.
> 3. **Dynamic Risk Scoring (0 to 100):** Every user in the organization receives a continuously updated risk score computed from historical Z-score deviations and threat persistence factors.
> 4. **Automated Playbook Response:** When a threat breaches critical risk thresholds, the system automatically executes containment playbooks — such as triggering forced MFA, locking the user account, or revoking active OAuth sessions."*

---

### 🟢 SLIDE 4: Cybersecurity Problem & SIEM Limitations
**Visual:** Slide 4 — *Cybersecurity Problem & SIEM Limitations* (3 Challenge Cards)

**🎙️ Spoken Speech:**
> *"Slide 4 addresses the critical industry pain points that inspired this project.
> 
> **Problem 1: Static SIEM Rules Fail.** Traditional Security Information and Event Management systems depend on fixed threshold rules. Malicious insiders exploit this by stealing data slowly over time ('low-and-slow' exfiltration) without ever breaching static thresholds.
> 
> **Problem 2: High False Positives & Analyst Fatigue.** Legacy tools generate thousands of uncorrelated alerts daily, overwhelming Security Operations Center analysts and causing critical threat warnings to be buried in noise.
> 
> **Problem 3: Delayed Incident Response.** Manual log aggregation and cross-table correlation often take hours or days, giving malicious actors ample time to exfiltrate proprietary data."*

---

### 🟢 SLIDE 5: End-to-End System Architecture Diagram
**Visual:** Slide 5 — *End-to-End System Architecture* (Architecture Diagram Graphic & 4-Stage Summary)

**🎙️ Spoken Speech:**
> *"Slide 5 showcases our complete end-to-end system architecture operating across four distinct stages:
> 
> - **Stage 1 (Data Ingestion):** Collects raw security events, identity access logs, SIEM telemetry, and activity data.
> - **Stage 2 (FastAPI & Redis Backend):** Filters incoming logs, manages user sessions, caches active baselines in Redis Pub/Sub, and routes telemetry to the ML pipeline.
> - **Stage 3 (ML Anomaly Engine):** Runs Isolation Forest model evaluations and Z-score statistical calculations against stored PostgreSQL 30-day historical profiles.
> - **Stage 4 (React SOC Dashboard):** Pushes real-time WebSocket alert notifications, populates threat heatmaps, and provides automated playbook buttons for analysts."*

---

### 🟢 SLIDE 6: Key Engineering Solutions & Innovation
**Visual:** Slide 6 — *Key Engineering Solutions & Innovation* (3 Innovation Cards)

**🎙️ Spoken Speech:**
> *"On Slide 6, we detail three key engineering innovations built into the platform:
> 
> - **Asynchronous Multi-Stream Ingestion:** By combining FastAPI's async event loop with Redis Pub/Sub, the system processes thousands of incoming events per second without dropping log packets.
> - **30-Day Dynamic Baseline Profiling:** Rather than comparing users against arbitrary global limits, our engine builds individual 30-day baseline vectors per user, accounting for role-specific work patterns.
> - **Sub-Second WebSocket Alert Stream:** Alerts are pushed immediately over persistent WebSockets directly to active browser sessions, reducing notification latency to less than one second."*

---

### 🟢 SLIDE 7: Measurable Security Impact & Metrics
**Visual:** Slide 7 — *Measurable Security Impact & Metrics* (4 Large Metric Callouts)

**🎙️ Spoken Speech:**
> *"Slide 7 presents the concrete performance outcomes measured in our testing environment:
> 
> - **90%+ MTTR Reduction:** Mean Time to Respond dropped from hours of manual investigation to sub-minute automated triage.
> - **4.6 Million+ Security Logs:** Successfully processed and analyzed across 30-day continuous simulation runs.
> - **1,001 Employees Tracked:** Concurrent risk scoring and baseline profiling maintained seamlessly in PostgreSQL.
> - **Sub-1 Second Alert Latency:** Real-time alert dispatching from backend anomaly detection to the SOC UI."*

---

### 🟢 SLIDE 8: Real Application Demonstration Screenshots
**Visual:** Slide 8 — *Real Application Demonstration Screenshots* (4-Panel Grid)

**🎙️ Spoken Speech:**
> *"Slide 8 highlights our live user interface across four core views:
> 1. Top Left: The **Security Dashboard** showing overall employee counts, active alerts, and 30-day activity trends.
> 2. Top Right: The **UEBA Intelligence Table** displaying real-time risk scores and anomaly breakdowns per user.
> 3. Bottom Left: The **Incident Triage Management** page for reviewing correlated security incidents.
> 4. Bottom Right: The **FastAPI Interactive API Documentation** showing OpenAPI telemetry endpoints."*

---

### 🟢 SLIDE 9: Threat Detection & ML Pipeline Workflow
**Visual:** Slide 9 — *Threat Detection & ML Pipeline Workflow* (3 Workflow Step Cards)

**🎙️ Spoken Speech:**
> *"Slide 9 outlines the step-by-step workflow of our machine learning pipeline:
> 
> - **Step 1 (Feature Extraction):** Normalizes incoming event timestamps, IP geolocations, request volumes, and data transfer sizes into a 5-dimensional feature vector.
> - **Step 2 (Anomaly Correlation):** Feeds vectors into the Isolation Forest model and computes statistical Z-score deviations against the user's historical baseline to assign a composite risk score (0 to 100).
> - **Step 3 (Playbook Containment):** Automatically correlates high-risk anomalies into incident tickets, triggers WebSocket UI alerts, and offers single-click automated mitigation actions."*

---

### 🟢 SLIDE 10: Future Roadmap & AI Enhancements
**Visual:** Slide 10 — *Future Roadmap & AI Enhancements* (3 Roadmap Cards)

**🎙️ Spoken Speech:**
> *"On Slide 10, we share our future expansion roadmap:
> 
> - **GenAI Incident Explainers:** Integrating Large Language Models to automatically generate natural-language root-cause summaries explaining complex anomaly vectors to SOC analysts.
> - **Graph Neural Network (GNN) Peer Grouping:** Deploying graph neural networks to detect cross-departmental lateral movement and multi-account insider collusion.
> - **Enterprise SOAR Connectors:** Expanding out-of-the-box webhooks for Splunk, Palo Alto Cortex XSOAR, and Microsoft Sentinel."*

---

### 🟢 SLIDE 11: Project Team & Key Contributors
**Visual:** Slide 11 — *Project Team & Key Contributors* (4 Team Role Cards)

**🎙️ Spoken Speech:**
> *"Slide 11 acknowledges our engineering team roles:
> - **Lead Security Architect:** Threat modeling, security system design, and RBAC authentication.
> - **ML & Analytics Engineer:** UEBA model development, Isolation Forest algorithm tuning, and Z-score calculation.
> - **Data Pipeline Engineer:** Asynchronous FastAPI backend microservices, Redis caching, and PostgreSQL schema design.
> - **Frontend UI/UX Specialist:** React dashboard development, real-time Recharts visualizations, and WebSocket stream integration."*

---

### 🟢 SLIDE 12: Live Application & Project Repository
**Visual:** Slide 12 — *Live Application & Project Repository* (GitHub & Localhost Links)

**🎙️ Spoken Speech:**
> *"Slide 12 provides access to our open-source codebase and live endpoints:
> - Our full project repository is hosted publicly on GitHub at **`github.com/balaji-16s/insider-threat-behavioral-intelligence-system`**.
> - The live system runs locally via Docker with the React Dashboard at `localhost:5173` and API Docs at `localhost:8000/docs`."*

---

### 🟢 SLIDE 13: Technical Discussion & Defense Topics
**Visual:** Slide 13 — *Technical Discussion & Defense Topics* (3 Discussion Cards)

**🎙️ Spoken Speech:**
> *"On Slide 13, we summarize key technical defense topics:
> - **Multi-Factor Z-Scores vs Global Limits:** By profiling individual user baselines, we avoid flagging scheduled, high-volume batch transfers performed by legitimate data engineers.
> - **Async High Throughput:** Redis Pub/Sub decouples log ingestion from model execution, preventing backend bottlenecks.
> - **Governance & Auditability:** All automated playbook actions operate with full role-based access control and immutable database logging."*

---

### 🟢 SLIDE 14: Conclusion & Q&A
**Visual:** Slide 14 — *Thank You & Q&A Slide*

**🎙️ Spoken Speech:**
> *"Thank you very much for your time and attention! We are now ready to jump into the live system demonstration and answer any questions."*

---

# PART B: Live System Demonstration Speech (Module-by-Module)

---

### 💻 MODULE 1: Authentication & Role-Based Access Control (`/login`)
**Action on Screen:** Open `http://localhost:5173/login`, show login form, enter `admin@itbis.com` / `Password123!`, click **Sign In**.

**🎙️ Spoken Speech:**
> *"We begin our live demonstration on the **Authentication & Login** page. The system enforces strict Role-Based Access Control supporting four user roles: Administrator, Security Manager, SOC Engineer, and Security Analyst.
> 
> I will sign in using our administrator account `admin@itbis.com`. Upon authentication, the FastAPI backend issues an encrypted OAuth2 JSON Web Token stored securely for session management."*

---

### 💻 MODULE 2: Executive Security Dashboard (`/`)
**Action on Screen:** Land on Dashboard main page. Hover over key metric cards (1,001 Total Employees, 4,740 Total Alerts, 4.6M Total Activity Logs). Point to 30-Day Activity Trends chart and Risk Distribution donut chart.

**🎙️ Spoken Speech:**
> *"Now we land on the **Executive Security Dashboard**. This page provides high-level situational awareness across the organization.
> 
> At a glance, we see **1,001 tracked employees**, **4,740 total alerts**, and over **4.6 million logged activity events**. 
> 
> Below, the **Activity Trends** curve plots daily log volumes over the past 30 days, while the **Risk Distribution** donut chart immediately highlights the breakdown of low, medium, and high-risk entities across the network."*

---

### 💻 MODULE 3: UEBA Intelligence Pipeline & Risk Scoring Engine (`/ueba`)
**Action on Screen:** Click **UEBA Intelligence** on the left navigation sidebar. Show the 4-step pipeline header (Behavioral Baselines -> Anomaly Detection -> Threat Assessment -> Risk Persistence). Point to total tracked users (1,001), baselines (200), open anomalies (200). Scroll down to **Consolidated UEBA Overview** table. Click **Run UEBA Pipeline** button.

**🎙️ Spoken Speech:**
> *"Next, let's navigate to the **UEBA Intelligence** module. This is the heart of our machine learning detection engine.
> 
> At the top, you see our 4-stage pipeline workflow: Baseline Profiling, Anomaly Detection, Threat Assessment, and Risk Persistence. 
> 
> In the Consolidated UEBA table below, every employee is dynamically ranked by their calculated risk score (from 0 to 100). For instance, users with high Z-score deviations across access times and data transfer volumes are flagged in yellow and red as High Risk.
> 
> When new log batches arrive from endpoint collectors, clicking **Run UEBA Pipeline** triggers background execution loops that recalculate Isolation Forest anomaly scores and update user risk persistence across the entire database in real time."*

---

### 💻 MODULE 4: Anomaly Detection Analytics & Heatmaps (`/anomalies`)
**Action on Screen:** Click **Anomaly Detection** on sidebar. Show filtering dropdowns (Severity, Anomaly Type, Date Range). Scroll through recent anomaly logs.

**🎙️ Spoken Speech:**
> *"Moving to the **Anomaly Detection** module, SOC analysts can perform deep-dive statistical analytics. 
> 
> Here, individual anomalies are categorized by type — such as *Off-Hours Login Spike*, *Unusual Resource Access*, or *Mass Data Download*. Analysts can filter events by severity level or date range to inspect specific anomalous event vectors."*

---

### 💻 MODULE 5: Incident Management & Automated Triage Playbooks (`/incidents`)
**Action on Screen:** Click **Incidents** on sidebar. Expand an incident ticket (e.g., *Escalated: Suspicious Privilege Changes*). Show event timeline and affected assets. Point to automated action buttons: **Lock Account**, **Force MFA**, **Revoke Session**. Click **Lock Account** button.

**🎙️ Spoken Speech:**
> *"Now let's examine **Incident Management**. High-severity anomalies that exceed critical risk thresholds are automatically correlated into actionable incident tickets.
> 
> Opening an incident ticket reveals the full chronological timeline of events, affected IP addresses, and targeted data repositories.
> 
> More importantly, our platform provides built-in automated mitigation playbooks. Rather than waiting for manual intervention, an analyst can click **Lock Account**, **Force MFA**, or **Revoke Active Sessions** to instantly isolate a compromised user directly from the UI."*

---

### 💻 MODULE 6: FastAPI Asynchronous Microservices & OpenAPI Docs (`http://localhost:8000/docs`)
**Action on Screen:** Open new browser tab to `http://localhost:8000/docs`. Scroll through Swagger API endpoint categories (`/auth`, `/users`, `/ueba`, `/anomalies`, `/incidents`). Expand `POST /api/v1/ueba/run-pipeline`.

**🎙️ Spoken Speech:**
> *"To inspect our backend architecture, we open the **FastAPI OpenAPI Swagger Documentation** at port 8000.
> 
> All microservices — including authentication, user management, UEBA pipeline triggers, and incident triage — are exposed via fully documented, asynchronous RESTful endpoints. The backend runs asynchronously to handle high concurrency and low latency."*

---

### 💻 MODULE 7: Docker Multi-Container Architecture (`itbis_backend`, `itbis_frontend`, `itbis_postgres`, `itbis_redis`)
**Action on Screen:** Show terminal window with `docker ps` command output displaying active containers.

**🎙️ Spoken Speech:**
> *"Finally, here in our terminal, running `docker ps` confirms our multi-container infrastructure. Four microservices operate in sync:
> 1. `itbis_backend`: FastAPI Python server
> 2. `itbis_frontend`: React + Vite web dashboard
> 3. `itbis_postgres`: PostgreSQL audit database
> 4. `itbis_redis`: In-memory cache & WebSocket Pub/Sub stream
> 
> This completes our live system demonstration. Thank you!"*
