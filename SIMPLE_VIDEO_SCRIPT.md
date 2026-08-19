# Insider Threat System — Simple 5-Minute Presentation Script

---

## 📽️ PART 1: Slide Presentation Script (Slides 1 – 14)

### Slide 1: Title Cover
> *"Hello everyone! Welcome to our presentation on the **Insider Threat Behavioral Intelligence System**. This project uses AI to detect and stop security threats inside a company network in real time."*

---

### Slide 2: Technology Stack
> *"Here is the tech stack we used. On the backend, we use **FastAPI** and **Redis** for fast data processing. On the frontend, we built a clean dashboard using **React and Vite**. We also use **PostgreSQL** to save data and **Docker** to run everything easily."*

---

### Slide 3: Core Features
> *"Our system has four main features:
> 1. It collects user activity logs continuously.
> 2. It uses Machine Learning to spot suspicious behavior.
> 3. It gives every user a risk score from 0 to 100.
> 4. It can automatically lock accounts or force MFA when a threat is found."*

---

### Slide 4: Problem Statement
> *"Why did we build this? Old security tools rely on fixed rules, so they miss clever insider threats. They also send thousands of false alerts, which confuses security teams and wastes time."*

---

### Slide 5: System Architecture
> *"This is our system architecture diagram. Logs come in from endpoints, get processed by FastAPI and Redis, run through our ML engine, and show up live on our React dashboard."*

---

### Slide 6: Engineering Solutions
> *"To solve these issues, our backend handles thousands of logs per second without slowing down. We calculate a 30-day baseline for each user, and we send live alerts to the dashboard in less than a second."*

---

### Slide 7: Measurable Impact
> *"Looking at our results: we reduced incident response time by over 90%. Our system successfully tested over 4.6 million logs across 1,001 tracked employees."*

---

### Slide 8: Real Screenshots
> *"Here are real screenshots from our running app: the Security Dashboard, the UEBA Intelligence table, the Incident Triage page, and our FastAPI API documentation."*

---

### Slide 9: ML Detection Workflow
> *"Our ML engine works in three simple steps: First, it extracts user activity features. Second, it calculates Z-scores and anomaly scores. Third, it triggers automated playbooks for high-risk threats."*

---

### Slide 10: Future Roadmap
> *"In the future, we plan to add AI summaries for incident reports, Graph Neural Networks to catch insider groups working together, and integrations with bigger enterprise tools."*

---

### Slide 11: Team Roles
> *"Our team worked across four roles: Security Architecture, Machine Learning, Data Pipeline Engineering, and Frontend UI Design."*

---

### Slide 12: GitHub & Links
> *"You can find our full project code on GitHub at **`github.com/balaji-16s/insider-threat-behavioral-intelligence-system`**. Our dashboard runs locally on port 5173 and API docs run on port 8000."*

---

### Slide 13: Technical Discussion
> *"In summary: our system tracks individual behavior instead of rigid limits, handles high log volume smoothly, and keeps full audit logs for security."*

---

### Slide 14: Conclusion & Q&A
> *"Thank you for listening! We are happy to answer any questions now."*

---

## 💻 PART 2: Live Application Demo Script (Short & Simple)

### 1. Login Screen (`/login`)
> *"First, we log in using our admin account `admin@itbis.com` with password `Password123!`."*

### 2. Security Dashboard (`/`)
> *"On the dashboard, we see 1,001 tracked employees, 4.6 million activity logs, and our daily activity charts."*

### 3. UEBA Intelligence (`/ueba`)
> *"On the UEBA page, every employee gets a risk score from 0 to 100. Clicking **'Run UEBA Pipeline'** updates all risk scores live."*

### 4. Incidents Page (`/incidents`)
> *"On the Incidents page, high-risk alerts turn into tickets. We can click **'Lock Account'** to stop a threat instantly."*

### 5. API Documentation (`:8000/docs`)
> *"Finally, here are our interactive FastAPI docs showing all our backend endpoints."*
