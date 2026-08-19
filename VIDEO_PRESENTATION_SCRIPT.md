# Insider Threat Intelligence & UEBA System — Full Video Presentation Transcript

**Total Video Duration:** 5:30 – 6:00 Minutes  
**Format:** Slide Deck Walkthrough + Live Software Demonstration  
**Presenter:** Lead Security Architect / Developer  

---

## 🎬 Video Recording Structure & Telemetry Guide

```
+-----------------------------------------------------------------------------------+
| 0:00 - 2:00  | PART 1: Slide Presentation (Slides 1 - 7)                          |
| 2:00 - 4:15  | PART 2: Live System Demonstration (Dashboard, UEBA, Incidents, API)  |
| 4:15 - 5:45  | PART 3: Detection Engine, AI Roadmap, Contributors & Conclusion    |
+-----------------------------------------------------------------------------------+
```

---

## ⏱️ Detailed Segment Schedule

| Time | Slide / Screen View | Onscreen Action | Spoken Topic / Narrative |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:30** | Slide 1: Cover | Title Screen | Welcome, Project Name & Vision |
| **0:30 – 1:00** | Slide 2 – 3 | Tech Stack & Core Features | Architecture stack (FastAPI, Redis, Postgres, React) |
| **1:00 – 1:30** | Slide 4 – 5 | Challenges & System Diagram | SIEM limitations, 4-tier decoupled pipeline |
| **1:30 – 2:00** | Slide 6 – 7 | Engineering Solutions & Metrics | MTTR reduction (90%+), 4.6M logs processed |
| **2:00 – 2:40** | Live Dashboard (`:5173`) | Hover on metrics & charts | 1,001 employees, 4.6M logs, activity trend curve |
| **2:40 – 3:20** | Live UEBA (`/ueba`) | Click "Run UEBA Pipeline" | Risk scores (0-100), Z-score, Isolation Forest |
| **3:20 – 3:55** | Live Incidents (`/incidents`) | Expand Incident & Playbooks | Incident escalation, lock account & revoke session |
| **3:55 – 4:15** | Live API Docs (`:8000/docs`) | Scroll Swagger UI | FastAPI async endpoints & JWT security |
| **4:15 – 4:45** | Slide 9 – 10 | Workflow & AI Roadmap | GenAI Incident Explainer & Graph Neural Networks |
| **4:45 – 5:30** | Slide 11 – 14 | Contributors & GitHub | Team roles, GitHub URL, Q&A & Wrap up |

---

## 🎙️ Complete Word-for-Word Voiceover Script

### PART 1: SLIDE PRESENTATION WALKTHROUGH (0:00 – 2:00)

#### Slide 1: Title Slide (0:00 – 0:30)
* **Visual:** Slide 1 ("Insider Threat Intel System — AI-POWERED UEBA PLATFORM")
* **Audio Voiceover:**
> *"Hello everyone! Welcome to our demonstration of the **Insider Threat Behavioral Intelligence System** — an enterprise-grade User and Entity Behavior Analytics (UEBA) platform engineered to detect, prioritize, and automatically mitigate insider threats in real time."*

---

#### Slide 2 & 3: Tech Stack & Core Capabilities (0:30 – 1:00)
* **Visual:** Slide 2 (Architecture Stack) & Slide 3 (Core Features)
* **Audio Voiceover:**
> *"Enterprise cybersecurity faces a major challenge today: traditional SIEM tools rely on rigid signature rules that miss low-and-slow data exfiltration while flooding SOC teams with thousands of false positives.  
> Our solution combines asynchronous data ingestion with continuous machine learning anomaly detection. Built on a modern tech stack featuring **FastAPI**, **Redis**, **PostgreSQL**, and **React with Vite**, our platform calculates dynamic risk scores from 0 to 100 for every employee across the organization."*

---

#### Slide 4 & 5: Challenges & System Architecture (1:00 – 1:30)
* **Visual:** Slide 4 (Challenges) & Slide 5 (System Architecture Diagram)
* **Audio Voiceover:**
> *"Here on Slide 5, you can see our decoupled system architecture operating across four stages:
> 1. **Data Ingestion**: Streaming high-volume user activity telemetry.
> 2. **FastAPI & Redis Backend**: Managing JWT authentication, session caching, and WebSocket alert dispatching.
> 3. **ML Anomaly Engine**: Evaluating Isolation Forest outlier models and statistical Z-scores against a 30-day baseline.
> 4. **React SOC Dashboard**: Delivering real-time alert pushes and interactive risk heatmaps directly to security analysts."*

---

#### Slide 6 & 7: Engineering Solutions & Impact (1:30 – 2:00)
* **Visual:** Slide 6 (Key Challenges) & Slide 7 (Measurable Outcomes)
* **Audio Voiceover:**
> *"By correlating security logs across historical baselines, we achieved over a **90% reduction in Mean Time to Respond (MTTR)** — enabling security operations centers to transition from reactive log hunting to automated, sub-minute threat containment."*

---

### PART 2: LIVE APPLICATION DEMONSTRATION (2:00 – 4:15)

**[ACTION: Switch screen recording to Browser Window at `http://localhost:5173`]**

#### 1. Security Dashboard (2:00 – 2:40)
* **Visual:** Main Dashboard screen at `http://localhost:5173`
* **Audio Voiceover:**
> *"Now, let's step into the live running application.  
> Here on our **Security Dashboard**, we have real-time oversight of **1,001 active employees** and **over 4.6 million log events**.  
> The dashboard presents our 30-day Activity Trends curve alongside the Risk Distribution breakdown, instantly highlighting high-risk assets and open security alerts."*

---

#### 2. UEBA Intelligence Pipeline (2:40 – 3:20)
* **Visual:** Click "UEBA Intelligence" on sidebar (`http://localhost:5173/ueba`)
* **Audio Voiceover:**
> *"Navigating to **UEBA Intelligence**, we see our 4-step processing pipeline: Behavioral Baselines, Anomaly Detection, Threat Assessment, and Risk Persistence.  
> In the Consolidated UEBA table below, employees are ranked dynamically by their calculated risk score. When new log batches arrive, clicking **Run UEBA Pipeline** triggers background execution loops that update Isolation Forest anomaly vectors and recalculate risk scores across the entire entity database."*

---

#### 3. Incident Management & Automated Triage (3:20 – 3:55)
* **Visual:** Click "Incidents" on sidebar (`http://localhost:5173/incidents`)
* **Audio Voiceover:**
> *"Moving to **Incidents**, high-severity anomalies are automatically bundled into actionable incident tickets — such as 'Suspicious Privilege Escalation' or 'Abnormal Data Volume Exfiltration'.  
> SOC analysts can inspect event timelines, analyze affected resources, and trigger automated playbook mitigations like **Lock Account**, **Force MFA**, or **Revoke Active Sessions** with a single click."*

---

#### 4. FastAPI Interactive API Telemetry (3:55 – 4:15)
* **Visual:** Switch tab to `http://localhost:8000/docs` (Swagger UI)
* **Audio Voiceover:**
> *"Under the hood, our backend exposes an interactive **FastAPI Swagger interface**. All microservices — from OAuth authentication and risk scoring to WebSocket notifications — run asynchronously in containerized Docker microservices for enterprise readiness."*

---

### PART 3: THREAT WORKFLOW, ROADMAP & CONCLUSION (4:15 – 5:45)

**[ACTION: Switch screen recording back to Presentation Slides]**

#### Slide 9 & 10: Detection Workflow & AI Roadmap (4:15 – 4:45)
* **Visual:** Slide 9 (Detection Workflow) & Slide 10 (Future Roadmap)
* **Audio Voiceover:**
> *"Looking ahead, our technology roadmap includes:
> - **GenAI Incident Explainers**: Automatically generating natural-language root-cause summaries for SOC analysts.
> - **Graph Neural Network Peer Grouping**: Deploying graph clustering to uncover lateral movement and multi-account insider collusion."*

---

#### Slide 11 & 12: Contributors & GitHub Repository (4:45 – 5:15)
* **Visual:** Slide 11 (Contributors) & Slide 12 (Live App & GitHub Link)
* **Audio Voiceover:**
> *"Our platform was developed by a team spanning security architecture, ML analytics, backend data pipelines, and UI/UX.  
> You can access the complete source code, installation guides, and Docker setup on our GitHub repository at:  
> **`github.com/balaji-16s/insider-threat-behavioral-intelligence-system`**."*

---

#### Slide 13 & 14: Questions & Thank You (5:15 – 5:30)
* **Visual:** Slide 13 (Q&A) & Slide 14 (Thank You)
* **Audio Voiceover:**
> *"Thank you for watching! We are now open for any questions or live feedback."*

---

## 🎯 Technical Q&A Defense Quick Guide

If asked questions during or after the video presentation:

1. **Q: How does your system differentiate between normal workload spikes and insider threats?**  
   * **A:** *"We calculate z-scores against each individual user's 30-day historical baseline rather than static global thresholds. If a user regularly transfers large files on Mondays, that behavior is part of their baseline and won't trigger false alarms."*

2. **Q: What machine learning models are used?**  
   * **A:** *"We combine Isolation Forest for multi-dimensional outlier detection with statistical Z-Score metrics across five behavioral factors: access time, request volume, data size, IP risk, and privilege level."*

3. **Q: How does the system handle high log throughput?**  
   * **A:** *"We use an asynchronous FastAPI backend paired with Redis in-memory caching and Pub/Sub streaming, allowing the system to process thousands of events per second with sub-second WebSocket notification delivery."*
