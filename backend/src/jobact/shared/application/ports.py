"""Protocols describing the application layer's boundary to every external
system this backend talks to: object storage, message broker, identity
provider, PDF rendering, and LLM gateway -- plus the two "environment"
seams, a clock and an id generator.

Pure application-layer code, same purity rule as `uow.py`: ZERO
SQLAlchemy/Redis/boto3/aioboto3/Authlib/ReportLab/LiteLLM/PydanticAI/
FastAPI imports are allowed in this module. Each Protocol here is
structural typing (`typing.Protocol`), not an ABC, and gets exactly one
real implementation in a later infrastructure task, plus an in-memory fake
in `tests/fakes.py` so application-layer code can be tested without ever
importing infrastructure.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID


@dataclass(frozen=True)
class ObjectMetadata:
    """Metadata about an object already stored in `ObjectStorage`, as
    returned by `head()`.

    A plain infrastructure-facing DTO -- not a `shared.domain.ValueObject`
    -- used by later tasks (e.g. Task 3.3's MediaAsset attach logic) to
    verify an uploaded object's checksum/size/type against what the client
    claimed when it requested the presigned upload URL.
    """

    content_type: str
    byte_size: int
    sha256: str


@runtime_checkable
class ObjectStorage(Protocol):
    """Presigned-URL object storage (S3/MinIO-shaped).

    The application layer never uploads/downloads bytes itself -- it hands
    a presigned URL to the client and lets the client talk to the object
    store directly, then verifies what landed via `head()`.
    """

    async def presigned_put(
        self, key: str, content_type: str, ttl_seconds: int
    ) -> str: ...

    async def presigned_get(self, key: str, ttl_seconds: int) -> str: ...

    async def head(self, key: str) -> ObjectMetadata | None: ...


@dataclass(frozen=True)
class Message:
    """A single message received from a `MessageBroker` stream.

    Concrete dataclass rather than a Protocol -- there's nothing pluggable
    about a received message's shape, only about the broker that produces
    it. `ack` is the message's own acknowledgement callback (bound to its
    stream/group/consumer by whichever `MessageBroker` produced it).
    """

    id: str
    stream: str
    payload: dict
    ack: Callable[[], Awaitable[None]]


@runtime_checkable
class MessageBroker(Protocol):
    """Stream-shaped message broker (Redis Streams' `XADD`/`XREADGROUP`
    vocabulary: `stream`/`group`/`consumer`, deliberately not renamed --
    Task 2.2 implements this directly over Redis Streams).
    """

    async def publish(self, stream: str, payload: dict) -> None: ...

    def consume(
        self, stream: str, group: str, consumer: str
    ) -> AsyncIterator[Message]: ...


@dataclass(frozen=True)
class ExternalIdentity:
    """The identity claims returned by an `IdentityProvider` after a
    successful authorization-code exchange.

    `nonce` is the ID token's own (verified) `nonce` claim, surfaced as-is
    -- comparing it against the value the caller originally issued via
    `authorization_url` is the CALLER's responsibility (it's the caller
    who stashed the expected nonce, e.g. in Redis, alongside `state`), not
    something this port or its implementations know how to check.
    """

    subject: str
    email: str
    email_verified: bool
    name: str
    picture: str | None
    nonce: str


@runtime_checkable
class IdentityProvider(Protocol):
    """OIDC-shaped external identity provider (Task 1.2 implements this
    over Google OIDC).
    """

    def authorization_url(self, state: str, nonce: str) -> str: ...

    async def exchange(self, code: str) -> ExternalIdentity: ...


@runtime_checkable
class PdfRenderer(Protocol):
    """Renders an arbitrary application-supplied `context` into PDF bytes.

    Deliberately minimal: Task 4.5 owns the actual ReportLab layout/content
    logic and decides what goes into `context`. This port only needs to be
    swappable for a fake in tests.
    """

    async def render(self, context: dict) -> bytes: ...


@runtime_checkable
class LlmGateway(Protocol):
    """A thin credentials/config provider for PydanticAI's model classes,
    NOT a call-shaped `complete()`-style API.

    PydanticAI's own `Agent`/`Model` classes own the actual HTTP request
    lifecycle and structured-output handling (Task 4.4), bound to
    LiteLLM's OpenAI-compatible endpoint -- a generic `complete()` wrapper
    here would be redundant and wouldn't match how PydanticAI actually
    calls out. This port exists only so Task 4.4's `LiteLlmGateway` can
    hand PydanticAI's model constructor a `base_url`/`api_key`, and so
    `LlmGateway`-typed code is fakeable without hitting LiteLLM's config
    file.
    """

    @property
    def base_url(self) -> str: ...

    @property
    def api_key(self) -> str: ...

    def model_name(self, alias: str) -> str: ...


@runtime_checkable
class Clock(Protocol):
    """A source of the current time, injectable so tests can control it."""

    def now(self) -> datetime:
        """Must return a timezone-aware UTC `datetime`."""
        ...


@runtime_checkable
class IdGenerator(Protocol):
    """A source of new identifiers, injectable so tests can make them
    deterministic.
    """

    def new_id(self) -> UUID: ...
