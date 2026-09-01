import { putBlob } from "@/lib/jobact/local-store"
import type { DraftPhoto } from "@/lib/jobact/store"

const MAX_EDGE = 2048
const MAX_BYTES = 5 * 1024 * 1024
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"])

async function normalizeToJpeg(file: File): Promise<Blob> {
  if (!ACCEPTED_TYPES.has(file.type)) {
    throw new Error("Choose a JPEG, PNG, or WebP photo.")
  }
  const bitmap = await createImageBitmap(file)
  try {
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement("canvas")
    canvas.width = Math.max(1, Math.round(bitmap.width * scale))
    canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    const context = canvas.getContext("2d")
    if (!context) throw new Error("This browser cannot process the photo.")
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)

    for (const quality of [0.88, 0.76, 0.64, 0.52]) {
      const jpeg = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", quality),
      )
      if (jpeg && jpeg.size <= MAX_BYTES) return jpeg
    }
    throw new Error("The normalized photo is larger than 5 MiB.")
  } finally {
    bitmap.close()
  }
}

/** Normalize a captured photo to a bounded JPEG and store it in
 * IndexedDB, scoped to the draft it belongs to. The returned `assetId`
 * is a local blob id (`local-store.ts`'s `LocalBlobRecord.id`), not a
 * server-issued one -- there is no server-side media store anymore. */
export async function saveVisitPhoto(
  file: File,
  phase: "before" | "after",
  draftId: string,
): Promise<DraftPhoto> {
  const jpeg = await normalizeToJpeg(file)
  const assetId = await putBlob(draftId, phase, jpeg, "image/jpeg")
  return { assetId, previewUrl: URL.createObjectURL(jpeg) }
}

const AUDIO_TYPES = new Set(["audio/webm", "audio/mp4"])
const MAX_AUDIO_BYTES = 25 * 1024 * 1024

export function validateVisitAudio(file: File): void {
  if (!AUDIO_TYPES.has(file.type) || file.size === 0 || file.size > MAX_AUDIO_BYTES) {
    throw new Error("The recording must be WebM/Opus or MP4/AAC and no larger than 25 MiB.")
  }
}
