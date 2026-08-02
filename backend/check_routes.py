import sys
sys.path.insert(0, '.')
from app.main import app

print(f'Total routes: {len(app.routes)}')
for r in app.routes:
    path = getattr(r, 'path', '?')
    methods = getattr(r, 'methods', None)
    print(f'  {sorted(methods) if methods else "ROUTER"} => {path}')
