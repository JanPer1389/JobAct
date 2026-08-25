"use client"

import { cn } from "@/lib/utils"
import {
  House,
  FileText,
  Users,
  User,
  Plus,
  RefreshCw,
  WifiOff,
  CircleAlert,
  ChevronRight,
  type LucideIcon,
} from "lucide-react"
import type { ReactNode } from "react"
import { useNav, type Screen } from "@/lib/jobact/store"
import { CURRENT_USER, reports as allReports } from "@/lib/jobact/data"
import { Logo } from "./ui"
import { Avatar } from "./cards"

/* ------------------------------------------------------------------ */
/*  App shell — sidebar on desktop, bottom tab bar on small screens    */
/* ------------------------------------------------------------------ */

export function AppShell({
  children,
  chrome,
  bottomNav,
  active,
}: {
  children: ReactNode
  chrome: boolean
  bottomNav: boolean
  active: Screen
}) {
  return (
    <div className="flex h-svh w-full overflow-hidden bg-background">
      {chrome && <Sidebar active={active} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="relative flex min-h-0 flex-1 flex-col">{children}</div>
        {bottomNav && <BottomNav active={active} />}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Sidebar (lg and up)                                                */
/* ------------------------------------------------------------------ */

interface NavItem {
  screen: Screen
  label: string
  icon: LucideIcon
}

const workspaceNav: NavItem[] = [
  { screen: "home", label: "Overview", icon: House },
  { screen: "reports", label: "Reports", icon: FileText },
  { screen: "customers", label: "Customers", icon: Users },
]

const operationsNav: NavItem[] = [
  { screen: "sync", label: "Sync & backups", icon: RefreshCw },
  { screen: "offline", label: "Offline queue", icon: WifiOff },
  { screen: "states", label: "Permissions", icon: CircleAlert },
]

function Sidebar({ active }: { active: Screen }) {
  const { reset, navigate } = useNav()
  const pendingSync = allReports.filter((r) => r.sync !== "synced").length

  return (
    <aside className="hidden w-[264px] shrink-0 flex-col border-r border-border bg-card/40 lg:flex">
      <div className="flex items-center gap-3 px-5 py-5">
        <Logo />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold tracking-tight text-foreground">JobAct</p>
          <p className="truncate text-xs text-muted-foreground">{CURRENT_USER.company}</p>
        </div>
      </div>

      <div className="px-4">
        <button
          onClick={() => navigate("customers", { picking: true })}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Plus className="size-4" strokeWidth={2.4} />
          New report
        </button>
      </div>

      <nav className="mt-7 flex min-h-0 flex-1 flex-col gap-7 overflow-y-auto px-4 pb-4">
        <NavGroup label="Workspace" items={workspaceNav} active={active} onSelect={reset} />
        <NavGroup
          label="Operations"
          items={operationsNav}
          active={active}
          onSelect={reset}
          badges={{ sync: pendingSync || undefined }}
        />
      </nav>

      <button
        onClick={() => reset("profile")}
        className={cn(
          "m-3 flex items-center gap-3 rounded-xl border border-border p-2.5 text-left transition-colors hover:bg-accent",
          active === "profile" ? "bg-accent" : "bg-card",
        )}
      >
        <Avatar initials={CURRENT_USER.initials} className="size-9 rounded-lg text-xs" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-foreground">{CURRENT_USER.name}</span>
          <span className="block truncate text-xs capitalize text-muted-foreground">{CURRENT_USER.role}</span>
        </span>
        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
      </button>
    </aside>
  )
}

function NavGroup({
  label,
  items,
  active,
  onSelect,
  badges,
}: {
  label: string
  items: NavItem[]
  active: Screen
  onSelect: (screen: Screen) => void
  badges?: Partial<Record<Screen, number | undefined>>
}) {
  return (
    <div>
      <p className="mb-2 px-3 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground/70">
        {label}
      </p>
      <div className="space-y-0.5">
        {items.map((item) => {
          const Icon = item.icon
          const isActive = active === item.screen
          const badge = badges?.[item.screen]
          return (
            <button
              key={item.screen}
              onClick={() => onSelect(item.screen)}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex h-10 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                isActive
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              <Icon className="size-4 shrink-0" strokeWidth={isActive ? 2.3 : 1.9} />
              <span className="flex-1 truncate text-left">{item.label}</span>
              {badge ? (
                <span className="rounded-full bg-warning/15 px-2 py-0.5 text-[11px] font-medium tabular-nums text-warning">
                  {badge}
                </span>
              ) : null}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Bottom tab bar (below lg)                                          */
/* ------------------------------------------------------------------ */

const tabs: NavItem[] = [
  { screen: "home", label: "Home", icon: House },
  { screen: "reports", label: "Reports", icon: FileText },
  { screen: "customers", label: "Customers", icon: Users },
  { screen: "profile", label: "More", icon: User },
]

export function BottomNav({ active }: { active: Screen }) {
  const { reset, navigate } = useNav()
  return (
    <nav className="relative shrink-0 border-t border-border bg-background/90 backdrop-blur-xl lg:hidden">
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
  tab: NavItem
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

/* Header for the tab-level screens (Reports, Customers, More) */
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
