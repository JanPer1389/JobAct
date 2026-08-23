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
import { Scroll } from "../shell"
import { Avatar } from "../cards"
import {
  customers as allCustomers,
  currency,
} from "@/lib/jobact/data"
import { useNav } from "@/lib/jobact/store"

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

function FlowFooter({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="shrink-0 border-t border-border bg-background/80 px-5 pb-8 pt-3 backdrop-blur-xl">
      {children}
    </div>
  )
}

/* ---------------------------- ADD CUSTOMER ---------------------------- */

export function AddCustomerScreen() {
  const { back, replace, frame, setDraft } = useNav()
  const picking = Boolean(frame.params.picking)
  const [name, setName] = useState("")

  return (
    <>
      <ScreenHeader title="Add customer" onBack={back} />
      <Scroll className="px-5 py-4">
        <div className="space-y-4">
          <Input id="name" label="Customer name" placeholder="e.g. Aurora Dental Clinic" value={name} onChange={(e) => setName(e.target.value)} />
          <Input id="address" label="Address" icon={MapPin} placeholder="Street, unit, city" />
          <Input id="phone" label="Phone" type="tel" placeholder="+1 (___) ___-____" />
          <Input id="type" label="Service type" placeholder="AC maintenance, cleaning, repair…" hint="Optional — helps you find them later" />
        </div>
      </Scroll>
      <FlowFooter>
        <Button
          size="lg"
          fullWidth
          disabled={!name.trim()}
          iconRight={picking ? ArrowRight : undefined}
          onClick={() => {
            setDraft({ customerId: "new", customerName: name || "New customer" })
            if (picking) replace("visitStart", { customerId: "new" })
            else back()
          }}
        >
          {picking ? "Save & continue" : "Save customer"}
        </Button>
      </FlowFooter>
    </>
  )
}

/* ----------------------------- VISIT START ---------------------------- */

export function VisitStartScreen() {
  const { back, navigate, frame } = useNav()
  const customer = useCustomer()
  const now = new Date()

  return (
    <>
      <ScreenHeader title="Start visit" subtitle="Step 2 · Confirm the details" onBack={back} step={2} totalSteps={6} />
      <Scroll className="px-5 py-4">
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
      </Scroll>
      <FlowFooter>
        <Button size="lg" fullWidth iconRight={ArrowRight} onClick={() => navigate("gps", frame.params)}>
          Confirm location
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

export function GpsScreen() {
  const { back, navigate, frame } = useNav()
  const [state, setState] = useState<"locating" | "found">("locating")
  const customer = useCustomer()

  useEffect(() => {
    const t = setTimeout(() => setState("found"), 1800)
    return () => clearTimeout(t)
  }, [])

  return (
    <>
      <ScreenHeader title="Location" onBack={back} />
      <Scroll className="flex flex-col px-5 py-4">
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
            ) : (
              <span className="relative flex flex-col items-center">
                <span className="grid size-11 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg">
                  <MapPin className="size-5" />
                </span>
                <span className="mt-1 size-2 rounded-full bg-primary/40" />
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
            ) : (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <LoaderCircle className="size-3.5 animate-spin" /> Locating
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{customer.address}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground/70">
            {state === "found" ? "37.7897, -122.4001 · ±5m" : "Acquiring satellites…"}
          </p>
        </Card>
      </Scroll>
      <FlowFooter>
        <Button
          size="lg"
          fullWidth
          disabled={state !== "found"}
          iconRight={ArrowRight}
          onClick={() => navigate("beforePhotos", frame.params)}
        >
          {state === "found" ? "Location confirmed" : "Confirming location…"}
        </Button>
      </FlowFooter>
    </>
  )
}

/* --------------------------- BEFORE PHOTOS ---------------------------- */

export function PhotosScreen({ phase }: { phase: "before" | "after" }) {
  const { back, navigate, frame, draft, setDraft } = useNav()
  const count = phase === "before" ? draft.beforePhotos : draft.afterPhotos
  const seeded = useRef(false)

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
  const next = phase === "before" ? "voice" : "reportDraft"

  return (
    <>
      <ScreenHeader
        title={title}
        subtitle={phase === "before" ? "Step 3 · Capture the starting state" : "Step 5 · Show the finished work"}
        onBack={back}
        step={step}
        totalSteps={6}
      />
      <Scroll className="px-5 py-4">
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

        <div className="mt-4 grid grid-cols-3 gap-2.5">
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
      </Scroll>
      <FlowFooter>
        <Button size="lg" fullWidth iconRight={ArrowRight} disabled={count === 0} onClick={() => navigate(next, frame.params)}>
          Continue
        </Button>
      </FlowFooter>
    </>
  )
}

/* ------------------------------- VOICE -------------------------------- */

export function VoiceScreen() {
  const { back, navigate, frame } = useNav()
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
      <Scroll className="flex flex-col items-center px-5 py-6">
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
      </Scroll>
      <FlowFooter>
        <Button size="lg" fullWidth iconRight={ArrowRight} disabled={seconds < 1} onClick={() => navigate("voiceProcessing", frame.params)}>
          Use recording
        </Button>
      </FlowFooter>
    </>
  )
}

/* -------------------------- VOICE PROCESSING -------------------------- */

export function VoiceProcessingScreen() {
  const { navigate, frame } = useNav()
  const steps = ["Transcribing your note", "Structuring the report", "Detecting materials & amount"]
  const [active, setActive] = useState(0)

  useEffect(() => {
    if (active >= steps.length) {
      const t = setTimeout(() => navigate("reportDraft", frame.params), 500)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => setActive((a) => a + 1), 900)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
      <div className="relative grid size-20 place-items-center rounded-3xl border border-border bg-card">
        <Sparkles className="size-8 text-foreground" />
        <span className="absolute inset-0 rounded-3xl border border-foreground/20 animate-ping" />
      </div>
      <h2 className="mt-6 text-lg font-semibold text-foreground">Building your report</h2>
      <p className="mt-1 text-sm text-muted-foreground">This usually takes a few seconds</p>

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
  const { back, navigate, frame, draft } = useNav()
  const customer = useCustomer()

  const generated =
    "Diagnosed and repaired the reported fault. Replaced the worn component, cleaned the surrounding assembly, and verified correct operation before leaving the site."

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
      <Scroll className="px-5 py-4">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2.5">
          <Sparkles className="size-4 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">Generated from your voice note — review and edit anything.</p>
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
          <p className="text-sm leading-relaxed text-foreground">{draft.workCompleted || generated}</p>
        </EditableSection>

        <EditableSection title="Materials / consumables" onEdit={() => navigate("editReport", frame.params)}>
          <ul className="space-y-1.5 text-sm text-foreground">
            <li className="flex justify-between"><span>Start capacitor 45µF</span><span className="text-muted-foreground">×1</span></li>
            <li className="flex justify-between"><span>Contact cleaner</span><span className="text-muted-foreground">×1</span></li>
          </ul>
        </EditableSection>

        <EditableSection title="Amount" onEdit={() => navigate("editReport", frame.params)}>
          <p className="font-mono text-2xl font-semibold text-foreground">{currency(Number(draft.amount) || 160)}</p>
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
      </Scroll>
      <FlowFooter>
        <div className="flex gap-3">
          <Button variant="secondary" size="lg" icon={Pencil} onClick={() => navigate("editReport", frame.params)}>
            Edit
          </Button>
          <Button size="lg" fullWidth iconRight={ArrowRight} onClick={() => navigate("signature", frame.params)}>
            Get signature
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
  const { back, frame, draft, setDraft } = useNav()
  const [work, setWork] = useState(
    draft.workCompleted ||
      "Diagnosed intermittent compressor fault. Replaced the start capacitor and cleaned the contactor points. Verified stable operation before leaving.",
  )
  const [amount, setAmount] = useState(draft.amount || "160")
  const [materials, setMaterials] = useState([
    { id: "m1", label: "Start capacitor 45µF", qty: "1" },
    { id: "m2", label: "Contact cleaner", qty: "1" },
  ])

  function save() {
    setDraft({ workCompleted: work, amount })
    back()
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
      <Scroll className="px-5 py-4">
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
                  defaultValue={m.label}
                  placeholder="Material"
                  className="h-11 flex-1 rounded-xl border border-input bg-card px-3 text-sm text-foreground focus:border-ring focus:outline-none"
                />
                <input
                  defaultValue={m.qty}
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
      </Scroll>
      <FlowFooter>
        <Button size="lg" fullWidth icon={Check} onClick={save}>
          Save changes
        </Button>
      </FlowFooter>
    </>
  )
}

/* ------------------------------ SIGNATURE ----------------------------- */

export function SignatureScreen() {
  const { back, navigate, frame, setDraft } = useNav()
  const [hasInk, setHasInk] = useState(false)
  const customer = useCustomer()

  return (
    <>
      <ScreenHeader title="Customer confirmation" onBack={back} />
      <Scroll className="px-5 py-4">
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">
            By signing, <span className="font-medium text-foreground">{customer.name}</span> confirms the work
            described was completed to their satisfaction.
          </p>
        </Card>

        <div className="mt-5">
          <SectionLabel>Signature</SectionLabel>
          <SignatureCanvas onChange={setHasInk} />
        </div>

        <Input id="signer" label="Signed by" placeholder="Name of person signing" defaultValue="On-site manager" className="mt-2" />

        <Card className="mt-4 flex items-center gap-3 p-3.5">
          <ShieldCheck className="size-5 shrink-0 text-muted-foreground" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            The signature is stored with the timestamp and GPS location as tamper-evident proof.
          </p>
        </Card>
      </Scroll>
      <FlowFooter>
        <div className="space-y-2.5">
          <Button
            size="lg"
            fullWidth
            icon={Check}
            disabled={!hasInk}
            onClick={() => {
              setDraft({ signed: true })
              navigate("completed", frame.params)
            }}
          >
            Confirm & finish
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

  return (
    <div className="flex flex-1 flex-col">
      <Scroll className="flex flex-col items-center px-5 pt-14">
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
            <SummaryRow label="Amount" value={currency(Number(draft.amount) || 160)} strong />
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
            <span className="font-mono text-xs text-muted-foreground">JA-2026-0483</span>
            <SyncIndicator state="syncing" />
          </div>
        </Card>
      </Scroll>

      <FlowFooter>
        <div className="space-y-2.5">
          <Button size="lg" fullWidth icon={Share2}>
            Send to customer
          </Button>
          <div className="flex gap-3">
            <Button variant="secondary" size="lg" fullWidth onClick={() => navigate("reportDetail", { reportId: "JA-2026-0481" })}>
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
