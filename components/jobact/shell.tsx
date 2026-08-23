"use client"

import { cn } from "@/lib/utils"
import { House, FileText, Users, User, Plus } from "lucide-react"
import type { ReactNode } from "react"
import { useNav, type Screen } from "@/lib/jobact/store"

/* Phone frame that centers the app and shows a device on desktop */
export function PhoneShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh w-full items-center justify-center bg-[radial-gradient(circle_at_top,oklch(0.22_0_0),oklch(0.13_0_0))] p-0 sm:p-6">
      <div className="relative flex h-svh w-full max-w-[420px] flex-col overflow-hidden bg-background sm:h-[880px] sm:rounded-[2.75rem] sm:border-[10px] sm:border-black sm:shadow-2xl sm:ring-1 sm:ring-white/10">
        {/* notch */}
        <div className="pointer-events-none absolute left-1/2 top-0 z-40 hidden h-6 w-32 -translate-x-1/2 rounded-b-2xl bg-black sm:block" />
        <StatusBar />
        <div className="relative flex min-h-0 flex-1 flex-col">{children}</div>
      </div>
    </div>
  )
}

function StatusBar() {
  return (
    <div className="flex h-9 shrink-0 items-center justify-between px-6 pt-1 text-xs font-medium text-foreground">
      <span className="tabular-nums">9:41</span>
      <div className="flex items-center gap-1.5">
        <svg viewBox="0 0 24 24" className="size-3.5" fill="currentColor" aria-hidden="true">
          <path d="M2 17h2v3H2zm4-3h2v6H6zm4-3h2v9h-2zm4-3h2v12h-2zm4-3h2v15h-2z" />
        </svg>
        <svg viewBox="0 0 24 24" className="size-3.5" fill="currentColor" aria-hidden="true">
          <path d="M12 6c3.3 0 6.3 1.3 8.5 3.4l-1.4 1.4C17.3 9 14.8 8 12 8s-5.3 1-7.1 2.8L3.5 9.4C5.7 7.3 8.7 6 12 6zm0 4c2 0 3.8.8 5.1 2.1l-1.4 1.4C14.8 12.6 13.5 12 12 12s-2.8.6-3.7 1.5l-1.4-1.4C8.2 10.8 10 10 12 10zm0 4c.8 0 1.6.3 2.1.9L12 18l-2.1-3.1c.5-.6 1.3-.9 2.1-.9z" />
        </svg>
        <svg viewBox="0 0 26 14" className="h-3.5 w-6" fill="none" aria-hidden="true">
          <rect x="0.5" y="0.5" width="21" height="13" rx="3.5" stroke="currentColor" opacity="0.4" />
          <rect x="2" y="2" width="16" height="10" rx="2" fill="currentColor" />
          <rect x="23" y="4" width="2" height="6" rx="1" fill="currentColor" opacity="0.6" />
        </svg>
      </div>
    </div>
  )
}

const tabs: { screen: Screen; label: string; icon: typeof House }[] = [
  { screen: "home", label: "Home", icon: House },
  { screen: "reports", label: "Reports", icon: FileText },
  { screen: "customers", label: "Customers", icon: Users },
  { screen: "profile", label: "More", icon: User },
]

export function BottomNav({ active }: { active: Screen }) {
  const { reset, navigate } = useNav()
  return (
    <nav className="relative shrink-0 border-t border-border bg-background/90 backdrop-blur-xl">
      <div className="grid grid-cols-5 items-end px-2 pb-6 pt-2">
        {tabs.slice(0, 2).map((t) => (
          <TabButton key={t.screen} tab={t} active={active} onClick={() => reset(t.screen)} />
        ))}
        <div className="flex justify-center">
          <button
            aria-label="Create report"
            onClick={() => navigate("customers", { picking: true })}
            className="grid size-14 -translate-y-3 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-black/40 transition-transform active:scale-95"
          >
            <Plus className="size-6" strokeWidth={2.5} />
          </button>
        </div>
        {tabs.slice(2).map((t) => (
          <TabButton key={t.screen} tab={t} active={active} onClick={() => reset(t.screen)} />
        ))}
      </div>
    </nav>
  )
}

function TabButton({
  tab,
  active,
  onClick,
}: {
  tab: { screen: Screen; label: string; icon: typeof House }
  active: Screen
  onClick: () => void
}) {
  const Icon = tab.icon
  const isActive = active === tab.screen
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex flex-col items-center gap-1 py-1 text-[10px] font-medium transition-colors",
        isActive ? "text-foreground" : "text-muted-foreground",
      )}
    >
      <Icon className="size-5" strokeWidth={isActive ? 2.4 : 1.9} />
      {tab.label}
    </button>
  )
}

/* Scrollable content region */
export function Scroll({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("no-scrollbar min-h-0 flex-1 overflow-y-auto", className)}>{children}</div>
  )
}
