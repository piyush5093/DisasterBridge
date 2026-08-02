"""
Tests for app/services/ingestion/pipeline.py — verifies orchestration
logic (per-source isolation on failure, result aggregation) using
mocked external clients so no real network calls happen, against
mongomock-motor so no real MongoDB is needed either.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from app.models.disaster_event import DisasterEvent
from app.services.external.gdacs_client import GDACSClientError
from app.services.ingestion.pipeline import run_full_ingestion, run_ndma_ingestion

FIXTURES = Path(__file__).parent / "fixtures"


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    client = AsyncMongoMockClient()
    await init_beanie(database=client["pipeline_test_db"], document_models=[DisasterEvent])
    yield


@pytest.mark.asyncio
async def test_run_full_ingestion_aggregates_both_sources():
    gdacs_data = json.loads((FIXTURES / "gdacs_sample_response.json").read_text())
    usgs_data = json.loads((FIXTURES / "usgs_sample_response.json").read_text())

    with (
        patch("app.services.ingestion.pipeline.GDACSClient") as MockGDACS,
        patch("app.services.ingestion.pipeline.USGSClient") as MockUSGS,
    ):
        MockGDACS.return_value.get_active_events = AsyncMock(return_value=gdacs_data)
        MockUSGS.return_value.get_summary_feed = AsyncMock(return_value=usgs_data)

        run = await run_full_ingestion()

    assert len(run.results) == 2
    assert run.failures == []
    assert run.total_created == 3 + 2  # 3 valid GDACS features + 2 USGS features
    assert run.total_skipped == 1  # 1 malformed GDACS feature


@pytest.mark.asyncio
async def test_gdacs_failure_does_not_block_usgs():
    usgs_data = json.loads((FIXTURES / "usgs_sample_response.json").read_text())

    with (
        patch("app.services.ingestion.pipeline.GDACSClient") as MockGDACS,
        patch("app.services.ingestion.pipeline.USGSClient") as MockUSGS,
    ):
        MockGDACS.return_value.get_active_events = AsyncMock(side_effect=GDACSClientError("simulated outage"))
        MockUSGS.return_value.get_summary_feed = AsyncMock(return_value=usgs_data)

        run = await run_full_ingestion()

    assert len(run.results) == 1  # only USGS succeeded
    assert len(run.failures) == 1
    assert "GDACS" in run.failures[0]
    assert run.total_created == 2  # USGS still ingested despite GDACS failing


@pytest.mark.asyncio
async def test_ndma_ingestion_polls_supplied_identifiers():
    cap_xml = (FIXTURES / "cap_alert_flood.xml").read_bytes()

    from app.utils.cap_parser import parse_cap_alert

    parsed = parse_cap_alert(cap_xml)

    with patch("app.services.ingestion.pipeline.NDMAClient") as MockNDMA:
        MockNDMA.return_value.fetch_alert = AsyncMock(return_value=parsed)

        run = await run_ndma_ingestion(["NDMA-2026-FL-000123"])

    assert len(run.results) == 1
    assert run.total_created == 1
    assert run.failures == []
