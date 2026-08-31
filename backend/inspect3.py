from sqlalchemy import create_engine, text
e = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
with e.connect() as con:
    print('=== MISSIONS STATUS ===')
    rows = con.execute(text('SELECT id, status::TEXT, team_name, supplies FROM missions')).fetchall()
    for r in rows:
        print(f'  {str(r[0])[:8]} | {r[1]:>12} | {r[2]} | {r[3]}')

    print()
    print('=== VOLUNTEERS TABLE ===')
    try:
        cols = con.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='volunteers' ORDER BY ordinal_position"
        )).fetchall()
        print('columns:', [c[0] for c in cols])
        cnt = con.execute(text('SELECT count(*) FROM volunteers')).scalar()
        print('count:', cnt)
    except Exception as ex:
        print('No volunteers table:', str(ex)[:80])

    print()
    print('=== ZONE PRIORITY RANKING ===')
    import urllib.request, json
    res = json.loads(urllib.request.urlopen('http://localhost:8000/api/analytics/zone-priority-ranking', timeout=10).read())
    print('First zone:', res[0] if res else 'empty')
    print('Keys:', list(res[0].keys()) if res else 'empty')
