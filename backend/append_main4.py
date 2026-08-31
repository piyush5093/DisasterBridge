with open('main.py', 'a') as f:
    f.write('''
import services_missions

class MissionStatusPayload(BaseModel):
    status: str

@app.patch("/api/missions/{mission_id}/status")
def update_mission_status(mission_id: str, payload: MissionStatusPayload, db: Session = Depends(get_db)):
    res = services_missions.update_mission_status(db, mission_id, payload.status)
    if "error" in res:
        raise HTTPException(status_code=res.get("code", 400), detail=res["error"])
    return res
''')
