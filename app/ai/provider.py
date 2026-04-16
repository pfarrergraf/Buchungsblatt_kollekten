from __future__ import annotations

from abc import ABC, abstractmethod

import requests


class AIDisabledError(Exception):
    pass


class AIProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        """Tool-Use-Runde. Gibt {'type': 'text', 'content': str} oder
        {'type': 'tool_calls', 'calls': [...], 'raw_...': ...} zurück.
        Standard: kein Tool-Support, fällt auf einfaches chat() zurück."""
        return {"type": "text", "content": self.chat(messages)}

    @property
    def supports_tools(self) -> bool:
        return False

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class DisabledProvider(AIProvider):
    @property
    def name(self) -> str:
        return "disabled"

    def chat(self, messages: list[dict]) -> str:
        raise AIDisabledError("KI ist nicht aktiviert.")

    def is_available(self) -> bool:
        return False


class _ChatCompletionsProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        provider_name: str,
        referer: str | None = None,
        requires_api_key: bool = False,
    ):
        self._api_key = api_key or ""
        self._model = model or ""
        self._base_url = base_url.rstrip("/")
        self._provider_name = provider_name
        self._referer = referer
        self._requires_api_key = requires_api_key

    @property
    def name(self) -> str:
        return self._provider_name

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer {0}".format(self._api_key)
        if self._referer:
            headers["HTTP-Referer"] = self._referer
        return headers

    @property
    def supports_tools(self) -> bool:
        return True

    def chat(self, messages: list[dict]) -> str:
        if not self._model:
            raise ValueError("Kein Modell konfiguriert.")
        response = requests.post(
            "{0}/chat/completions".format(self._base_url),
            headers=self._headers(),
            json={"model": self._model, "messages": messages, "max_tokens": 1024},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        import json as _json
        if not self._model:
            raise ValueError("Kein Modell konfiguriert.")
        response = requests.post(
            "{0}/chat/completions".format(self._base_url),
            headers=self._headers(),
            json={"model": self._model, "messages": messages, "tools": tools,
                  "tool_choice": "auto", "max_tokens": 2048},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        choice = payload["choices"][0]
        message = choice["message"]
        finish = choice.get("finish_reason", "")
        if finish == "tool_calls" or message.get("tool_calls"):
            calls = []
            for tc in message.get("tool_calls", []):
                try:
                    args = _json.loads(tc["function"]["arguments"])
                except Exception:
                    args = {}
                calls.append({"id": tc["id"], "name": tc["function"]["name"], "args": args})
            return {"type": "tool_calls", "calls": calls, "raw_message": message}
        return {"type": "text", "content": str(message.get("content", ""))}

    def is_available(self) -> bool:
        """Prüft Erreichbarkeit ohne echten Chat-Call (spart Rate-Limit-Tokens)."""
        if not self._base_url:
            return False
        if self._requires_api_key and not self._api_key:
            return False
        try:
            r = requests.get(
                "{0}/models".format(self._base_url),
                headers=self._headers(),
                timeout=8,
            )
            return 200 <= r.status_code < 400
        except Exception:
            return False


class OpenRouterProvider(_ChatCompletionsProvider):
    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(
            api_key,
            model,
            base_url,
            "openrouter",
            referer="kollekten-automation/1.0",
            requires_api_key=True,
        )


class OpenAIProvider(_ChatCompletionsProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        super().__init__(api_key, model, base_url, "openai", requires_api_key=True)


class LocalOpenAICompatibleProvider(_ChatCompletionsProvider):
    def __init__(self, api_key: str, model: str, base_url: str, provider_name: str):
        super().__init__(api_key, model, base_url, provider_name)


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key or ""
        self._model = model or ""

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def supports_tools(self) -> bool:
        return True

    def _headers(self) -> dict:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def chat(self, messages: list[dict]) -> str:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=self._headers(),
            json={"model": self._model, "max_tokens": 1024, "messages": messages},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload["content"][0]["text"])

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=self._headers(),
            json={"model": self._model, "max_tokens": 2048,
                  "messages": messages, "tools": tools},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("stop_reason") == "tool_use":
            calls = [
                {"id": b["id"], "name": b["name"], "args": b["input"]}
                for b in payload["content"]
                if b.get("type") == "tool_use"
            ]
            return {"type": "tool_calls", "calls": calls, "raw_content": payload["content"]}
        text = "".join(b.get("text", "") for b in payload["content"] if b.get("type") == "text")
        return {"type": "text", "content": text}

    def is_available(self) -> bool:
        """Anthropic: leichter Check ohne echten Inference-Call."""
        if not self._api_key or not self._model:
            return False
        try:
            r = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=8,
            )
            return 200 <= r.status_code < 400
        except Exception:
            return False


def get_provider(cfg: dict) -> AIProvider:
    ai_cfg = cfg.get("ai") or {}
    provider_name = str(ai_cfg.get("provider") or "disabled").strip().lower()
    api_key = str(ai_cfg.get("api_key") or "")
    model = str(ai_cfg.get("model") or "")
    base_url = str(ai_cfg.get("base_url") or "").strip()

    if provider_name == "openrouter":
        base_url = base_url or str(ai_cfg.get("openrouter_base_url") or "https://openrouter.ai/api/v1")
        return OpenRouterProvider(api_key=api_key, model=model, base_url=base_url)
    if provider_name == "openai":
        base_url = base_url or "https://api.openai.com/v1"
        return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
    if provider_name == "ollama":
        base_url = base_url or "http://localhost:11434/v1"
        return LocalOpenAICompatibleProvider(api_key=api_key, model=model, base_url=base_url, provider_name="ollama")
    if provider_name == "lmstudio":
        base_url = base_url or "http://localhost:1234/v1"
        return LocalOpenAICompatibleProvider(api_key=api_key, model=model, base_url=base_url, provider_name="lmstudio")
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    return DisabledProvider()
