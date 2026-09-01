"use client"

import { cn } from "@/lib/utils"
import type { ReactNode } from "react"

/* ------------------------------------------------------------------ */
/*  App shell -- one scrollable region, no sidebar/bottom nav. The     */
/*  local demo is a single linear flow ("one obvious action"), not a   */
/*  multi-section app, so there is nothing for persistent chrome to    */
/*  navigate between.                                                  */
/* ------------------------------------------------------------------ */

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-svh w-full overflow-hidden bg-background">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="relative flex min-h-0 flex-1 flex-col">{children}</div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Content regions                                                    */
/* ------------------------------------------------------------------ */

/* Scrollable content region */
export function Scroll({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("thin-scrollbar min-h-0 flex-1 overflow-y-auto", className)}>{children}</div>
  )
}

type ContentWidth = "wide" | "form"

const widthClasses: Record<ContentWidth, string> = {
  wide: "max-w-[1180px]",
  form: "max-w-2xl",
}

/* Scrollable page body with a readable max width on large screens */
export function Page({
  children,
  className,
  width = "wide",
}: {
  children: ReactNode
  className?: string
  width?: ContentWidth
}) {
  return (
    <Scroll>
      <div className={cn("mx-auto w-full px-5 py-4 lg:px-10 lg:py-8", widthClasses[width], className)}>
        {children}
      </div>
    </Scroll>
  )
}

/* Pinned bar of primary actions at the bottom of a screen */
export function ActionBar({
  children,
  width = "form",
}: {
  children: ReactNode
  width?: ContentWidth
}) {
  return (
    <div className="shrink-0 border-t border-border bg-background/80 backdrop-blur-xl">
      <div className={cn("mx-auto w-full px-5 pb-8 pt-3 lg:px-10 lg:pb-5 lg:pt-4", widthClasses[width])}>
        {children}
      </div>
    </div>
  )
}

/* Header for a tab-level screen (currently only Home) */
export function PageHeader({
  title,
  subtitle,
  right,
  children,
  width = "wide",
}: {
  title: string
  subtitle?: string
  right?: ReactNode
  children?: ReactNode
  width?: ContentWidth
}) {
  return (
    <header className="shrink-0 border-b border-border">
      <div className={cn("mx-auto w-full px-5 pb-3 pt-3 lg:px-10 lg:pb-5 lg:pt-7", widthClasses[width])}>
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="truncate text-xl font-semibold tracking-tight text-foreground lg:text-2xl">
              {title}
            </h1>
            {subtitle && <p className="mt-0.5 truncate text-xs text-muted-foreground lg:text-sm">{subtitle}</p>}
          </div>
          {right}
        </div>
        {children}
      </div>
    </header>
  )
}
