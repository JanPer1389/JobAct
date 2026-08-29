import { apiFetch, type ReportResponse, type WorkflowState } from "@/lib/jobact/api"

export type PollOutcome<T> =
  | { outcome: "terminal"; value: T }
  | { outcome: "timeout" }
  | { outcome: "error"; error: unknown }

interface PollOptions<T> {
  intervalMs?: number
  maxAttempts?: number
  signal?: AbortSignal
  onValue?: (value: T) => void
}

/**
 * Polls until `isTerminal` accepts a value, the attempt budget runs out, or
 * the request fails. Every outcome is bounded and explicit, so a caller can
 * always leave its loading state -- there is no path that polls forever.
 */
export async function pollUntil<T>(
  fetchOnce: () => Promise<T>,
  isTerminal: (value: T) => boolean,
  { intervalMs = 1000, maxAttempts = 60, signal, onValue }: PollOptions<T> = {},
): Promise<PollOutcome<T>> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (signal?.aborted) return { outcome: "timeout" }
    try {
      const value = await fetchOnce()
      onValue?.(value)
      if (isTerminal(value)) return { outcome: "terminal", value }
    } catch (error) {
      return { outcome: "error", error }
    }
    await sleep(intervalMs, signal)
  }
  return { outcome: "timeout" }
}

/** Poll one report until its workflow reaches any of `states`. */
export function pollReportUntilState(
  reportId: string,
  states: WorkflowState[],
  options: PollOptions<ReportResponse> = {},
): Promise<PollOutcome<ReportResponse>> {
  return pollUntil(
    () => apiFetch<ReportResponse>(`/api/v1/reports/${reportId}`),
    (report) =>
      report.workflow_state !== null && states.includes(report.workflow_state),
    options,
  )
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer)
        resolve()
      },
      { once: true },
    )
  })
}
