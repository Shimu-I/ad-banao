"""Adapters for the free AI services. Only this module talks to the network.

The prompt, parsing, fact checking and fallback live in app.domain.generation, which
knows nothing about Gemini, Groq or HTTP, so it can be tested with fake providers.
"""

from app.domain.generation import Provider, ProviderError


def _post_json(url: str, *, headers: dict, body: dict, timeout: float = 30.0) -> dict:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ProviderError("the httpx package is not installed") from exc
    try:
        response = httpx.post(url, headers=headers, json=body, timeout=timeout)
    except httpx.HTTPError as exc:
        raise ProviderError(f"network problem ({type(exc).__name__})") from exc
    if response.status_code == 429:
        raise ProviderError("rate limit reached")
    if response.status_code in (401, 403):
        raise ProviderError("the API key was rejected")
    if response.status_code >= 400:
        raise ProviderError(f"the service returned {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("the service returned something that is not JSON") from exc


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def complete(self, prompt: str) -> str:
        data = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            body={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}},
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("the reply had no text") from exc


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def complete(self, prompt: str) -> str:
        data = _post_json(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            body={"model": self.model, "temperature": 0.4, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": prompt}]},
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("the reply had no text") from exc


def providers_from_settings(settings) -> list[Provider]:
    """Providers that have a key, in the order they are tried."""
    found: list[Provider] = []
    if settings.gemini_api_key:
        found.append(GeminiProvider(settings.gemini_api_key, settings.gemini_model))
    if settings.groq_api_key:
        found.append(GroqProvider(settings.groq_api_key, settings.groq_model))
    return found
