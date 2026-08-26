"use client"

import { useEffect, useRef, useState } from "react"
import {
  ArrowRight,
  MapPin,
  Clock,
  Calendar,
  Check,
  Mic,
  Pencil,
  Sparkles,
  Camera,
  ShieldCheck,
  Share2,
  House,
  Plus,
  Trash2,
  CircleCheck,
  LoaderCircle,
  TriangleAlert,
} from "lucide-react"
import {
  Button,
  Card,
  Input,
  AmountField,
  ScreenHeader,
  SectionLabel,
  PhotoThumb,
  CaptureButton,
  SignatureCanvas,
  SuccessMark,
  StatusBadge,
  SyncIndicator,
} from "../ui"
import { Page, ActionBar } from "../shell"
import { Avatar } from "../cards"
import {
  customers as allCustomers,
  currency,
} from "@/lib/jobact/data"
import { useNav } from "@/lib/jobact/store"
import {
  apiFetch,
  type CustomerResponse,
  type MediaUploadResponse,
  type ReportResponse,
  type VisitResponse,
} from "@/lib/jobact/api"
import type { SignatureCanvasHandle } from "../ui"

function useCustomer() {
  const { frame, draft } = useNav()
  const id = (frame.params.customerId as string) || draft.customerId
  const known = allCustomers.find((c) => c.id === id)
  return {
    name: known?.name || draft.customerName || "New customer",
    address: known?.address || draft.address || "Address on file",
    type: known?.type || "Service visit",
  }
}

function FlowFooter({ children }: { children: React.ReactNode }) {
  return <ActionBar width="form">{children}</ActionBar>
}

/* ---------------------------- ADD CUSTOMER ---------------------------- */

export function AddCustomerScreen() {
  const { back, replace, frame, setDraft } = useNav()
  const picking = Boolean(frame.params.picking)
  const [name, setName] = useState("")
  const [address, setAddress] = useState("")
  const [phone, setPhone] = useState("")
  const [serviceType, setServiceType] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const saveKey = useRef(crypto.randomUUID())

  async function saveCustomer() {
    setSaving(true)
    setError(null)
    try {
      const customer = await apiFetch<CustomerResponse>("/api/v1/customers", {
        method: "POST",
        headers: { "Idempotency-Key": saveKey.current },
        body: JSON.stringify({
          name,
          address,
          phone,
          service_type: serviceType || "Service visit",
        }),
      })
      setDraft({
        customerId: customer.id,
        customerName: customer.name,
        address: customer.address,
        visitId: undefined,
        reportId: undefined,
        revisionId: undefined,
        signatureAssetId: undefined,
        rawNotes: "",
        report: undefined,
        beforePhotos: 0,
        afterPhotos: 0,
        workCompleted: "",
        amount: "",
        signed: false,
      })
      if (picking) replace("visitStart", { customerId: customer.id })
      else back()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save customer.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ScreenHeader title="Add customer" onBack={back} />
      <Page width="form">
        <div className="space-y-4">
          <Input id="name" label="Customer name" placeholder="e.g. Aurora Dental Clinic" value={name} onChange={(e) => setName(e.target.value)} />
          <Input id="address" label="Address" icon={MapPin} placeholder="Street, unit, city" value={address} onChange={(e) => setAddress(e.target.value)} />
          <Input id="phone" label="Phone" type="tel" placeholder="+1 (___) ___-____" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <Input id="type" label="Service type" placeholder="AC maintenance, cleaning, repair…" hint="Optional — helps you find them later" value={serviceType} onChange={(e) => setServiceType(e.target.value)} />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
      </Page>
      <FlowFooter>
        <Button
          size="lg"
          fullWidth
          disabled={!name.trim() || !address.trim() || !phone.trim() || saving}
          iconRight={picking ? ArrowRight : undefined}
          onClick={saveCustomer}
        >
          {picking ? "Save & continue" : "Save customer"}
        </Button>
      </FlowFooter>
    </>
  )
}

/* ----------------------------- VISIT START ---------------------------- */

export function VisitStartScreen() {
  const { back, navigate, frame, draft, setDraft } = useNav()
  const customer = useCustomer()
  const now = new Date()
  const visitId = useRef(crypto.randomUUID())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const startKey = useRef(crypto.randomUUID())

  async function startVisit() {
    if (!draft.customerId) return
    setSaving(true)
    setError(null)
    try {
      const visit = await apiFetch<VisitResponse>("/api/v1/visits", {
        method: "POST",
        headers: { "Idempotency-Key": startKey.current },
        body: JSON.stringify({ id: visitId.current, customer_id: draft.customerId }),
      })
      setDraft({ visitId: visit.id })
      navigate("gps", frame.params)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start visit.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ScreenHeader title="Start visit" subtitle="Step 2 · Confirm the details" onBack={back} step={2} totalSteps={6} />
      <Page width="form">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <Avatar initials={customer.name.slice(0, 2).toUpperCase()} className="size-12 rounded-2xl" />
            <div className="min-w-0">
              <p className="text-base font-semibold text-foreground">{customer.name}</p>
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin className="size-3" /> {customer.address}
              </p>
            </div>
          </div>
        </Card>

        <SectionLabel>
          <span className="mt-5 block">Visit metadata</span>
        </SectionLabel>
        <Card className="divide-y divide-border">
          <MetaRow icon={Calendar} label="Date" value="August 22, 2026" />
          <MetaRow icon={Clock} label="Start time" value="09:41 AM" auto />
          <MetaRow icon={MapPin} label="Location" value="Locating…" pending />
        </Card>
        <p className="mt-3 px-1 text-xs leading-relaxed text-muted-foreground">
          Date, time and GPS are captured automatically and attached to the report as proof.
        </p>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        <Button size="lg" fullWidth iconRight={ArrowRight} disabled={saving} onClick={startVisit}>
          {saving ? "Starting visit…" : "Confirm location"}
        </Button>
      </FlowFooter>
    </>
  )
}

function MetaRow({
  icon: Icon,
  label,
  value,
  auto,
  pending,
}: {
  icon: typeof Clock
  label: string
  value: string
  auto?: boolean
  pending?: boolean
}) {
  return (
    <div className="flex items-center gap-3 p-3.5">
      <span className="grid size-9 place-items-center rounded-xl bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </span>
      <span className="flex-1 text-sm text-muted-foreground">{label}</span>
      <span className={"text-sm font-medium " + (pending ? "text-muted-foreground" : "text-foreground")}>
        {value}
      </span>
      {auto && <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">auto</span>}
    </div>
  )
}

/* ------------------------------- GPS ---------------------------------- */

type GeoPoint = { lat: number; lon: number; accuracy: number }

function requestBrowserLocation(): Promise<GeoPoint> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("unsupported"))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          accuracy: position.coords.accuracy,
        }),
      reject,
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 },
    )
  })
}

function describeLocationError(err: unknown): string {
  if (err instanceof Error && err.message === "unsupported") {
    return "This browser can't share your location. Try a different browser or device."
  }
  if (typeof err === "object" && err !== null && "code" in err) {
    switch ((err as GeolocationPositionError).code) {
      case 1: // PERMISSION_DENIED
        return "Location access was denied. Allow location access for this site, then try again."
      case 2: // POSITION_UNAVAILABLE
        return "Your location couldn't be determined. Try moving somewhere with a clearer signal."
      case 3: // TIMEOUT
        return "Finding your location took too long. Try again."
    }
  }
  return "Couldn't get your location. Try again."
}

export function GpsScreen() {
  const { back, navigate, frame, draft } = useNav()
  const [state, setState] = useState<"locating" | "found" | "error">("locating")
  const [point, setPoint] = useState<GeoPoint | null>(null)
  const [locateError, setLocateError] = useState<string | null>(null)
  const customer = useCustomer()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const locationKey = useRef(crypto.randomUUID())

  function locate() {
    setState("locating")
    setLocateError(null)
    requestBrowserLocation()
      .then((next) => {
        setPoint(next)
        setState("found")
      })
      .catch((reason) => {
        setLocateError(describeLocationError(reason))
        setState("error")
      })
  }

  useEffect(() => {
    locate()
  }, [])

  async function confirmLocation() {
    if (!draft.visitId || !point) return
    setSaving(true)
    setError(null)
    try {
      await apiFetch<VisitResponse>(`/api/v1/visits/${draft.visitId}`, {
        method: "PATCH",
        headers: { "Idempotency-Key": locationKey.current },
        body: JSON.stringify({
          gps_lat: point.lat,
          gps_lon: point.lon,
          gps_accuracy_m: point.accuracy,
        }),
      })
      navigate("beforePhotos", frame.params)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save location.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ScreenHeader title="Location" onBack={back} />
      <Page width="form" className="flex flex-col">
        <div className="relative overflow-hidden rounded-3xl border border-border" style={{ height: 260 }}>
          {/* stylised monochrome map */}
          <div
            className="absolute inset-0"
            style={{
              backgroundColor: "oklch(0.2 0 0)",
              backgroundImage:
                "linear-gradient(oklch(0.26 0 0) 1px, transparent 1px), linear-gradient(90deg, oklch(0.26 0 0) 1px, transparent 1px)",
              backgroundSize: "34px 34px",
            }}
          />
          <svg className="absolute inset-0 h-full w-full" aria-hidden="true">
            <path d="M-10 60 L120 90 L220 40 L440 120" stroke="oklch(0.32 0 0)" strokeWidth="10" fill="none" />
            <path d="M40 -10 L90 120 L60 300" stroke="oklch(0.32 0 0)" strokeWidth="8" fill="none" />
            <path d="M300 -10 L260 300" stroke="oklch(0.3 0 0)" strokeWidth="6" fill="none" />
          </svg>
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
            {state === "locating" ? (
              <span className="flex size-16 items-center justify-center">
                <span className="absolute size-16 animate-ping rounded-full bg-foreground/20" />
                <span className="size-4 rounded-full bg-foreground" />
              </span>
            ) : state === "found" ? (
              <span className="relative flex flex-col items-center">
                <span className="grid size-11 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg">
                  <MapPin className="size-5" />
                </span>
                <span className="mt-1 size-2 rounded-full bg-primary/40" />
              </span>
            ) : (
              <span className="grid size-11 place-items-center rounded-full bg-destructive/15 text-destructive">
                <TriangleAlert className="size-5" />
              </span>
            )}
          </div>
        </div>

        <Card className="mt-4 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">GPS location</p>
            {state === "found" ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-success">
                <CircleCheck className="size-3.5" /> Confirmed
              </span>
            ) : state === "error" ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive">
                <TriangleAlert className="size-3.5" /> Location needed
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <LoaderCircle className="size-3.5 animate-spin" /> Locating
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{customer.address}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground/70">
            {state === "found" && point
              ? `${point.lat.toFixed(5)}, ${point.lon.toFixed(5)} · ±${Math.round(point.accuracy)}m`
              : state === "error"
                ? "Location unavailable"
                : "Acquiring satellites…"}
          </p>
        </Card>
        {state === "error" && locateError && (
          <p className="mt-3 text-sm text-destructive">{locateError}</p>
        )}
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        {state === "error" ? (
          <Button size="lg" fullWidth iconRight={ArrowRight} onClick={locate}>
            Try again
          </Button>
        ) : (
          <Button
            size="lg"
            fullWidth
            disabled={state !== "found" || saving}
            iconRight={ArrowRight}
            onClick={confirmLocation}
          >
            {state === "found" ? (saving ? "Saving…" : "Location confirmed") : "Locating…"}
          </Button>
        )}
      </FlowFooter>
    </>
  )
}

/* --------------------------- BEFORE PHOTOS ---------------------------- */

export function PhotosScreen({ phase }: { phase: "before" | "after" }) {
  const { back, navigate, frame, draft, setDraft } = useNav()
  const count = phase === "before" ? draft.beforePhotos : draft.afterPhotos
  const seeded = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const photosKey = useRef(crypto.randomUUID())

  // seed with a sensible default so previews look real
  useEffect(() => {
    if (seeded.current) return
    seeded.current = true
    if (phase === "before" && draft.beforePhotos === 0) setDraft({ beforePhotos: 2 })
    if (phase === "after" && draft.afterPhotos === 0) setDraft({ afterPhotos: 2 })
  }, [phase, draft.beforePhotos, draft.afterPhotos, setDraft])

  function add() {
    if (phase === "before") setDraft({ beforePhotos: draft.beforePhotos + 1 })
    else setDraft({ afterPhotos: draft.afterPhotos + 1 })
  }
  function removeAt() {
    if (phase === "before") setDraft({ beforePhotos: Math.max(0, draft.beforePhotos - 1) })
    else setDraft({ afterPhotos: Math.max(0, draft.afterPhotos - 1) })
  }

  const step = phase === "before" ? 3 : 5
  const title = phase === "before" ? "Before photos" : "After photos"
  const next = phase === "before" ? "voice" : "signature"

  async function continueFlow() {
    if (!draft.visitId) return
    setSaving(true)
    setError(null)
    try {
      await apiFetch<VisitResponse>(`/api/v1/visits/${draft.visitId}`, {
        method: "PATCH",
        headers: { "Idempotency-Key": photosKey.current },
        body: JSON.stringify(
          phase === "before"
            ? { before_photo_count: count }
            : { after_photo_count: count },
        ),
      })
      navigate(next, frame.params)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save photo count.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ScreenHeader
        title={title}
        subtitle={phase === "before" ? "Step 3 · Capture the starting state" : "Step 5 · Show the finished work"}
        onBack={back}
        step={step}
        totalSteps={6}
      />
      <Page width="form">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {count} photo{count === 1 ? "" : "s"} captured
          </p>
          <span
            className={
              "rounded-full px-2.5 py-1 text-xs font-medium " +
              (phase === "before" ? "bg-muted text-muted-foreground" : "bg-success/15 text-success")
            }
          >
            {title}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2.5 sm:grid-cols-4">
          <CaptureButton onCapture={add} />
          {Array.from({ length: count }).map((_, i) => (
            <PhotoThumb key={i} tone={phase} index={i + 1} onRemove={removeAt} />
          ))}
        </div>

        <Card className="mt-5 flex items-start gap-3 p-3.5">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
            <Camera className="size-4" />
          </span>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {phase === "before"
              ? "Photograph the problem area before you start. These become part of the proof archive."
              : "Capture the completed work from the same angles as your before photos for a clear comparison."}
          </p>
        </Card>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        <Button size="lg" fullWidth iconRight={ArrowRight} disabled={count === 0 || saving} onClick={continueFlow}>
          Continue
        </Button>
      </FlowFooter>
    </>
  )
}

/* ------------------------------- VOICE -------------------------------- */

export function VoiceScreen() {
  const { back, navigate, frame, setDraft } = useNav()
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (!recording) return
    const t = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [recording])

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0")
  const ss = String(seconds % 60).padStart(2, "0")

  return (
    <>
      <ScreenHeader title="Describe the work" subtitle="Step 4 · Speak, don't type" onBack={back} step={4} totalSteps={6} />
      <Page width="form" className="flex flex-col items-center lg:py-10">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-foreground text-balance">
            What did you do on this visit?
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
            Mention what you repaired or serviced and any materials used. We&apos;ll turn it into a clean report.
          </p>
        </div>

        {/* waveform */}
        <div className="mt-10 flex h-24 items-center justify-center gap-1">
          {Array.from({ length: 28 }).map((_, i) => (
            <span
              key={i}
              className={"w-1 rounded-full " + (recording ? "bg-foreground" : "bg-border")}
              style={{
                height: recording ? `${12 + Math.abs(Math.sin(i * 0.9 + seconds)) * 56}px` : "12px",
                transition: "height 0.2s ease",
              }}
            />
          ))}
        </div>

        <p className="mt-4 font-mono text-2xl font-semibold tabular-nums text-foreground">
          {mm}:{ss}
        </p>
        <p className="text-xs text-muted-foreground">{recording ? "Recording…" : "Tap to start recording"}</p>

        <button
          onClick={() => setRecording((r) => !r)}
          aria-label={recording ? "Stop recording" : "Start recording"}
          className={
            "mt-8 grid size-20 place-items-center rounded-full transition-all active:scale-95 " +
            (recording
              ? "bg-destructive text-destructive-foreground shadow-lg shadow-destructive/30"
              : "bg-primary text-primary-foreground shadow-lg shadow-black/30")
          }
        >
          {recording ? <span className="size-6 rounded-md bg-current" /> : <Mic className="size-8" />}
        </button>

        <button
          onClick={() => navigate("editReport", { ...frame.params, manual: true })}
          className="mt-8 text-sm font-medium text-muted-foreground underline underline-offset-4 hover:text-foreground"
        >
          Type it instead
        </button>
      </Page>
      <FlowFooter>
        <Button
          size="lg"
          fullWidth
          iconRight={ArrowRight}
          disabled={seconds < 1}
          onClick={() => {
            setDraft({
              rawNotes:
                "Diagnosed an intermittent compressor fault. Replaced the start capacitor, cleaned the contactor points, and verified stable operation. Used one 45uF capacitor and contact cleaner. Charged 160 dollars.",
            })
            navigate("voiceProcessing", frame.params)
          }}
        >
          Use recording
        </Button>
      </FlowFooter>
    </>
  )
}

/* -------------------------- VOICE PROCESSING -------------------------- */

export function VoiceProcessingScreen() {
  const { navigate, frame, draft, setDraft } = useNav()
  const steps = ["Transcribing your note", "Structuring the report", "Detecting materials & amount"]
  const [active, setActive] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)
  const notesKey = useRef(crypto.randomUUID())
  const reportKey = useRef(crypto.randomUUID())

  useEffect(() => {
    if (started.current) return
    started.current = true
    let cancelled = false

    async function buildReport() {
      if (!draft.visitId || !draft.rawNotes) {
        throw new Error("Visit notes are missing.")
      }
      setActive(1)
      await apiFetch<VisitResponse>(`/api/v1/visits/${draft.visitId}`, {
        method: "PATCH",
        headers: { "Idempotency-Key": notesKey.current },
        body: JSON.stringify({ raw_notes: draft.rawNotes }),
      })
      const created = await apiFetch<ReportResponse>("/api/v1/reports", {
        method: "POST",
        headers: { "Idempotency-Key": reportKey.current },
        body: JSON.stringify({ visit_id: draft.visitId, raw_notes: draft.rawNotes }),
      })
      if (cancelled) return
      setDraft({
        reportId: created.id,
        revisionId: created.current_revision.id,
        report: created,
      })
      setActive(2)

      for (let attempt = 0; attempt < 60 && !cancelled; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000))
        const report = await apiFetch<ReportResponse>(`/api/v1/reports/${created.id}`)
        if (cancelled) return
        setDraft({
          revisionId: report.current_revision.id,
          report,
          workCompleted: report.current_revision.work_completed,
          amount:
            report.current_revision.amount_cents === null
              ? ""
              : String(report.current_revision.amount_cents / 100),
        })
        if (report.workflow_state === "MANUAL_INPUT_REQUIRED") {
          navigate("editReport", { ...frame.params, manual: true })
          return
        }
        if (report.workflow_state === "REVIEW_PENDING") {
          setActive(3)
          navigate("reportDraft", frame.params)
          return
        }
      }
      throw new Error("Report drafting timed out. Please try again.")
    }

    buildReport().catch((reason: unknown) => {
      if (!cancelled) {
        setError(reason instanceof Error ? reason.message : "Could not build report.")
      }
    })
    return () => {
      cancelled = true
    }
  }, [draft.rawNotes, draft.visitId, frame.params, navigate, setDraft])

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
      <div className="relative grid size-20 place-items-center rounded-3xl border border-border bg-card">
        <Sparkles className="size-8 text-foreground" />
        <span className="absolute inset-0 rounded-3xl border border-foreground/20 animate-ping" />
      </div>
      <h2 className="mt-6 text-lg font-semibold text-foreground">Building your report</h2>
      <p className="mt-1 text-sm text-muted-foreground">This usually takes a few seconds</p>
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

      <div className="mt-8 w-full max-w-xs space-y-3 text-left">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-3">
            <span
              className={
                "grid size-6 place-items-center rounded-full border text-xs " +
                (i < active
                  ? "border-success bg-success text-success-foreground"
                  : i === active
                    ? "border-foreground text-foreground"
                    : "border-border text-muted-foreground")
              }
            >
              {i < active ? <Check className="size-3.5" strokeWidth={3} /> : i === active ? <LoaderCircle className="size-3.5 animate-spin" /> : i + 1}
            </span>
            <span className={"text-sm " + (i <= active ? "text-foreground" : "text-muted-foreground")}>{s}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* --------------------------- REPORT DRAFT ----------------------------- */

export function ReportDraftScreen() {
  const { back, navigate, frame, draft, setDraft } = useNav()
  const customer = useCustomer()
  const report = draft.report
  const revision = report?.current_revision
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const confirmKey = useRef(crypto.randomUUID())

  async function continueToEvidence() {
    if (!draft.reportId) return
    setConfirming(true)
    setError(null)
    try {
      const confirmed = revision?.confirmed_by_user_at
        ? report
        : await apiFetch<ReportResponse>(`/api/v1/reports/${draft.reportId}/confirm`, {
            method: "POST",
            headers: { "Idempotency-Key": confirmKey.current },
          })
      if (confirmed) setDraft({ report: confirmed })
      navigate("afterPhotos", frame.params)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not confirm report.")
    } finally {
      setConfirming(false)
    }
  }

  return (
    <>
      <ScreenHeader
        title="Report draft"
        subtitle="Step 6 · Review the generated report"
        onBack={back}
        step={6}
        totalSteps={6}
        right={<StatusBadge status="draft" />}
      />
      <Page width="form">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2.5">
          <Sparkles className="size-4 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">
            {revision?.source === "ai"
              ? "AI draft — check the amount and edit anything before signing."
              : "Review and confirm the report before signing."}
          </p>
        </div>

        <SectionLabel>
          <span className="mt-5 block">Visit</span>
        </SectionLabel>
        <Card className="p-4">
          <p className="text-sm font-semibold text-foreground">{customer.name}</p>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="size-3" /> {customer.address}
          </p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1"><Calendar className="size-3" /> Aug 22, 2026</span>
            <span className="inline-flex items-center gap-1"><Clock className="size-3" /> 09:41 AM</span>
            <span className="inline-flex items-center gap-1"><Camera className="size-3" /> {draft.beforePhotos + draft.afterPhotos} photos</span>
          </div>
        </Card>

        <EditableSection title="Work completed" onEdit={() => navigate("editReport", frame.params)}>
          <p className="text-sm leading-relaxed text-foreground">
            {revision?.work_completed || draft.workCompleted}
          </p>
        </EditableSection>

        <EditableSection title="Materials / consumables" onEdit={() => navigate("editReport", frame.params)}>
          <ul className="space-y-1.5 text-sm text-foreground">
            {(revision?.materials ?? []).map((material) => (
              <li key={`${material.label}-${material.qty}`} className="flex justify-between">
                <span>{material.label}</span>
                <span className="text-muted-foreground">×{material.qty}</span>
              </li>
            ))}
          </ul>
        </EditableSection>

        <EditableSection title="Amount" onEdit={() => navigate("editReport", frame.params)}>
          <p className="font-mono text-2xl font-semibold text-foreground">
            {revision?.amount_cents === null
              ? "Not specified"
              : `${(revision?.amount_cents ?? 0) / 100} ${revision?.currency ?? "RUB"}`}
          </p>
        </EditableSection>

        <SectionLabel>
          <span className="mt-5 block">Visit evidence</span>
        </SectionLabel>
        <div className="grid grid-cols-2 gap-2.5">
          <Card className="p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Before</p>
            <div className="grid grid-cols-2 gap-1.5">
              {Array.from({ length: Math.min(draft.beforePhotos || 2, 2) }).map((_, i) => (
                <PhotoThumb key={i} tone="before" index={i + 1} />
              ))}
            </div>
          </Card>
          <Card className="p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">After</p>
            <div className="grid grid-cols-2 gap-1.5">
              {Array.from({ length: Math.min(draft.afterPhotos || 2, 2) }).map((_, i) => (
                <PhotoThumb key={i} tone="after" index={i + 1} />
              ))}
            </div>
          </Card>
        </div>
      </Page>
      <FlowFooter>
        {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
        <div className="flex gap-3">
          <Button variant="secondary" size="lg" icon={Pencil} onClick={() => navigate("editReport", frame.params)}>
            Edit
          </Button>
          <Button size="lg" fullWidth iconRight={ArrowRight} disabled={confirming} onClick={continueToEvidence}>
            {confirming ? "Confirming…" : "Continue"}
          </Button>
        </div>
      </FlowFooter>
    </>
  )
}

function EditableSection({
  title,
  children,
  onEdit,
}: {
  title: string
  children: React.ReactNode
  onEdit: () => void
}) {
  return (
    <section className="mt-5">
      <div className="mb-2 flex items-center justify-between">
        <SectionLabel>{title}</SectionLabel>
        <button onClick={onEdit} className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
          <Pencil className="size-3" /> Edit
        </button>
      </div>
      <Card className="p-4">{children}</Card>
    </section>
  )
}

/* ----------------------------- EDIT REPORT ---------------------------- */

export function EditReportScreen() {
  const { back, replace, frame, draft, setDraft } = useNav()
  const typingNotes = Boolean(frame.params.manual) && !draft.reportId
  const [work, setWork] = useState(
    (Boolean(frame.params.manual)
      ? draft.rawNotes
      : draft.report?.current_revision.work_completed || draft.workCompleted) ||
      "Diagnosed intermittent compressor fault. Replaced the start capacitor and cleaned the contactor points. Verified stable operation before leaving.",
  )
  const [amount, setAmount] = useState(
    draft.report?.current_revision.amount_cents === null
      ? ""
      : draft.amount || String((draft.report?.current_revision.amount_cents ?? 16000) / 100),
  )
  const [materials, setMaterials] = useState(
    draft.report?.current_revision.materials.map((material) => ({
      id: crypto.randomUUID(),
      ...material,
    })) ?? [],
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const updateKey = useRef(crypto.randomUUID())
  const confirmKey = useRef(crypto.randomUUID())

  async function save() {
    if (typingNotes) {
      setDraft({ rawNotes: work })
      replace("voiceProcessing", frame.params)
      return
    }
    if (!draft.reportId) return
    setSaving(true)
    setError(null)
    try {
      const updated = await apiFetch<ReportResponse>(
        `/api/v1/reports/${draft.reportId}/revision`,
        {
          method: "PATCH",
          headers: { "Idempotency-Key": updateKey.current },
          body: JSON.stringify({
            work_completed: work,
            amount_cents: amount ? Math.round(Number(amount) * 100) : null,
            currency: draft.report?.current_revision.currency ?? "RUB",
            materials: materials
              .filter((material) => material.label.trim())
              .map(({ label, qty }) => ({ label, qty })),
          }),
        },
      )
      const confirmed = await apiFetch<ReportResponse>(
        `/api/v1/reports/${draft.reportId}/confirm`,
        {
          method: "POST",
          headers: { "Idempotency-Key": confirmKey.current },
        },
      )
      setDraft({
        workCompleted: work,
        amount,
        revisionId: confirmed.current_revision.id,
        report: { ...updated, ...confirmed },
      })
      replace("reportDraft", frame.params)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save report.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ScreenHeader
        title="Edit report"
        onBack={back}
        right={
          <Button size="sm" onClick={save}>
            Done
          </Button>
        }
      />
      <Page width="form">
        <label className="block">
          <span className="mb-1.5 flex items-center justify-between text-sm font-medium text-muted-foreground">
            Work completed
            <span className="inline-flex items-center gap-1 text-xs"><Mic className="size-3" /> from voice</span>
          </span>
          <textarea
            value={work}
            onChange={(e) => setWork(e.target.value)}
            rows={5}
            className="w-full resize-none rounded-xl border border-input bg-card p-4 text-sm leading-relaxed text-foreground focus:border-ring focus:outline-none"
          />
        </label>

        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between">
            <SectionLabel>Materials / consumables</SectionLabel>
            <button
              onClick={() => setMaterials((m) => [...m, { id: crypto.randomUUID(), label: "", qty: "1" }])}
              className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <Plus className="size-3" /> Add
            </button>
          </div>
          <div className="space-y-2">
            {materials.map((m) => (
              <div key={m.id} className="flex items-center gap-2">
                <input
                  value={m.label}
                  onChange={(event) =>
                    setMaterials((list) =>
                      list.map((item) =>
                        item.id === m.id ? { ...item, label: event.target.value } : item,
                      ),
                    )
                  }
                  placeholder="Material"
                  className="h-11 flex-1 rounded-xl border border-input bg-card px-3 text-sm text-foreground focus:border-ring focus:outline-none"
                />
                <input
                  value={m.qty}
                  onChange={(event) =>
                    setMaterials((list) =>
                      list.map((item) =>
                        item.id === m.id ? { ...item, qty: event.target.value } : item,
                      ),
                    )
                  }
                  className="h-11 w-14 rounded-xl border border-input bg-card px-3 text-center text-sm text-foreground focus:border-ring focus:outline-none"
                />
                <button
                  onClick={() => setMaterials((list) => list.filter((x) => x.id !== m.id))}
                  aria-label="Remove material"
                  className="grid size-11 place-items-center rounded-xl text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-5">
          <AmountField label="Amount charged" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ""))} placeholder="0" />
        </div>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        <Button size="lg" fullWidth icon={Check} disabled={saving} onClick={save}>
          {typingNotes ? "Use these notes" : saving ? "Saving…" : "Save changes"}
        </Button>
      </FlowFooter>
    </>
  )
}

/* ------------------------------ SIGNATURE ----------------------------- */

export function SignatureScreen() {
  const { back, navigate, frame, draft, setDraft } = useNav()
  const [hasInk, setHasInk] = useState(false)
  const [signerName, setSignerName] = useState("On-site manager")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const signatureRef = useRef<SignatureCanvasHandle>(null)
  const readyKey = useRef(crypto.randomUUID())
  const uploadKey = useRef(crypto.randomUUID())
  const attachKey = useRef(crypto.randomUUID())
  const signKey = useRef(crypto.randomUUID())
  const customer = useCustomer()

  async function waitForCompletion() {
    if (!draft.reportId) return false
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      const completed = await apiFetch<ReportResponse>(
        `/api/v1/reports/${draft.reportId}`,
      )
      setDraft({ report: completed })
      if (completed.workflow_state === "COMPLETED") {
        navigate("completed", frame.params)
        return true
      }
    }
    return false
  }

  async function finishReport() {
    if (!draft.reportId) return
    setSaving(true)
    setError(null)
    try {
      let report = draft.report
      if (report?.workflow_state === "COMPLETED") {
        navigate("completed", frame.params)
        return
      }
      if (report?.workflow_state === "PDF_PENDING") {
        if (!(await waitForCompletion())) {
          throw new Error("PDF generation timed out. The report remains saved.")
        }
        return
      }
      if (report?.workflow_state !== "SIGNATURE_PENDING") {
        report = await apiFetch<ReportResponse>(
          `/api/v1/reports/${draft.reportId}/ready-for-signature`,
          {
            method: "POST",
            headers: { "Idempotency-Key": readyKey.current },
          },
        )
        setDraft({ report })
      }

      const png = await signatureRef.current?.exportPng()
      if (!png) throw new Error("Draw a signature before continuing.")
      const digest = await crypto.subtle.digest("SHA-256", await png.arrayBuffer())
      const sha256 = Array.from(new Uint8Array(digest), (byte) =>
        byte.toString(16).padStart(2, "0"),
      ).join("")
      const upload = await apiFetch<MediaUploadResponse>("/api/v1/media/uploads", {
        method: "POST",
        headers: { "Idempotency-Key": uploadKey.current },
        body: JSON.stringify({
          content_type: "image/png",
          byte_size: png.size,
          sha256,
          kind: "signature",
          report_id: draft.reportId,
        }),
      })
      const uploadResponse = await fetch(upload.upload_url, {
        method: "PUT",
        headers: { "Content-Type": "image/png", "x-amz-meta-sha256": sha256 },
        body: png,
      })
      if (!uploadResponse.ok) throw new Error("Signature upload failed.")
      await apiFetch(`/api/v1/media/${upload.media_asset_id}/attach`, {
        method: "POST",
        headers: { "Idempotency-Key": attachKey.current },
      })
      const signed = await apiFetch<ReportResponse>(
        `/api/v1/reports/${draft.reportId}/sign`,
        {
          method: "POST",
          headers: { "Idempotency-Key": signKey.current },
          body: JSON.stringify({
            signer_name: signerName,
            signature_media_asset_id: upload.media_asset_id,
          }),
        },
      )
      setDraft({
        signed: true,
        signatureAssetId: upload.media_asset_id,
        report: signed,
      })

      if (!(await waitForCompletion())) {
        throw new Error("PDF generation timed out. The report remains saved.")
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not sign report.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ScreenHeader title="Customer confirmation" onBack={back} />
      <Page width="form">
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">
            By signing, <span className="font-medium text-foreground">{customer.name}</span> confirms the work
            described was completed to their satisfaction.
          </p>
        </Card>

        <div className="mt-5">
          <SectionLabel>Signature</SectionLabel>
          <SignatureCanvas ref={signatureRef} onChange={setHasInk} />
        </div>

        <Input id="signer" label="Signed by" placeholder="Name of person signing" value={signerName} onChange={(event) => setSignerName(event.target.value)} className="mt-2" />

        <Card className="mt-4 flex items-center gap-3 p-3.5">
          <ShieldCheck className="size-5 shrink-0 text-muted-foreground" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            The signature is stored with the timestamp and GPS location as tamper-evident proof.
          </p>
        </Card>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        <div className="space-y-2.5">
          <Button
            size="lg"
            fullWidth
            icon={Check}
            disabled={!hasInk || !signerName.trim() || saving}
            onClick={finishReport}
          >
            {saving ? "Finalizing…" : "Confirm & finish"}
          </Button>
          <Button variant="ghost" size="md" fullWidth icon={Share2} onClick={() => navigate("completed", frame.params)}>
            Send link to sign instead
          </Button>
        </div>
      </FlowFooter>
    </>
  )
}

/* ------------------------------ COMPLETED ----------------------------- */

export function CompletedScreen() {
  const { reset, navigate, draft } = useNav()
  const customer = useCustomer()
  const [error, setError] = useState<string | null>(null)
  const revision = draft.report?.current_revision
  const completedAmount =
    revision?.amount_cents === null || revision?.amount_cents === undefined
      ? "Not specified"
      : `${(revision.amount_cents / 100).toFixed(2)} ${revision.currency}`

  async function openPdf() {
    const assetId = draft.report?.pdf_media_asset_id
    if (!assetId) {
      setError("The PDF is not available yet.")
      return
    }
    try {
      const result = await apiFetch<{ url: string }>(`/api/v1/media/${assetId}/url`)
      window.location.assign(result.url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not open PDF.")
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <Page width="form" className="flex flex-col items-center pt-10 lg:pt-14">
        <SuccessMark />
        <h1 className="mt-6 text-2xl font-semibold tracking-tight text-foreground">Report completed</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">Proof of this visit is saved and secured.</p>

        <Card className="mt-8 w-full p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">{customer.name}</p>
            <StatusBadge status="completed" />
          </div>
          <div className="mt-4 space-y-3 text-sm">
            <SummaryRow label="Date & time" value="Aug 22, 2026 · 09:41 AM" />
            <SummaryRow label="Location" value="Captured · ±5m" />
            <SummaryRow label="Photos" value={`${draft.beforePhotos + draft.afterPhotos} (before & after)`} />
            <SummaryRow label="Signature" value={draft.signed ? "Signed on-site" : "Link sent"} />
            <SummaryRow label="Amount" value={completedAmount} strong />
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
            <span className="font-mono text-xs text-muted-foreground">
              {draft.report?.human_id ?? "Report"}
            </span>
            <SyncIndicator state="synced" />
          </div>
        </Card>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>

      <FlowFooter>
        <div className="space-y-2.5">
          <Button size="lg" fullWidth icon={Share2} onClick={openPdf}>
            Open signed PDF
          </Button>
          <div className="flex gap-3">
            <Button variant="secondary" size="lg" fullWidth onClick={() => navigate("reportDetail", { reportId: draft.reportId })}>
              View report
            </Button>
            <Button variant="ghost" size="lg" icon={House} onClick={() => reset("home")}>
              Done
            </Button>
          </div>
        </div>
      </FlowFooter>
    </div>
  )
}

function SummaryRow({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={strong ? "font-mono font-semibold text-foreground" : "font-medium text-foreground"}>{value}</span>
    </div>
  )
}
