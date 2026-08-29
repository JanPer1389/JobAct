# Whisper Voice Transcription Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Add private browser voice recording and asynchronous Whisper transcription that continues the existing report-analysis workflow.

**Architecture:** Voice media remains a `MediaAsset`; the report workflow owns transcription state and dispatch. `stt-worker` is a separate Compose service consuming a dedicated Redis stream and passing only persisted text to the current Anthropic drafting activity.

**Tech Stack:** Next.js/React MediaRecorder, FastAPI, SQLAlchemy, Redis Streams, MinIO/S3, faster-whisper, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-28-whisper-voice-transcription-design.md`

## Global Constraints

- Preserve typed notes and current report review/signature/PDF behavior.
- Store audio privately in object storage; never send bytes through Redis or to Anthropic.
- Accept WebM/Opus and MP4/AAC only; maximum 25 MiB and 600 seconds.
- Use multilingual Whisper `small`, CPU `int8`, transcription mode, and automatic language detection.
- Add focused tests before each production change; tests never download a Whisper model or call a paid provider.

### Task 1: Workflow, report, and media contracts

Add `TRANSCRIPTION_PENDING`, the voice-versus-text report request contract, an audio media kind/validation path, transcription response data, and safe manual recovery/retry transitions. Test all state, XOR, ownership, and response behavior first.

### Task 2: STT boundary, durable activity, and worker

Add fakeable audio validation/transcription ports, the faster-whisper adapter, a claimed transcription activity, `TranscriptionDispatchRequested`, `outbox.Transcription`, and a dedicated `stt-worker`. Test success, duplicate delivery, failure, retry, privacy, and transcript-to-drafting handoff.

### Task 3: Browser recording and processing UX

Add a testable MediaRecorder controller, binary audio upload helper, draft state, English/Russian copy, real processing states, polling updates, transcript display, retry, and typed fallback. Test browser APIs through mocks and preserve the current typed path.

### Task 4: Compose, documentation, and verification

Add the STT dependency/image target/service/model cache and configuration. Update architecture docs and PAPERCUT, then run focused/full backend tests, frontend tests/typecheck/build, lint/mypy, Compose validation, smoke checks, diff review, commit, and push.
