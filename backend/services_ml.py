import pickle
import pandas as pd
from sqlalchemy.orm import Session
from models import GridCell, PredictionRecord
import uuid
from datetime import datetime

# Global model cache
ML_MODELS = None

def load_models():
    global ML_MODELS
    if ML_MODELS is None:
        try:
            with open('models_pkl/demand_model.pkl', 'rb') as f:
                ML_MODELS = pickle.load(f)
        except Exception as e:
            print(f"Error loading models: {e}")
            return None
    return ML_MODELS

def get_confidence_interval(val: float, variance: float = 0.15):
    val = float(val)
    return {
        "predicted": val,
        "ci_lower": val * (1 - variance),
        "ci_upper": val * (1 + variance)
    }

def predict_demand_for_zone(db: Session, zone_id: str, vuln_demographics: dict = None):
    vuln_demographics = vuln_demographics or {}
    zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
    if not zone:
        return {"error": "Zone not found"}
        
    models = load_models()
    if not models:
        return {"error": "ML Models not initialized"}

    # Prepare input features
    pop = float(zone.population_exposed or 1000)
    sev = float(zone.severity_score or 50)
    bldgs = pop * 0.2
    
    input_df = pd.DataFrame([{'population': pop, 'severity': sev, 'buildings': bldgs}])
    
    # Run predictions
    # Note: models['water'] is reused for hygiene_kits demand (same population-severity curve)
    raw_food = float(models['food'].predict(input_df).item())
    raw_hygiene = float(models['water'].predict(input_df).item())   # water model key unchanged in pkl
    raw_medical = float(models['medical'].predict(input_df).item())
    raw_shelter = float(models['shelter'].predict(input_df).item())
    
    # Vulnerability Adjustment
    vuln_weight = (vuln_demographics.get("medically_dependent", 0) * 0.5) + \
                  (vuln_demographics.get("elderly", 0) * 0.3) + \
                  (vuln_demographics.get("children", 0) * 0.2)
    
    adj_medical = float(raw_medical * (1 + (vuln_weight * 0.8)))
    adj_food = float(raw_food * (1 + (vuln_weight * 0.2)))
    
    # Record prediction in DB
    record = PredictionRecord(
        zone_id=zone.id,
        predicted_food=adj_food,
        predicted_hygiene_kits=raw_hygiene,
        predicted_medical=adj_medical,
        predicted_shelter=raw_shelter,
        confidence_interval_low={
            "food": float(adj_food * 0.85), "hygiene_kits": float(raw_hygiene * 0.85),
            "medical": float(adj_medical * 0.85), "shelter": float(raw_shelter * 0.85)
        },
        confidence_interval_high={
            "food": float(adj_food * 1.15), "hygiene_kits": float(raw_hygiene * 1.15),
            "medical": float(adj_medical * 1.15), "shelter": float(raw_shelter * 1.15)
        },
        model_version="RandomForest-v1.0",
        is_latest=True,
        created_at=datetime.utcnow()
    )
    
    db.query(PredictionRecord).filter(PredictionRecord.zone_id == zone.id).update({"is_latest": False})
    db.add(record)
    
    # Update grid cell with predicted values
    zone.predicted_demand_food = adj_food
    zone.predicted_demand_hygiene_kits = raw_hygiene
    zone.predicted_demand_medical = adj_medical
    zone.predicted_demand_shelter = raw_shelter
    
    db.commit()
    
    return {
        "zone_id": str(zone.id),
        "prediction_record_id": str(record.id),
        "model_version": "RandomForest-v1.0",
        "food": get_confidence_interval(adj_food),
        "hygiene_kits": get_confidence_interval(raw_hygiene),
        "medical": get_confidence_interval(adj_medical),
        "shelter": get_confidence_interval(raw_shelter)
    }

def recalibrate_prediction(db: Session, zone_id: str, new_severity: float, reason: str):
    zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
    if not zone: return {"error": "Zone not found"}
    
    zone.severity_score = float(new_severity)
    db.commit()
    
    result = predict_demand_for_zone(db, zone_id)
    if "error" not in result:
        rec_id = result["prediction_record_id"]
        rec = db.query(PredictionRecord).filter(PredictionRecord.id == rec_id).first()
        rec.recalibration_reason = reason
        db.commit()
        result["recalibration_reason"] = reason
    
    return result

def simulate_scenario(db: Session, zone_id: str, severity_delta: float):
    zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
    if not zone: return {"error": "Zone not found"}
    
    models = load_models()
    pop = float(zone.population_exposed or 1000)
    sev = min(100.0, max(0.0, float(zone.severity_score or 50) + float(severity_delta)))
    bldgs = pop * 0.2
    
    input_df = pd.DataFrame([{'population': pop, 'severity': sev, 'buildings': bldgs}])
    
    return {
        "scenario": "simulated",
        "zone_id": str(zone.id),
        "severity_used": float(sev),
        "predicted_food": float(models['food'].predict(input_df).item()),
        "predicted_hygiene_kits": float(models['water'].predict(input_df).item()),
        "predicted_medical": float(models['medical'].predict(input_df).item()),
        "predicted_shelter": float(models['shelter'].predict(input_df).item()),
        "writes_to_db": False
    }
