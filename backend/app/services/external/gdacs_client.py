"""
GDACS (Global Disaster Alert and Coordination System) API client.

Endpoints used (confirmed from GDACS's public API quick-start docs and
Monty/STAC extension documentation — https://www.gdacs.org/Documents/2025/GDACS_API_quickstart_v1.pdf):

- EVENTS4APP: https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP
  No query params. Returns a GeoJSON FeatureCollection of currently active
  events across all types — this is what the GDACS mobile app itself uses,
  so it's the simplest "give me what's live right now" call.

- SEARCH: https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
  Query params for custom extraction:
    eventlist   - semicolon-separated event type codes, e.g. "EQ;TC;FL"
    fromdate    - YYYY-MM-DD
    todate      - YYYY-MM-DD
    alertlevel  - "green" | "orange" | "red" (single value per GDACS docs)
  Returns a GeoJSON FeatureCollection.

- geteventdata: https://www.gdacs.org/gdacsapi/api/events/geteventdata?eventtype=FL&eventid=1102983
  Single-event detail lookup, optionally with &episodeid=N for a specific episode.

VERIFIED against a live response (2026-07-24): fetched the SEARCH endpoint
directly and confirmed the property key names assumed in
`gdacs_ingestion.py` — eventid, eventtype, episodeid, eventname, name,
alertlevel, alertscore, episodealertlevel, episodealertscore, severitydata
{severity, severitytext, severityunit}, country, iso3, fromdate, todate,
datemodified, iscurrent (a *string* "true"/"false", not a JSON bool — the
normalizer already handles this), and url.{report, details, geometry} all
match exactly. `population` was NOT present in any live feature checked —
it's fine that the normalizer treats it as optional.

One open question from that same check: `eventlist` (tried both
comma- and semicolon-separated) and `fromdate`/`todate` did not appear to
actually narrow the result set — requests with different filter values
returned the same ~100 most-recent-across-all-types events. This may be a
quirk of the endpoint, a param-name mismatch, or specific to the date
ranges tried. Until confirmed, treat SEARCH as "recent events, filters
best-effort" and rely on `event_type` in the stored rows (and the
`list_events` API filters) for the source of truth rather than the
request params alone.
"""

from datetime import date, datetime
from typing import Any

import httpx

from app.core.config import settings

EVENTS4APP_PATH = "events/geteventlist/EVENTS4APP"
SEARCH_PATH = "events/geteventlist/SEARCH"
EVENT_DETAIL_PATH = "events/geteventdata"

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


class GDACSClientError(Exception):
    """Raised when the GDACS API returns an error or an unparseable response."""


class GDACSClient:
    def __init__(self, base_url: str | None = None, timeout: httpx.Timeout = DEFAULT_TIMEOUT):
        self.base_url = (base_url or settings.GDACS_API_BASE).rstrip("/")
        self._timeout = timeout

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.base_url}/{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise GDACSClientError(
                    f"GDACS API returned {exc.response.status_code} for {exc.request.url}"
                ) from exc
            except httpx.RequestError as exc:
                raise GDACSClientError(f"GDACS API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise GDACSClientError("GDACS API returned a non-JSON response") from exc

    async def get_active_events(self) -> dict:
        """
        Fetch all currently active events (EVENTS4APP). No parameters —
        this mirrors what the official GDACS app displays.
        """
        return await self._get(EVENTS4APP_PATH)

    async def search_events(
        self,
        event_types: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        alert_level: str | None = None,
    ) -> dict:
        """
        Custom extraction via the SEARCH endpoint.

        event_types: GDACS codes — any of EQ, TC, FL, VO, WF, DR.
        alert_level: "green", "orange", or "red" (GDACS accepts one value
                     per request based on published examples).

        Filters are also re-applied client-side on the response (see
        `_apply_client_side_filters` below): live testing on 2026-07-24
        showed the server-side eventlist/fromdate/todate params don't
        reliably narrow GDACS's own result set, so this method guarantees
        the *caller's* filter contract even when the API's does not.
        """
        params: dict[str, Any] = {}
        if event_types:
            params["eventlist"] = ";".join(event_types)
        if from_date:
            params["fromdate"] = from_date.isoformat()
        if to_date:
            params["todate"] = to_date.isoformat()
        if alert_level:
            params["alertlevel"] = alert_level.lower()

        geojson = await self._get(SEARCH_PATH, params=params)
        geojson["features"] = self._apply_client_side_filters(
            geojson.get("features", []), event_types, from_date, to_date, alert_level
        )
        return geojson

    @staticmethod
    def _apply_client_side_filters(
        features: list[dict[str, Any]],
        event_types: list[str] | None,
        from_date: date | None,
        to_date: date | None,
        alert_level: str | None,
    ) -> list[dict[str, Any]]:
        if not (event_types or from_date or to_date or alert_level):
            return features

        wanted_types = {t.upper() for t in event_types} if event_types else None
        wanted_alert = alert_level.capitalize() if alert_level else None
        filtered = []

        for feature in features:
            props = feature.get("properties", {}) or {}

            if wanted_types and str(props.get("eventtype", "")).upper() not in wanted_types:
                continue
            if wanted_alert and str(props.get("alertlevel", "")) != wanted_alert:
                continue

            feature_from = props.get("fromdate")
            if from_date and feature_from:
                try:
                    if datetime.fromisoformat(str(feature_from).replace("Z", "")).date() < from_date:
                        continue
                except ValueError:
                    pass

            feature_to = props.get("todate")
            if to_date and feature_to:
                try:
                    if datetime.fromisoformat(str(feature_to).replace("Z", "")).date() > to_date:
                        continue
                except ValueError:
                    pass

            filtered.append(feature)

        return filtered

    async def get_event_detail(
        self, event_type: str, event_id: str, episode_id: str | None = None
    ) -> dict:
        """Fetch a single event (optionally a specific episode)."""
        params: dict[str, Any] = {"eventtype": event_type, "eventid": event_id}
        if episode_id:
            params["episodeid"] = episode_id
        return await self._get(EVENT_DETAIL_PATH, params=params)
