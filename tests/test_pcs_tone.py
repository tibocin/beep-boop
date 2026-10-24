# tests/test_pcs_tone.py
# Purpose: Lock PCS tone fallback I/O for tkt:pcs-tone-fallback.
# Related: modules/core/pcs_tone.py, modules/enums.py Tone
# Tags: test, pcs, tone, fallback

"""Known PCS tones pass through. Everything else is conversational."""

import asyncio

from modules.core.pcs_tone import (
    pcs_tone_fetcher,
    resolve_tone,
    tone_from_pcs_payload,
)
from modules.enums import Tone

SECRET = "pcs-test-key"


def test_variables_resolved_professional():
    tone = tone_from_pcs_payload({"variables_resolved": {"tone": "professional"}})
    assert tone is Tone.PROFESSIONAL


def test_metadata_matter_of_fact_alias():
    tone = tone_from_pcs_payload({"metadata": {"tone": "matter-of-fact"}})
    assert tone is Tone.MATTER_OF_FACT


def test_variables_win_over_metadata():
    tone = tone_from_pcs_payload(
        {
            "variables_resolved": {"tone": "casual"},
            "metadata": {"tone": "professional"},
        }
    )
    assert tone is Tone.CASUAL


def test_unknown_tone_falls_back():
    async def fetch():
        return {"variables_resolved": {"tone": "enthusiastic"}}

    result = asyncio.run(resolve_tone(fetch))
    assert result.tone is Tone.CONVERSATIONAL
    assert result.source == "fallback"
    assert result.reason == "pcs_tone_missing"


def test_timeout_falls_back_without_the_key():
    async def fetch():
        raise TimeoutError(f"timed out {SECRET}")

    result = asyncio.run(resolve_tone(fetch))
    assert result.tone is Tone.CONVERSATIONAL
    assert result.source == "fallback"
    assert result.reason == "pcs_unavailable:TimeoutError"
    assert SECRET not in result.reason


def test_http_503_falls_back_and_hides_the_key():
    async def transport(url, headers, body, timeout):
        assert headers["X-API-Key"] == SECRET
        assert url.endswith("/api/v1/prompts/generate")
        return 503, {"error": f"down {SECRET}"}

    fetch = pcs_tone_fetcher(
        base_url="http://pcs.local",
        api_key=SECRET,
        transport=transport,
    )

    async def scenario():
        try:
            await fetch()
        except Exception as exc:
            assert SECRET not in str(exc)
        return await resolve_tone(fetch)

    result = asyncio.run(scenario())
    assert result.source == "fallback"
    assert result.tone is Tone.CONVERSATIONAL
    assert SECRET not in result.reason
