with open('main.py', 'a') as f:
    f.write('''
class PriorityOverridePayload(BaseModel):
    priority_override: str

@app.patch("/api/zones/{zone_id}/priority-override")
def override_zone_priority(zone_id: str, payload: PriorityOverridePayload, db: Session = Depends(get_db)):
    from models import GridCell, PriorityEnum
    zone = db.query(GridCell).filter(GridCell.id == zone_id).first()
    if not zone: raise HTTPException(status_code=404, detail="Zone not found")
    try:
        new_prio = PriorityEnum(payload.priority_override.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid priority enum")
    
    zone.priority_override = new_prio
    db.commit()
    db.refresh(zone)
    return {"id": str(zone.id), "priority_override": zone.priority_override.name}
''')
