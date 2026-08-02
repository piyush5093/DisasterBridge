"""
Unified data normalization pipeline — orchestrates all source-specific
ingestion modules (gdacs_ingestion, usgs_ingestion; NDMA excluded, see
below) behind one call, so a single scheduled job (Celery beat, or a
simple cron hitting the API) keeps `disaster_events` up to date across
every feed without the caller needing to know about each source
individually.

NDMA is deliberately NOT included in `run_full_ingestion`: per
ndma_client.py's documented limitation, there's no confirmed public
endpoint to discover which CAP alert identifiers are currently active,
so NDMA ingestion can only run against specific identifiers supplied by
the caller (see `run_ndma_ingestion` below, kept separate for that
reason) rather than being pollable "as a whole" the way GDACS/USGS are.
"""

from dataclasses import dataclass, field

from app.schemas.disaster_event import IngestionResult
from app.services.external.gdacs_client import GDACSClient, GDACSClientError
from app.services.external.ndma_client import NDMAClient, NDMAClientError
from app.services.external.usgs_client import USGSClient, USGSClientError
from app.services.ingestion.gdacs_ingestion import upsert_events as gdacs_upsert
from app.services.ingestion.ndma_ingestion import upsert_alert as ndma_upsert
from app.services.ingestion.usgs_ingestion import upsert_events as usgs_upsert


@dataclass
class PipelineRunResult:
    results: list[IngestionResult] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def total_created(self) -> int:
        return sum(r.created for r in self.results)

    @property
    def total_updated(self) -> int:
        return sum(r.updated for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.skipped for r in self.results)


async def run_full_ingestion(usgs_min_magnitude: float = 4.5) -> PipelineRunResult:
    """
    Pull everything currently pollable without prior knowledge (GDACS
    active events + a recent USGS summary feed) and upsert it all.
    One source failing doesn't abort the others — each is isolated so a
    GDACS outage, say, doesn't block USGS ingestion.
    """
    run = PipelineRunResult()

    gdacs_client = GDACSClient()
    try:
        geojson = await gdacs_client.get_active_events()
        run.results.append(await gdacs_upsert(geojson.get("features", [])))
    except GDACSClientError as exc:
        run.failures.append(f"GDACS: {exc}")

    usgs_client = USGSClient()
    try:
        geojson = await usgs_client.get_summary_feed(feed="4.5_day")
        run.results.append(await usgs_upsert(geojson.get("features", [])))
    except USGSClientError as exc:
        run.failures.append(f"USGS: {exc}")

    return run


async def run_ndma_ingestion(identifiers: list[str]) -> PipelineRunResult:
    """
    Poll a caller-supplied list of NDMA CAP identifiers (see module
    docstring for why this can't be "everything active" like the other
    two sources). One shared NDMAClient is used across the batch so its
    mandatory ETag cache actually does its job across calls.
    """
    run = PipelineRunResult()
    client = NDMAClient()

    for identifier in identifiers:
        try:
            alert = await client.fetch_alert(identifier)
        except NDMAClientError as exc:
            run.failures.append(f"NDMA[{identifier}]: {exc}")
            continue

        if alert is None:
            run.results.append(IngestionResult(source="NDMA", fetched=0, created=0, updated=0, skipped=0))
            continue

        run.results.append(await ndma_upsert(alert))

    return run
