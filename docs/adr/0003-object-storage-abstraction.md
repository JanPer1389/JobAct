# ADR-0003: Object storage behind a port; MinIO in dev, S3-compatible API for production

## Status

Accepted, implemented (Milestone 1). **Superseded for normal demo operation by
[ADR-0007](0007-local-demo-downgrade.md)** — the demo stores evidence in browser IndexedDB
instead; kept here as the historical record and reference design for a future real
deployment.

## Context

PAPERCUT specifies Yandex Object Storage for production, reached through an `ObjectStorage`
abstraction so the business logic never depends on a specific provider — important both
architecturally and because PAPERCUT commits to a Russian launch with in-country data
residency, where the production storage provider is a deliberate, non-generic choice.
"S3-compatible" here means the S3 **API** as a protocol both MinIO and Yandex Object Storage
speak, not Amazon S3 the service.

## Decision

`shared/application/ports.py` declares `ObjectStorage` as a `Protocol`
(`presigned_put`, `presigned_get`, `head`, `upload`, `download`). `shared/infrastructure/
object_storage/s3_compatible.py` implements it once, using `aioboto3`, against whatever
S3-compatible endpoint `Settings` points at — MinIO locally (`docker-compose.yml`), Yandex
Object Storage in production, by configuration alone.

`MediaAsset` lifecycle is `pending_upload → uploaded → attached`
(`contexts/media/domain/media_asset.py`): the client requests a presigned PUT URL, uploads
directly to storage, then calls `attach`, which `head()`s the object and rejects the
transition if the reported `sha256`, `content_type`, or `byte_size` don't match what the
client claimed — the asset stays `pending_upload` on mismatch rather than being trusted.

## Consequences

- Swapping MinIO for Yandex Object Storage in production is a `.env`/`Settings` change, not a
  code change — the one implementation already speaks the shared S3 API both use.
- The `sha256`-verified attach step means a `MediaAsset` marked `attached` is a real integrity
  guarantee, not just "the client said it uploaded something" — this is what the signed PDF's
  embedded signature image and its provenance ultimately rest on.
- Bucket privacy and time-limited signed URLs (both `presigned_put` and `presigned_get`) mean
  no object is ever served from a public, permanent URL — access always goes through the API,
  which can apply organization-scoping and expiry.
