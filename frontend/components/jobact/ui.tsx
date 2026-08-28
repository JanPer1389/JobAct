"use client"

import { cn } from "@/lib/utils"
import {
  ChevronLeft,
  Check,
  CheckCheck,
  RefreshCw,
  WifiOff,
  CloudUpload,
  TriangleAlert,
  LoaderCircle,
  type LucideIcon,
} from "lucide-react"
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from "react"
import type { ReportStatus, SyncState } from "@/lib/jobact/data"
import { useNav } from "@/lib/jobact/store"
import { statusLabel, syncLabel, t } from "@/lib/jobact/i18n"

/* ------------------------------------------------------------------ */
/*  Brand                                                              */
/* ------------------------------------------------------------------ */

export function Logo({ size = "md" }: { size?: "md" | "lg" }) {
  const s = size === "lg" ? "size-16 rounded-3xl" : "size-11 rounded-2xl"
  return (
    <div
      className={cn(
        "grid shrink-0 place-items-center border border-white/10 bg-gradient-to-br from-elevated to-background shadow-inner",
        s,
      )}
    >
      <svg
        viewBox="0 0 24 24"
        className={size === "lg" ? "size-8" : "size-6"}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Buttons                                                            */
/* ------------------------------------------------------------------ */

type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive"
type ButtonSize = "lg" | "md" | "sm"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  icon?: LucideIcon
  iconRight?: LucideIcon
  fullWidth?: boolean
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80",
  secondary:
    "bg-secondary text-secondary-foreground hover:bg-accent border border-border",
  ghost: "bg-transparent text-foreground hover:bg-accent",
  destructive:
    "bg-transparent text-destructive border border-destructive/40 hover:bg-destructive/10",
}

const sizeClasses: Record<ButtonSize, string> = {
  lg: "h-14 px-6 text-base rounded-2xl gap-2.5",
  md: "h-11 px-4 text-sm rounded-xl gap-2",
  sm: "h-9 px-3 text-sm rounded-lg gap-1.5",
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      icon: Icon,
      iconRight: IconRight,
      fullWidth,
      className,
      children,
      ...props
    },
    ref,
  ) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex select-none items-center justify-center font-medium transition-colors disabled:pointer-events-none disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        variantClasses[variant],
        sizeClasses[size],
        fullWidth && "w-full",
        className,
      )}
      {...props}
    >
      {Icon && <Icon className={cn(size === "lg" ? "size-5" : "size-4")} />}
      {children}
      {IconRight && (
        <IconRight className={cn(size === "lg" ? "size-5" : "size-4")} />
      )}
    </button>
  ),
)
Button.displayName = "Button"

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon
  label: string
}

export function IconButton({ icon: Icon, label, className, ...props }: IconButtonProps) {
  return (
    <button
      aria-label={label}
      className={cn(
        "grid size-10 place-items-center rounded-full text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    >
      <Icon className="size-5" />
    </button>
  )
}

/* ------------------------------------------------------------------ */
/*  Inputs                                                             */
/* ------------------------------------------------------------------ */

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  icon?: LucideIcon
  hint?: string
  error?: string
}

export function Input({ label, icon: Icon, hint, error, className, id, ...props }: FieldProps) {
  const descriptionId = id ? `${id}-description` : undefined
  return (
    <label htmlFor={id} className="block">
      {label && (
        <span className="mb-1.5 block text-sm font-medium text-muted-foreground">
          {label}
        </span>
      )}
      <span className="relative flex items-center">
        {Icon && (
          <Icon className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground" />
        )}
        <input
          id={id}
          aria-invalid={Boolean(error)}
          aria-describedby={hint || error ? descriptionId : undefined}
          className={cn(
            "h-12 w-full rounded-xl border border-input bg-card px-4 text-[15px] text-foreground placeholder:text-muted-foreground/70 transition-colors focus:border-ring focus:outline-none",
            Icon && "pl-10",
            error && "border-destructive focus:border-destructive",
            className,
          )}
          {...props}
        />
      </span>
      {(error || hint) && (
        <span
          id={descriptionId}
          className={cn(
            "mt-1.5 block text-xs",
            error ? "text-destructive" : "text-muted-foreground",
          )}
        >
          {error ?? hint}
        </span>
      )}
    </label>
  )
}

export function SearchField({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="relative flex items-center">
      <svg
        className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3-3" />
      </svg>
      <input
        type="search"
        className={cn(
          "h-12 w-full rounded-xl border border-input bg-card pl-10 pr-4 text-[15px] text-foreground placeholder:text-muted-foreground/70 focus:border-ring focus:outline-none",
          className,
        )}
        {...props}
      />
    </div>
  )
}

interface AmountFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  currencySymbol?: string
}

export function AmountField({ label, className, currencySymbol = "$", ...props }: AmountFieldProps) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-sm font-medium text-muted-foreground">
          {label}
        </span>
      )}
      <span className="relative flex items-center">
        <span className="absolute left-4 text-xl font-semibold text-muted-foreground">{currencySymbol}</span>
        <input
          inputMode="decimal"
          className={cn(
            "h-16 w-full rounded-xl border border-input bg-card pl-9 pr-4 font-mono text-2xl font-semibold tabular-nums text-foreground placeholder:text-muted-foreground/50 focus:border-ring focus:outline-none",
            className,
          )}
          {...props}
        />
      </span>
    </label>
  )
}

/* ------------------------------------------------------------------ */
/*  Surfaces                                                           */
/* ------------------------------------------------------------------ */

export function Card({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-2xl border border-border bg-card", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="mb-3 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
      {children}
    </p>
  )
}

/* ------------------------------------------------------------------ */
/*  Status badges                                                      */
/* ------------------------------------------------------------------ */

const statusClassName: Record<ReportStatus, string> = {
  draft: "bg-muted text-muted-foreground border-border",
  unsigned: "bg-warning/15 text-warning border-warning/25",
  completed: "bg-success/15 text-success border-success/25",
  offline: "bg-muted text-muted-foreground border-border",
}

export function StatusBadge({ status }: { status: ReportStatus }) {
  const { locale } = useNav()
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        statusClassName[status],
      )}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {statusLabel(locale, status)}
    </span>
  )
}

const syncMeta: Record<SyncState, { icon: LucideIcon; className: string }> = {
  synced: { icon: CheckCheck, className: "text-success" },
  pending: { icon: CloudUpload, className: "text-warning" },
  syncing: { icon: RefreshCw, className: "text-muted-foreground" },
  failed: { icon: TriangleAlert, className: "text-destructive" },
  offline: { icon: WifiOff, className: "text-muted-foreground" },
}

export function SyncIndicator({
  state,
  showLabel = true,
}: {
  state: SyncState
  showLabel?: boolean
}) {
  const { locale } = useNav()
  const meta = syncMeta[state]
  const Icon = meta.icon
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", meta.className)}>
      <Icon className={cn("size-3.5", state === "syncing" && "animate-spin")} />
      {showLabel && syncLabel(locale, state)}
    </span>
  )
}

export function OfflineBanner() {
  const { locale } = useNav()
  return (
    <div className="flex items-center gap-2 border-b border-border bg-muted px-4 py-2 text-xs font-medium text-muted-foreground">
      <WifiOff className="size-3.5" />
      {t(locale, "offlineBannerText")}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Progress / steps                                                   */
/* ------------------------------------------------------------------ */

export function StepProgress({ step, total }: { step: number; total: number }) {
  const { locale } = useNav()
  const flowStepLabels = [
    t(locale, "stepCustomer"),
    t(locale, "stepDetails"),
    t(locale, "stepBeforeShort"),
    t(locale, "stepVoiceShort"),
    t(locale, "stepAfterShort"),
    t(locale, "stepReviewShort"),
  ]
  const labels = total === flowStepLabels.length ? flowStepLabels : null
  return (
    <div aria-label={`${step}/${total}`}>
      <div className="flex items-center gap-1.5">
        {Array.from({ length: total }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-1 flex-1 rounded-full transition-colors",
              i < step ? "bg-primary" : "bg-border",
            )}
          />
        ))}
      </div>
      {labels && (
        <div className="mt-2 hidden gap-1.5 lg:flex" aria-hidden="true">
          {labels.map((label, i) => (
            <span
              key={label}
              className={cn(
                "flex-1 truncate text-[11px] font-medium transition-colors",
                i === step - 1
                  ? "text-foreground"
                  : i < step
                    ? "text-muted-foreground"
                    : "text-muted-foreground/50",
              )}
            >
              {label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Photo thumbnail + capture control                                  */
/* ------------------------------------------------------------------ */

export function PhotoThumb({
  tone = "before",
  onRemove,
  index,
}: {
  tone?: "before" | "after"
  onRemove?: () => void
  index: number
}) {
  const { locale } = useNav()
  const toneLabel = tone === "before" ? t(locale, "beforeShort") : t(locale, "afterShort")
  return (
    <div className="group relative aspect-square overflow-hidden rounded-xl border border-border bg-elevated">
      <div
        className="absolute inset-0"
        style={{
          background:
            tone === "before"
              ? "repeating-linear-gradient(135deg, oklch(0.28 0 0) 0 10px, oklch(0.25 0 0) 10px 20px)"
              : "repeating-linear-gradient(135deg, oklch(0.34 0 0) 0 10px, oklch(0.3 0 0) 10px 20px)",
        }}
        aria-hidden="true"
      />
      <span className="absolute left-2 top-2 rounded-md bg-background/70 px-1.5 py-0.5 text-[10px] font-medium text-foreground backdrop-blur">
        {toneLabel} {index}
      </span>
      {onRemove && (
        <button
          onClick={onRemove}
          aria-label={t(locale, "removePhotoLabel", { label: toneLabel, n: index })}
          className="absolute right-1.5 top-1.5 grid size-6 place-items-center rounded-full bg-background/80 text-foreground backdrop-blur transition hover:bg-destructive hover:text-destructive-foreground"
        >
          <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
}

export function CaptureButton({ onCapture }: { onCapture: () => void }) {
  const { locale } = useNav()
  return (
    <button
      onClick={onCapture}
      aria-label={t(locale, "capturePhotoLabel")}
      className="grid aspect-square w-full place-items-center rounded-xl border border-dashed border-border bg-card text-muted-foreground transition-colors hover:border-ring hover:text-foreground"
    >
      <svg viewBox="0 0 24 24" className="size-7" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z" />
        <circle cx="12" cy="13" r="3.5" />
      </svg>
    </button>
  )
}

/* ------------------------------------------------------------------ */
/*  Empty / loading / error states                                     */
/* ------------------------------------------------------------------ */

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center px-8 py-16 text-center">
      <div className="mb-4 grid size-14 place-items-center rounded-2xl border border-border bg-card text-muted-foreground">
        <Icon className="size-6" />
      </div>
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <p className="mt-1.5 max-w-[26ch] text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function LoadingState({ label }: { label?: string }) {
  const { locale } = useNav()
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
      <LoaderCircle className="size-6 animate-spin" />
      <p className="text-sm">{label ?? t(locale, "loading")}</p>
    </div>
  )
}

export function ErrorState({
  icon: Icon = TriangleAlert,
  title,
  description,
  retryLabel,
  onRetry,
  secondary,
}: {
  icon?: LucideIcon
  title: string
  description: string
  retryLabel?: string
  onRetry?: () => void
  secondary?: ReactNode
}) {
  const { locale } = useNav()
  return (
    <div className="flex flex-col items-center justify-center px-8 py-14 text-center">
      <div className="mb-4 grid size-14 place-items-center rounded-2xl border border-destructive/30 bg-destructive/10 text-destructive">
        <Icon className="size-6" />
      </div>
      <h3 className="text-base font-semibold text-foreground text-balance">{title}</h3>
      <p className="mt-1.5 max-w-[30ch] text-sm leading-relaxed text-muted-foreground text-pretty">
        {description}
      </p>
      {onRetry && (
        <Button variant="secondary" size="md" icon={RefreshCw} className="mt-5" onClick={onRetry}>
          {retryLabel ?? t(locale, "tryAgain")}
        </Button>
      )}
      {secondary && <div className="mt-3">{secondary}</div>}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Modal / bottom sheet                                               */
/* ------------------------------------------------------------------ */

export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div className="absolute inset-0 z-50 flex items-end justify-center lg:items-center">
      <button
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px] animate-in fade-in"
      />
      <div className="relative z-10 w-full rounded-t-3xl border-t border-border bg-popover p-5 pb-8 animate-in slide-in-from-bottom duration-300 lg:max-w-lg lg:rounded-2xl lg:border lg:pb-5 lg:shadow-2xl lg:slide-in-from-bottom-4">
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-border lg:hidden" />
        {title && <h3 className="mb-4 text-lg font-semibold text-foreground">{title}</h3>}
        {children}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Screen header                                                      */
/* ------------------------------------------------------------------ */

export function ScreenHeader({
  title,
  subtitle,
  onBack,
  right,
  step,
  totalSteps,
  width = "form",
}: {
  title?: string
  subtitle?: string
  onBack?: () => void
  right?: ReactNode
  step?: number
  totalSteps?: number
  width?: "wide" | "form"
}) {
  const { canGoBack, locale: canGoBackLocale } = useNav()
  // Screens pass `back` unconditionally; only draw the control when it can do something
  const showBack = Boolean(onBack) && canGoBack

  return (
    <header className="shrink-0 border-b border-border bg-background/80 backdrop-blur-xl">
      <div
        className={cn(
          "mx-auto w-full px-4 pb-3 pt-3 lg:px-10 lg:pb-5 lg:pt-6",
          width === "wide" ? "max-w-[1180px]" : "max-w-2xl",
        )}
      >
        <div className="flex items-center gap-2">
          {showBack && (
            <IconButton icon={ChevronLeft} label={t(canGoBackLocale, "goBack")} onClick={onBack} className="-ml-2" />
          )}
          <div className="min-w-0 flex-1">
            {title && (
              <h1 className="truncate text-base font-semibold text-foreground lg:text-2xl lg:tracking-tight">
                {title}
              </h1>
            )}
            {subtitle && (
              <p className="truncate text-xs text-muted-foreground lg:mt-0.5 lg:text-sm">{subtitle}</p>
            )}
          </div>
          {right}
        </div>
        {step && totalSteps && (
          <div className="mt-3 lg:mt-4">
            <StepProgress step={step} total={totalSteps} />
          </div>
        )}
      </div>
    </header>
  )
}

/* ------------------------------------------------------------------ */
/*  Signature canvas                                                   */
/* ------------------------------------------------------------------ */

export interface SignatureCanvasHandle {
  exportPng: () => Promise<Blob | null>
}

export const SignatureCanvas = forwardRef<
  SignatureCanvasHandle,
  {
    onChange?: (hasInk: boolean) => void
  }
>(function SignatureCanvas({ onChange }, ref) {
  const { locale } = useNav()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const activePointer = useRef<number | null>(null)
  const inkRef = useRef(false)
  const [hasInk, setHasInk] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ratio = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * ratio
    canvas.height = rect.height * ratio
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    ctx.scale(ratio, ratio)
    ctx.lineWidth = 2.5
    ctx.lineCap = "round"
    ctx.lineJoin = "round"
    ctx.strokeStyle = "#fafafa"
  }, [])

  useImperativeHandle(ref, () => ({
    exportPng: () =>
      new Promise((resolve) => {
        if (!inkRef.current || !canvasRef.current) {
          resolve(null)
          return
        }
        canvasRef.current.toBlob(resolve, "image/png")
      }),
  }))

  function pos(e: React.PointerEvent) {
    const rect = canvasRef.current!.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top }
  }

  function start(e: React.PointerEvent) {
    e.preventDefault()
    if (activePointer.current !== null) return
    e.currentTarget.setPointerCapture(e.pointerId)
    activePointer.current = e.pointerId
    drawing.current = true
    const ctx = canvasRef.current!.getContext("2d")!
    const { x, y } = pos(e)
    ctx.beginPath()
    ctx.arc(x, y, ctx.lineWidth / 2, 0, Math.PI * 2)
    ctx.fillStyle = ctx.strokeStyle
    ctx.fill()
    ctx.beginPath()
    ctx.moveTo(x, y)
    markInk()
  }

  function move(e: React.PointerEvent) {
    if (!drawing.current || activePointer.current !== e.pointerId) return
    e.preventDefault()
    const ctx = canvasRef.current!.getContext("2d")!
    const { x, y } = pos(e)
    ctx.lineTo(x, y)
    ctx.stroke()
    markInk()
  }

  function end(e: React.PointerEvent) {
    if (activePointer.current !== e.pointerId) return
    drawing.current = false
    activePointer.current = null
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId)
    }
  }

  function markInk() {
    if (inkRef.current) return
    inkRef.current = true
    setHasInk(true)
    onChange?.(true)
  }

  function clear() {
    const canvas = canvasRef.current!
    const ctx = canvas.getContext("2d")!
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    inkRef.current = false
    setHasInk(false)
    onChange?.(false)
  }

  return (
    <div>
      <div className="relative overflow-hidden rounded-2xl border border-border bg-elevated">
        <canvas
          ref={canvasRef}
          onPointerDown={start}
          onPointerMove={move}
          onPointerUp={end}
          onPointerCancel={end}
          onLostPointerCapture={end}
          className="h-48 w-full cursor-crosshair touch-none lg:h-56"
        />
        {!hasInk && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1 text-muted-foreground">
            <PenLineIcon />
            <span className="text-sm">{t(locale, "signHereHint")}</span>
          </div>
        )}
        <div className="pointer-events-none absolute inset-x-6 bottom-8 border-b border-dashed border-border" />
      </div>
      <div className="mt-2 flex justify-end">
        <Button variant="ghost" size="sm" onClick={clear} disabled={!hasInk}>
          {t(locale, "clear")}
        </Button>
      </div>
    </div>
  )
})

function PenLineIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  )
}

/* ------------------------------------------------------------------ */
/*  Confirmation check circle                                          */
/* ------------------------------------------------------------------ */

export function SuccessMark() {
  return (
    <div className="relative grid size-20 place-items-center">
      <span className="absolute inset-0 rounded-full bg-success/15 animate-ping" style={{ animationIterationCount: 2 }} />
      <span className="relative grid size-20 place-items-center rounded-full bg-success text-success-foreground">
        <Check className="size-9" strokeWidth={3} />
      </span>
    </div>
  )
}
