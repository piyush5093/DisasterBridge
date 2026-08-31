import json
from datetime import datetime
from sqlalchemy.orm import Session
from models import Mission, MissionStatusEnum, AllocationPlan, ResourceItem

def update_mission_status(db: Session, mission_id: str, new_status_str: str):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return {"error": "Mission not found", "code": 404}
        
    try:
        new_status = MissionStatusEnum(new_status_str)
    except ValueError:
        return {"error": f"Invalid status: {new_status_str}", "code": 400}
        
    valid_transitions = {
        MissionStatusEnum.pending: [MissionStatusEnum.assigned, MissionStatusEnum.cancelled],
        MissionStatusEnum.assigned: [MissionStatusEnum.in_transit, MissionStatusEnum.cancelled],
        MissionStatusEnum.in_transit: [MissionStatusEnum.delivered, MissionStatusEnum.cancelled],
        MissionStatusEnum.delivered: [],
        MissionStatusEnum.cancelled: []
    }
    
    current_status = mission.status
    if new_status not in valid_transitions[current_status]:
        return {"error": f"Invalid transition from {current_status.name} to {new_status.name}", "code": 400}
        
    # Apply transition
    mission.status = new_status
    now = datetime.utcnow()
    
    if new_status == MissionStatusEnum.in_transit:
        mission.dispatched_at = now
    elif new_status == MissionStatusEnum.delivered:
        mission.delivered_at = now
    elif new_status == MissionStatusEnum.cancelled:
        # Restore inventory to source depots for any allocation plans tied to this zone.
        # Decision: restore on cancellation (conservative — inventory is only "spent"
        # on delivered missions; cancelling a mission returns stock so it can be reallocated).
        if mission.zone_id:
            plans = db.query(AllocationPlan).filter(
                AllocationPlan.zone_id == mission.zone_id
            ).all()
            for plan in plans:
                depot = db.query(ResourceItem).filter(
                    ResourceItem.id == plan.source_depot_id
                ).first()
                if depot:
                    depot.quantity += plan.allocated_quantity
                    if depot.quantity > 0.01 and depot.status == 'depleted':
                        depot.status = 'available'

    # Append to status_history
    history = mission.status_history or []
    if isinstance(history, str):
        try:
            history = json.loads(history)
        except:
            history = []
    
    # We must explicitly create a new list for SQLAlchemy JSON column mutation tracking, 
    # or use flag_modified. Creating a new list is safer.
    new_history = list(history)
    new_history.append({"status": new_status.name, "timestamp": now.isoformat()})
    mission.status_history = new_history
    
    db.commit()
    db.refresh(mission)
    
    return {
        "id": str(mission.id),
        "status": mission.status.name,
        "dispatched_at": mission.dispatched_at,
        "delivered_at": mission.delivered_at,
        "status_history": mission.status_history
    }
