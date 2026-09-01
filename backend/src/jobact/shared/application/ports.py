"""Protocols describing the application layer's boundary to the external
systems the demo backend still talks to: speech-to-text and the AI
connector. Pure application-layer code: no framework/driver imports
allowed here.

Trimmed for the local-demo downgrade -- object storage, message broker,
identity provider, password hashing, PDF rendering, clock, and id
generator all described a boundary this app no longer has (there is
nothing left to persist, queue, or generate ids for). `PdfRenderer` and
`AiConnector`'s concrete implementations are still called directly by
`apps/api/demo_service.py` rather than through dependency injection, so
only `AiConnector` (used for type-hinting the connector across the two
AI calls) survives as a Protocol here.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class AudioInspection:
    """Sanitized facts derived from the audio bytes at request time."""

    container: str
    codec: str
    duration_seconds: float


@dataclass(frozen=True)
class SpeechTranscription:
    """Speech-to-text output; text is preserved exactly as produced."""

    text: str
    language: str | None


@runtime_checkable
class AudioInspector(Protocol):
    async def inspect(
        self, data: bytes, declared_content_type: str
    ) -> AudioInspection: ...


@runtime_checkable
class SpeechTranscriber(Protocol):
    async def transcribe(
        self, data: bytes, content_type: str
    ) -> SpeechTranscription: ...


@runtime_checkable
class AiConnector(Protocol):
    """Provider-neutral model construction used by the two AI calls.

    ``Any`` deliberately keeps PydanticAI/provider classes out of the
    application port. The concrete connector lives in
    `shared/infrastructure/llm/connectors.py`.
    """

    @property
    def provider_name(self) -> str: ...

    def model_name(self, alias: str) -> str: ...

    def build_model(self, alias: str, http_client: Any | None = None) -> Any: ...
