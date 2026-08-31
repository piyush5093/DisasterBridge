# Disaster Bridge
**Disaster Resource Allocation & Relief Coordination**

Disaster Bridge is an AI-powered logistics platform that automatically ingests disaster alerts (GDACS, USGS, NDMA), predicts ground-level resource demand using machine learning, and orchestrates optimal supply routes via OR-Tools and OSRM.

## Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** with the **PostGIS** extension enabled.

## Setup Instructions

### 1. Database Setup
Ensure PostgreSQL is running on `localhost:5432` with user `postgres` and password `postgres` (or update the `.env` / connection string).
Create the database and enable PostGIS:
```sql
CREATE DATABASE postgres;
\c postgres
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 2. Backend Setup
Navigate to the `backend` directory, create a virtual environment, install dependencies, and run migrations:
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# Run migrations to create tables
alembic upgrade head

# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000
```
The backend will run on `http://localhost:8000`.

### 3. Frontend Setup
In a new terminal, navigate to the `frontend` directory and install NPM packages:
```bash
cd frontend
npm install
npm run dev
```
The frontend will run on `http://localhost:5173`.

## First Run (Populating Demo Data)
On your very first run, the database will be completely empty. To populate the map and trigger the workflow, you must ingest disaster events and classify zones via the API.
With the backend running, open a terminal and run:
```bash
# 1. Ingest events from GDACS
curl -X POST http://localhost:8000/api/ingest/gdacs/sync

# 2. Ingest events from USGS
curl -X POST http://localhost:8000/api/ingest/usgs/sync

# 3. Create dummy resource depots
curl -X POST -H "Content-Type: application/json" -d '{"resource_type": "water", "quantity": 10000, "unit": "liters", "lat": 35.6, "lng": 139.7, "depot_name": "Tokyo Base"}' http://localhost:8000/api/resources
```
You can now open the UI at `http://localhost:5173` and view the active incidents and dashboard.

## Known Limitations / "Coming Soon"
The following UI modules are currently under active development and have functional backend counterparts but no React screens yet:
- Volunteers
- Relief Map
- Settings
