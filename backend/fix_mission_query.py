import re

with open('main.py', 'r') as f:
    content = f.read()

old_query = '''SELECT m.id, m.team_name, m.status, r.distance_km, r.estimated_duration_minutes, z.priority, ST_AsGeoJSON(r.route_geometry)'''
new_query = '''SELECT m.id, m.team_name, m.status, r.distance_km, r.estimated_duration_minutes, z.priority, ST_AsGeoJSON(r.route_geometry), r.road_status, r.is_fallback_straight_line'''

old_return = '''return [{"id": str(r[0]), "team": r[1], "status": r[2], "distance": r[3], "duration": r[4], "priority": r[5], "geometry": json.loads(r[6]) if r[6] else None} for r in rows]'''
new_return = '''return [{"id": str(r[0]), "team": r[1], "status": r[2], "distance": r[3], "duration": r[4], "priority": r[5], "geometry": json.loads(r[6]) if r[6] else None, "road_status": r[7], "fallback": r[8]} for r in rows]'''

content = content.replace(old_query, new_query)
content = content.replace(old_return, new_return)

with open('main.py', 'w') as f:
    f.write(content)
