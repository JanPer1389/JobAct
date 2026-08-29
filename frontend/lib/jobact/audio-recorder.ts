export type RecordingState =
  | "unsupported"
  | "permission-required"
  | "ready"
  | "recording"
  | "preparing"
  | "uploading"
  | "failed"

const MAX_RECORDING_MS = 10 * 60 * 1000

export function preferredAudioMimeType(): string | null {
  if (typeof MediaRecorder === "undefined") return null
  for (const mimeType of ["audio/webm;codecs=opus", "audio/mp4;codecs=mp4a.40.2"]) {
    if (MediaRecorder.isTypeSupported(mimeType)) return mimeType
  }
  return null
}

export class BrowserAudioRecorder {
  private stream: MediaStream | null = null
  private recorder: MediaRecorder | null = null
  private timer: ReturnType<typeof setTimeout> | null = null

  async start(onState: (state: RecordingState) => void): Promise<Blob> {
    const mimeType = preferredAudioMimeType()
    if (!mimeType || !navigator.mediaDevices?.getUserMedia) {
      onState("unsupported")
      throw new Error("Microphone recording is not supported by this browser.")
    }
    onState("permission-required")
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const chunks: BlobPart[] = []
    this.recorder = new MediaRecorder(this.stream, { mimeType })
    const complete = new Promise<Blob>((resolve, reject) => {
      this.recorder!.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data)
      }
      this.recorder!.onstop = () => {
        this.release()
        const blob = new Blob(chunks, { type: mimeType.split(";")[0] })
        blob.size ? resolve(blob) : reject(new Error("The recording is empty."))
      }
      this.recorder!.onerror = () => reject(new Error("Microphone recording failed."))
    })
    this.recorder.start()
    this.timer = setTimeout(() => this.stop(), MAX_RECORDING_MS)
    onState("recording")
    return complete
  }

  stop() {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
    if (this.recorder?.state === "recording") this.recorder.stop()
  }

  release() {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
    this.stream?.getTracks().forEach((track) => track.stop())
    this.stream = null
    this.recorder = null
  }
}
