"use client"

import { cn } from "@/lib/utils"
import { ChevronRight, MapPin, Clock, ImageIcon, Camera } from "lucide-react"
import { StatusBadge, SyncIndicator } from "./ui"
import { currency, type Customer, type Report } from "@/lib/jobact/data"

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

function customerInitials(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
}

export function CustomerCard({
  customer,
  onClick,
  selected,
}: {
  customer: Customer
  onClick?: () => void
  selected?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-2xl border bg-card p-3 text-left transition-colors hover:bg-accent",
        selected ? "border-ring" : "border-border",
      )}
    >
      <Avatar initials={customerInitials(customer.name)} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{customer.name}</p>
        <p className="truncate text-xs text-muted-foreground">{customer.address}</p>
      </div>
      <div className="text-right">
        <p className="text-[11px] text-muted-foreground">{customer.type}</p>
        <p className="text-[11px] text-muted-foreground/70">{customer.visits} visits</p>
      </div>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
    </button>
  )
}

export function ReportCard({
  report,
  onClick,
  showTech,
}: {
  report: Report
  onClick?: () => void
  showTech?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full flex-col gap-3 rounded-2xl border border-border bg-card p-4 text-left transition-colors hover:bg-accent"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{report.customerName}</p>
          <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{report.id}</p>
        </div>
        <StatusBadge status={report.status} />
      </div>
      <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {report.workCompleted}
      </p>
      <div className="flex items-center justify-between border-t border-border pt-3">
        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Clock className="size-3" />
            {report.date} · {report.time}
          </span>
          <span className="inline-flex items-center gap-1">
            <Camera className="size-3" />
            {report.beforePhotos + report.afterPhotos}
          </span>
        </div>
        <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
          {currency(report.amount)}
        </span>
      </div>
      {showTech && (
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>by {report.technician}</span>
          <SyncIndicator state={report.sync} />
        </div>
      )}
    </button>
  )
}

export function VisitCard({
  report,
  onClick,
}: {
  report: Report
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-2xl border border-border bg-card p-3 text-left transition-colors hover:bg-accent"
    >
      <div
        className="grid size-11 shrink-0 place-items-center rounded-xl border border-border text-muted-foreground"
        style={{
          background:
            "repeating-linear-gradient(135deg, oklch(0.26 0 0) 0 6px, oklch(0.23 0 0) 6px 12px)",
        }}
      >
        <ImageIcon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{report.customerName}</p>
        <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
          <MapPin className="size-3 shrink-0" />
          {report.address}
        </p>
      </div>
      <div className="text-right">
        <p className="text-xs font-medium text-foreground">{report.time}</p>
        <p className="text-[11px] text-muted-foreground">{report.date.split(",")[0]}</p>
      </div>
    </button>
  )
}

export { customerInitials }
