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

export interface CustomerResponse {
  id: string
  name: string
  address: string
  phone: string
  service_type: string
  created_at: string
}

export interface VisitResponse {
  id: string
  customer_id: string
  technician_id: string
  status: string
  started_at: string
  gps_lat: number | null
  gps_lon: number | null
  gps_accuracy_m: number | null
  before_photo_count: number
  after_photo_count: number
}

export interface ReportMaterial {
  label: string
  qty: string
}

export interface ReportResponse {
  id: string
  human_id: string
  status: string
  visit_id: string
  current_revision: {
    id: string
    revision_no: number
    source: string
    work_completed: string
    amount_cents: number | null
    currency: string
    ai_confidence: string | null
    confirmed_by_user_at: string | null
    amount_confirmed_at: string | null
    frozen_at: string | null
    materials: ReportMaterial[]
    visual_comparison_status: string | null
    visual_comparison: VisualAuditResult | null
  }
  signed_at: string | null
  completed_at: string | null
  workflow_state: WorkflowState | null
  workflow_error: {
    code: string
    http_status: number
    message: string
    retryable: boolean
  } | null
  pdf_media_asset_id: string | null
  transcription?: {
    status: "queued" | "running" | "completed" | "failed"
    media_asset_id: string
    transcript: string | null
    detected_language: string | null
  } | null
}

export type WorkflowState =
  | "COLLECTING_EVIDENCE"
  | "TRANSCRIPTION_PENDING"
  | "DRAFTING_PENDING"
  | "REVIEW_PENDING"
  | "SIGNATURE_PENDING"
  | "FINALIZATION_PENDING"
  | "PDF_PENDING"
  | "COMPLETED"
  | "MANUAL_INPUT_REQUIRED"
  | "FAILED"

export interface ManualRecoveryResponse {
  raw_notes: string
  stage: "analysis" | "pdf"
}

export interface MediaUploadResponse {
  media_asset_id: string
  upload_url: string
  expires_at: string
}

export interface AuthMethodsResponse {
  password: boolean
  google: boolean
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

const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"])

export async function apiFetch<T>(
  input: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  const method = (init.method ?? "GET").toUpperCase()

  if (MUTATION_METHODS.has(method) && !headers.has("Idempotency-Key")) {
    headers.set("Idempotency-Key", crypto.randomUUID())
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(input, {
    ...init,
    method,
    headers,
    credentials: "include",
  })

  if (!response.ok) {
    throw new JobActApiError(await readErrorEnvelope(response))
  }
  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
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
