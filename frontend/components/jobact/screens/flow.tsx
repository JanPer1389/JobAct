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
  CaptureButton,
  SignatureCanvas,
  SuccessMark,
  StatusBadge,
} from "../ui"
import { Page, ActionBar } from "../shell"
import { Avatar } from "../cards"
import { humanReportId, useNav } from "@/lib/jobact/store"
import {
  JobActApiError,
  analyzeReport,
  renderCheckPdf,
  transcribeRecording,
  type AnalyzeContext,
} from "@/lib/jobact/api"
import { saveVisitPhoto, validateVisitAudio } from "@/lib/jobact/media"
import { BrowserAudioRecorder, type RecordingState } from "@/lib/jobact/audio-recorder"
import { formatGpsEvidence } from "@/lib/jobact/location-evidence"
import { finalizeDraft, getBlob, putBlob, saveCheck } from "@/lib/jobact/local-store"
import { setActiveDraftId } from "@/lib/jobact/local-prefs"
import {
  formatCurrency,
  formatDateTime,
  t,
  tPlural,
  verdictLabel,
  type AppLocale,
} from "@/lib/jobact/i18n"
import type { SignatureCanvasHandle } from "../ui"

function currencySymbol(currency: string | undefined) {
  return currency === "RUB" ? "₽" : "$"
}

function FlowFooter({ children }: { children: React.ReactNode }) {
  return <ActionBar width="form">{children}</ActionBar>
}

/* --------------------------- CUSTOMER / JOB INFO ----------------------- */

export function AddCustomerScreen() {
  const { back, navigate, setDraft, locale } = useNav()
  const [name, setName] = useState("")
  const [address, setAddress] = useState("")
  const [phone, setPhone] = useState("")
  const [serviceType, setServiceType] = useState("")

  function saveCustomer() {
    setDraft({
      customerName: name,
      customerAddress: address,
      customerPhone: phone,
      customerServiceType: serviceType || t(locale, "defaultServiceType"),
    })
    navigate("visitStart")
  }

  return (
    <>
      <ScreenHeader title={t(locale, "addCustomerTitle")} onBack={back} />
      <Page width="form">
        <div className="space-y-4">
          <Input id="name" label={t(locale, "customerNameLabel")} placeholder={t(locale, "customerNamePlaceholder")} value={name} onChange={(e) => setName(e.target.value)} />
          <Input id="address" label={t(locale, "addressLabel")} icon={MapPin} placeholder={t(locale, "addressPlaceholder")} value={address} onChange={(e) => setAddress(e.target.value)} />
          <Input id="phone" label={t(locale, "phoneLabel")} type="tel" placeholder="+7 (___) ___-____" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <Input id="type" label={t(locale, "serviceTypeLabel")} placeholder={t(locale, "serviceTypePlaceholder")} hint={t(locale, "serviceTypeHint")} value={serviceType} onChange={(e) => setServiceType(e.target.value)} />
        </div>
      </Page>
      <FlowFooter>
        <Button
          size="lg"
          fullWidth
          disabled={!name.trim() || !address.trim() || !phone.trim()}
          iconRight={ArrowRight}
          onClick={saveCustomer}
        >
          {t(locale, "saveAndContinue")}
        </Button>
      </FlowFooter>
    </>
  )
}

/* ----------------------------- VISIT START ---------------------------- */

export function VisitStartScreen() {
  const { back, navigate, draft, locale } = useNav()
  const now = new Date()

  return (
    <>
      <ScreenHeader title={t(locale, "startVisitTitle")} subtitle={t(locale, "stepConfirmDetails")} onBack={back} step={2} totalSteps={6} />
      <Page width="form">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <Avatar initials={draft.customerName.slice(0, 2).toUpperCase() || "??"} className="size-12 rounded-2xl" />
            <div className="min-w-0">
              <p className="text-base font-semibold text-foreground">{draft.customerName}</p>
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin className="size-3" /> {draft.customerAddress}
              </p>
            </div>
          </div>
        </Card>

        <SectionLabel>
          <span className="mt-5 block">{t(locale, "visitMetadata")}</span>
        </SectionLabel>
        <Card className="divide-y divide-border">
          <MetaRow icon={Calendar} label={t(locale, "dateLabel")} value={new Intl.DateTimeFormat(locale, { year: "numeric", month: "long", day: "numeric" }).format(now)} />
          <MetaRow icon={Clock} label={t(locale, "startTimeLabel")} value={new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(now)} auto autoLabel={t(locale, "autoBadge")} />
          <MetaRow icon={MapPin} label={t(locale, "locationLabel")} value={t(locale, "locatingEllipsis")} pending />
        </Card>
        <p className="mt-3 px-1 text-xs leading-relaxed text-muted-foreground">
          {t(locale, "dateTimeGpsNote")}
        </p>
      </Page>
      <FlowFooter>
        <Button size="lg" fullWidth iconRight={ArrowRight} onClick={() => navigate("gps")}>
          {t(locale, "confirmLocationBtn")}
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
  autoLabel,
  pending,
}: {
  icon: typeof Clock
  label: string
  value: string
  auto?: boolean
  autoLabel?: string
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
      {auto && <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{autoLabel}</span>}
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

function describeLocationError(locale: AppLocale, err: unknown): string {
  if (err instanceof Error && err.message === "unsupported") {
    return t(locale, "locErrUnsupported")
  }
  if (typeof err === "object" && err !== null && "code" in err) {
    switch ((err as GeolocationPositionError).code) {
      case 1: // PERMISSION_DENIED
        return t(locale, "locErrDenied")
      case 2: // POSITION_UNAVAILABLE
        return t(locale, "locErrUnavailable")
      case 3: // TIMEOUT
        return t(locale, "locErrTimeout")
    }
  }
  return t(locale, "locErrGeneric")
}

export function GpsScreen() {
  const { back, navigate, draft, setDraft, locale } = useNav()
  const [state, setState] = useState<"locating" | "found" | "error">("locating")
  const [point, setPoint] = useState<GeoPoint | null>(null)
  const [locateError, setLocateError] = useState<string | null>(null)

  function locate() {
    setState("locating")
    setLocateError(null)
    requestBrowserLocation()
      .then((next) => {
        setPoint(next)
        setState("found")
      })
      .catch((reason) => {
        setLocateError(describeLocationError(locale, reason))
        setState("error")
      })
  }

  useEffect(() => {
    locate()
  }, [])

  function confirmLocation() {
    if (!point) return
    setDraft({ gpsLat: point.lat, gpsLon: point.lon, gpsAccuracyM: point.accuracy })
    navigate("beforePhotos")
  }

  return (
    <>
      <ScreenHeader title={t(locale, "locationTitle")} onBack={back} />
      <Page width="form" className="flex flex-col">
        <div className="relative overflow-hidden rounded-3xl border border-border bg-muted" style={{ height: 260 }}>
          {state === "found" && point ? (
            <div className="grid h-full place-items-center" aria-live="polite">
              <div className="flex flex-col items-center gap-3 px-6 text-center">
                <span className="grid size-16 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg">
                  <MapPin className="size-7" />
                </span>
                <span className="text-sm font-medium text-foreground">{t(locale, "confirmedLabel")}</span>
                <span className="font-mono text-sm text-muted-foreground">
                  {formatGpsEvidence(point)}
                </span>
              </div>
            </div>
          ) : (
            <div className="grid h-full place-items-center" aria-live="polite">
              {state === "locating" ? (
                <span className="flex flex-col items-center gap-3 text-muted-foreground">
                  <LoaderCircle className="size-8 animate-spin" />
                  <span className="text-sm">{t(locale, "locatingLabel")}</span>
                </span>
              ) : (
                <span className="flex flex-col items-center gap-3 text-destructive">
                  <TriangleAlert className="size-8" />
                  <span className="text-sm">{t(locale, "locationUnavailable")}</span>
                </span>
              )}
            </div>
          )}
        </div>

        <Card className="mt-4 p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">{t(locale, "gpsLocationLabel")}</p>
            {state === "found" ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-success">
                <CircleCheck className="size-3.5" /> {t(locale, "confirmedLabel")}
              </span>
            ) : state === "error" ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive">
                <TriangleAlert className="size-3.5" /> {t(locale, "locationNeededLabel")}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <LoaderCircle className="size-3.5 animate-spin" /> {t(locale, "locatingLabel")}
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{draft.customerAddress}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground/70">
            {state === "found" && point
              ? formatGpsEvidence(point)
              : state === "error"
                ? t(locale, "locationUnavailable")
                : t(locale, "acquiringSatellites")}
          </p>
        </Card>
        {state === "error" && locateError && (
          <p className="mt-3 text-sm text-destructive">{locateError}</p>
        )}
      </Page>
      <FlowFooter>
        {state === "error" ? (
          <Button size="lg" fullWidth iconRight={ArrowRight} onClick={locate}>
            {t(locale, "tryAgain")}
          </Button>
        ) : (
          <Button
            size="lg"
            fullWidth
            disabled={state !== "found"}
            iconRight={ArrowRight}
            onClick={confirmLocation}
          >
            {state === "found" ? t(locale, "locationConfirmedBtn") : t(locale, "locatingEllipsis")}
          </Button>
        )}
      </FlowFooter>
    </>
  )
}

/* --------------------------- BEFORE / AFTER PHOTOS --------------------- */

export function PhotosScreen({ phase }: { phase: "before" | "after" }) {
  const { back, navigate, draft, setDraft, locale } = useNav()
  const photos = phase === "before" ? draft.beforePhotoAssets : draft.afterPhotoAssets
  const maxPhotos = phase === "before" ? 6 : draft.beforePhotoAssets.length
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function addFiles(files: FileList | null) {
    if (!files) return
    setUploading(true)
    setError(null)
    try {
      let next = [...photos]
      for (const file of Array.from(files).slice(0, maxPhotos - photos.length)) {
        next = [...next, await saveVisitPhoto(file, phase, draft.id)]
        if (phase === "before") {
          setDraft({ beforePhotoAssets: next })
        } else {
          setDraft({ afterPhotoAssets: next })
        }
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t(locale, "couldNotUploadPhoto"))
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  function removeAt(index: number) {
    const next = photos.filter((_, photoIndex) => photoIndex !== index)
    URL.revokeObjectURL(photos[index].previewUrl)
    if (phase === "before") {
      // After photos are paired to before photos by position, so removing a
      // before photo invalidates the pairing that was already captured.
      setDraft({ beforePhotoAssets: next, afterPhotoAssets: [] })
    } else {
      setDraft({ afterPhotoAssets: next })
    }
  }

  const step = phase === "before" ? 3 : 5
  const title = phase === "before" ? t(locale, "beforePhotosTitle") : t(locale, "afterPhotosTitle")
  const next = phase === "before" ? "notes" : "analysisProcessing"
  const count = photos.length
  const pairCountValid = phase === "before" ? count >= 1 : count === draft.beforePhotoAssets.length

  function continueFlow() {
    navigate(next)
  }

  return (
    <>
      <ScreenHeader
        title={title}
        subtitle={phase === "before" ? t(locale, "stepCaptureStart") : t(locale, "stepShowFinishedWork")}
        onBack={back}
        step={step}
        totalSteps={6}
      />
      <Page width="form">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {tPlural(locale, "photosCaptured", count)}
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
          {count < maxPhotos && (
            <CaptureButton onCapture={() => inputRef.current?.click()} />
          )}
          <input
            ref={inputRef}
            className="hidden"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            multiple
            onChange={(event) => void addFiles(event.target.files)}
          />
          {photos.map((photo, i) => (
            <div key={photo.assetId} className="relative aspect-square overflow-hidden rounded-xl border border-border bg-muted">
              <img src={photo.previewUrl} alt={`${title} ${i + 1}`} className="size-full object-cover" />
              <span className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-white">{t(locale, "pairLabel", { n: i + 1 })}</span>
              <button
                type="button"
                aria-label={t(locale, "removePhotoLabel", { label: title, n: i + 1 })}
                onClick={() => removeAt(i)}
                className="absolute right-1 top-1 grid size-7 place-items-center rounded-full bg-black/70 text-white"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </div>

        <Card className="mt-5 flex items-start gap-3 p-3.5">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
            <Camera className="size-4" />
          </span>
          <p className="text-xs leading-relaxed text-muted-foreground">
            {phase === "before"
              ? t(locale, "beforePhotosHint")
              : t(locale, "afterPhotosHint", { n: draft.beforePhotoAssets.length })}
          </p>
        </Card>
        {uploading && <p className="mt-3 text-sm text-muted-foreground">{t(locale, "normalizingUploading")}</p>}
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        <Button size="lg" fullWidth iconRight={ArrowRight} disabled={!pairCountValid || uploading} onClick={continueFlow}>
          {phase === "after" ? t(locale, "startAiAnalysisBtn") : t(locale, "continueLabel")}
        </Button>
      </FlowFooter>
    </>
  )
}

/* ------------------------------- NOTES -------------------------------- */

export function NotesScreen() {
  const { back, navigate, draft, setDraft, locale } = useNav()
  const [notes, setNotes] = useState(draft.rawNotes)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recorder = useRef(new BrowserAudioRecorder())
  const [recordingState, setRecordingState] = useState<RecordingState>("ready")
  const tooShort = notes.trim().length < 20

  useEffect(() => () => recorder.current.release(), [])

  async function recordVoice() {
    setError(null)
    try {
      const recording = recorder.current.start(setRecordingState)
      // Start returns only after stop; a second tap stops the active recorder.
      const blob = await recording
      setRecordingState("preparing")
      const extension = blob.type === "audio/mp4" ? "mp4" : "webm"
      const file = new File([blob], `voice-note.${extension}`, { type: blob.type })
      validateVisitAudio(file)
      setRecordingState("uploading")
      const transcribed = await transcribeRecording(file, file.name)
      setDraft({ notesSource: "voice", rawNotes: transcribed.transcript })
      setNotes(transcribed.transcript)
      setRecordingState("ready")
    } catch (reason) {
      setRecordingState("failed")
      setError(
        reason instanceof JobActApiError
          ? reason.response.detail
          : reason instanceof Error
            ? reason.message
            : t(locale, "microphoneUnavailable"),
      )
    }
  }

  function switchToTyped(value: string) {
    recorder.current.release()
    setNotes(value)
    setDraft({ notesSource: "typed" })
  }

  function chooseTyped() {
    recorder.current.release()
    setRecordingState("ready")
    setDraft({ notesSource: "typed" })
  }

  function chooseVoice() {
    setNotes("")
    setDraft({ notesSource: "voice", rawNotes: "" })
  }

  function saveNotes() {
    const isTypedInput = draft.notesSource === "typed"
    if ((isTypedInput && tooShort) || (!isTypedInput && !draft.rawNotes)) {
      return
    }
    setSaving(true)
    setError(null)
    if (draft.notesSource === "typed") {
      setDraft({ rawNotes: notes })
    }
    navigate("afterPhotos")
    setSaving(false)
  }

  return (
    <>
      <ScreenHeader
        title={t(locale, "describeWorkTitle")}
        subtitle={t(locale, "stepDescribeWork")}
        onBack={back}
        step={4}
        totalSteps={6}
      />
      <Page width="form">
        <div>
          <h2 className="text-lg font-semibold text-foreground text-balance">
            {t(locale, "whatDidYouDo")}
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
            {t(locale, "whatDidYouDoDesc")}
          </p>
        </div>

        <div className="mt-5">
          <p className="mb-2 text-sm font-medium text-muted-foreground">
            {t(locale, "chooseInputMethod")}
          </p>
          <div className="flex gap-2">
            <Button
              variant={draft.notesSource === "typed" ? "primary" : "secondary"}
              size="sm"
              onClick={chooseTyped}
            >
              {t(locale, "typedNotes")}
            </Button>
            <Button
              variant={draft.notesSource === "voice" ? "primary" : "secondary"}
              size="sm"
              icon={Mic}
              onClick={chooseVoice}
            >
              {t(locale, "recordVoice")}
            </Button>
          </div>
        </div>

        {draft.notesSource === "typed" ? <label className="mt-5 block">
          <span className="mb-1.5 block text-sm font-medium text-muted-foreground">
            {t(locale, "workNotesLabel")}
          </span>
          <textarea
            value={notes}
            onChange={(event) => switchToTyped(event.target.value)}
            rows={8}
            autoFocus
            placeholder={t(locale, "workNotesPlaceholder")}
            className="w-full resize-none rounded-xl border border-input bg-card p-4 text-sm leading-relaxed text-foreground focus:border-ring focus:outline-none"
          />
        </label> : <div className="mt-5 rounded-xl border border-border bg-card p-4">
          <p className="text-sm font-medium text-foreground">{t(locale, "voiceNotes")}</p>
          <p className="mt-1 text-xs text-muted-foreground">{t(locale, "whatDidYouDoDesc")}</p>
          <Button
            className="mt-3"
            variant="secondary"
            icon={Mic}
            onClick={() => {
              if (recordingState === "recording") recorder.current.stop()
              else void recordVoice()
            }}
            disabled={recordingState === "preparing" || recordingState === "uploading"}
          >
            {recordingState === "recording" ? t(locale, "stopRecording") : t(locale, "startRecording")}
          </Button>
          {recordingState === "recording" && <p className="mt-2 text-xs text-muted-foreground">{t(locale, "recordingInProgress")}</p>}
          {recordingState === "preparing" && <p className="mt-2 text-xs text-muted-foreground">{t(locale, "preparingRecording")}</p>}
          {recordingState === "uploading" && <p className="mt-2 text-xs text-muted-foreground">{t(locale, "uploadingRecording")}</p>}
          {draft.notesSource === "voice" && draft.rawNotes && (
            <p className="mt-3 rounded-lg bg-muted p-3 text-xs leading-relaxed text-foreground">{draft.rawNotes}</p>
          )}
        </div>}
        {draft.notesSource === "typed" && <p className="mt-2 text-xs text-muted-foreground">
          {tooShort ? t(locale, "tooShortHint") : t(locale, "roughNotesFine")}
        </p>}
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        <Button
          size="lg"
          fullWidth
          iconRight={ArrowRight}
          disabled={(draft.notesSource === "typed" ? tooShort : !draft.rawNotes) || saving}
          onClick={saveNotes}
        >
          {saving
            ? t(locale, "savingChangesEllipsis")
            : draft.notesSource === "voice"
              ? t(locale, "continueToAfterPhoto")
              : t(locale, "continueLabel")}
        </Button>
      </FlowFooter>
    </>
  )
}

/* ------------------------- ANALYSIS PROCESSING ------------------------ */

function analysisErrorMessage(locale: AppLocale, error: unknown): { message: string; retryable: boolean } {
  if (error instanceof JobActApiError) {
    switch (error.response.type) {
      case "ai-provider-configuration-error":
      case "ai-not-configured":
        return { message: t(locale, "analysisProviderConfigurationError"), retryable: false }
      case "ai-analysis-timeout":
        return { message: t(locale, "analysisTimedOutError"), retryable: true }
      case "evidence-incomplete":
      case "photos-not-paired":
        return { message: t(locale, "photosMustFormPairs"), retryable: true }
      default:
        return { message: error.response.detail || t(locale, "analysisIncompleteError"), retryable: true }
    }
  }
  return { message: error instanceof Error ? error.message : t(locale, "couldNotAnalyseVisit"), retryable: true }
}

export function AnalysisProcessingScreen() {
  const { navigate, replace, reset, draft, setDraft, currency, locale } = useNav()
  const analysisSteps = [t(locale, "uploadingEvidence"), t(locale, "draftingReport"), t(locale, "comparingPhotos")]
  const [active, setActive] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [canRetry, setCanRetry] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const navigation = useRef({ draft, currency, navigate, replace, setDraft })
  navigation.current = { draft, currency, navigate, replace, setDraft }

  useEffect(() => {
    const controller = new AbortController()
    setCanRetry(true)
    const current = navigation.current
    const currentDraft = current.draft

    async function runAnalysis() {
      if (!currentDraft.rawNotes) {
        throw new Error(t(locale, "visitNotesMissing"))
      }
      if (
        currentDraft.beforePhotoAssets.length === 0 ||
        currentDraft.beforePhotoAssets.length !== currentDraft.afterPhotoAssets.length
      ) {
        throw new Error(t(locale, "photosMustFormPairs"))
      }

      setActive(1)
      const photoPairs = await Promise.all(
        currentDraft.beforePhotoAssets.slice(0, 6).map(async (before, index) => {
          const after = currentDraft.afterPhotoAssets[index]
          const [beforeRecord, afterRecord] = await Promise.all([
            getBlob(before.assetId),
            getBlob(after.assetId),
          ])
          if (!beforeRecord || !afterRecord) {
            throw new Error(t(locale, "photosMustFormPairs"))
          }
          return { before: beforeRecord.blob, after: afterRecord.blob }
        }),
      )
      if (controller.signal.aborted) return

      const context: AnalyzeContext = {
        raw_notes: currentDraft.rawNotes,
        customer_name: currentDraft.customerName,
        customer_address: currentDraft.customerAddress,
        customer_service_type: currentDraft.customerServiceType,
        gps_lat: currentDraft.gpsLat ?? null,
        gps_lon: currentDraft.gpsLon ?? null,
        currency: current.currency,
        locale,
      }
      setActive(2)
      const result = await analyzeReport(context, photoPairs, controller.signal)
      if (controller.signal.aborted) return

      current.setDraft({
        currency: current.currency,
        workCompleted: result.work_completed,
        materials: result.materials,
        amountCents: result.suggested_amount_cents,
        estimatedWorkUnits: result.estimated_work_units,
        aiConfidence: result.confidence,
        visualComparison: result.visual_comparison,
        amountConfirmed: false,
      })
      current.replace("reportDraft")
    }

    runAnalysis().catch((reason: unknown) => {
      if (controller.signal.aborted) return
      const presentation = analysisErrorMessage(locale, reason)
      setCanRetry(presentation.retryable)
      setError(presentation.message)
    })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt])

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
        <div className="grid size-20 place-items-center rounded-3xl border border-border bg-card">
          <TriangleAlert className="size-8 text-warning" />
        </div>
        <h2 className="mt-6 text-lg font-semibold text-foreground">
          {t(locale, "analysisNeedsAttention")}
        </h2>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">{error}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button variant="secondary" onClick={() => replace("afterPhotos")}>
            {t(locale, "reviewPhotosBtn")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => navigate("editReport", { manual: true })}
          >
            {t(locale, "writeManuallyBtn")}
          </Button>
          {canRetry && (
            <Button
              onClick={() => {
                setError(null)
                setActive(0)
                setAttempt((value) => value + 1)
              }}
            >
              {t(locale, "tryAgainAction")}
            </Button>
          )}
        </div>
        <Button variant="secondary" size="md" className="mt-6" onClick={() => reset("home")}>
          {t(locale, "returnToWorkspace")}
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
      <div className="relative grid size-20 place-items-center rounded-3xl border border-border bg-card">
        <Sparkles className="size-8 text-foreground" />
        <span className="absolute inset-0 rounded-3xl border border-foreground/20 animate-ping" />
      </div>
      <h2 className="mt-6 text-lg font-semibold text-foreground">{t(locale, "analysingVisit")}</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {t(locale, "analysingVisitDesc")}
      </p>

      <div className="mt-8 w-full max-w-xs space-y-3 text-left">
        {analysisSteps.map((label, index) => (
          <div key={label} className="flex items-center gap-3">
            <span
              className={
                "grid size-6 place-items-center rounded-full border text-xs " +
                (index < active
                  ? "border-success bg-success text-success-foreground"
                  : index === active
                    ? "border-foreground text-foreground"
                    : "border-border text-muted-foreground")
              }
            >
              {index < active ? (
                <Check className="size-3.5" strokeWidth={3} />
              ) : index === active ? (
                <LoaderCircle className="size-3.5 animate-spin" />
              ) : (
                index + 1
              )}
            </span>
            <span
              className={
                "text-sm " + (index <= active ? "text-foreground" : "text-muted-foreground")
              }
            >
              {label}
            </span>
          </div>
        ))}
      </div>
      <Button variant="secondary" size="md" className="mt-8" onClick={() => reset("home")}>
        {t(locale, "returnToWorkspace")}
      </Button>
    </div>
  )
}

/* --------------------------- REPORT DRAFT ----------------------------- */

export function ReportDraftScreen() {
  const { back, navigate, replace, draft, setDraft, locale } = useNav()
  const comparison = draft.visualComparison

  function confirmAndContinue() {
    setDraft({ amountConfirmed: true })
    navigate("signature")
  }

  return (
    <>
      <ScreenHeader
        title={t(locale, "reportDraftTitle")}
        subtitle={t(locale, "stepReviewReport")}
        onBack={back}
        step={6}
        totalSteps={6}
        right={<StatusBadge status="draft" />}
      />
      <Page width="form">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2.5">
          <Sparkles className="size-4 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">{t(locale, "aiDraftNotice")}</p>
        </div>

        <SectionLabel>
          <span className="mt-5 block">{t(locale, "visitLabel")}</span>
        </SectionLabel>
        <Card className="p-4">
          <p className="text-sm font-semibold text-foreground">{draft.customerName}</p>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="size-3" /> {draft.customerAddress}
          </p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1"><Calendar className="size-3" /> {new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric" }).format(new Date())}</span>
            <span className="inline-flex items-center gap-1"><Clock className="size-3" /> {new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(new Date())}</span>
            <span className="inline-flex items-center gap-1"><Camera className="size-3" /> {tPlural(locale, "photosCount", draft.beforePhotoAssets.length + draft.afterPhotoAssets.length)}</span>
          </div>
        </Card>

        <EditableSection title={t(locale, "workCompletedLabel")} editLabel={t(locale, "editBtn")} onEdit={() => navigate("editReport")}>
          <p className="text-sm leading-relaxed text-foreground">{draft.workCompleted}</p>
        </EditableSection>

        <EditableSection title={t(locale, "materialsLabel")} editLabel={t(locale, "editBtn")} onEdit={() => navigate("editReport")}>
          <ul className="space-y-1.5 text-sm text-foreground">
            {draft.materials.map((material) => (
              <li key={`${material.label}-${material.qty}`} className="flex justify-between">
                <span>{material.label}</span>
                <span className="text-muted-foreground">×{material.qty}</span>
              </li>
            ))}
          </ul>
        </EditableSection>

        <EditableSection title={t(locale, "amountLabel")} editLabel={t(locale, "editBtn")} onEdit={() => navigate("editReport")}>
          <p className="font-mono text-2xl font-semibold text-foreground">
            {draft.amountCents === null
              ? t(locale, "notSpecified")
              : formatCurrency(locale, draft.amountCents / 100, draft.currency)}
          </p>
        </EditableSection>

        <SectionLabel>
          <span className="mt-5 block">{t(locale, "visitEvidenceLabel")}</span>
        </SectionLabel>
        <div className="grid grid-cols-2 gap-2.5">
          <Card className="p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">{t(locale, "beforeLabel")}</p>
            <div className="grid grid-cols-2 gap-1.5">
              {draft.beforePhotoAssets.map((photo, i) => (
                <img
                  key={photo.assetId}
                  src={photo.previewUrl}
                  alt={`${t(locale, "beforeLabel")} ${i + 1}`}
                  className="aspect-square w-full rounded-lg border border-border object-cover"
                />
              ))}
            </div>
          </Card>
          <Card className="p-3">
            <p className="mb-2 text-xs font-medium text-muted-foreground">{t(locale, "afterLabel")}</p>
            <div className="grid grid-cols-2 gap-1.5">
              {draft.afterPhotoAssets.map((photo, i) => (
                <img
                  key={photo.assetId}
                  src={photo.previewUrl}
                  alt={`${t(locale, "afterLabel")} ${i + 1}`}
                  className="aspect-square w-full rounded-lg border border-border object-cover"
                />
              ))}
            </div>
          </Card>
        </div>

        {comparison ? (
          <>
            <SectionLabel>
              <span className="mt-6 block">{t(locale, "beforeAfterComparisonLabel")}</span>
            </SectionLabel>
            <Card className="mt-2 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {comparison.verdict.replaceAll("_", " ")}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-foreground">{comparison.summary}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="font-mono text-3xl font-semibold text-foreground">
                    {comparison.quality_assessment.score}/10
                  </p>
                  <p className="text-xs text-muted-foreground">{comparison.confidence}% confidence</p>
                </div>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-foreground">
                {comparison.comparison.match_explanation}
              </p>
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                {comparison.comparison.visible_changes.map((item, index) => (
                  <li key={index}>• {item}</li>
                ))}
              </ul>
            </Card>
            <ResultList title={t(locale, "visuallyConfirmed")} items={comparison.comparison.visible_changes} />
            <ResultList title={t(locale, "doneWell")} items={comparison.quality_assessment.strengths} />
            <ResultList title={t(locale, "issuesSuspicious")} items={comparison.quality_assessment.issues} />
            <ResultList title={t(locale, "unverified")} items={comparison.quality_assessment.unverified_items} />
            <section className="mt-5">
              <SectionLabel>{t(locale, "priceAssessmentLabel")}</SectionLabel>
              <Card className="mt-2 p-4">
                <p className="text-sm font-semibold text-foreground">
                  {verdictLabel(locale, comparison.price_assessment.price_verdict)}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {comparison.price_assessment.price_explanation}
                </p>
              </Card>
            </section>
            <ResultList title={t(locale, "analysisLimitations")} items={comparison.limitations} />
            <ResultList title={t(locale, "recommendedNextSteps")} items={comparison.recommended_next_steps} />
            <Card className="mt-5 p-4 text-xs leading-relaxed text-muted-foreground">
              {t(locale, "visualAssessmentDisclaimer")}
            </Card>
          </>
        ) : (
          <Card className="mt-5 flex gap-3 p-4">
            <TriangleAlert className="size-5 shrink-0 text-warning" />
            <div>
              <p className="text-sm font-semibold text-foreground">
                {t(locale, "noComparisonAttached")}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {t(locale, "noComparisonAttachedDesc")}
              </p>
            </div>
          </Card>
        )}
      </Page>
      <FlowFooter>
        <div className="space-y-2.5">
          <Button size="lg" fullWidth iconRight={ArrowRight} onClick={confirmAndContinue}>
            {t(locale, "confirmAndSignBtn")}
          </Button>
          <div className="grid grid-cols-3 gap-2">
            <Button variant="secondary" icon={Pencil} onClick={() => navigate("editReport")}>
              {t(locale, "editBtn")}
            </Button>
            <Button variant="secondary" onClick={() => replace("beforePhotos")}>
              {t(locale, "recaptureBtn")}
            </Button>
            <Button variant="secondary" onClick={() => replace("analysisProcessing")}>
              {t(locale, "rerunBtn")}
            </Button>
          </div>
        </div>
      </FlowFooter>
    </>
  )
}

function EditableSection({
  title,
  editLabel,
  children,
  onEdit,
}: {
  title: string
  editLabel: string
  children: React.ReactNode
  onEdit: () => void
}) {
  return (
    <section className="mt-5">
      <div className="mb-2 flex items-center justify-between">
        <SectionLabel>{title}</SectionLabel>
        <button onClick={onEdit} className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
          <Pencil className="size-3" /> {editLabel}
        </button>
      </div>
      <Card className="p-4">{children}</Card>
    </section>
  )
}

/* ----------------------------- EDIT REPORT ---------------------------- */

export function EditReportScreen() {
  const { back, replace, frame, draft, setDraft, locale } = useNav()
  const typingNotes = Boolean(frame.params.manual) && !draft.workCompleted
  const [work, setWork] = useState(typingNotes ? draft.rawNotes : draft.workCompleted)
  const [amount, setAmount] = useState(draft.amountCents === null ? "" : String(draft.amountCents / 100))
  const [materials, setMaterials] = useState(
    draft.materials.map((material) => ({ id: crypto.randomUUID(), ...material })),
  )

  function save() {
    if (typingNotes) {
      setDraft({ rawNotes: work })
      replace("analysisProcessing")
      return
    }
    setDraft({
      workCompleted: work,
      amountCents: amount ? Math.round(Number(amount) * 100) : null,
      materials: materials.filter((material) => material.label.trim()).map(({ label, qty }) => ({ label, qty })),
      amountConfirmed: true,
    })
    replace("reportDraft")
  }

  return (
    <>
      <ScreenHeader
        title={t(locale, "editReportTitle")}
        onBack={back}
        right={
          <Button size="sm" onClick={save}>
            {t(locale, "done")}
          </Button>
        }
      />
      <Page width="form">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted-foreground">
            {t(locale, "workCompletedLabel")}
          </span>
          <textarea
            value={work}
            onChange={(e) => setWork(e.target.value)}
            rows={5}
            className="w-full resize-none rounded-xl border border-input bg-card p-4 text-sm leading-relaxed text-foreground focus:border-ring focus:outline-none"
          />
        </label>

        {!typingNotes && (
          <>
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between">
                <SectionLabel>{t(locale, "materialsLabel")}</SectionLabel>
                <button
                  onClick={() => setMaterials((m) => [...m, { id: crypto.randomUUID(), label: "", qty: "1" }])}
                  className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                >
                  <Plus className="size-3" /> {t(locale, "addBtn")}
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
                      placeholder={t(locale, "materialPlaceholder")}
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
                      aria-label={t(locale, "removeMaterialLabel")}
                      className="grid size-11 place-items-center rounded-xl text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5">
              <AmountField
                label={t(locale, "amountChargedLabel")}
                currencySymbol={currencySymbol(draft.currency)}
                value={amount}
                onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ""))}
                placeholder="0"
              />
            </div>
          </>
        )}
      </Page>
      <FlowFooter>
        <Button size="lg" fullWidth icon={Check} onClick={save}>
          {typingNotes ? t(locale, "useTheseNotesBtn") : t(locale, "saveChangesBtn")}
        </Button>
      </FlowFooter>
    </>
  )
}

/* --------------------------- RESULT SECTIONS -------------------------- */

function ResultList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <section className="mt-5">
      <SectionLabel>{title}</SectionLabel>
      <Card className="mt-2 p-4">
        <ul className="space-y-2 text-sm text-foreground">
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>• {item}</li>
          ))}
        </ul>
      </Card>
    </section>
  )
}

/* ------------------------------ SIGNATURE ----------------------------- */

export function SignatureScreen() {
  const { back, navigate, draft, setDraft, locale } = useNav()
  const [hasInk, setHasInk] = useState(false)
  const [signerName, setSignerName] = useState(() => draft.signerName ?? t(locale, "defaultSignerName"))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const signatureRef = useRef<SignatureCanvasHandle>(null)

  async function finishReport() {
    if (!draft.amountConfirmed) return
    setSaving(true)
    setError(null)
    try {
      const png = await signatureRef.current?.exportPng()
      if (!png) throw new Error(t(locale, "signatureRequired"))

      const humanId = humanReportId(draft.id)
      const nowIso = new Date().toISOString()
      const pdfBlob = await renderCheckPdf(
        {
          report_number: humanId,
          customer_name: draft.customerName,
          customer_address: draft.customerAddress,
          customer_phone: draft.customerPhone,
          customer_service_type: draft.customerServiceType,
          timestamp: nowIso,
          gps_lat: draft.gpsLat ?? null,
          gps_lon: draft.gpsLon ?? null,
          work_completed: draft.workCompleted,
          materials: draft.materials,
          amount_cents: draft.amountCents,
          currency: draft.currency,
          signer_name: signerName,
          locale,
        },
        png,
      )
      const pdfBlobId = await putBlob(draft.id, "pdf", pdfBlob, "application/pdf")

      await saveCheck({
        id: draft.id,
        humanId,
        customerName: draft.customerName,
        customerAddress: draft.customerAddress,
        customerPhone: draft.customerPhone,
        customerServiceType: draft.customerServiceType,
        gpsLat: draft.gpsLat ?? null,
        gpsLon: draft.gpsLon ?? null,
        workCompleted: draft.workCompleted,
        materials: draft.materials,
        amountCents: draft.amountCents,
        currency: draft.currency,
        visualComparison: draft.visualComparison,
        aiConfidence: draft.aiConfidence,
        signed: true,
        signerName,
        beforePhotoIds: draft.beforePhotoAssets.map((p) => p.assetId),
        afterPhotoIds: draft.afterPhotoAssets.map((p) => p.assetId),
        pdfBlobId,
        completedAt: nowIso,
      })
      await finalizeDraft(draft.id)
      setActiveDraftId(null)

      setDraft({ signed: true, signerName, pdfBlobId, humanId, completed: true })
      navigate("completed")
    } catch (reason) {
      setError(
        reason instanceof JobActApiError
          ? reason.response.detail
          : reason instanceof Error
            ? reason.message
            : t(locale, "couldNotSignReport"),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ScreenHeader title={t(locale, "customerConfirmationTitle")} onBack={back} />
      <Page width="form">
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">
            {t(locale, "signingConfirmsText", { name: draft.customerName })}
          </p>
        </Card>

        <div className="mt-5">
          <SectionLabel>{t(locale, "signatureLabel")}</SectionLabel>
          <SignatureCanvas ref={signatureRef} onChange={setHasInk} />
        </div>

        <Input id="signer" label={t(locale, "signedByLabel")} placeholder={t(locale, "signerNamePlaceholder")} value={signerName} onChange={(event) => setSignerName(event.target.value)} className="mt-2" />

        <Card className="mt-4 flex items-center gap-3 p-3.5">
          <ShieldCheck className="size-5 shrink-0 text-muted-foreground" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            {t(locale, "signatureStoredNote")}
          </p>
        </Card>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>
      <FlowFooter>
        <Button
          size="lg"
          fullWidth
          icon={Check}
          disabled={!hasInk || !signerName.trim() || saving}
          onClick={finishReport}
        >
          {saving ? t(locale, "finalizingEllipsis") : t(locale, "confirmAndFinishBtn")}
        </Button>
      </FlowFooter>
    </>
  )
}

/* ------------------------------ COMPLETED ----------------------------- */

export function CompletedScreen() {
  const { reset, navigate, draft, locale } = useNav()
  const [error, setError] = useState<string | null>(null)
  const completedAmount =
    draft.amountCents === null ? t(locale, "notSpecified") : formatCurrency(locale, draft.amountCents / 100, draft.currency)
  const now = new Date()

  async function openPdf() {
    if (!draft.pdfBlobId) {
      setError(t(locale, "pdfNotAvailable"))
      return
    }
    try {
      const record = await getBlob(draft.pdfBlobId)
      if (!record) throw new Error(t(locale, "pdfNotAvailable"))
      window.open(URL.createObjectURL(record.blob), "_blank")
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t(locale, "couldNotOpenPdf"))
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <Page width="form" className="flex flex-col items-center pt-10 lg:pt-14">
        <SuccessMark />
        <h1 className="mt-6 text-2xl font-semibold tracking-tight text-foreground">{t(locale, "reportCompletedTitle")}</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">{t(locale, "reportCompletedSubtitle")}</p>

        <Card className="mt-8 w-full p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">{draft.customerName}</p>
            <StatusBadge status="completed" />
          </div>
          <div className="mt-4 space-y-3 text-sm">
            <SummaryRow label={t(locale, "dateTimeLabel")} value={formatDateTime(locale, now.toISOString())} />
            <SummaryRow label={t(locale, "locationLabel")} value={t(locale, "locationCapturedLabel")} />
            <SummaryRow label={t(locale, "photosLabel")} value={tPlural(locale, "photosCount", draft.beforePhotoAssets.length + draft.afterPhotoAssets.length)} />
            <SummaryRow label={t(locale, "signatureStatusLabel")} value={draft.signed ? t(locale, "signedOnSiteLabel") : t(locale, "linkSentLabel")} />
            <SummaryRow label={t(locale, "amountLabel")} value={completedAmount} strong />
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
            <span className="font-mono text-xs text-muted-foreground">
              {draft.humanId ?? t(locale, "reportFallback")}
            </span>
          </div>
        </Card>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </Page>

      <FlowFooter>
        <div className="space-y-2.5">
          <Button size="lg" fullWidth icon={Share2} onClick={openPdf}>
            {t(locale, "openSignedPdfBtn")}
          </Button>
          <div className="flex gap-3">
            <Button variant="secondary" size="lg" fullWidth onClick={() => navigate("checkDetail", { checkId: draft.id })}>
              {t(locale, "viewReportBtn")}
            </Button>
            <Button variant="ghost" size="lg" icon={House} onClick={() => reset("home")}>
              {t(locale, "doneAction")}
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
