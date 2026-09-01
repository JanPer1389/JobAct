"use client"

import type { Screen } from "@/lib/jobact/store"
import type { AppCurrency } from "@/lib/jobact/i18n"
import type { VisualAuditResult } from "@/lib/jobact/api"
import {
  STORE_BLOBS,
  STORE_CHECKS,
  STORE_DRAFTS,
  dbDelete,
  dbGet,
  dbGetAll,
  dbGetAllByIndex,
  dbPut,
  isQuotaExceededError,
} from "./local-db.ts"

export { isQuotaExceededError }

/** Statuses a card/detail view can render -- kept here (rather than the
 * removed `lib/jobact/data.ts`) since it now describes local check/draft
 * state, not demo server data. */
export type ReportStatus = "draft" | "unsigned" | "completed" | "offline"
export type SyncState = "synced" | "pending" | "syncing" | "failed" | "offline"

export interface LocalMaterial {
  label: string
  qty: string
}

export interface LocalDraft {
  id: string
  /** Which screen to resume on after a page reload. */
  screen: Screen
  customerName: string
  customerAddress: string
  customerPhone: string
  customerServiceType: string
  gpsLat: number | null
  gpsLon: number | null
  gpsAccuracyM: number | null
  /** Ordered blob ids -- before/after photos are paired by position. */
  beforePhotoIds: string[]
  afterPhotoIds: string[]
  rawNotes: string
  notesSource: "typed" | "voice"
  workCompleted: string
  materials: LocalMaterial[]
  amountCents: number | null
  currency: AppCurrency
  estimatedWorkUnits: number | null
  aiConfidence: "high" | "medium" | "low" | null
  visualComparison: VisualAuditResult | null
  amountConfirmed: boolean
  signerName: string | null
  createdAt: string
  updatedAt: string
}

export type BlobKind = "before" | "after" | "signature" | "pdf"

export interface LocalBlobRecord {
  id: string
  draftId: string
  kind: BlobKind
  blob: Blob
  contentType: string
}

export interface LocalCheck {
  id: string
  humanId: string
  customerName: string
  customerAddress: string
  customerPhone: string
  customerServiceType: string
  gpsLat: number | null
  gpsLon: number | null
  workCompleted: string
  materials: LocalMaterial[]
  amountCents: number | null
  currency: AppCurrency
  visualComparison: VisualAuditResult | null
  aiConfidence: "high" | "medium" | "low" | null
  signed: boolean
  signerName: string | null
  beforePhotoIds: string[]
  afterPhotoIds: string[]
  pdfBlobId: string | null
  completedAt: string
}

const MAX_HISTORY = 20

function newId(): string {
  return crypto.randomUUID()
}

export function newDraft(screen: Screen): LocalDraft {
  const now = new Date().toISOString()
  return {
    id: newId(),
    screen,
    customerName: "",
    customerAddress: "",
    customerPhone: "",
    customerServiceType: "",
    gpsLat: null,
    gpsLon: null,
    gpsAccuracyM: null,
    beforePhotoIds: [],
    afterPhotoIds: [],
    rawNotes: "",
    notesSource: "typed",
    workCompleted: "",
    materials: [],
    amountCents: null,
    currency: "RUB",
    estimatedWorkUnits: null,
    aiConfidence: null,
    visualComparison: null,
    amountConfirmed: false,
    signerName: null,
    createdAt: now,
    updatedAt: now,
  }
}

export async function saveDraft(draft: LocalDraft): Promise<void> {
  await dbPut(STORE_DRAFTS, { ...draft, updatedAt: new Date().toISOString() })
}

export async function loadDraft(id: string): Promise<LocalDraft | undefined> {
  return dbGet<LocalDraft>(STORE_DRAFTS, id)
}

/** Abandon a draft entirely -- also deletes every blob attached to it,
 * since nothing else will ever reference them. */
export async function deleteDraft(id: string): Promise<void> {
  const blobs = await dbGetAllByIndex<LocalBlobRecord>(STORE_BLOBS, "draftId", id)
  await Promise.all(blobs.map((blob) => dbDelete(STORE_BLOBS, blob.id)))
  await dbDelete(STORE_DRAFTS, id)
}

/** Retire a draft that just became a completed check: deletes only the
 * draft record, not its blobs -- the check being saved still references
 * the same photo/PDF blob ids (`putBlob` was called with this draft's id
 * as `draftId`), so cascading their deletion here would corrupt the
 * check it belongs to. */
export async function finalizeDraft(id: string): Promise<void> {
  await dbDelete(STORE_DRAFTS, id)
}

export async function putBlob(
  draftId: string,
  kind: BlobKind,
  blob: Blob,
  contentType: string,
): Promise<string> {
  const id = newId()
  await dbPut<LocalBlobRecord>(STORE_BLOBS, { id, draftId, kind, blob, contentType })
  return id
}

export async function getBlob(id: string): Promise<LocalBlobRecord | undefined> {
  return dbGet<LocalBlobRecord>(STORE_BLOBS, id)
}

export async function deleteBlob(id: string): Promise<void> {
  await dbDelete(STORE_BLOBS, id)
}

/** Object URLs are created on demand by the caller (and must be revoked
 * by the caller) -- this store never caches one, since a stale URL that
 * outlives its blob is a classic leak source. */
export async function blobObjectUrl(id: string): Promise<string | null> {
  const record = await getBlob(id)
  return record ? URL.createObjectURL(record.blob) : null
}

export async function saveCheck(check: LocalCheck): Promise<void> {
  await dbPut(STORE_CHECKS, check)
  await pruneHistory()
}

export async function getCheck(id: string): Promise<LocalCheck | undefined> {
  return dbGet<LocalCheck>(STORE_CHECKS, id)
}

export async function listRecentChecks(limit = 5): Promise<LocalCheck[]> {
  const all = await dbGetAll<LocalCheck>(STORE_CHECKS)
  return all.sort((a, b) => b.completedAt.localeCompare(a.completedAt)).slice(0, limit)
}

async function pruneHistory(): Promise<void> {
  const all = await dbGetAll<LocalCheck>(STORE_CHECKS)
  if (all.length <= MAX_HISTORY) return
  const sorted = all.sort((a, b) => b.completedAt.localeCompare(a.completedAt))
  const stale = sorted.slice(MAX_HISTORY)
  for (const check of stale) {
    if (check.pdfBlobId) await dbDelete(STORE_BLOBS, check.pdfBlobId)
    for (const id of [...check.beforePhotoIds, ...check.afterPhotoIds]) {
      await dbDelete(STORE_BLOBS, id)
    }
    await dbDelete(STORE_CHECKS, check.id)
  }
}
