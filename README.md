# 🌍 DisasterShieldAI

> **An AI-powered Disaster Response Coordination Agent built using Google Agent Development Kit (ADK) and Gemini 3.5 Flash.**

---

## 📌 Overview

DisasterShieldAI is an intelligent emergency response assistant that analyzes disaster reports and instantly generates a coordinated disaster response plan.

The agent identifies the disaster type, estimates its severity, calculates required emergency resources, recommends temporary shelters, assigns a response priority level, and provides actionable public safety recommendations.

The goal is to assist disaster management authorities in making faster and more informed decisions during emergencies.

---

## 🚀 Features

- 🌊 Detects multiple disaster types
  - Flood
  - Earthquake
  - Fire
  - Cyclone
  - Landslide
  - Chemical Leak
  - Heatwave
  - Tsunami
  - Building Collapse
  - Industrial Accident

- 📊 Estimates
  - Disaster severity
  - Affected population

- 🚑 Calculates emergency resources
  - Food kits
  - Medical kits
  - Rescue teams
  - Ambulances
  - Doctors
  - Volunteers
  - Boats
  - Helicopters
  - Fire engines

- 🏫 Recommends shelter plans
  - Shelter type
  - Number of shelters
  - Required capacity

- 🚨 Assigns response priority
  - 🔴 Critical
  - 🟠 High
  - 🟡 Medium
  - 🟢 Low

- 📋 Generates a complete Disaster Response Report

---

# 🛠 Tech Stack

| Category | Technology |
|-----------|------------|
| Language | Python 3.13 |
| AI Framework | Google Agent Development Kit (ADK) |
| LLM | Gemini 3.5 Flash |
| Backend | Python |
| Environment | PowerShell / Windows |
| Version Control | Git & GitHub |

---

# 📂 Project Structure

```
DisasterShieldAI
│
├── disaster_shield_ai
│   │
│   ├── agent.py
│   ├── __init__.py
│   │
│   ├── tools
│   │   ├── incident_tool.py
│   │   ├── resource_tool.py
│   │   ├── shelter_tool.py
│   │
│   └── .env
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# ⚙️ How It Works

The AI agent follows the workflow below:

```
User Disaster Report
          │
          ▼
Analyze Incident Tool
          │
          ▼
Identify
• Disaster Type
• Severity
• Population
          │
          ▼
Resource Calculation Tool
          │
          ▼
Shelter Recommendation Tool
          │
          ▼
Gemini AI
          │
          ▼
Disaster Response Report
```

---

# 📋 Sample Input

```
Flood in Howrah.
500 people stranded.
Roads blocked.
```

---

# 📋 Sample Output

```
Disaster Type: Flood

Severity: High

Priority Level: 🔴 Critical

Affected Population: 500

Resources Required

• Food Kits: 500
• Medical Kits: 500
• Rescue Teams: 5
• Ambulances: 10
• Doctors: 5
• Volunteers: 20
• Boats: 3

Shelter Recommendation

Government School
2 Shelters
Capacity: 500

Emergency Response Plan

• Evacuate stranded civilians
• Deploy rescue boats
• Set up medical camps
• Distribute relief materials
• Activate temporary shelters

Public Safety Recommendations

• Avoid floodwaters
• Move to higher ground
• Drink boiled water
• Follow official advisories
```

---

# ▶️ Installation

Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/DisasterShieldAI.git
```

Go inside the project

```bash
cd DisasterShieldAI
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env` file

```env
GOOGLE_API_KEY=YOUR_API_KEY
```

Run the ADK Web Interface

```bash
adk web
```

Open

```
http://127.0.0.1:8000
```

---

# 📸 Demo

https://youtu.be/ZPION3SMUp0

---

# 📷 Screenshots

<img width="1920" height="908" alt="Introduction" src="https://github.com/user-attachments/assets/b9d6ad32-c343-441c-a57e-68b547c4d28d" />

<img width="1920" height="912" alt="Chemical Leak Sample" src="https://github.com/user-attachments/assets/0821eba4-ab7e-4cb1-8137-8f766c61ca6f" />

<img width="1920" height="907" alt="Flood Sample" src="https://github.com/user-attachments/assets/68659be6-21a2-42b6-9776-4f6d104c9e77" />

---

# 🎯 Future Improvements

- Live weather API integration
- GIS map visualization
- SMS and Email emergency alerts
- Hospital availability tracking
- Real-time shelter occupancy
- Multi-language support
- Disaster prediction using ML models
- Integration with government emergency services

---

# 👩‍💻 Developed By

**Somoshree Pal**

_ECE Undergraduate_


---

# 📜 License

This project is licensed under the MIT License.
