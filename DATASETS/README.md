# 📂 DATASETS — Integration Plan

## 📁 Available Datasets

| File | Size | Type | Status |
|------|------|------|--------|
| `district_wise_details.csv` | 0.6 KB | Kerala Floods 2018 — district stats | ✅ Ready |
| `46d6c279-ae09-43a8-8691-7a5386f69e3a.kml` | 5.25 MB | Chennai Floods 2015 — road/location geospatial | ✅ Ready |
| `ind_pd_2020_1km.tif` | 17.24 MB | India Population Density Raster (2020, 1km grid) | ✅ Ready |
| `ind_pd_2020_1km_ASCII_XYZ/` | ~225 MB | Same as TIF but CSV format (X=lon, Y=lat, Z=population) | ✅ Ready |

---

## 🎯 Task 1: ML Engine — Dataset Integration

### What will be done:
1. **`ml_engine/scripts/train_demand_model.py`** — NEW file
   - `district_wise_details.csv` load చేస్తుంది
   - Feature engineering: rainfall_excess, landslide_risk, camp_ratio columns create చేస్తుంది
   - **Target variables** calculate చేస్తుంది:
     - `food_packets_needed` (camps x 3 meals x 3 days)
     - `water_liters_needed` (affected people x 5L/day x 3 days)
     - `medical_kits_needed` (fatalities ratio based)
   - **Scikit-learn RandomForestRegressor** తో train చేస్తుంది
   - Model `ml_engine/models/saved/demand_model.pkl` లో save చేస్తుంది

2. **`ml_engine/data/processed/kerala_processed.csv`** — AUTO-GENERATED
   - Raw CSV లో feature engineering apply చేసిన processed data

3. **`ml_engine/scripts/population_loader.py`** — NEW file
   - `ind_pd_2020_1km_ASCII_XYZ.csv` నుండి
   - ఒక zone (lat, lon, radius) కి population density lookup చేస్తుంది
   - Backend API call చేసినప్పుడు zone population automatically fill అవుతుంది

4. **`ml_engine/scripts/geospatial_loader.py`** — NEW file
   - `46d6c279-....kml` (Chennai 2015) parse చేస్తుంది
   - Flooded road segments extract చేస్తుంది
   - DisasterZone seed data గా DB లో load చేస్తుంది

---

## 🎯 Task 2: Backend API — Dataset Connect

### What will be done:
1. **`backend/app/services/demand_predictor.py`** — NEW file
   - Trained ML model (`demand_model.pkl`) load చేస్తుంది
   - Zone data (rainfall, population, landslides) input గా తీసుకుని
   - **Predicted demand** (food, water, medical kits) return చేస్తుంది

2. **`backend/app/api/routes/zones.py`** — MODIFY existing file
   - `GET /api/zones/{id}/demand` — NEW endpoint add చేస్తుంది
   - Zone details తీసుకుని ML predictor call చేసి demand estimates return చేస్తుంది

3. **`backend/app/services/zone_classifier.py`** — MODIFY existing file
   - Population density lookup (TIF data) integrate చేసి `population_total` auto-fill అవుతుంది

4. **`database/seeds/seed_disaster_zones.py`** — NEW file
   - Kerala 2018 + Chennai 2015 data ని DB లో seed చేస్తుంది
   - Demo/testing కోసం realistic zones with coordinates

---

## 📊 Data Flow (After Integration)

```
DATASETS/district_wise_details.csv
        |
        v
ml_engine/scripts/train_demand_model.py  <--- Feature Engineering
        |
        v
ml_engine/models/saved/demand_model.pkl  <--- Trained Model (RandomForest)
        |
        v
backend/app/services/demand_predictor.py <--- Load & Predict
        |
        v
GET /api/zones/{id}/demand               <--- New API Endpoint
        |
        v
Frontend Dashboard                       <--- Show resource recommendations


DATASETS/ind_pd_2020_1km_ASCII_XYZ.csv
        |
        v
ml_engine/scripts/population_loader.py  <--- Zone population lookup
        |
        v
backend/app/services/zone_classifier.py <--- Auto-fill population_total


DATASETS/46d6c279-....kml (Chennai 2015)
        |
        v
ml_engine/scripts/geospatial_loader.py  <--- Parse flood zones
        |
        v
database/seeds/seed_disaster_zones.py   <--- Seed DB with real zones
        |
        v
GET /api/zones/                         <--- Available for frontend map
```

---

## 📋 Files To Be Created/Modified

### NEW Files:
| File | Purpose |
|------|---------|
| `ml_engine/scripts/train_demand_model.py` | Kerala CSV load + RF model train |
| `ml_engine/scripts/population_loader.py` | TIF/CSV population lookup |
| `ml_engine/scripts/geospatial_loader.py` | KML parse + zone extract |
| `ml_engine/data/processed/kerala_processed.csv` | Auto-generated processed data |
| `ml_engine/models/saved/demand_model.pkl` | Auto-generated trained model |
| `backend/app/services/demand_predictor.py` | ML model inference service |
| `database/seeds/seed_disaster_zones.py` | Real zone seeder |

### MODIFIED Files:
| File | Change |
|------|--------|
| `backend/app/api/routes/zones.py` | Add `GET /api/zones/{id}/demand` endpoint |
| `backend/app/services/zone_classifier.py` | Add population density auto-fill |

---

## ✅ Execution Order

```
Step 1 → train_demand_model.py      (Kerala CSV load, feature eng, RF train, save .pkl)
Step 2 → geospatial_loader.py       (Chennai KML parse, flood zones extract)
Step 3 → seed_disaster_zones.py     (Seed DB with Kerala + Chennai zones)
Step 4 → demand_predictor.py        (Backend service: load .pkl, predict)
Step 5 → zones.py (modify)          (Add /api/zones/{id}/demand endpoint)
Step 6 → Test API                   (curl /api/zones/1/demand → food/water/medical)
```

---

*Created: 2026-07-30 | Project: AI Disaster Response Management System*
