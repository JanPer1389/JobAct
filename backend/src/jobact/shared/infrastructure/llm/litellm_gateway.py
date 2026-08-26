"""`LlmGateway` over the LiteLLM proxy.

The application never sees an OpenRouter key -- only LiteLLM's own
internal master key (`Settings.litellm_master_key`), matching the
plan's stated credential design: `OPENROUTER_API_KEY` lives in
`backend/.env` and is injected into the LiteLLM container only.
"""

from __future__ import annotations

from jobact.shared.infrastructure.config import Settings

# The one alias the application knows -- matches litellm_config.yaml's
# `report-drafter` model_name (Task 0.1). `model_name()` maps a logical
# name to whatever string the LiteLLM proxy expects; today that's the
# alias unchanged, but the indirection means a future logical name
# doesn't have to match LiteLLM's config verbatim everywhere it's used.
_KNOWN_ALIASES = {"report-drafter": "report-drafter"}


class LiteLlmGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def base_url(self) -> str:
        return self._settings.litellm_base_url

    @property
    def api_key(self) -> str:
        return self._settings.litellm_master_key

    def model_name(self, alias: str) -> str:
        if alias not in _KNOWN_ALIASES:
            raise ValueError(f"Unknown LLM alias: {alias!r}.")
        return _KNOWN_ALIASES[alias]
