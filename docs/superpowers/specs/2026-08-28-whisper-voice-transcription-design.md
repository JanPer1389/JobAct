# Whisper Voice Transcription Design

## Goal

Capture a technician's microphone recording in the browser, store it as private media, transcribe it asynchronously with Whisper in a dedicated worker, and feed the resulting text into the existing report-drafting workflow.

## Design

Voice reports use the existing report-fulfillment workflow. A report created with an attached `audio` `MediaAsset` starts in `TRANSCRIPTION_PENDING`; typed notes still start in `DRAFTING_PENDING`. A dedicated `TranscriptionDispatchRequested` event is routed to `outbox.Transcription`, which only `stt-worker` consumes. The worker claims the durable run, downloads and validates the private object, transcribes it with CPU/int8 `faster-whisper` multilingual `small`, persists the canonical transcript in `Visit.raw_notes`, snapshots it into the existing drafting input, then dispatches the current Anthropic activity.

The frontend uses an explicit MediaRecorder state machine. It requests microphone access only after an action, records WebM/Opus where supported and MP4/AAC otherwise, releases tracks at every exit, uploads the Blob through the existing presigned-media flow, and keeps typed notes as recovery.

## Safety and operations

Audio accepts only WebM/Opus or MP4/AAC, up to 25 MiB and 600 seconds. The worker validates actual containers/codecs and never logs media bytes, transcript content, signed URLs, or temporary paths. Workflow claims, retries, safe failures, and a manual typed fallback prevent a permanently spinning UI. Whisper transcribes rather than translates; UI locale controls only Anthropic's output language.
