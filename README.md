# HealthAI — AI-Driven Health Platform

> Built for the Healthcare Hackathon 2025 · Problem Statement: Build AI-driven health-tech solutions that enhance healthcare delivery, patient engagement, and health literacy.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open in browser
http://localhost:5000
```

### Demo Account
- **Email:** demo@healthai.com  
- **Password:** demo1234

> A demo account with pre-loaded medications, symptom logs, and health data is auto-created on first run.

---

## 📦 Project Structure

```
healthai/
├── app.py                    # Flask app factory + config
├── models.py                 # SQLAlchemy DB models
├── requirements.txt
├── routes/
│   ├── auth.py               # Login / Signup / Logout
│   ├── dashboard.py          # Central hub + health score engine
│   ├── health_check.py       # Symptom checker + report analyzer
│   ├── medications.py        # Medication tracker + adherence
│   ├── emergency.py          # Emergency SOS + appointments
│   ├── profile.py            # Profile settings + document vault
│   └── api.py                # Chatbot AI engine
├── templates/
│   ├── base.html             # Base layout (navbar, chatbot FAB)
│   ├── index.html            # Landing page
│   ├── dashboard.html        # Dashboard
│   ├── health_check.html     # Health Check tools
│   ├── medications.html      # Medication management
│   ├── emergency.html        # Emergency & appointments
│   ├── profile.html          # Profile & document vault
│   └── auth/
│       ├── login.html
│       └── signup.html
├── static/
│   └── css/
│       └── main.css          # Full clinical design system
└── uploads/                  # User-uploaded files (auto-created)
```

---

## ✨ Features

### 1. 🏠 Landing Page
- Hero section with platform tagline and CTA
- Feature cards, stats, about section
- Responsive for all screen sizes

### 2. 🔐 Authentication
- Email/password signup & login
- Flask-Login session management
- Bcrypt password hashing

### 3. 📊 Dashboard (Central Hub)
- **Health Score** — computed from medication adherence, BMI, and symptom history
- **Alerts panel** — actionable AI-generated alerts
- **Score trend chart** — Chart.js line graph of historical scores
- **Medication quick-log** — mark taken/missed from dashboard
- **Symptom timeline** — chronological log
- **AI Memory panel** — pattern-based insights
- **Quick Actions** — jump to any feature instantly

### 4. 🩺 Health Check Tools
- **Symptom Checker** — AI rule-based engine with:
  - Condition probability scoring
  - Urgency triage (Low → Emergency)
  - Personalized recommendations
  - Quick-add symptom chips
- **Report Analyzer** — Upload PDF/image, get:
  - Key metric extraction
  - Normal/borderline/abnormal flags
  - AI recommendation

### 5. 💊 Smart Medication Management
- Add medications (name, dosage, frequency, timing, dates)
- Daily take/miss logging
- 7-day stacked bar chart (Chart.js)
- 30-day adherence percentage gauge
- AI behavior pattern insights

### 6. ⚡ Emergency & Quick Actions
- **Emergency SOS** — One-tap call to 112/108 with pulsing button
- **User emergency card** — Blood group, allergies, emergency contact
- **Health summary** — View + copy full health profile
- **Doctor booking** — Specialty selection with AI recommendations
- **Appointment management** — List + cancel appointments

### 7. 👤 Profile & Document Vault
- Personal info (age, gender, blood group, height, weight)
- Auto-calculated BMI with category
- Known allergies + chronic conditions
- Emergency contacts + caregiver email
- **Document Vault** — upload/delete health documents (prescriptions, reports, insurance, etc.)
- Profile completion tracker with hints

### 8. 🤖 AI Chatbot
- Floating chat button on all authenticated pages
- Rule-based NLP engine covering:
  - Medication queries
  - Symptom guidance
  - Health score insights
  - Emergency guidance
  - Nutrition, exercise, sleep, stress tips
  - Blood pressure, diabetes advice
- Full chat history logged to DB

---

## 🗄️ Database Schema

| Table | Description |
|-------|-------------|
| `users` | User accounts + health profile |
| `symptom_logs` | Symptom checks with AI analysis |
| `medications` | Active/past medications |
| `medication_logs` | Daily taken/missed logs |
| `report_logs` | Uploaded report analyses |
| `documents` | Health document vault |
| `health_scores` | Historical AI health scores |
| `appointments` | Doctor appointments |
| `chat_logs` | AI chatbot conversation history |

---

## 🎨 Design System

- **Theme:** Clinical Light Mode
- **Fonts:** Playfair Display (headings) + DM Sans (body) + DM Mono (numbers)
- **Colors:** Primary Blue #1A5CFF · Teal #00B8A9 · Clinical whites and grays
- **CSS Variables:** Full design token system
- **Components:** Cards, badges, buttons, forms, timeline, score ring, chatbot window
- **Framework:** Bootstrap 5.3 + custom clinical CSS

---

## 🧠 AI Engine

The AI decision engine is rule-based (no external API required):

- **Symptom Analysis** — keyword matching → condition mapping → urgency triage
- **Health Score** — weighted formula: adherence (40%) + BMI (30%) + symptom load (30%)
- **Chatbot** — intent detection → contextual response generation
- **Behavior Detection** — adherence pattern analysis with alerts

---

## 📋 Hackathon Alignment

| Problem Statement | Implementation |
|---|---|
| Enhance healthcare delivery | AI symptom checker + report analyzer |
| Patient engagement | Daily medication logging + health score gamification |
| Health literacy | AI explanations, condition info, recommendations |
| Emergency response | One-tap SOS + health summary sharing |
| Behavior patterns | 30-day adherence tracking + AI insights |

---

*Built with ❤️ for Healthcare Hackathon 2025*