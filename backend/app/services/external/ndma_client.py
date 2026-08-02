"""
NDMA SACHET CAP alert feed client.

CONFIRMED against NDMA's own published integration guide (fetched
2026-07-24 from https://sachet.ndma.gov.in/docs/Integration_Guide_For_Agencies.pdf,
linked from the "RSS FEED" / https://sachet.ndma.gov.in/CapFeed page):

  GET https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=<ID>

returns one CAP v1.2 XML document for the alert with that `identifier`,
and supports ETag-based caching:
  - First request: 200 OK + XML body + `ETag: "<value>"` response header.
  - Subsequent requests MUST send `If-None-Match: "<value>"`.
  - Server returns 304 Not Modified (no body) if unchanged, or a fresh
    200 + new ETag if the alert was updated.
NDMA's guide states this caching is *mandatory* for consuming agencies
(to avoid unnecessary load), so this client always sends `If-None-Match`
once it has a cached ETag for that identifier, and callers should treat
a `None` XML return as "unchanged, keep using what's already in the DB".

⚠️ IMPORTANT LIMITATION: `identifier` is the CAP alert's OWN identifier
(a value NDMA assigns per-alert), not a discovery mechanism. The public
integration guide describes fetching a *known* identifier, but does not
document a public "list current active alert identifiers" endpoint —
that appears to be provided separately during agency onboarding with
NDMA (the guide is titled "for Agencies", implying registration).
Until that discovery endpoint is confirmed, this client can only fetch
alerts by identifier that the caller already knows about (e.g. from a
partner feed, manual entry, or an onboarding-provided list) — it cannot
independently discover "what alerts exist right now" the way GDACS's
EVENTS4APP or USGS's summary feeds do. Flagged clearly rather than
guessing at an unconfirmed listing endpoint.
"""

import httpx

from app.utils.cap_parser import ParsedCapAlert, parse_cap_alert

FETCH_XML_URL = "https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile"

DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)


class NDMAClientError(Exception):
    """Raised when the NDMA CAP feed returns an error or unparseable response."""


class NDMAClient:
    """
    Stateful per-identifier ETag cache lives on the instance (`_etags`).
    For Day 5's scheduled ingestion, one long-lived NDMAClient instance
    should be reused across polling cycles so the ETag cache persists
    between runs — a fresh instance per call defeats the caching NDMA
    requires.
    """

    def __init__(self, timeout: httpx.Timeout = DEFAULT_TIMEOUT):
        self._timeout = timeout
        self._etags: dict[str, str] = {}

    async def fetch_alert(self, identifier: str) -> ParsedCapAlert | None:
        """
        Fetch and parse one CAP alert by identifier.

        Returns:
          - a ParsedCapAlert if the alert is new or has changed
          - None if the server returned 304 Not Modified (alert unchanged
            since the last fetch — caller should keep the existing DB row)
          - None if the alert genuinely couldn't be parsed (logged as an
            error via NDMAClientError being raised instead, for anything
            that isn't a clean 304)
        """
        headers = {}
        cached_etag = self._etags.get(identifier)
        if cached_etag:
            headers["If-None-Match"] = cached_etag

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(
                    FETCH_XML_URL, params={"identifier": identifier}, headers=headers
                )
            except httpx.RequestError as exc:
                raise NDMAClientError(f"NDMA CAP feed request failed: {exc}") from exc

        if response.status_code == 304:
            return None  # unchanged — caller keeps existing data

        if response.status_code != 200:
            raise NDMAClientError(
                f"NDMA CAP feed returned {response.status_code} for identifier={identifier}"
            )

        new_etag = response.headers.get("ETag")
        if new_etag:
            self._etags[identifier] = new_etag

        parsed = parse_cap_alert(response.content)
        if parsed is None:
            raise NDMAClientError(f"NDMA CAP feed returned unparseable XML for identifier={identifier}")

        return parsed
