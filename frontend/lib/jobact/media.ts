import { apiFetch, type MediaUploadResponse } from "@/lib/jobact/api"
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

async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer())
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("")
}

export async function uploadVisitPhoto(
  file: File,
  phase: "before" | "after",
  visitId: string,
): Promise<DraftPhoto> {
  const jpeg = await normalizeToJpeg(file)
  const sha256 = await sha256Hex(jpeg)
  const upload = await apiFetch<MediaUploadResponse>("/api/v1/media/uploads", {
    method: "POST",
    body: JSON.stringify({
      content_type: "image/jpeg",
      byte_size: jpeg.size,
      sha256,
      kind: "photo",
      phase,
      visit_id: visitId,
    }),
  })
  const response = await fetch(upload.upload_url, {
    method: "PUT",
    headers: { "Content-Type": "image/jpeg", "x-amz-meta-sha256": sha256 },
    body: jpeg,
  })
  if (!response.ok) throw new Error("Photo upload failed.")
  await apiFetch(`/api/v1/media/${upload.media_asset_id}/attach`, { method: "POST" })
  return { assetId: upload.media_asset_id, previewUrl: URL.createObjectURL(jpeg) }
}

const AUDIO_TYPES = new Set(["audio/webm", "audio/mp4"])
const MAX_AUDIO_BYTES = 25 * 1024 * 1024

/** Upload a finished microphone recording directly to the private media store. */
export async function uploadVisitAudio(file: File, visitId: string): Promise<string> {
  if (!AUDIO_TYPES.has(file.type) || file.size === 0 || file.size > MAX_AUDIO_BYTES) {
    throw new Error("The recording must be WebM/Opus or MP4/AAC and no larger than 25 MiB.")
  }
  const sha256 = await sha256Hex(file)
  const upload = await apiFetch<MediaUploadResponse>("/api/v1/media/uploads", {
    method: "POST",
    body: JSON.stringify({
      content_type: file.type,
      byte_size: file.size,
      sha256,
      kind: "audio",
      visit_id: visitId,
    }),
  })
  const response = await fetch(upload.upload_url, {
    method: "PUT",
    headers: { "Content-Type": file.type, "x-amz-meta-sha256": sha256 },
    body: file,
  })
  if (!response.ok) throw new Error("Audio upload failed.")
  await apiFetch(`/api/v1/media/${upload.media_asset_id}/attach`, { method: "POST" })
  return upload.media_asset_id
}
