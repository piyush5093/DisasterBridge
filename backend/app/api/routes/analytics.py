"""
Analytics API Routes — Dashboard aggregation endpoints
GET /api/analytics/dashboard         — full dashboard summary
GET /api/analytics/severity-trend    — severity distribution snapshot
GET /api/analytics/resource-utilization — per-category utilization rates
GET /api/analytics/teams-overview    — team deployment status breakdown
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.zone import DisasterZone, SeverityLevel
from app.models.resource import Resource
from app.models.depot import Depot
from app.models.event import FieldTeam, DisasterEvent

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """
    Aggregated dashboard data — single call to power the main command view.
    Returns zones summary, resource inventory, team status, and feed stats.
    """
    # ── Zones ────────────────────────────────────────────────────────────────
    active_zones = db.query(DisasterZone).filter(DisasterZone.is_active == 1).all()
    total_affected = sum(z.population_affected for z in active_zones)
    severity_counts = {
        "critical": sum(1 for z in active_zones if z.severity == SeverityLevel.CRITICAL),
        "high":     sum(1 for z in active_zones if z.severity == SeverityLevel.HIGH),
        "medium":   sum(1 for z in active_zones if z.severity == SeverityLevel.MEDIUM),
        "low":      sum(1 for z in active_zones if z.severity == SeverityLevel.LOW),
    }

    # Top 5 most severe zones
    top_zones = sorted(active_zones, key=lambda z: z.severity_score, reverse=True)[:5]
    top_zones_data = [
        {
            "id": z.id, "name": z.name, "state": z.state,
            "severity": z.severity, "severity_score": z.severity_score,
            "population_affected": z.population_affected,
            "disaster_type": z.disaster_type,
        }
        for z in top_zones
    ]

    # ── Resources ────────────────────────────────────────────────────────────
    all_resources = db.query(Resource).all()
    resource_summary: dict = {}
    total_critical_resources = 0
    for r in all_resources:
        cat = r.category
        if cat not in resource_summary:
            resource_summary[cat] = {
                "total": 0, "available": 0, "deployed": 0, "critical_count": 0
            }
        resource_summary[cat]["total"]     += r.quantity_total
        resource_summary[cat]["available"] += r.quantity_available
        resource_summary[cat]["deployed"]  += r.quantity_deployed
        if r.is_critical():
            resource_summary[cat]["critical_count"] += 1
            total_critical_resources += 1

    # ── Teams ────────────────────────────────────────────────────────────────
    all_teams = db.query(FieldTeam).all()
    teams_summary = {
        "total":    len(all_teams),
        "deployed": sum(1 for t in all_teams if t.status == "deployed"),
        "transit":  sum(1 for t in all_teams if t.status == "transit"),
        "standby":  sum(1 for t in all_teams if t.status == "standby"),
        "offline":  sum(1 for t in all_teams if t.status == "offline"),
        "total_members": sum(t.members for t in all_teams),
    }

    # ── Depots ───────────────────────────────────────────────────────────────
    active_depots = db.query(Depot).filter(Depot.is_active == 1).count()

    # ── Events ───────────────────────────────────────────────────────────────
    total_events = db.query(DisasterEvent).count()

    return {
        "zones": {
            "active":          len(active_zones),
            "total_affected":  total_affected,
            "severity":        severity_counts,
            "top_zones":       top_zones_data,
        },
        "resources": {
            "total_items":              len(all_resources),
            "critical_alerts":          total_critical_resources,
            "by_category":              resource_summary,
        },
        "teams":    teams_summary,
        "depots":   {"active": active_depots},
        "events":   {"total_ingested": total_events},
    }


@router.get("/severity-trend")
def get_severity_trend(db: Session = Depends(get_db)):
    """
    Returns current severity distribution snapshot for chart rendering.
    Groups active zones by severity and disaster type.
    """
    zones = db.query(DisasterZone).filter(DisasterZone.is_active == 1).all()

    by_severity = {}
    by_type = {}
    by_state = {}

    for z in zones:
        # Severity
        by_severity[z.severity] = by_severity.get(z.severity, 0) + 1
        # Disaster type
        by_type[z.disaster_type] = by_type.get(z.disaster_type, 0) + 1
        # State
        by_state[z.state] = by_state.get(z.state, 0) + 1

    # Severity score distribution (buckets)
    buckets = {"0-2": 0, "2-4": 0, "4-6": 0, "6-8": 0, "8-10": 0}
    for z in zones:
        s = z.severity_score
        if s < 2:
            buckets["0-2"] += 1
        elif s < 4:
            buckets["2-4"] += 1
        elif s < 6:
            buckets["4-6"] += 1
        elif s < 8:
            buckets["6-8"] += 1
        else:
            buckets["8-10"] += 1

    return {
        "by_severity":      by_severity,
        "by_disaster_type": by_type,
        "by_state":         by_state,
        "score_distribution": buckets,
        "total_active_zones": len(zones),
    }


@router.get("/resource-utilization")
def get_resource_utilization(db: Session = Depends(get_db)):
    """
    Resource utilization rates per category — for gauge/progress charts.
    """
    resources = db.query(Resource).all()

    categories: dict = {}
    for r in resources:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"total": 0, "available": 0, "deployed": 0, "items": 0}
        categories[cat]["total"]     += r.quantity_total
        categories[cat]["available"] += r.quantity_available
        categories[cat]["deployed"]  += r.quantity_deployed
        categories[cat]["items"]     += 1

    result = []
    for cat, data in categories.items():
        total = data["total"]
        deployed = data["deployed"]
        utilization_pct = round(deployed / total * 100, 1) if total > 0 else 0.0
        availability_pct = round(data["available"] / total * 100, 1) if total > 0 else 0.0
        result.append({
            "category":         cat,
            "total":            total,
            "available":        data["available"],
            "deployed":         data["deployed"],
            "utilization_pct":  utilization_pct,
            "availability_pct": availability_pct,
            "item_count":       data["items"],
            "status": (
                "critical" if availability_pct < 20 else
                "warning"  if availability_pct < 40 else
                "ok"
            ),
        })

    return {"categories": result, "total_categories": len(result)}


@router.get("/teams-overview")
def get_teams_overview(db: Session = Depends(get_db)):
    """
    Full team deployment breakdown with zone assignments.
    """
    teams = db.query(FieldTeam).all()
    zones_map = {
        z.id: z.name
        for z in db.query(DisasterZone).all()
    }

    data = [
        {
            "id":          t.id,
            "team_code":   t.team_code,
            "team_name":   t.team_name,
            "members":     t.members,
            "status":      t.status,
            "zone_id":     t.zone_id,
            "zone_name":   zones_map.get(t.zone_id) if t.zone_id else None,
            "location":    t.location_txt,
        }
        for t in teams
    ]

    return {
        "teams": data,
        "total": len(data),
        "deployed_count": sum(1 for t in teams if t.status == "deployed"),
    }
