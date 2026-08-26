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
