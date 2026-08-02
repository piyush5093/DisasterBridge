# 🚨 AI Disaster Response System — Project Flowchart & Structure

## 🗂️ Project Folder Structure

```
📁 Infosys Springboard 7.0/
│
├── 📁 frontend/                    ← React.js + Leaflet.js Dashboard
│   ├── 📁 public/
│   └── 📁 src/
│       ├── 📁 components/
│       │   ├── 📁 Map/             ← Leaflet map component
│       │   ├── 📁 Dashboard/       ← Stat cards, charts
│       │   ├── 📁 Alerts/          ← Live alerts panel
│       │   ├── 📁 ResourceCards/   ← Food, Medical, Transport cards
│       │   └── 📁 FieldTeams/      ← Team status tracker
│       ├── 📁 pages/               ← Route pages
│       ├── 📁 services/            ← API calls to backend
│       ├── 📁 hooks/               ← Custom React hooks
│       └── 📁 utils/               ← Helper functions
│
├── 📁 backend/                     ← FastAPI Python Server
│   ├── 📁 app/
│   │   ├── 📁 api/routes/          ← API endpoints
│   │   ├── 📁 models/              ← DB models (SQLAlchemy)
│   │   ├── 📁 schemas/             ← Pydantic schemas
│   │   ├── 📁 services/            ← Business logic
│   │   ├── 📁 core/                ← Config, security
│   │   └── 📁 db/                  ← Database connection
│   └── 📁 tests/
│
├── 📁 ml_engine/                   ← Machine Learning
│   ├── 📁 data/
│   │   ├── 📁 raw/                 ← Raw disaster datasets
│   │   └── 📁 processed/           ← Cleaned, feature-engineered
│   ├── 📁 notebooks/               ← Jupyter notebooks
│   ├── 📁 models/saved/            ← Trained .pkl model files
│   ├── 📁 scripts/                 ← Training scripts
│   └── 📁 evaluation/              ← Model evaluation reports
│
├── 📁 database/                    ← PostgreSQL + PostGIS
│   ├── 📁 migrations/              ← Alembic migration files
│   ├── 📁 seeds/                   ← Initial data
│   └── 📁 schemas/                 ← SQL schema definitions
│
├── 📁 optimizer/                   ← OR-Tools Optimizer
│   ├── 📁 algorithms/              ← LP/ILP algorithms
│   └── 📁 tests/
│
├── 📁 data_ingestion/              ← External API Connectors
│   ├── 📁 feeds/                   ← GDACS, USGS, NDMA feeds
│   ├── 📁 parsers/                 ← Data parsers
│   └── 📁 connectors/              ← API connector classes
│
├── 📁 docs/                        ← Documentation
│   ├── 📁 architecture/
│   ├── 📁 api_reference/
│   ├── 📁 flowcharts/
│   └── 📁 deployment/
│
├── 📁 tests/                       ← Integration & E2E Tests
├── 📁 scripts/                     ← Utility scripts
├── 📁 config/                      ← App configuration files
│
├── 📄 disaster_demo.html           ← Current UI Prototype ✅
├── 📄 docker-compose.yml           ← Docker services
├── 📄 .env.example                 ← Environment variables template
├── 📄 .gitignore
└── 📄 README.md
```

---

## 🔄 System Flowchart

```mermaid
flowchart TD
    %% =========== EXTERNAL DATA SOURCES ===========
    subgraph SOURCES["🌐 External Data Sources"]
        GDACS["📡 GDACS API\n(Global Disasters)"]
        USGS["🌍 USGS API\n(Earthquakes)"]
        NDMA["🏛️ NDMA API\n(India Alerts)"]
        SAT["🛰️ Satellite Imagery\n(ISRO / Sentinel-2)"]
        OSM["🗺️ OpenStreetMap\n(Building footprints)"]
    end

    %% =========== DATA INGESTION ===========
    subgraph INGEST["📥 Module 1: Data Ingestion & Geospatial Assessment"]
        FEED["Feed Aggregator\n(data_ingestion/feeds)"]
        PARSE["Data Parser\n(data_ingestion/parsers)"]
        GEO["Geospatial Impact Assessor\nFlood/Earthquake extent +\nPopulation density rasters"]
        ZONE["Zone Classifier\nGrid cells + Severity scores\n(Critical / High / Medium / Low)"]
        POSTGIS[("🗄️ PostGIS DB\nZones, Depots,\nField Records")]
    end

    %% =========== ML ENGINE ===========
    subgraph ML["🤖 Module 2: Resource Demand Prediction Engine"]
        HIST["Historical Data\n(Kerala 2018, Chennai 2015)"]
        TRAIN["Regression Model\nTraining (Scikit-learn)"]
        VUL["Vulnerability Weighting\n(Elderly, Children,\nMedically dependent)"]
        PRED["Demand Predictor\nFood / Water / Medical /\nShelter per zone"]
        CONF["Confidence Intervals\n87% accuracy"]
        FASTAPI["⚡ FastAPI Endpoint\n/api/predict/demand"]
    end

    %% =========== OPTIMIZER ===========
    subgraph OPT["⚙️ Module 3: Logistics & Optimization"]
        DEPOT["Resource Depots\n(Delhi, Mumbai, Hyderabad)"]
        ORTOOLS["OR-Tools Optimizer\nLinear Programming\nMax coverage with constraints"]
        ROUTE["Routing Engine\nOptimal delivery routes\n(Post-disaster road access)"]
        OVERRIDE["Priority Override\n(Commander can manually\nelevate zone priority)"]
    end

    %% =========== DASHBOARD ===========
    subgraph DASH["🖥️ Module 3: Command Dashboard (Frontend)"]
        MAP["🗺️ Leaflet.js Map\nReal-time impact zones\nResource depot markers"]
        STATS["📊 Stat Cards\nPeople Affected\nTeams Deployed\nResource Coverage"]
        ALERTS["🔔 Live Alerts\nCritical / Warning /\nInfo / OK"]
        TEAMS["👥 Field Teams\nDeployed / Transit / Standby"]
        ACTIONS["⚡ Quick Actions\nEmergency Dispatch\nRun AI Optimizer\nSituation Report"]
    end

    %% =========== FIELD ===========
    subgraph FIELD["📱 Field Operations"]
        MOBILE["Mobile-friendly\nMission Assignments"]
        MANIFEST["Supply Manifests\n(What to carry)"]
        NAV["Navigation Support\n(Optimized routes)"]
    end

    %% =========== REPORTING ===========
    subgraph REPORT["📋 Post-Event Analytics"]
        SITREP["Situation Reports\n(PDF generation)"]
        DONOR["Donor Accountability\nReports"]
        PLAN["Future Preparedness\nPlanning"]
    end

    %% =========== CONNECTIONS ===========
    GDACS --> FEED
    USGS --> FEED
    NDMA --> FEED
    SAT --> FEED
    OSM --> GEO

    FEED --> PARSE --> GEO --> ZONE --> POSTGIS

    HIST --> TRAIN --> VUL --> PRED --> CONF --> FASTAPI
    POSTGIS --> PRED

    FASTAPI --> ORTOOLS
    DEPOT --> ORTOOLS
    ORTOOLS --> ROUTE
    OVERRIDE --> ORTOOLS
    ROUTE --> DASH

    POSTGIS --> MAP
    FASTAPI --> STATS
    FASTAPI --> ALERTS
    ROUTE --> TEAMS

    TEAMS --> MOBILE --> MANIFEST --> NAV

    DASH --> ACTIONS
    ACTIONS --> MOBILE
    ACTIONS --> ORTOOLS

    DASH --> REPORT
    REPORT --> SITREP
    REPORT --> DONOR
    REPORT --> PLAN

    %% =========== STYLES ===========
    style SOURCES fill:#0b1628,stroke:#00c8ff,color:#e8f4fd
    style INGEST  fill:#0b1628,stroke:#ffd32a,color:#e8f4fd
    style ML      fill:#0b1628,stroke:#00ffcc,color:#e8f4fd
    style OPT     fill:#0b1628,stroke:#ff6b35,color:#e8f4fd
    style DASH    fill:#0b1628,stroke:#2ed573,color:#e8f4fd
    style FIELD   fill:#0b1628,stroke:#00c8ff,color:#e8f4fd
    style REPORT  fill:#0b1628,stroke:#7a9db8,color:#e8f4fd

    style POSTGIS fill:#1a2a4a,stroke:#00ffcc,color:#00ffcc
    style FASTAPI fill:#1a2a4a,stroke:#00c8ff,color:#00c8ff
    style ORTOOLS fill:#1a2a4a,stroke:#ff6b35,color:#ff6b35
```

---

## 🔀 Detailed Data Flow

```mermaid
sequenceDiagram
    participant EXT as 🌐 External APIs
    participant ING as 📥 Data Ingestion
    participant DB  as 🗄️ PostGIS DB
    participant ML  as 🤖 ML Engine
    participant OPT as ⚙️ Optimizer
    participant API as ⚡ FastAPI
    participant UI  as 🖥️ Dashboard
    participant FT  as 👥 Field Team

    EXT->>ING: Real-time disaster events (GDACS, USGS)
    ING->>ING: Parse & classify zones
    ING->>DB: Store impact zones + severity scores
    DB->>ML: Zone data + population density
    ML->>ML: Predict resource demand per zone
    ML->>API: Return demand estimates + confidence
    API->>OPT: Pass demand requirements
    OPT->>OPT: Linear programming optimization
    OPT->>API: Return allocation plan + routes
    API->>UI: WebSocket push (real-time updates)
    UI->>UI: Update map, alerts, stats
    UI->>FT: Send mission assignments
    FT->>API: Field reports (status updates)
    API->>ML: Recalibrate predictions
    API->>DB: Log all operations
```

---

## 📦 Module-wise Development Flow

```mermaid
flowchart LR
    M1["📥 Module 1\nWeeks 1-2\nData Ingestion\n& Geospatial"] --> M2["🤖 Module 2\nWeeks 3-4\nML Demand\nPrediction"]
    M2 --> M3["🖥️ Module 3\nWeeks 5-6\nLogistics\nDashboard"]
    M3 --> M4["✅ Module 4\nWeeks 7-8\nTesting &\nFinalization"]

    style M1 fill:#1a2a4a,stroke:#ffd32a,color:#ffd32a
    style M2 fill:#1a2a4a,stroke:#00ffcc,color:#00ffcc
    style M3 fill:#1a2a4a,stroke:#00c8ff,color:#00c8ff
    style M4 fill:#1a2a4a,stroke:#2ed573,color:#2ed573
```

---

## 🔑 Key API Endpoints (to be built)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/zones` | All disaster zones with severity |
| `GET` | `/api/zones/{id}` | Single zone details |
| `POST` | `/api/predict/demand` | ML demand prediction for a zone |
| `GET` | `/api/resources` | Current resource inventory |
| `POST` | `/api/optimize` | Run OR-Tools optimizer |
| `GET` | `/api/routes` | Optimized delivery routes |
| `GET` | `/api/teams` | Field team statuses |
| `POST` | `/api/alerts` | Create new alert |
| `GET` | `/api/feeds/live` | Live disaster event feed |
| `GET` | `/api/reports/situation` | Generate situation report |
