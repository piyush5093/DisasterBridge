import sys
with open('main.py', 'a') as f:
    f.write('''
@app.get("/api/predictions/{zone_id}/history")
def get_prediction_history(zone_id: str, db: Session = Depends(get_db)):
    from models import PredictionRecord
    records = db.query(PredictionRecord).filter(PredictionRecord.zone_id == zone_id).order_by(PredictionRecord.prediction_time.desc()).all()
    return [{
        "id": str(r.id),
        "prediction_time": r.prediction_time.isoformat(),
        "model_version": r.model_version,
        "severity_score_used": r.severity_score_used,
        "predicted_demand_food": r.predicted_demand_food,
        "predicted_demand_water": r.predicted_demand_water,
        "predicted_demand_medical": r.predicted_demand_medical,
        "predicted_demand_shelter": r.predicted_demand_shelter,
        "confidence_intervals": r.confidence_intervals
    } for r in records]

@app.get("/api/zones/list")
def list_zones(db: Session = Depends(get_db)):
    from models import GridCell
    zones = db.query(GridCell).all()
    return [{"id": str(z.id), "severity": z.severity_score} for z in zones]
''')
