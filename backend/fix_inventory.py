"""
Fix: reset_inventory.py created a duplicate food row instead of updating the existing one.
This script removes the zero-quantity duplicates (keeping the highest-quantity row per type)
and then resets all to seeds.
"""
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')

with engine.connect() as con:
    # Show current state
    rows = con.execute(text("SELECT id, resource_type::TEXT, quantity, status::TEXT FROM resource_items ORDER BY resource_type, quantity DESC")).fetchall()
    print("Before cleanup:")
    for r in rows:
        print(f"  {r[0]} | {r[1]:<10} | qty={r[2]:.1f} | {r[3]}")

    # Delete zero-quantity rows for food (the depleted duplicates from old sessions)
    # Keep only one row per resource_type - the one with highest quantity
    con.execute(text("""
        DELETE FROM resource_items
        WHERE id NOT IN (
            SELECT DISTINCT ON (resource_type) id
            FROM resource_items
            ORDER BY resource_type, quantity DESC
        )
    """))
    con.execute(text("COMMIT"))

    # Now reset to seeds
    updates = [
        ('food',    5000.0, 'kg',    'available'),
        ('water',   8000.0, 'liters','available'),
        ('medical',  500.0, 'kits',  'available'),
        ('shelter',  200.0, 'units', 'available'),
    ]
    for rtype, qty, unit, status in updates:
        con.execute(text(
            "UPDATE resource_items SET quantity=:q, status=:s WHERE resource_type::TEXT=:t"
        ), {"q": qty, "s": status, "t": rtype})
    con.execute(text("COMMIT"))

    # Show final state
    rows = con.execute(text("SELECT id, resource_type::TEXT, quantity, unit, status::TEXT FROM resource_items ORDER BY resource_type")).fetchall()
    print("\nAfter cleanup + reset:")
    for r in rows:
        print(f"  {r[0]} | {r[1]:<10} | qty={r[2]:.1f} {r[3]:<8} | {r[4]}")
