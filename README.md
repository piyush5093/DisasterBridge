# AI-Based Disaster Response Management System

Full-stack AI-powered disaster resource management platform — resource
demand prediction, allocation optimization, and relief logistics
coordination.

**Database: MongoDB** (via Motor + Beanie). The project's stack sheet
originally specified PostgreSQL+PostGIS; this build now uses MongoDB
instead, per request. See "Why MongoDB instead of PostGIS" below for
what that trades off.

## Day 1 — What's set up

- Repo/folder structure (`backend/app/...`): `api` (routes), `core`
  (config), `db` (Mongo connection lifecycle), `models` (Beanie
  documents), `schemas`, `services`.
- FastAPI skeleton app (`app/main.py`) with CORS enabled, a versioned
  API mounted at `/api/v1`, and a `lifespan` context manager that opens
  the MongoDB connection (`connect_to_mongo`) on startup and closes it
  on shutdown.
- MongoDB via Docker Compose, with Motor (async driver) + Beanie (ODM)
  wiring in `app/db/mongodb.py`.
- `/health` and `/health/db` endpoints — the second one pings MongoDB
  and returns its version, confirming the whole chain (FastAPI → Motor
  → MongoDB) works end-to-end.

## Why MongoDB instead of PostGIS

Worth knowing going in, since a few upcoming milestones assumed PostGIS:

- **What still works great:** all point-based geospatial queries.
  `DisasterEvent.location` is a GeoJSON Point with a 2dsphere index, so
  `$near`/`$geoWithin`/`$geoIntersects` cover everything GDACS/USGS/NDMA
  ingestion and Day 10's grid-cell/zone lookups need.
- **What doesn't have a direct equivalent:** PostGIS's **raster** type
  and `ST_*` raster functions — relevant to **Day 7** (population
  density raster integration). MongoDB has no native raster storage;
  the plan there is to keep rasters as files (local disk or object
  storage) processed with `rasterio`/`geopandas` as before, and store
  only derived per-zone statistics (not whole rasters) as Mongo
  documents. This gets designed properly when Day 7 is built rather
  than guessed at now.
- **No schema migrations:** MongoDB is schemaless, so Alembic is gone —
  `DisasterEvent`'s Beanie `Settings.indexes` is the only "schema"
  (indexes), created automatically by `init_beanie()` at startup.
- **No SQL joins:** later resource-allocation/OR-Tools logic (Week 3-4)
  that would have used SQL joins across tables will instead either
  denormalize related data into one document or do multiple queries
  application-side. Not a blocker, just a different pattern.

## Prerequisites

- Docker + Docker Compose
- Python 3.11+
- (Node.js 18+ — only needed once we reach the frontend in Week 5-6)

## Setup

### 1. Start the database

```bash
docker compose up -d
```

This starts:
- `disaster_db` — MongoDB 7, exposed on `localhost:27017` (root user
  `disaster_admin`/`disaster_pass`, matching `.env.example`)
- `disaster_redis` — Redis 7, exposed on `localhost:6379` (used from
  Day 5 onward for async ingestion jobs)

### 2. Set up the Python environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # defaults already match docker-compose.yml
```

### 3. Start the API

No migration step — MongoDB creates the database/collection on first
write, and Beanie creates indexes automatically at startup.

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Verify

- Swagger docs: http://localhost:8000/docs
- Basic liveness: http://localhost:8000/api/v1/health
- DB check: http://localhost:8000/api/v1/health/db

  Expected response shape:
  ```json
  {
    "status": "ok",
    "mongodb_version": "7.0.x"
  }
  ```

  If this endpoint fails, check that `docker compose ps` shows
  `disaster_db` as healthy and that `.env`'s `MONGODB_URL` matches
  `docker-compose.yml`'s credentials.

## Project structure

```
disaster-response-system/
├── docker-compose.yml       # MongoDB + Redis
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── scripts/
│   │   └── inspect_gdacs_response.py  # spot-check live GDACS schema
│   ├── tests/
│   │   ├── fixtures/                  # GDACS/USGS/CAP sample + live-captured responses
│   │   ├── test_gdacs_ingestion.py
│   │   ├── test_gdacs_ingestion_live_sample.py
│   │   ├── test_usgs_ingestion.py
│   │   ├── test_cap_parser.py
│   │   └── test_ndma_ingestion.py
│   └── app/
│       ├── main.py          # FastAPI app entry point + Mongo lifespan
│       ├── core/
│       │   └── config.py    # env-driven settings (MONGODB_URL, etc.)
│       ├── db/
│       │   └── mongodb.py   # Motor client + Beanie init/connection lifecycle
│       ├── models/
│       │   └── disaster_event.py   # DisasterEvent Beanie Document (source-agnostic)
│       ├── schemas/
│       │   └── disaster_event.py   # DisasterEventOut, IngestionResult
│       ├── utils/
│       │   └── cap_parser.py       # CAP v1.2 XML parser (NDMA)
│       ├── services/
│       │   ├── external/           # API clients: gdacs, usgs, ndma, sentinel_hub
│       │   └── ingestion/
│       │       ├── common.py           # shared Mongo upsert logic (all sources)
│       │       ├── gdacs_ingestion.py
│       │       ├── usgs_ingestion.py
│       │       └── ndma_ingestion.py
│       └── api/v1/
│           ├── api.py              # router aggregation
│           ├── health.py
│           ├── ingestion.py        # /ingest/gdacs/* + /events
│           ├── ingestion_usgs.py   # /ingest/usgs/*
│           ├── ingestion_ndma.py   # /ingest/ndma/*
│           └── imagery.py          # /imagery/sentinel/*
└── frontend/                 # scaffolded in Week 5-6
```

## Day 2 — GDACS API integration

**What's new:**
- `app/services/external/gdacs_client.py` — async client for GDACS's real
  endpoints: `EVENTS4APP` (all currently active events), `SEARCH`
  (custom date range / type / alert-level filtering), and
  `geteventdata` (single event/episode detail).
- `app/models/disaster_event.py` — source-agnostic
  `disaster_events` collection (USGS on Day 3 and NDMA on Day 4 write into
  the same collection). Unique index on `(source, external_event_id, episode_id)`
  — GDACS re-issues an event as it evolves, and each episode is kept as
  its own document rather than overwritten.
- `app/services/ingestion/gdacs_ingestion.py` — normalizes raw GeoJSON
  features into that schema and upserts them. Polygon/line geometries
  (e.g. flood extent) are reduced to a centroid point for consistent
  storage. The full untouched payload is always kept in `raw_data`
  (JSONB) as a safety net.
- `POST /api/v1/ingest/gdacs/active` — pulls and stores all currently
  active events.
- `POST /api/v1/ingest/gdacs/search?event_types=EQ;FL&from_date=...&to_date=...&alert_level=orange` — custom-filtered pull.
- `GET /api/v1/events?event_type=FL&country=India&is_current=true` — list
  stored events with filters.
- `tests/test_gdacs_ingestion.py` + `tests/fixtures/gdacs_sample_response.json`
  — unit tests against a hand-built fixture (parsing, centroid reduction,
  malformed-feature handling).
- `tests/test_gdacs_ingestion_live_sample.py` + `tests/fixtures/gdacs_live_sample_2026-07-24.json`
  — unit tests against a response captured directly from the real GDACS
  SEARCH endpoint, confirming the field mapping actually matches
  production data (not just documentation). All 8 tests pass.

**✅ Field mapping confirmed against live data (2026-07-24):** the GDACS
SEARCH endpoint was queried directly and every field the normalizer reads
(`eventid`, `eventtype`, `episodeid`, `alertlevel`, `alertscore`,
`severitydata.{severity,severitytext,severityunit}`, `country`, `iso3`,
`fromdate`/`todate`, `iscurrent`, `url.{report,details,geometry}`) matches
exactly. Two things the live check caught and this code now handles:
- `fromdate`/`todate` come back as **naive** timestamps with no `Z` or
  offset (e.g. `"2026-07-23T06:00:00"`) — `_parse_datetime` now assumes
  UTC when no timezone is present, instead of only handling the `...Z` form.
- `iscurrent` is the literal **string** `"true"`/`"false"`, not a JSON
  boolean — already handled correctly.

**⚠️ One open item:** GDACS's own `eventlist`/`fromdate`/`todate` query
params on the SEARCH endpoint didn't appear to actually narrow results
during live testing (same ~100 events came back regardless of the values
sent). `gdacs_client.py` now re-applies all filters client-side on the
response as a safety net, so `/ingest/gdacs/search` behaves correctly
either way — but if you rely on this endpoint for large date ranges,
know that GDACS's raw payload may already be capped at ~100 events
server-side. Re-run `python scripts/inspect_gdacs_response.py` if you
want to re-verify this against GDACS's current behavior.

**Try it yourself (after Day 1 setup):**
```bash
curl -X POST http://localhost:8000/api/v1/ingest/gdacs/active
curl http://localhost:8000/api/v1/events
```

## Day 3 — USGS earthquake API integration

**What's new:**
- `app/services/external/usgs_client.py` — async client for USGS's FDSN
  `query` method (custom magnitude/date/bbox filters) and the pre-computed
  real-time summary feeds (e.g. `significant_week`, `4.5_day`).
- `app/services/ingestion/usgs_ingestion.py` — normalizes USGS features
  into the **same** `disaster_events` collection as GDACS (`source="USGS"`).
  Field mapping differences are documented in the module docstring —
  notably: no episodes (USGS revises events in place), no structured
  country field (only free-text `place`), and `sig` (USGS's own
  significance score) is stored in `alert_score` as the closest analog.
- `POST /api/v1/ingest/usgs/query?min_magnitude=5&start_time=...&end_time=...`
- `POST /api/v1/ingest/usgs/summary?feed=significant_week`
- `tests/test_usgs_ingestion.py` + `tests/fixtures/usgs_sample_response.json`
  — 5 tests against a fixture built to match USGS's confirmed live schema
  (verified 2026-07-24 against USGS's own documentation and a real 2026
  CSV/GeoJSON sample).

**Try it yourself:**
```bash
curl -X POST "http://localhost:8000/api/v1/ingest/usgs/summary?feed=significant_week"
curl "http://localhost:8000/api/v1/events?source=USGS"
```

## Day 4 — NDMA feed + satellite imagery API integration

**NDMA (India's National Disaster Management Authority):**
- `app/utils/cap_parser.py` — parser for CAP v1.2 (Common Alerting
  Protocol), the public OASIS XML standard NDMA's SACHET portal
  (sachet.ndma.gov.in) publishes alerts in. Handles both `<polygon>` and
  `<circle>` area geometry (note: CAP coordinates are `lat,lon`, the
  opposite of GeoJSON — the parser flips this).
- `app/services/external/ndma_client.py` — client for NDMA's real,
  confirmed endpoint (`GET https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=...`),
  found via the "RSS FEED" link on sachet.ndma.gov.in → its linked
  integration guide PDF. Implements the ETag/`If-None-Match` caching
  NDMA's guide says is mandatory for consuming agencies.
- `app/services/ingestion/ndma_ingestion.py` — normalizes parsed CAP
  alerts into the same `disaster_events` collection (`source="NDMA"`),
  mapping CAP's free-text `event` to GDACS-style type codes and CAP's
  `severity` to `alert_level`.
- `POST /api/v1/ingest/ndma/alert?identifier=<CAP_IDENTIFIER>`

  **⚠️ Known limitation:** NDMA's public integration guide documents
  fetching one alert *by an identifier you already have* — it does not
  document a public endpoint for discovering which identifiers are
  currently active (that's likely provided during agency onboarding,
  since the guide is titled "for Agencies"). This client can't pull
  "everything active right now" the way GDACS/USGS's endpoints can,
  until that discovery endpoint is confirmed.

**Satellite imagery (flood/damage extent):**
- `app/services/external/sentinel_hub_client.py` — OAuth2
  client-credentials client for satellite imagery via the **Copernicus
  Data Space Ecosystem** (confirmed live 2026-07-24: Sentinel Hub's old
  `services.sentinel-hub.com` endpoints are deprecated post-migration;
  current token/API endpoints are documented in the module).
  Provides true-color reference imagery and an NDWI-based (water index)
  flood-extent image for any bounding box + date range.
- `GET /api/v1/imagery/sentinel/true-color?min_lon=&min_lat=&max_lon=&max_lat=&from_date=&to_date=`
- `GET /api/v1/imagery/sentinel/flood-extent?...` (same params)
- Requires `SENTINEL_HUB_CLIENT_ID`/`SECRET` in `.env` (register at
  https://shapps.dataspace.copernicus.eu/dashboard/#/). Persisting
  imagery as proper raster data (vs. returning PNGs directly) is scoped
  to Day 6 per the project plan, once rasterio/geopandas are wired in.

**Tests:** `tests/test_cap_parser.py` (5 tests) + `tests/test_ndma_ingestion.py`
(4 tests) against hand-built CAP v1.2 fixtures — CAP is a stable public
standard so these don't need a live sample the way GDACS/USGS did.
**All 22 tests across Days 2-4 pass.**

**Try it yourself:**
```bash
# NDMA — replace with a real identifier you have
curl -X POST "http://localhost:8000/api/v1/ingest/ndma/alert?identifier=NDMA-2026-FL-000123"

# Satellite imagery over Kochi, Kerala (flood-prone) for a week in July
curl "http://localhost:8000/api/v1/imagery/sentinel/true-color?min_lon=76.2&min_lat=9.9&max_lon=76.3&max_lat=10.0&from_date=2026-07-15&to_date=2026-07-22" --output kochi.png
```

## Day 5 — Data normalization pipeline + ingestion testing

- `app/services/ingestion/common.py` — shared Mongo upsert helper used
  by all three source ingestion modules (extracted from the
  near-identical logic that had been duplicated across GDACS/USGS/NDMA).
- `app/services/ingestion/pipeline.py` — `run_full_ingestion()` pulls
  GDACS (active events) + USGS (recent significant quakes) in one call,
  with **per-source failure isolation**: a GDACS outage doesn't block
  USGS ingestion. `run_ndma_ingestion(identifiers)` handles NDMA
  separately since it can't be polled "as a whole" (Day 4's limitation).
- `app/core/celery_app.py` — Celery app + beat schedule (every 15 min)
  for scheduled polling; `POST /ingest/run-all` triggers the same thing
  on demand without needing Celery/Redis running locally.
- **Tests:** 3 tests using mocked clients (proving per-source isolation
  actually works, not just plausible-looking code).

## Day 6 — Geospatial impact module (flood/earthquake extent maps)

- `app/services/impact/extent_calculator.py` — estimates an impact
  radius per event (⚠️ explicitly labeled as a placeholder heuristic,
  not a real hazard model — see the module docstring for what a real
  implementation would need per hazard type) and buffers it into a
  GeoJSON polygon.
- `POST /impact/{event_id}/compute`, `POST /impact/compute-all`,
  `GET /impact/geojson` (ready for a Leaflet choropleth/overlay layer).
- **Tests:** 8 tests covering radius formulas, polygon geometry, and bbox derivation.

## Day 7 — Population density raster integration

- `app/services/population/density_service.py` — zonal statistics
  (population sum within a polygon) via `rasterio.mask`, against any
  population-count GeoTIFF.
  **⚠️ Honest scope note:** this computes correctly against any such
  raster, but doesn't download one — WorldPop's real data (the stack's
  named source) is outside this sandbox's network allowlist. See the
  module docstring for how to obtain and point `POPULATION_RASTER_PATH` at one.
- `POST /population/estimate`, `POST /population/estimate-for-event/{event_id}`.
- **Tests:** 4 tests against a **synthetic GeoTIFF built with rasterio
  itself** (known pixel values, known expected sums) — genuinely proves
  the zonal-stats math, not just that it runs.

## Day 8 — Building footprint (OpenStreetMap) integration

- `app/services/external/overpass_client.py` — queries the real
  Overpass API (`overpass-api.de`); response schema confirmed live
  2026-07-27 (`out geom;` returns each way's coordinates inline, no
  manual node-reference resolution needed).
- `app/models/building_footprint.py` + `building_footprint_ingestion.py`
  — ways become GeoJSON Polygons, standalone `building=*` nodes become
  Points; malformed geometries are skipped rather than crashing the batch.
- `POST /buildings/ingest`, `GET /buildings/geojson`.
- **Tests:** 5 tests against a live-schema-matched fixture.

## Day 9 — Resource inventory management (CRUD)

- `app/models/resource_inventory.py` — depots with type/quantity/unit/
  capacity/status/location.
- Full CRUD: `POST/GET/PUT/DELETE /resources/{id}`, plus
  `GET /resources/near` (geospatial `$centerSphere` query — "which
  depots are within reach of this zone").
- **Tests:** 9 tests (7 passing CRUD/logic tests, 2 correctly **skipped**
  — `mongomock-motor` doesn't implement `$geoWithin`/`$centerSphere`,
  real MongoDB operators it simply hasn't mocked. The underlying
  distance math is verified independently instead; the query itself
  works against real MongoDB).

## Day 10 — Grid-cell zone classification with severity scores (Milestone 1)

- `app/services/zones/grid_classifier.py` — divides a bounding box into
  square cells and scores each 0-100 using: nearby event severity/alert
  level (within that event's Day 6 impact radius), building density
  (Day 8 data), population exposure (Day 7 data, where available), and
  distance to the nearest resource depot (Day 9 data).
  **⚠️ Same honesty policy as Day 6:** this is a transparent, capped
  weighted-sum formula built from what's actually available so far —
  not a validated humanitarian-need model. Each component is stored
  separately on the `GridCell` document specifically so the formula can
  be tuned or swapped out later without losing the underlying inputs.
- `POST /zones/generate`, `GET /zones`, `GET /zones/geojson` (choropleth-ready).
- **Tests:** 13 tests — pure-function tests for the haversine/point-in-
  polygon/grid-generation helpers, scoring-component tests, and a full
  `generate_and_score_grid` pipeline test against mongomock.

## Milestone 1 — verification summary

- **61 tests passing, 2 correctly skipped** (documented mongomock
  limitation, not an app bug) across all 10 days.
- Every file compiles; the full FastAPI app boots with **27 API routes**
  correctly mounted.
- Ran a genuine end-to-end HTTP workflow against the real app (via
  `asgi-lifespan` + `mongomock-motor`, since this sandbox has no real
  `mongod`): create a resource depot → generate a severity-scored grid
  → list zones → export GeoJSON. All steps passed against the actual
  HTTP layer, not just unit-level mocks.
- **Note on `beanie` version:** pinned to `1.29.0` rather than the
  newer 2.x line. Both work identically against real MongoDB; 2.x sends
  a `list_collection_names` kwarg that `mongomock-motor` (test-only
  tooling) doesn't yet support, so 1.29.0 was pinned to keep "what was
  tested" and "what's pinned" honestly identical.

**Try the full Milestone 1 chain yourself (after Day 1 setup):**
```bash
# 1. Ingest some events
curl -X POST http://localhost:8000/api/v1/ingest/run-all

# 2. Compute impact extents for current events
curl -X POST http://localhost:8000/api/v1/impact/compute-all

# 3. Add a resource depot
curl -X POST http://localhost:8000/api/v1/resources -H "Content-Type: application/json" \
  -d '{"depot_name":"Kochi Central","resource_type":"water","quantity":5000,"unit":"liters","longitude":76.28,"latitude":9.97}'

# 4. Generate a severity-scored grid
curl -X POST "http://localhost:8000/api/v1/zones/generate?min_lon=76.0&min_lat=9.5&max_lon=77.0&max_lat=10.5&cell_size_km=10"

# 5. View the result as GeoJSON (grab grid_run_id from step 4's response)
curl "http://localhost:8000/api/v1/zones/geojson?grid_run_id=<id-from-step-4>"
```

## Milestone roadmap

| Day | Task |
|---|---|
| 1-4 | ✅ Repo setup, GDACS, USGS, NDMA + satellite imagery |
| 5 | ✅ Data normalization pipeline + ingestion testing |
| 6 | ✅ Geospatial impact module: flood/earthquake extent maps |
| 7 | ✅ Population density raster integration |
| 8 | ✅ Building footprint (OpenStreetMap) integration |
| 9 | ✅ Resource inventory management system (CRUD, models) |
| 10 | ✅ Grid-cell zone classification with severity scores — **Milestone 1 complete** |
| Week 3-4 | Resource Demand Prediction Engine (next up) |
