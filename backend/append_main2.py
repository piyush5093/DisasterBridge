with open('main.py', 'a') as f:
    f.write('''
import services_ml
import services_logistics

class PredictionPayload(BaseModel):
    vulnerability_demographics: dict = {"elderly": 0.3, "children": 0.2, "medically_dependent": 0.1}

@app.post("/predict/demand/{zone_id}")
def predict_demand(zone_id: str, payload: PredictionPayload, db: Session = Depends(get_db)):
    res = services_ml.predict_demand_for_zone(db, zone_id, payload.vulnerability_demographics)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

class RecalibratePayload(BaseModel):
    new_severity: float
    reason: str

@app.post("/api/predictions/{zone_id}/recalibrate")
def recalibrate_prediction(zone_id: str, payload: RecalibratePayload, db: Session = Depends(get_db)):
    res = services_ml.recalibrate_prediction(db, zone_id, payload.new_severity, payload.reason)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/predictions/simulate")
def simulate_scenario(zone_id: str, severity_delta: float, db: Session = Depends(get_db)):
    res = services_ml.simulate_scenario(db, zone_id, severity_delta)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/allocation/optimize")
def optimize_allocation(zone_id: str, db: Session = Depends(get_db)):
    res = services_logistics.optimize_allocation(db, zone_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/allocation/optimize-with-routes")
def optimize_with_routes(plan_run_id: str, db: Session = Depends(get_db)):
    res = services_logistics.generate_routes_for_plan(db, plan_run_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/missions/create-from-plan")
def create_missions_from_plan(plan_run_id: str, db: Session = Depends(get_db)):
    res = services_logistics.create_missions_for_plan(db, plan_run_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/relief-plan/generate")
def generate_unified_plan(zone_id: str, db: Session = Depends(get_db)):
    res = services_logistics.generate_unified_plan(db, zone_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res
''')
