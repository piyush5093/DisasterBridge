import urllib.request
import json

base = "http://localhost:8000"
ids = [
    ("red",    "f6c3be8f-3faf-4550-a091-bbc3ae77bce8"),
    ("red",    "eecddff8-cb0f-4fa4-9608-443b6ce30f26"),
    ("orange", "8fddcb0a-e30e-408a-9fe0-5a8701dc3488"),
    ("green",  "0ed47235-ef42-4b8f-8f5e-b359478cb395"),
]

for level, event_id in ids:
    url = f"{base}/api/zones/classify?event_id={event_id}"
    req = urllib.request.Request(url, data=b'{}', method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            print(f"SUCCESS [{level}] id={event_id[:8]}... status={data['status']} severity={data['severity_score']:.1f} priority={data['priority']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"FAIL [{level}] id={event_id[:8]}... HTTP {e.code}: {body}")
    except Exception as e:
        print(f"ERROR [{level}] id={event_id[:8]}... {e}")
