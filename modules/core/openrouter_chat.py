# modules/core/openrouter_chat.py
# Purpose: OpenRouter chat-completions client for beep-boop cloud fallback.
# Related: modules/core/llm_client.py UnifiedLLMClient, env OPENROUTER_API_KEY
# Tags: openrouter, chat, llm, fallback

"""Chat completions against the OpenRouter OpenAI-compatible API.

The API key stays in the process environment. Errors never include it.
"""

from __future__ import annotations

import json
import os
from typing import Any, Awaitable, Callable, Dict, List, Optional

import aiohttp

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
# Transport: (url, headers, json body, timeout seconds) -> (status, payload)
Transport = Callable[[str, Dict[str, str], Dict[str, Any], float], Awaitable[tuple[int, Any]]]


class OpenRouterConfigError(RuntimeError):
    """Raised when the client cannot call OpenRouter because config is missing."""


class OpenRouterHTTPError(RuntimeError):
    """Raised when OpenRouter returns a non-success status or an unusable body."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(f"openrouter http {status_code}: {detail}")


def _redact(text: str, secret: str) -> str:
    """Drop the API key and clip text so logs cannot leak credentials."""
    cleaned = text.replace(secret, "[redacted]") if secret else text
    return cleaned[:180]


async def _aiohttp_transport(
    url: str,
    headers: Dict[str, str],
    body: Dict[str, Any],
    timeout: float,
) -> tuple[int, Any]:
    """POST JSON with aiohttp. Side effect: one HTTPS request."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.post(url, headers=headers, json=body) as response:
            raw = await response.text()
    try:
        payload: Any = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"raw": raw[:180]}
    return response.status, payload


class OpenRouterChatClient:
    """Async chat client for OpenRouter /chat/completions.

    Inputs are chat messages. Output is the unified dict shape
    `{text, usage, metadata}` used by UnifiedLLMClient.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        transport: Optional[Transport] = None,
    ) -> None:
        # None reads the environment. An explicit empty string stays empty.
        if api_key is None:
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.api_key = api_key or ""
        self.model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL
        configured = base_url or os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = configured.rstrip("/")
        self.timeout = timeout
        self._transport = transport or _aiohttp_transport

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST one chat completion. Raises OpenRouterConfigError or OpenRouterHTTPError.

        Does not log the bearer token. Mutation: network I/O via the transport.
        """
        if not self.api_key:
            raise OpenRouterConfigError("OPENROUTER_API_KEY is not set")

        outbound = list(messages)
        if system_prompt:
            outbound = [{"role": "system", "content": system_prompt}] + outbound

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": outbound,
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            status, payload = await self._transport(url, headers, body, self.timeout)
        except Exception as exc:
            detail = _redact(str(exc), self.api_key)
            raise OpenRouterHTTPError(0, detail or "transport failed") from exc

        if status != 200:
            detail = _redact(json.dumps(payload) if not isinstance(payload, str) else payload, self.api_key)
            raise OpenRouterHTTPError(status, detail or "request failed")
        return self._parse_success(payload)

    def _parse_success(self, payload: Any) -> Dict[str, Any]:
        """Map an OpenRouter 200 body onto the unified completion dict."""
        if not isinstance(payload, dict):
            raise OpenRouterHTTPError(200, "response was not an object")
        choices = payload.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise OpenRouterHTTPError(200, "response missing choices")
        message = choices[0].get("message") or {}
        text = message.get("content")
        if not isinstance(text, str):
            raise OpenRouterHTTPError(200, "response missing message content")
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return {
            "text": text,
            "usage": {
                "total_tokens": int(usage.get("total_tokens") or 0),
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
            },
            "metadata": {
                "model": payload.get("model") or self.model,
                "finish_reason": choices[0].get("finish_reason") or "stop",
                "streamed": False,
                "provider": "openrouter",
            },
        }
