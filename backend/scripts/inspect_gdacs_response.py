"""
Spot-check GDACS API responses against what gdacs_ingestion.py expects.

The field mapping in gdacs_ingestion.py has already been verified against
a live GDACS response (2026-07-24 — see the docstrings in gdacs_client.py
and tests/test_gdacs_ingestion_live_sample.py, which pins that response
as a fixture). Run this script when you want to re-check that GDACS
hasn't changed its schema since, or to eyeball what's currently active.

Usage:
    python scripts/inspect_gdacs_response.py
"""

import asyncio
import json

from app.services.external.gdacs_client import GDACSClient


async def main() -> None:
    client = GDACSClient()
    geojson = await client.get_active_events()

    features = geojson.get("features", [])
    print(f"Fetched {len(features)} active events from GDACS EVENTS4APP.\n")

    if not features:
        print("No active events right now — try search_events() with a wider date range instead.")
        return

    first = features[0]
    print("Geometry type of first feature:", first.get("geometry", {}).get("type"))
    print("\nProperty keys present on first feature:")
    for key in sorted(first.get("properties", {}).keys()):
        print(f"  - {key}")

    print("\nFull first feature (pretty-printed):")
    print(json.dumps(first, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
