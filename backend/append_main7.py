with open('main.py', 'a') as f:
    f.write('''
class BatchPlanPayload(BaseModel):
    zone_ids: list[str]
    create_missions: bool = True

@app.post("/api/relief-plan/generate-batch")
def generate_unified_plan_batch(payload: BatchPlanPayload, db: Session = Depends(get_db)):
    import services_logistics_batch
    res = services_logistics_batch.generate_unified_plan_batch(db, payload.zone_ids, payload.create_missions)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res
''')
