with open('main.py', 'a') as f:
    f.write('''
@app.get("/api/resources/{resource_id}")
def get_resource(resource_id: str, db: Session = Depends(get_db)):
    from models import ResourceItem
    res = db.query(ResourceItem).filter(ResourceItem.id == resource_id).first()
    if not res: raise HTTPException(status_code=404, detail="Not found")
    return {"id": str(res.id), "resource_type": res.resource_type, "quantity": res.quantity, "status": res.status}

class ResourceUpdatePayload(BaseModel):
    quantity: float
    status: str

@app.put("/api/resources/{resource_id}")
def update_resource(resource_id: str, payload: ResourceUpdatePayload, db: Session = Depends(get_db)):
    from models import ResourceItem
    res = db.query(ResourceItem).filter(ResourceItem.id == resource_id).first()
    if not res: raise HTTPException(status_code=404, detail="Not found")
    res.quantity = payload.quantity
    res.status = payload.status
    db.commit()
    db.refresh(res)
    return {"id": str(res.id), "quantity": res.quantity, "status": res.status}

@app.delete("/api/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: str, db: Session = Depends(get_db)):
    from models import ResourceItem
    res = db.query(ResourceItem).filter(ResourceItem.id == resource_id).first()
    if not res: raise HTTPException(status_code=404, detail="Not found")
    db.delete(res)
    db.commit()
    return None
''')
