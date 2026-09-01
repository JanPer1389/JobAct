"""Shared STT primitives: the audio guardrails and failure types used by
the transcription adapters.

This module used to also hold `TranscribeAudioActivity`, a durable
claim/lease/retry orchestration layer for running transcription on a
background worker against Postgres-backed workflow state. The local-demo
downgrade removed that orchestration (see `apps/api/demo_service.py`,
which calls the transcriber directly from a stateless request instead),
but `FasterWhisperTranscriber` and `PyAvAudioInspector` -- the actual
protected STT implementation -- still import their exception types and
size/duration constants from here, so this module stays at the same
import path with the same names, unchanged.
"""

from __future__ import annotations

MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_TRANSCRIPT_CHARS = 20_000
MIN_TRANSCRIPT_CHARS = 20


class AudioInvalidError(Exception):
    pass


class AudioTooLongError(Exception):
    pass


class TranscriptionUnavailableError(Exception):
    pass
