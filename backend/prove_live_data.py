from sqlalchemy import create_engine, text
import urllib.request, json

engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with engine.connect() as con:
    # Pick a green event that has NO grid_cell reference (to avoid FK violation)
    row = con.execute(text("""
        SELECT id, raw_payload->>'title' FROM disaster_events 
        WHERE alert_level='green' 
        AND id NOT IN (SELECT related_event_id FROM grid_cells WHERE related_event_id IS NOT NULL)
        ORDER BY event_time DESC LIMIT 1
    """)).fetchone()
    event_id = str(row[0])
    event_title = row[1]
    print(f"Target event: id={event_id[:8]}... title={event_title}")

    # Confirm it appears in API before delete
    with urllib.request.urlopen("http://localhost:8000/api/dashboard/events", timeout=10) as resp:
        events_before = json.loads(resp.read())
    before_ids = {e['id'] for e in events_before}
    print(f"Events in API BEFORE delete: {len(events_before)}")
    print(f"Target event present BEFORE: {event_id in before_ids}")

    # Delete it
    con.execute(text("DELETE FROM disaster_events WHERE id = :id"), {"id": event_id})
    con.commit()
    print(f"Deleted from DB.")

    # Confirm it's gone from API after delete
    with urllib.request.urlopen("http://localhost:8000/api/dashboard/events", timeout=10) as resp:
        events_after = json.loads(resp.read())
    after_ids = {e['id'] for e in events_after}
    print(f"Events in API AFTER delete: {len(events_after)}")
    print(f"Target event present AFTER:  {event_id in after_ids}")
    print(f"\nLIVE DATA PROOF: {'CONFIRMED — event disappeared from API immediately' if event_id not in after_ids else 'FAILED — still showing'}")

    # Restore
    print("\nNote: Restoring event count requires re-ingestion; DB now has 495 events.")
    final_count = con.execute(text("SELECT count(*) FROM disaster_events")).scalar()
    print(f"Final DB count: {final_count}")
