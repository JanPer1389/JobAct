"use client"

import { cn } from "@/lib/utils"
import { Camera, Clock } from "lucide-react"
import { StatusBadge } from "./ui"
import { type LocalCheck } from "@/lib/jobact/local-store"
import { useNav } from "@/lib/jobact/store"
import { formatCurrency, formatDate, formatTime } from "@/lib/jobact/i18n"

export function Avatar({
  initials,
  className,
}: {
  initials: string
  className?: string
}) {
  return (
    <span
      className={cn(
        "grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-elevated text-sm font-semibold text-foreground",
        className,
      )}
    >
      {initials}
    </span>
  )
}

export function customerInitials(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
}

export function CheckCard({
  check,
  onClick,
}: {
  check: LocalCheck
  onClick?: () => void
}) {
  const { locale } = useNav()
  return (
    <button
      onClick={onClick}
      className="flex w-full flex-col gap-3 rounded-2xl border border-border bg-card p-4 text-left transition-colors hover:bg-accent"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{check.customerName}</p>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{check.humanId}</p>
        </div>
        <StatusBadge status="completed" />
      </div>
      <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {check.workCompleted}
      </p>
      <div className="flex items-center justify-between border-t border-border pt-3">
        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Clock className="size-3" />
            {formatDate(locale, check.completedAt)} · {formatTime(locale, check.completedAt)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Camera className="size-3" />
            {check.beforePhotoIds.length + check.afterPhotoIds.length}
          </span>
        </div>
        <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
          {check.amountCents === null
            ? "—"
            : formatCurrency(locale, check.amountCents / 100, check.currency)}
        </span>
      </div>
    </button>
  )
}
