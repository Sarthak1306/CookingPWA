import httpx

from app.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT = 30.0


class OpenRouterError(Exception):
    pass


async def chat_completion(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """One call to OpenRouter's chat completions endpoint. Returns the
    assistant message dict (role, content, tool_calls?). Raises
    OpenRouterError on any non-2xx response or network failure — the
    caller (the job worker) is what turns that into a visible, retryable
    error rather than an indefinite spinner."""
    body = {"model": settings.model_name, "messages": messages}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
    except httpx.TimeoutException:
        raise OpenRouterError("The request timed out.")
    except httpx.HTTPError as exc:
        raise OpenRouterError(f"Network error talking to OpenRouter: {exc}")

    if resp.status_code != 200:
        raise OpenRouterError(f"OpenRouter returned {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise OpenRouterError("OpenRouter response had no choices.")
    return choices[0]["message"]
