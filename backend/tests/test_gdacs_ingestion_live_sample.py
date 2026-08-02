"""
Validates `normalize_feature` against a REAL response captured live from
the GDACS SEARCH endpoint on 2026-07-24 (see fixtures/gdacs_live_sample_2026-07-24.json),
as opposed to test_gdacs_ingestion.py's hand-built fixture. This is what
confirms the field-name assumptions in gdacs_ingestion.py/gdacs_client.py
are actually correct rather than merely plausible.

Key things this live sample caught that the hand-built fixture didn't:
- `fromdate`/`todate` have no 'Z' suffix and no timezone offset at all
  (e.g. "2026-07-23T06:00:00"), unlike the fixture's "...Z" values.
- `iscurrent` is the literal string "true"/"false", not a JSON boolean.
"""

import json
from pathlib import Path

from app.services.ingestion.gdacs_ingestion import normalize_feature

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gdacs_live_sample_2026-07-24.json"


def load_fixture() -> dict:
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def test_live_tropical_cyclone_feature_normalizes_correctly():
    data = load_fixture()
    feature = data["features"][0]  # TC ELEVEN-26

    normalized = normalize_feature(feature)

    assert normalized is not None
    assert normalized["source"] == "GDACS"
    assert normalized["external_event_id"] == "1001294"
    assert normalized["episode_id"] == "2"
    assert normalized["event_type"] == "TC"
    assert normalized["alert_level"] == "Orange"
    assert normalized["alert_score"] == 2
    assert normalized["severity_value"] == 138.888
    assert normalized["severity_unit"] == "km/h"
    assert normalized["country"] == "China"
    assert normalized["iso3"] == "CHN"
    assert normalized["source_url"] == (
        "https://www.gdacs.org/report.aspx?eventid=1001294&episodeid=2&eventtype=TC"
    )


def test_live_sample_naive_datetime_is_assumed_utc():
    """The real API returns 'fromdate' with no offset at all — confirm we
    don't silently drop it or crash, and that we attach UTC rather than
    leaving it naive (since the DB column is timezone-aware)."""
    data = load_fixture()
    feature = data["features"][0]

    normalized = normalize_feature(feature)

    assert normalized["from_date"] is not None
    assert normalized["from_date"].tzinfo is not None
    assert normalized["from_date"].year == 2026
    assert normalized["from_date"].month == 7
    assert normalized["from_date"].day == 23


def test_live_sample_string_iscurrent_parses_as_bool():
    data = load_fixture()
    current_feature = data["features"][0]  # iscurrent: "true"
    past_feature = data["features"][1]  # iscurrent: "false"

    assert normalize_feature(current_feature)["is_current"] is True
    assert normalize_feature(past_feature)["is_current"] is False


def test_live_drought_event_with_multi_country_string():
    """DR events report `country` as a comma-joined string of multiple
    countries (e.g. "Ethiopia, Kenya, Somalia") rather than one ISO3 —
    confirm this passes through as-is rather than erroring."""
    data = load_fixture()
    feature = data["features"][2]  # DR East Africa-2026

    normalized = normalize_feature(feature)

    assert normalized is not None
    assert normalized["country"] == "Ethiopia, Kenya, Somalia"
    assert normalized["severity_unit"] == "km2"
