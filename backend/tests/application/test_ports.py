"""Tests for `jobact.shared.application.ports`.

These verify that each in-memory fake in `tests/fakes.py` structurally
satisfies its Protocol (via `isinstance`, which only works because every
Protocol in `ports.py` is `@runtime_checkable`), and exercise a bit of
real behavior on each fake so they earn their keep as reusable test
infrastructure for later tasks, not just tautological isinstance checks.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from jobact.shared.application.ports import (
    Clock,
    ExternalIdentity,
    IdentityProvider,
    IdGenerator,
    LlmGateway,
    MessageBroker,
    ObjectStorage,
    PdfRenderer,
)
from tests.fakes import (
    FakeClock,
    FakeIdentityProvider,
    FakeIdGenerator,
    FakeLlmGateway,
    FakeMessageBroker,
    FakeObjectStorage,
    FakePdfRenderer,
)

# --- structural typing: fakes satisfy their protocols -----------------


def test_fake_object_storage_satisfies_protocol() -> None:
    assert isinstance(FakeObjectStorage(), ObjectStorage)


def test_fake_message_broker_satisfies_protocol() -> None:
    assert isinstance(FakeMessageBroker(), MessageBroker)


def test_fake_identity_provider_satisfies_protocol() -> None:
    assert isinstance(FakeIdentityProvider(), IdentityProvider)


def test_fake_pdf_renderer_satisfies_protocol() -> None:
    assert isinstance(FakePdfRenderer(), PdfRenderer)


def test_fake_llm_gateway_satisfies_protocol() -> None:
    assert isinstance(FakeLlmGateway(), LlmGateway)


def test_fake_clock_satisfies_protocol() -> None:
    assert isinstance(FakeClock(), Clock)


def test_fake_id_generator_satisfies_protocol() -> None:
    assert isinstance(FakeIdGenerator(), IdGenerator)


# --- the fakes are actually useful, not just stubs ---------------------


async def test_fake_object_storage_head_reflects_a_completed_put() -> None:
    storage = FakeObjectStorage()
    assert await storage.head("reports/1.jpg") is None

    storage.put("reports/1.jpg", b"hello world", content_type="image/jpeg")

    metadata = await storage.head("reports/1.jpg")
    assert metadata is not None
    assert metadata.content_type == "image/jpeg"
    assert metadata.byte_size == len(b"hello world")
    assert len(metadata.sha256) == 64  # hex-encoded sha256 digest

    put_url = await storage.presigned_put("reports/1.jpg", "image/jpeg", 60)
    get_url = await storage.presigned_get("reports/1.jpg", 60)
    assert put_url != get_url


async def test_fake_message_broker_records_published_messages() -> None:
    broker = FakeMessageBroker()

    await broker.publish("reports.created", {"report_id": "abc"})

    assert broker.published == [("reports.created", {"report_id": "abc"})]


async def test_fake_message_broker_consume_yields_message_with_working_ack() -> None:
    broker = FakeMessageBroker()
    await broker.publish("reports.created", {"report_id": "abc"})

    messages = [
        msg async for msg in broker.consume("reports.created", group="g", consumer="c")
    ]

    assert len(messages) == 1
    assert messages[0].stream == "reports.created"
    assert messages[0].payload == {"report_id": "abc"}
    await messages[0].ack()  # must not raise


async def test_fake_identity_provider_exchange_returns_configured_identity() -> None:
    identity = ExternalIdentity(
        subject="sub-1",
        email="user@example.com",
        email_verified=True,
        name="User",
        picture=None,
    )
    provider = FakeIdentityProvider()
    provider.identities["auth-code"] = identity

    assert await provider.exchange("auth-code") is identity
    assert provider.authorization_url("state", "nonce").startswith("https://")


async def test_fake_pdf_renderer_records_context_and_returns_bytes() -> None:
    renderer = FakePdfRenderer()

    pdf = await renderer.render({"title": "Report"})

    assert isinstance(pdf, bytes)
    assert len(pdf) > 0
    assert renderer.rendered_contexts == [{"title": "Report"}]


def test_fake_llm_gateway_maps_alias_to_configured_model_name() -> None:
    gateway = FakeLlmGateway(model_names={"report-drafter": "gpt-4o-mini"})

    assert gateway.base_url
    assert gateway.api_key
    assert gateway.model_name("report-drafter") == "gpt-4o-mini"
    assert gateway.model_name("unmapped-alias") == "unmapped-alias"


def test_fake_clock_is_settable_and_stays_timezone_aware() -> None:
    clock = FakeClock()
    fixed = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)

    clock.set(fixed)

    assert clock.now() == fixed
    assert clock.now().tzinfo is not None


def test_fake_id_generator_uses_preloaded_ids_then_falls_back() -> None:
    preloaded = uuid4()
    generator = FakeIdGenerator(ids=[preloaded])

    assert generator.new_id() == preloaded
    second = generator.new_id()
    third = generator.new_id()
    assert isinstance(second, UUID)
    assert second != third  # deterministic sequence, not random, but not repeating
