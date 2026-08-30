type WorkflowError = {
  code: string
  http_status?: number
  message?: string
  retryable: boolean
} | null | undefined

type AnalysisFailureMessageKey =
  | "analysisProviderConfigurationError"
  | "analysisTimedOutError"
  | "analysisIncompleteError"

export function analysisFailurePresentation(
  error: WorkflowError,
): { messageKey: AnalysisFailureMessageKey; retryable: boolean } {
  const messageKey =
    error?.code === "AI_PROVIDER_CONFIGURATION_ERROR"
      ? "analysisProviderConfigurationError"
      : error?.code === "AI_ANALYSIS_TIMEOUT"
        ? "analysisTimedOutError"
        : "analysisIncompleteError"

  return { messageKey, retryable: error?.retryable ?? true }
}
