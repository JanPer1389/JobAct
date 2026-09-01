/** Thin client for the three stateless `/api/v1/demo/*` endpoints -- the
 * backend's entire surface after the local-demo downgrade. There is no
 * session, no idempotency key, and no JSON-only body: every mutating
 * call here posts `multipart/form-data` (bytes plus a JSON `context`
 * field) and gets back either a JSON result or, for the PDF endpoint,
 * the rendered file directly.
 */

export interface ApiErrorDetail {
  loc: Array<string | number>
  message: string
}

export interface ApiErrorEnvelope {
  type: string
  title: string
  status: number
  detail: string
  correlation_id: string
  errors: ApiErrorDetail[]
}

export class JobActApiError extends Error {
  readonly response: ApiErrorEnvelope

  constructor(response: ApiErrorEnvelope) {
    super(response.detail)
    this.name = "JobActApiError"
    this.response = response
  }
}

export interface VisualAuditResult {
  verdict: "high_quality" | "partially_completed" | "poor_quality" | "insufficient_data"
  confidence: number
  summary: string
  comparison: {
    visible_changes: string[]
    work_matches_description: boolean
    match_explanation: string
  }
  quality_assessment: {
    score: number
    strengths: string[]
    issues: string[]
    unverified_items: string[]
  }
  price_assessment: {
    provided_price_usd: number | null
    fair_price_range_usd: { min: number | null; max: number | null }
    price_verdict: string
    price_explanation: string
  }
  evidence: Array<{ observation: string; impact: string }>
  limitations: string[]
  recommended_next_steps: string[]
}

export interface TranscribeResponse {
  transcript: string
  detected_language: string | null
  duration_seconds: number
}

export interface AnalyzeMaterial {
  label: string
  qty: string
}

export interface AnalyzeContext {
  raw_notes: string
  customer_name: string
  customer_address: string
  customer_service_type: string
  gps_lat: number | null
  gps_lon: number | null
  currency: "USD" | "RUB"
  locale: "en-US" | "ru-RU"
}

export interface AnalyzeResponse {
  work_completed: string
  materials: AnalyzeMaterial[]
  estimated_work_units: number | null
  suggested_amount_cents: number | null
  currency: string
  confidence: "high" | "medium" | "low"
  visual_comparison: VisualAuditResult
}

export interface CheckPdfContext {
  report_number: string
  customer_name: string
  customer_address: string
  customer_phone: string
  customer_service_type: string
  timestamp: string
  gps_lat: number | null
  gps_lon: number | null
  work_completed: string
  materials: AnalyzeMaterial[]
  amount_cents: number | null
  currency: "USD" | "RUB"
  signer_name: string
  locale: "en-US" | "ru-RU"
}

async function readErrorEnvelope(response: Response): Promise<ApiErrorEnvelope> {
  const fallback: ApiErrorEnvelope = {
    type: "unexpected-response",
    title: response.statusText || "Request failed",
    status: response.status,
    detail: "The server returned an unexpected error response.",
    correlation_id: "",
    errors: [],
  }

  try {
    const body: unknown = await response.json()
    if (!isErrorEnvelope(body)) {
      return fallback
    }
    return body
  } catch {
    return fallback
  }
}

function isErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== "object" || value === null) {
    return false
  }

  const candidate = value as Partial<ApiErrorEnvelope>
  return (
    typeof candidate.type === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.status === "number" &&
    typeof candidate.detail === "string" &&
    typeof candidate.correlation_id === "string" &&
    Array.isArray(candidate.errors)
  )
}

async function postForJson<T>(path: string, form: FormData, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { method: "POST", body: form, signal })
  if (!response.ok) throw new JobActApiError(await readErrorEnvelope(response))
  return (await response.json()) as T
}

export async function transcribeRecording(
  file: Blob,
  filename: string,
  signal?: AbortSignal,
): Promise<TranscribeResponse> {
  const form = new FormData()
  form.set("file", file, filename)
  return postForJson<TranscribeResponse>("/api/v1/demo/transcribe", form, signal)
}

export async function analyzeReport(
  context: AnalyzeContext,
  photoPairs: Array<{ before: Blob; after: Blob }>,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const form = new FormData()
  form.set("context", JSON.stringify(context))
  photoPairs.forEach((pair, index) => {
    form.append("before", pair.before, `before-${index}.jpg`)
    form.append("after", pair.after, `after-${index}.jpg`)
  })
  return postForJson<AnalyzeResponse>("/api/v1/demo/analyze", form, signal)
}

export async function renderCheckPdf(
  context: CheckPdfContext,
  signaturePng: Blob,
  signal?: AbortSignal,
): Promise<Blob> {
  const form = new FormData()
  form.set("context", JSON.stringify(context))
  form.set("signature", signaturePng, "signature.png")
  const response = await fetch("/api/v1/demo/check-pdf", { method: "POST", body: form, signal })
  if (!response.ok) throw new JobActApiError(await readErrorEnvelope(response))
  return response.blob()
}
