with open('main.py', 'a') as f:
    f.write('''
import services_phase3
from pydantic import BaseModel

class ResourcePayload(BaseModel):
    resource_type: str
    quantity: float
    unit: str
    lat: float
    lng: float
    depot_name: str
    status: str = "available"

@app.post("/api/resources")
def create_resource(payload: ResourcePayload, db: Session = Depends(get_db)):
    return services_phase3.create_resource(db, payload.dict())

@app.get("/api/resources/near")
def get_resources_near(lat: float, lng: float, radius_km: float, db: Session = Depends(get_db)):
    return services_phase3.get_resources_near(db, lat, lng, radius_km)

@app.post("/api/zones/classify")
def classify_zones(event_id: str, db: Session = Depends(get_db)):
    res = services_phase3.classify_zones(db, event_id)
    if "error" in res: raise HTTPException(status_code=400, detail=res["error"])
    return res

''')
