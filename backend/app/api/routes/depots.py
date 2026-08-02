"""
Depots API Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.depot import Depot
from app.schemas.resource import DepotCreate, DepotResponse

router = APIRouter()


@router.get("/", response_model=List[DepotResponse])
def list_depots(db: Session = Depends(get_db)):
    return db.query(Depot).filter(Depot.is_active == 1).all()


@router.get("/{depot_id}", response_model=DepotResponse)
def get_depot(depot_id: int, db: Session = Depends(get_db)):
    d = db.query(Depot).filter(Depot.id == depot_id).first()
    if not d:
        raise HTTPException(status_code=404, detail=f"Depot {depot_id} not found")
    return d


@router.post("/", response_model=DepotResponse, status_code=201)
def create_depot(payload: DepotCreate, db: Session = Depends(get_db)):
    d = Depot(**payload.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d
