<div align="center">
  <h1>🚨 AI-Based Disaster Response Management System</h1>
  <h3>Resource Allocation & Relief Coordination (Disaster Bridge)</h3>
  <p><strong>Springboard Internship 2026 Project</strong></p>
</div>

<br />

## 📖 Overview

**Disaster Bridge** is an intelligent, AI-driven logistics and coordination platform built to streamline and optimize disaster response. During critical emergencies, response times and resource allocations mean the difference between life and death. 

This platform automatically ingests live global disaster alerts (from GDACS, USGS, NDMA), utilizes machine learning models to predict ground-level resource demand (food, water, medical kits, shelter), and orchestrates optimal supply routes using Google OR-Tools and OpenStreetMap (OSRM) data. 

---

## ✨ Key Features

- **📡 Live Incident Ingestion**: Automatically pulls and standardizes live earthquake, flood, and cyclone alerts.
- **🧠 AI Resource Prediction**: Machine learning (Random Forest model) estimates exact quantities of survival supplies required based on event severity and affected population.
- **🗺️ Intelligent Routing**: Calculates the fastest delivery routes from supply depots to disaster zones, avoiding blocked roads.
- **📊 Premium Analytics Dashboard**: Real-time KPI tracking, coverage achievement percentages, and average delivery response times with zero-whitespace premium UI.
- **📄 Automated PDF Reporting**: Instantly generate professional, branded Post-Event PDF reports using `jsPDF` for stakeholder updates.
- **🔐 Secure Role-Based Access**: Complete JWT-based authentication system for Field Commanders and Volunteers.

---

## 🛠️ Tech Stack

**Frontend:**
- React 18, TypeScript, Vite
- Tailwind CSS (Premium styling, gradients, micro-animations)
- Recharts (Data visualization)
- Leaflet / React-Leaflet (Live map rendering)
- jsPDF & AutoTable (Report generation)

**Backend:**
- Python 3.10+, FastAPI
- PostgreSQL + PostGIS (Geospatial data handling)
- SQLAlchemy & Alembic (ORM & Migrations)
- Scikit-learn (Random Forest ML predictions)
- Google OR-Tools (Logistics optimization)

---

## 🚀 Local Setup & Installation

### 1. Database Requirements
Ensure you have **PostgreSQL 14+** installed. You must install the **PostGIS** extension to support geographic coordinates and radius calculations.

```sql
CREATE DATABASE postgres;
\c postgres
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. Backend Initialization
The backend is powered by FastAPI. Navigate to the `backend` directory:

```bash
cd backend
python -m venv venv

# Activate Virtual Environment
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt

# Run Database Migrations
alembic upgrade head

# Start the API Server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*API will run on: `http://localhost:8000` (Visit `/docs` for Swagger UI).*

### 3. Frontend Initialization
The frontend is built with Vite & React. Navigate to the `frontend` directory in a new terminal:

```bash
cd frontend
npm install
npm run dev
```
*Web App will run on: `http://localhost:5173`.*

---

## ⚙️ Triggering the Pipeline (First Run)
On your first run, the database will be empty. To populate the map, you need to ingest live disaster data and create supply depots.

1. **Ingest GDACS Events:**
   ```bash
   curl -X POST http://localhost:8000/api/ingest/gdacs/sync
   ```
2. **Ingest USGS Events:**
   ```bash
   curl -X POST http://localhost:8000/api/ingest/usgs/sync
   ```
3. **Register a Supply Depot:**
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"resource_type": "water", "quantity": 10000, "unit": "liters", "lat": 28.6139, "lng": 77.2090, "depot_name": "Delhi Central Base"}' http://localhost:8000/api/resources
   ```
4. Log in to the frontend Dashboard to view predictions, generate missions, and view the AI's resource routing!

---

## 👨‍💻 Developed By
**Piyush Patil**  
*Built for the Springboard AI-Based Disaster Response Management System Internship (July 2026).*
