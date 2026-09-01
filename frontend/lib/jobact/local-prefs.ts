"use client"

/** Small synchronous `localStorage` preferences -- the browser-storage
 * split documented in the downgrade plan: tiny scalar preferences here,
 * structured records/blobs in IndexedDB (`local-db.ts`/`local-store.ts`).
 */

import type { AppCurrency, AppLocale } from "@/lib/jobact/i18n"

const KEY_LOCALE = "jobact.locale"
const KEY_CURRENCY = "jobact.currency"
const KEY_USER_NAME = "jobact.demoUserName"
const KEY_ACTIVE_DRAFT = "jobact.activeDraftId"

function readItem(key: string): string | null {
  if (typeof window === "undefined") return null
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeItem(key: string, value: string | null): void {
  if (typeof window === "undefined") return
  try {
    if (value === null) window.localStorage.removeItem(key)
    else window.localStorage.setItem(key, value)
  } catch {
    // Private-browsing / storage-disabled browsers throw here; the
    // preference just doesn't persist across reloads.
  }
}

export function getStoredLocale(): AppLocale {
  return readItem(KEY_LOCALE) === "en-US" ? "en-US" : "ru-RU"
}

export function setStoredLocale(locale: AppLocale): void {
  writeItem(KEY_LOCALE, locale)
}

export function getStoredCurrency(): AppCurrency {
  return readItem(KEY_CURRENCY) === "USD" ? "USD" : "RUB"
}

export function setStoredCurrency(currency: AppCurrency): void {
  writeItem(KEY_CURRENCY, currency)
}

export function getStoredUserName(): string | null {
  return readItem(KEY_USER_NAME)
}

export function setStoredUserName(name: string): void {
  writeItem(KEY_USER_NAME, name)
}

export function getActiveDraftId(): string | null {
  return readItem(KEY_ACTIVE_DRAFT)
}

export function setActiveDraftId(id: string | null): void {
  writeItem(KEY_ACTIVE_DRAFT, id)
}
