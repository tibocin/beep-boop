# modules/core/pcs_tone.py
# Purpose: Map a PCS prompt-generation payload to Tone, or fall back locally.
# Related: modules/enums.py Tone, PCS POST /api/v1/prompts/generate
# Tags: pcs, tone, fallback

"""PCS is optional. A missing or unknown tone becomes conversational.

The API key is never copied into ToneResolution.reason.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional

import aiohttp

from ..enums import Tone

DEFAULT_TONE = Tone.CONVERSATIONAL
GENERATE_PATH = "/api/v1/prompts/generate"
Transport = Callable[[str, Dict[str, str], Dict[str, Any], float], Awaitable[tuple[int, Any]]]

_ALIASES = {
    "matter-of-fact": "matter_of_fact",
    "matter of fact": "matter_of_fact",
    "shamanic-esoteric": "shamanic_esoteric",
    "shamanic esoteric": "shamanic_esoteric",
}


class PcsToneUnavailable(RuntimeError):
    """Raised when PCS cannot be asked for a tone. Message must not include the key."""


@dataclass(frozen=True)
class ToneResolution:
    """Result of a tone lookup.

    source is 'pcs' when a known tone was present, otherwise 'fallback'.
    """

    tone: Tone
    source: str
    reason: str


def coerce_tone(value: object) -> Optional[Tone]:
    """Return a Tone for a known label, or None when the value is unusable."""
    if not isinstance(value, str):
        return None
    raw = value.strip().lower()
    if not raw:
        return None
    key = _ALIASES.get(raw, raw.replace("-", "_").replace(" ", "_"))
    try:
        return Tone(key)
    except ValueError:
        return None


def _candidate_values(payload: Mapping[str, Any]) -> list[object]:
    """Tone fields in the order PCS generation is trusted."""
    found: list[object] = []
    variables = payload.get("variables_resolved")
    if isinstance(variables, Mapping):
        found.append(variables.get("tone"))
    metadata = payload.get("metadata")
    if isinstance(metadata, Mapping):
        found.append(metadata.get("tone"))
    context = payload.get("context_used")
    if isinstance(context, Mapping):
        found.append(context.get("tone"))
    found.append(payload.get("tone"))
    return found


def tone_from_pcs_payload(payload: object) -> Optional[Tone]:
    """First known tone in the PCS payload, or None."""
    if not isinstance(payload, Mapping):
        return None
    for value in _candidate_values(payload):
        tone = coerce_tone(value)
        if tone is not None:
            return tone
    return None


def resolution_from_payload(
    payload: object,
    *,
    fallback: Tone = DEFAULT_TONE,
) -> ToneResolution:
    """Map a payload that was already fetched. None and unknown tones fall back."""
    tone = tone_from_pcs_payload(payload)
    if tone is None:
        return ToneResolution(fallback, "fallback", "pcs_tone_missing")
    return ToneResolution(tone, "pcs", "pcs_tone")


async def resolve_tone(
    fetch: Callable[[], Awaitable[object]],
    *,
    fallback: Tone = DEFAULT_TONE,
) -> ToneResolution:
    """Call fetch and fall back when it fails or returns no known tone.

    Side effect: whatever fetch does. The reason names the exception type only.
    """
    try:
        payload = await fetch()
    except Exception as exc:
        return ToneResolution(fallback, "fallback", f"pcs_unavailable:{type(exc).__name__}")
    return resolution_from_payload(payload, fallback=fallback)


def _redact(text: str, secret: str) -> str:
    cleaned = text.replace(secret, "[redacted]") if secret else text
    return cleaned[:180]


async def _aiohttp_transport(
    url: str,
    headers: Dict[str, str],
    body: Dict[str, Any],
    timeout: float,
) -> tuple[int, Any]:
    """POST JSON to PCS. Side effect: one HTTP request."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.post(url, headers=headers, json=body) as response:
            raw = await response.text()
    try:
        payload: Any = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"raw": _redact(raw, "")}
    return response.status, payload


def pcs_tone_fetcher(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    template_name: str = "beep-boop-tone",
    variables: Optional[Dict[str, Any]] = None,
    transport: Optional[Transport] = None,
    timeout: float = 5.0,
) -> Callable[[], Awaitable[object]]:
    """Build a fetch coroutine for POST /api/v1/prompts/generate.

    None for api_key reads PCS_API_KEY. An explicit empty string stays empty.
    """
    if api_key is None:
        api_key = os.environ.get("PCS_API_KEY", "")
    secret = api_key or ""
    root = (base_url or os.environ.get("PCS_BASE_URL") or "http://localhost:8000").rstrip("/")
    send = transport or _aiohttp_transport

    async def fetch() -> object:
        if not secret:
            raise PcsToneUnavailable("PCS_API_KEY is not set")
        url = f"{root}{GENERATE_PATH}"
        headers = {"X-API-Key": secret, "Content-Type": "application/json"}
        body = {"template_name": template_name, "variables": variables or {}}
        try:
            status, payload = await send(url, headers, body, timeout)
        except Exception as exc:
            raise PcsToneUnavailable(_redact(str(exc), secret) or "transport failed") from exc
        if status != 200:
            detail = payload if isinstance(payload, str) else json.dumps(payload)
            raise PcsToneUnavailable(f"pcs http {status}: {_redact(detail, secret)}")
        if not isinstance(payload, dict):
            raise PcsToneUnavailable("pcs response was not an object")
        return payload

    return fetch
