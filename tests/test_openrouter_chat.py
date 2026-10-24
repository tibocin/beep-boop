# tests/test_openrouter_chat.py
# Purpose: Lock the OpenRouter chat client I/O from tkt:openrouter-chat-client.
# Related: modules/core/openrouter_chat.py, modules/core/llm_client.py
# Tags: test, openrouter, chat

"""Programmatic checks for the OpenRouter client and the unified fallback."""

import asyncio

from modules.core.llm_client import UnifiedLLMClient
from modules.core.openrouter_chat import (
    OpenRouterChatClient,
    OpenRouterConfigError,
    OpenRouterHTTPError,
)

SECRET = "sk-test-secret"


def _ok_payload():
    return {
        "model": "openai/gpt-4o-mini",
        "choices": [
            {"message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def test_chat_completion_returns_pong():
    async def transport(url, headers, body, timeout):
        assert url.endswith("/chat/completions")
        assert headers["Authorization"] == f"Bearer {SECRET}"
        assert body["messages"][-1]["content"] == "ping"
        return 200, _ok_payload()

    client = OpenRouterChatClient(api_key=SECRET, transport=transport)

    result = asyncio.run(
        client.chat_completion([{"role": "user", "content": "ping"}])
    )

    assert result["text"] == "pong"
    assert result["metadata"]["provider"] == "openrouter"
    assert result["usage"]["total_tokens"] == 2


def test_missing_key_raises_without_echoing_secret():
    client = OpenRouterChatClient(api_key="", transport=_unused)

    try:
        asyncio.run(client.chat_completion([{"role": "user", "content": "ping"}]))
    except OpenRouterConfigError as exc:
        assert SECRET not in str(exc)
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("expected OpenRouterConfigError")


def test_http_401_redacts_key():
    async def transport(url, headers, body, timeout):
        return 401, {"error": f"bad key {SECRET}"}

    client = OpenRouterChatClient(api_key=SECRET, transport=transport)

    try:
        asyncio.run(client.chat_completion([{"role": "user", "content": "ping"}]))
    except OpenRouterHTTPError as exc:
        assert exc.status_code == 401
        assert SECRET not in str(exc)
    else:
        raise AssertionError("expected OpenRouterHTTPError")


def test_unified_client_uses_openrouter_when_ollama_is_down():
    class FakeOpenRouter:
        def __init__(self):
            self.api_key = "present"

        async def chat_completion(self, messages, temperature=0.7, max_tokens=None, system_prompt=None):
            assert messages[0]["content"] == "hi"
            return {"text": "via-or", "usage": {}, "metadata": {"provider": "openrouter"}}

    async def scenario():
        client = UnifiedLLMClient(
            enable_fallback=True,
            cloud_provider="openrouter",
            openrouter_client=FakeOpenRouter(),
        )

        async def down():
            return False

        client._check_ollama_health = down
        return await client.chat_completion([{"role": "user", "content": "hi"}])

    result = asyncio.run(scenario())
    assert result["text"] == "via-or"
    assert result["metadata"]["provider"] == "openrouter"


async def _unused(url, headers, body, timeout):
    raise AssertionError("transport should not run without a key")
