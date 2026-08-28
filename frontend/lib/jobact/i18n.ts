export const appLocales = ["en-US", "ru-RU"] as const
export type AppLocale = (typeof appLocales)[number]

type TranslationKey =
  | "language"
  | "english"
  | "russian"
  | "saving"
  | "languageSaveError"
  | "preferences"
  | "workspace"
  | "operations"
  | "overview"
  | "reports"
  | "customers"
  | "newReport"
  | "account"
  | "signOut"

const translations: Record<AppLocale, Record<TranslationKey, string>> = {
  "en-US": {
    language: "Language", english: "English", russian: "Russian", saving: "Saving…",
    languageSaveError: "Could not save language preference.", preferences: "Preferences",
    workspace: "Workspace", operations: "Operations", overview: "Overview", reports: "Reports",
    customers: "Customers", newReport: "New report", account: "Account", signOut: "Sign out",
  },
  "ru-RU": {
    language: "Язык", english: "English", russian: "Русский", saving: "Сохранение…",
    languageSaveError: "Не удалось сохранить язык.", preferences: "Настройки",
    workspace: "Рабочее пространство", operations: "Операции", overview: "Обзор", reports: "Отчёты",
    customers: "Клиенты", newReport: "Новый отчёт", account: "Аккаунт", signOut: "Выйти",
  },
}

export function t(locale: AppLocale, key: TranslationKey) {
  return translations[locale][key]
}

export function formatCurrency(locale: AppLocale, value: number, currency = "USD") {
  return new Intl.NumberFormat(locale, { style: "currency", currency, maximumFractionDigits: 0 }).format(value)
}
