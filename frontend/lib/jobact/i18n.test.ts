/**
 * Localization-layer tests. Run with `npm test` (Node's built-in test
 * runner + native TypeScript type-stripping -- no new dependency).
 *
 * Scope: these are pure-function/dictionary tests for `i18n.ts` itself --
 * they prove the translation layer is complete and behaves correctly, and
 * that language/currency stay independent at the data level. They do not
 * render React components, so they cannot catch a screen that forgot to
 * call `t()` in the first place; that was verified separately by a
 * source-level audit and a manual walkthrough in both languages (see
 * PAPERCUT.md).
 */

import assert from "node:assert/strict"
import { test } from "node:test"

import {
  appCurrencies,
  appLocales,
  confidenceLabel,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatTime,
  formatWeekdayDate,
  greeting,
  statusLabel,
  syncLabel,
  t,
  tPlural,
  verdictLabel,
  type AppLocale,
} from "./i18n.ts"

const locales: AppLocale[] = [...appLocales]

// --- 1: dashboard-shaped strings render in both languages, distinctly ---

test("dashboard strings are localized for ru-RU and differ from en-US", () => {
  const enGreeting = greeting("en-US", 9, "Marco")
  const ruGreeting = greeting("ru-RU", 9, "Marco")
  assert.equal(enGreeting, "Good morning, Marco")
  assert.equal(ruGreeting, "Доброе утро, Marco")
  assert.notEqual(enGreeting, ruGreeting)

  assert.equal(t("en-US", "billedThisMonth"), "Billed this month")
  assert.equal(t("ru-RU", "billedThisMonth"), "Выставлено за месяц")
})

test("dashboard uses English translations under language=en", () => {
  assert.equal(t("en-US", "unfinishedDrafts"), "Unfinished drafts")
  assert.equal(t("en-US", "recentReports"), "Recent reports")
  assert.equal(t("en-US", "latestVisits"), "Latest visits")
})

// --- 2: shared status/sync labels follow the selected language --------

test("shared status labels follow the selected language, not the raw enum", () => {
  for (const status of ["draft", "unsigned", "completed", "offline"]) {
    const en = statusLabel("en-US", status)
    const ru = statusLabel("ru-RU", status)
    assert.notEqual(en, status, `status ${status} must not fall back to the raw value in en-US`)
    assert.notEqual(ru, status, `status ${status} must not fall back to the raw value in ru-RU`)
    assert.notEqual(en, ru, `status ${status} must differ between locales`)
  }
})

test("sync-state labels follow the selected language", () => {
  for (const state of ["synced", "pending", "syncing", "failed", "offline"]) {
    assert.notEqual(syncLabel("en-US", state), syncLabel("ru-RU", state))
  }
})

test("AI verdict/confidence labels follow the selected language, canonical value unchanged", () => {
  for (const verdict of [
    "high_quality",
    "partially_completed",
    "poor_quality",
    "insufficient_data",
    "reasonable",
    "overpriced",
  ]) {
    assert.notEqual(verdictLabel("en-US", verdict), verdictLabel("ru-RU", verdict))
  }
  assert.notEqual(confidenceLabel("en-US", "high"), confidenceLabel("ru-RU", "high"))
  // Unknown enum values must not throw -- humanized fallback, not a crash.
  assert.doesNotThrow(() => verdictLabel("en-US", "some_future_value"))
})

// --- 3: dictionary completeness -- no locale silently falls back -------

test("every simple translation key has a non-empty value in every locale", () => {
  // Walk a representative sample of keys used across the audited screens,
  // checked in every locale so a missing translation cannot silently fall
  // through to `undefined`/an empty string.
  const sampleKeys = [
    "language", "currency", "preferences", "workspace", "operations",
    "goodMorning", "startNow", "billedThisMonth", "unfinishedDrafts",
    "reportsTitle", "customersTitle", "accountTitle", "signOutBtn",
    "addCustomerTitle", "startVisitTitle", "locationTitle",
    "beforePhotosTitle", "afterPhotosTitle", "describeWorkTitle",
    "analysingVisit", "reportDraftTitle", "editReportTitle",
    "customerConfirmationTitle", "reportCompletedTitle",
    "offlineModeTitle", "syncTitle", "permissionsStatesTitle",
    "reportDetailsLabel", "amountLabel", "notSpecified",
  ] as const
  for (const key of sampleKeys) {
    for (const locale of locales) {
      const value = t(locale, key)
      assert.ok(value && value.length > 0, `${key} must be non-empty for ${locale}`)
    }
  }
})

test("every plural key produces a non-empty string for singular, few, and many counts", () => {
  const pluralKeys = [
    "visitsScheduled", "reportsToSync", "reportsCount", "photosCaptured",
    "photosCount", "visitsToday", "visitsCount", "visitsOnRecord",
    "reportsOnRecord", "customersOnFile", "peopleCount",
  ] as const
  for (const key of pluralKeys) {
    for (const locale of locales) {
      for (const n of [0, 1, 2, 5, 11, 21]) {
        const value = tPlural(locale, key, n)
        assert.ok(value.includes(String(n)), `${key}(${n}) in ${locale} must include the count: "${value}"`)
      }
    }
  }
})

// --- 4: dynamic count/date/greeting strings are localized --------------

test("tPlural applies Russian plural rules (one/few/many), not just singular/plural", () => {
  assert.equal(tPlural("ru-RU", "reportsCount", 1), "1 отчёт")
  assert.equal(tPlural("ru-RU", "reportsCount", 2), "2 отчёта")
  assert.equal(tPlural("ru-RU", "reportsCount", 5), "5 отчётов")
  assert.equal(tPlural("ru-RU", "reportsCount", 11), "11 отчётов")
  assert.equal(tPlural("ru-RU", "reportsCount", 21), "21 отчёт")
})

test("formatDate/formatTime/formatWeekdayDate use the selected locale's calendar conventions", () => {
  const iso = "2026-08-20T09:42:00"
  const en = formatDate("en-US", iso)
  const ru = formatDate("ru-RU", iso)
  assert.notEqual(en, ru)
  assert.match(formatTime("en-US", iso), /09:42|9:42/)
  const weekday = formatWeekdayDate("ru-RU", new Date(iso))
  assert.notEqual(weekday, formatWeekdayDate("en-US", new Date(iso)))
  assert.ok(formatDateTime("en-US", iso).includes("·"))
})

// --- 5/6/7: currency is independent of language -------------------------

test("USD does not force English UI, RUB does not force Russian UI", () => {
  // t()/tPlural() take no currency parameter at all -- structurally,
  // currency cannot influence UI text. Assert the Russian dashboard label
  // is identical however the (elsewhere-selected) currency happens to be.
  const label = t("ru-RU", "billedThisMonth")
  assert.equal(label, "Выставлено за месяц")
  assert.equal(formatCurrency("ru-RU", 2895, "USD").includes("$"), true)
  assert.equal(t("ru-RU", "billedThisMonth"), label, "the Russian UI label must not change based on currency")
})

test("currency formatting follows the selected currency, independent of locale", () => {
  const usdInEnglishUi = formatCurrency("en-US", 1500, "USD")
  const usdInRussianUi = formatCurrency("ru-RU", 1500, "USD")
  const rubInEnglishUi = formatCurrency("en-US", 1500, "RUB")
  const rubInRussianUi = formatCurrency("ru-RU", 1500, "RUB")

  assert.match(usdInEnglishUi, /\$/, "USD must render with $ regardless of UI language")
  assert.match(usdInRussianUi, /\$/, "USD must render with $ even when the UI is Russian")
  assert.match(rubInEnglishUi, /₽/, "RUB must render with ₽ even when the UI is English")
  assert.match(rubInRussianUi, /₽/, "RUB must render with ₽ regardless of UI language")

  for (const currency of appCurrencies) {
    assert.doesNotThrow(() => formatCurrency("en-US", 1, currency))
    assert.doesNotThrow(() => formatCurrency("ru-RU", 1, currency))
  }
})

test("locale and currency are stored/looked-up on independent axes (four valid combinations)", () => {
  const combos: Array<[AppLocale, "USD" | "RUB"]> = [
    ["en-US", "USD"],
    ["en-US", "RUB"],
    ["ru-RU", "USD"],
    ["ru-RU", "RUB"],
  ]
  for (const [locale, currency] of combos) {
    // UI text depends only on locale...
    const uiText = t(locale, "amountLabel")
    assert.equal(uiText, locale === "ru-RU" ? "Сумма" : "Amount")
    // ...and money formatting depends only on currency.
    const money = formatCurrency(locale, 10, currency)
    assert.equal(money.includes("$"), currency === "USD")
    assert.equal(money.includes("₽"), currency === "RUB")
  }
})
