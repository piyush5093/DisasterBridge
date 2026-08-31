"""
Create volunteers table and seed with sample data.
"""
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

with engine.connect() as con:
    # Create volunteers table
    con.execute(text("""
        CREATE TABLE IF NOT EXISTS volunteers (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            full_name   TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            phone       TEXT,
            role        TEXT NOT NULL DEFAULT 'general',
            skills      TEXT[],
            status      TEXT NOT NULL DEFAULT 'available',
            zone_id     UUID REFERENCES grid_cells(id) ON DELETE SET NULL,
            notes       TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """))
    con.execute(text("COMMIT"))

    # Seed sample volunteers
    volunteers = [
        ("Arjun Mehta",     "arjun@disasterbridge.com",  "+91-9821001234", "medic",      ["medical", "first_aid"],       "available"),
        ("Priya Sharma",    "priya@disasterbridge.com",  "+91-9821005678", "logistics",  ["logistics", "driving"],       "available"),
        ("Rohit Verma",     "rohit@disasterbridge.com",  "+91-9821009012", "rescue",     ["rescue", "swimming"],         "available"),
        ("Anjali Singh",    "anjali@disasterbridge.com", "+91-9821003456", "medic",      ["medical", "nursing"],         "deployed"),
        ("Suresh Kumar",    "suresh@disasterbridge.com", "+91-9821007890", "logistics",  ["logistics", "warehouse"],     "available"),
        ("Nisha Patel",     "nisha@disasterbridge.com",  "+91-9821002345", "rescue",     ["rescue", "climbing"],         "off_duty"),
        ("Vikram Joshi",    "vikram@disasterbridge.com", "+91-9821006789", "general",    ["driving", "communication"],   "available"),
        ("Kavya Reddy",     "kavya@disasterbridge.com",  "+91-9821001122", "medic",      ["medical", "triage"],          "deployed"),
        ("Amit Gupta",      "amit@disasterbridge.com",   "+91-9821003344", "rescue",     ["rescue", "fire"],             "available"),
        ("Meera Nair",      "meera@disasterbridge.com",  "+91-9821005566", "logistics",  ["logistics", "coordination"],  "available"),
        ("Rajesh Pillai",   "rajesh@disasterbridge.com", "+91-9821007788", "general",    ["driving", "cooking"],         "off_duty"),
        ("Divya Iyer",      "divya@disasterbridge.com",  "+91-9821009900", "medic",      ["medical", "counseling"],      "available"),
    ]

    # Only insert if table is empty
    count = con.execute(text("SELECT COUNT(*) FROM volunteers")).scalar()
    if count == 0:
        for name, email, phone, role, skills, status in volunteers:
            skills_pg = "{" + ",".join(skills) + "}"
            con.execute(text("""
                INSERT INTO volunteers (full_name, email, phone, role, skills, status)
                VALUES (:name, :email, :phone, :role, :skills, :status)
            """), {"name": name, "email": email, "phone": phone,
                   "role": role, "skills": skills_pg, "status": status})
        con.execute(text("COMMIT"))
        print(f"Seeded {len(volunteers)} volunteers")
    else:
        print(f"Volunteers table already has {count} rows - skipping seed")

    rows = con.execute(text("SELECT full_name, role, status FROM volunteers ORDER BY role")).fetchall()
    print("\nVolunteers:")
    for r in rows:
        print(f"  {r[0]:<20} {r[1]:<12} {r[2]}")
