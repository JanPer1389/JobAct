"use client"

/**
 * Minimal promise-based IndexedDB wrapper for the local-demo downgrade.
 * One database (`jobact-demo`), three object stores:
 *   - `drafts`: the in-progress "Создать чек" flow, one row per draft.
 *   - `blobs`: photo/audio/signature/PDF bytes, keyed separately from
 *     drafts so large binary data never rides along with draft reads/writes.
 *   - `checks`: completed, signed checks -- the local history list.
 *
 * No ORM, no schema library: the domain shapes live in `local-store.ts`,
 * this file only knows how to open the database and do get/put/delete/
 * list against a named store.
 */

const DB_NAME = "jobact-demo"
const DB_VERSION = 1

export const STORE_DRAFTS = "drafts"
export const STORE_BLOBS = "blobs"
export const STORE_CHECKS = "checks"

let dbPromise: Promise<IDBDatabase> | null = null

function openDb(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_DRAFTS)) {
        const drafts = db.createObjectStore(STORE_DRAFTS, { keyPath: "id" })
        drafts.createIndex("updatedAt", "updatedAt")
      }
      if (!db.objectStoreNames.contains(STORE_BLOBS)) {
        const blobs = db.createObjectStore(STORE_BLOBS, { keyPath: "id" })
        blobs.createIndex("draftId", "draftId")
      }
      if (!db.objectStoreNames.contains(STORE_CHECKS)) {
        const checks = db.createObjectStore(STORE_CHECKS, { keyPath: "id" })
        checks.createIndex("completedAt", "completedAt")
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error("Could not open the local database."))
  })
  return dbPromise
}

function wrap<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed."))
  })
}

export async function dbPut<T>(store: string, value: T): Promise<void> {
  const db = await openDb()
  const tx = db.transaction(store, "readwrite")
  await wrap(tx.objectStore(store).put(value))
}

export async function dbGet<T>(store: string, id: string): Promise<T | undefined> {
  const db = await openDb()
  const tx = db.transaction(store, "readonly")
  return wrap(tx.objectStore(store).get(id))
}

export async function dbDelete(store: string, id: string): Promise<void> {
  const db = await openDb()
  const tx = db.transaction(store, "readwrite")
  await wrap(tx.objectStore(store).delete(id))
}

export async function dbGetAllByIndex<T>(
  store: string,
  index: string,
  key: IDBValidKey,
): Promise<T[]> {
  const db = await openDb()
  const tx = db.transaction(store, "readonly")
  return wrap(tx.objectStore(store).index(index).getAll(key))
}

export async function dbGetAll<T>(store: string): Promise<T[]> {
  const db = await openDb()
  const tx = db.transaction(store, "readonly")
  return wrap(tx.objectStore(store).getAll())
}

/** True for both `QuotaExceededError` (evaluating storage limits) and the
 * broader `DOMException` shape IndexedDB uses for it across browsers. */
export function isQuotaExceededError(error: unknown): boolean {
  return (
    typeof DOMException !== "undefined" &&
    error instanceof DOMException &&
    (error.name === "QuotaExceededError" || error.code === 22)
  )
}
