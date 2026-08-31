import sys
with open('main.py', 'a') as f:
    f.write('''
@app.get("/api/resources")
def list_all_resources(db: Session = Depends(get_db)):
    from models import ResourceItem
    res = db.query(ResourceItem).all()
    return [{
        "id": str(r.id),
        "resource_type": r.resource_type.name if hasattr(r.resource_type, 'name') else r.resource_type,
        "quantity": r.quantity,
        "unit": r.unit,
        "status": r.status,
        "depot_name": r.depot_name,
        "lat": db.execute(text("SELECT ST_Y(location::geometry) FROM resource_items WHERE id = :id"), {"id": r.id}).scalar(),
        "lng": db.execute(text("SELECT ST_X(location::geometry) FROM resource_items WHERE id = :id"), {"id": r.id}).scalar()
    } for r in res]
''')
