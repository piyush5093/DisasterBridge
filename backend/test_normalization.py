import pytest
from services import normalize_event_type, normalize_alert_level
from models import EventTypeEnum, AlertLevelEnum

def test_normalize_event_type():
    assert normalize_event_type("Earthquake - 6.5M") == EventTypeEnum.earthquake
    assert normalize_event_type("EQ") == EventTypeEnum.earthquake
    assert normalize_event_type("Flash Flood") == EventTypeEnum.flood
    assert normalize_event_type("FL") == EventTypeEnum.flood
    assert normalize_event_type("Tropical Cyclone") == EventTypeEnum.cyclone
    assert normalize_event_type("Severe Drought") == EventTypeEnum.drought
    assert normalize_event_type("Wildfire warning") == EventTypeEnum.wildfire
    assert normalize_event_type("Unknown Disaster") == EventTypeEnum.other

def test_normalize_alert_level():
    assert normalize_alert_level("Red Alert") == AlertLevelEnum.red
    assert normalize_alert_level("ORANGE") == AlertLevelEnum.orange
    assert normalize_alert_level("green_status") == AlertLevelEnum.green
    assert normalize_alert_level("unspecified") == AlertLevelEnum.low
