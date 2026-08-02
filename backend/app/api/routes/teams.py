"""
Field Teams API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.event import FieldTeam
from app.schemas.resource import TeamCreate, TeamResponse

router = APIRouter()


@router.get("/", response_model=List[TeamResponse])
def list_teams(
    status: Optional[str] = Query(None, description="deployed / transit / standby"),
    db: Session = Depends(get_db)
):
    query = db.query(FieldTeam)
    if status:
        query = query.filter(FieldTeam.status == status.lower())
    return query.all()


@router.get("/summary")
def teams_summary(db: Session = Depends(get_db)):
    teams = db.query(FieldTeam).all()
    return {
        "total":    len(teams),
        "deployed": sum(1 for t in teams if t.status == "deployed"),
        "transit":  sum(1 for t in teams if t.status == "transit"),
        "standby":  sum(1 for t in teams if t.status == "standby"),
        "members":  sum(t.members for t in teams),
    }


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(team_id: int, db: Session = Depends(get_db)):
    t = db.query(FieldTeam).filter(FieldTeam.id == team_id).first()
    if not t:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    return t


@router.post("/", response_model=TeamResponse, status_code=201)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)):
    t = FieldTeam(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{team_id}/status")
def update_team_status(
    team_id: int,
    status: str,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    t = db.query(FieldTeam).filter(FieldTeam.id == team_id).first()
    if not t:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    t.status = status.lower()
    if location:
        t.location_txt = location
    db.commit()
    return {"message": f"Team {t.team_code} status updated to {status}"}
