import assert from "node:assert/strict"
import test from "node:test"

import { t } from "./i18n.ts"
import { analysisFailurePresentation } from "./workflow-errors.ts"

test("provider configuration failures are localized and cannot be retried", () => {
  const presentation = analysisFailurePresentation(
    {
      code: "AI_PROVIDER_CONFIGURATION_ERROR",
      http_status: 503,
      message: "English server message must not leak into Russian UI.",
      retryable: false,
    },
  )

  assert.equal(
    t("ru-RU", presentation.messageKey),
    "Сервис ИИ настроен некорректно. Введите отчёт вручную или обратитесь к администратору.",
  )
  assert.equal(presentation.retryable, false)
})
