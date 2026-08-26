"""In-memory fakes for the application-layer ports in
`jobact.shared.application.ports`.

One small, focused fake per Protocol -- shared test infrastructure meant
to be imported by test suites across `tests/` (not just `tests/application`),
so application-layer code (and, from Phase 1 onward, real handlers) can be
tested without ever touching Postgres, Redis, S3/MinIO, Google OIDC,
ReportLab, or LiteLLM.

Each fake satisfies its Protocol structurally -- no explicit subclassing
needed, that's the point of `typing.Protocol` -- and additionally carries
just enough in-memory state to be genuinely useful in later tests (e.g.
asserting on what a handler published, or controlling "the current time").
"""

import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from jobact.shared.application.ports import (
    ExternalIdentity,
    Message,
    ObjectMetadata,
)


class FakeObjectStorage:
    """In-memory object store.

    `presigned_put`/`presigned_get` return deterministic fake URLs (no
    real network call). `put()` is a test helper simulating a client
    completing an upload through the presigned PUT URL -- after calling
    it, `head()` reports real-looking metadata (content type, byte size,
    sha256) for that key, mirroring what Task 3.3's MediaAsset attach
    logic will need to verify.
    """

    def __init__(self) -> None:
        self._objects: dict[str, ObjectMetadata] = {}

    async def presigned_put(self, key: str, content_type: str, ttl_seconds: int) -> str:
        return f"https://fake-storage.test/{key}?method=PUT&content_type={content_type}&ttl={ttl_seconds}"

    async def presigned_get(self, key: str, ttl_seconds: int) -> str:
        return f"https://fake-storage.test/{key}?method=GET&ttl={ttl_seconds}"

    async def head(self, key: str) -> ObjectMetadata | None:
        return self._objects.get(key)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Test helper: simulate a client completing an upload for `key`."""
        self._objects[key] = ObjectMetadata(
            content_type=content_type,
            byte_size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )


class FakeMessageBroker:
    """In-memory message broker.

    `published` records every `publish()` call as `(stream, payload)` so
    tests can assert on what a handler sent without a real Redis Streams
    instance. `consume()` replays whatever has been published to that
    stream so far as `Message`s with a working (no-op) `ack()`.
    """

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []
        self._streams: dict[str, list[Message]] = {}

    async def publish(self, stream: str, payload: dict) -> None:
        self.published.append((stream, payload))
        message = Message(
            id=str(uuid4()),
            stream=stream,
            payload=payload,
            ack=self._ack,
        )
        self._streams.setdefault(stream, []).append(message)

    async def consume(
        self, stream: str, group: str, consumer: str
    ) -> AsyncIterator[Message]:
        for message in self._streams.get(stream, []):
            yield message

    @staticmethod
    async def _ack() -> None:
        return None


class FakeIdentityProvider:
    """In-memory identity provider.

    Preload `identities[code] = ExternalIdentity(...)` to control what
    `exchange()` returns for a given authorization code. `authorization_url`
    records every call in `authorization_urls` so tests can assert on the
    `state`/`nonce` a caller generated.
    """

    def __init__(self) -> None:
        self.identities: dict[str, ExternalIdentity] = {}
        self.authorization_urls: list[tuple[str, str]] = []

    def authorization_url(self, state: str, nonce: str) -> str:
        self.authorization_urls.append((state, nonce))
        return f"https://fake-idp.test/authorize?state={state}&nonce={nonce}"

    async def exchange(self, code: str) -> ExternalIdentity:
        try:
            return self.identities[code]
        except KeyError:
            raise ValueError(f"no fake identity configured for code {code!r}") from None


class FakePdfRenderer:
    """In-memory PDF renderer.

    Records every `context` it was asked to render (so tests can assert
    what a handler passed in) and returns a small fixed byte string
    standing in for real PDF bytes.
    """

    def __init__(self) -> None:
        self.rendered_contexts: list[dict] = []

    async def render(self, context: dict) -> bytes:
        self.rendered_contexts.append(context)
        return b"%PDF-1.4 fake pdf content"


class FakeLlmGateway:
    """In-memory LLM gateway. Fixed/settable credentials plus a settable
    alias -> model-name mapping, so tests never need LiteLLM's config file.
    """

    def __init__(
        self,
        base_url: str = "https://fake-llm.test",
        api_key: str = "fake-api-key",
        model_names: dict[str, str] | None = None,
        drafting_result: Any | None = None,
        drafting_error: Exception | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model_names = dict(model_names) if model_names else {}
        self._drafting_result = drafting_result
        self._drafting_error = drafting_error
        self.draft_inputs: list[str] = []

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_key(self) -> str:
        return self._api_key

    def model_name(self, alias: str) -> str:
        return self._model_names.get(alias, alias)

    async def draft(self, raw_notes: str) -> Any:
        self.draft_inputs.append(raw_notes)
        if self._drafting_error is not None:
            raise self._drafting_error
        if self._drafting_result is None:
            raise ValueError("No fake drafting result configured.")
        return self._drafting_result


class FakeClock:
    """Settable clock. Defaults to a fixed UTC instant so tests are
    deterministic unless they call `set()`.
    """

    def __init__(self, initial: datetime | None = None) -> None:
        self._current = initial or datetime(2020, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self._current

    def set(self, value: datetime) -> None:
        self._current = value


class FakeIdGenerator:
    """Deterministic id generator.

    Preload specific ids via the constructor or `queue()` so a test can
    pin exactly which UUID a handler will see next; once the preloaded
    queue is exhausted, falls back to a sequential (still deterministic,
    non-random) source so tests never flake on uniqueness.
    """

    def __init__(self, ids: list[UUID] | None = None) -> None:
        self._queue: list[UUID] = list(ids) if ids else []
        self._counter = 0

    def new_id(self) -> UUID:
        if self._queue:
            return self._queue.pop(0)
        self._counter += 1
        return UUID(int=self._counter)

    def queue(self, *ids: UUID) -> None:
        self._queue.extend(ids)
