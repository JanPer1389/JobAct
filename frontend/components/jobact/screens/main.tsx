"use client"

import { useEffect, useMemo, useState, type FormEvent } from "react"
import {
  Plus,
  ArrowRight,
  FileText,
  Users as UsersIcon,
  ChevronRight,
  Bell,
  WifiOff,
  RefreshCw,
  CircleAlert,
  Camera,
  MapPin,
  Mic,
  ShieldCheck,
  LogOut,
  SlidersHorizontal,
  KeyRound,
  Link2,
  type LucideIcon,
} from "lucide-react"
import {
  Button,
  Card,
  SearchField,
  SectionLabel,
  StatusBadge,
  SyncIndicator,
  EmptyState,
  IconButton,
  Input,
} from "../ui"
import { ScreenHeader } from "../ui"
import { Page, PageHeader } from "../shell"
import { CustomerCard, ReportCard, VisitCard, Avatar } from "../cards"
import {
  reports as allReports,
  customers as allCustomers,
  teamMembers,
  CURRENT_USER,
  currency,
  type ReportStatus,
} from "@/lib/jobact/data"
import { useNav } from "@/lib/jobact/store"
import {
  apiFetch,
  JobActApiError,
  type AuthMethodsResponse,
  type CustomerResponse,
  type ReportResponse,
} from "@/lib/jobact/api"
import { appLocales, t, type AppLocale } from "@/lib/jobact/i18n"

/* -------------------------------- HOME -------------------------------- */

export function HomeScreen() {
  const { navigate } = useNav()
  const drafts = allReports.filter((r) => r.status === "draft" || r.status === "unsigned")
  const recent = allReports.filter((r) => r.status === "completed").slice(0, 3)
  const today = allReports.slice(0, 2)
  const pendingSync = allReports.filter((r) => r.sync !== "synced").length

  return (
    <>
      <PageHeader
        title={`Good morning, ${CURRENT_USER.name.split(" ")[0]}`}
        subtitle="Friday, August 22 · 2 visits scheduled"
        right={
          <div className="flex items-center gap-1">
            <IconButton icon={Bell} label="Notifications" />
            <button onClick={() => navigate("profile")} aria-label="Profile" className="lg:hidden">
              <Avatar initials={CURRENT_USER.initials} />
            </button>
          </div>
        }
      />

      <Page width="wide">
        {/* Primary action */}
        <button
          onClick={() => navigate("customers", { picking: true })}
          className="group relative w-full overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-elevated to-card p-5 text-left shadow-lg shadow-black/30 transition active:scale-[0.99] hover:border-white/20 lg:p-8"
        >
          <div className="flex items-center justify-between gap-6">
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                Start now
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-foreground lg:text-3xl">
                Create report
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Photos, location & signature in ~2 min
              </p>
            </div>
            <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-primary text-primary-foreground transition-transform group-hover:scale-105 lg:size-16">
              <Plus className="size-7" strokeWidth={2.5} />
            </span>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground lg:mt-7 lg:gap-x-7 lg:text-sm">
            <span className="inline-flex items-center gap-1.5"><Camera className="size-3.5" /> Photos</span>
            <span className="inline-flex items-center gap-1.5"><Mic className="size-3.5" /> Voice</span>
            <span className="inline-flex items-center gap-1.5"><MapPin className="size-3.5" /> GPS</span>
            <span className="inline-flex items-center gap-1.5"><ShieldCheck className="size-3.5" /> Signature</span>
          </div>
        </button>

        {/* At-a-glance numbers */}
        <div className="mt-5 grid grid-cols-2 gap-3 lg:mt-6 lg:grid-cols-4">
          <StatTile label="Billed this month" value={currency(2895)} />
          <StatTile label="Reports" value="18" />
          <StatTile label="Signed on-site" value="94%" />
          <StatTile label="Awaiting sync" value={String(pendingSync)} tone={pendingSync ? "warning" : "default"} />
        </div>

        <div className="mt-7 grid gap-7 lg:mt-8 lg:grid-cols-3 lg:gap-8">
          {/* Main column */}
          <div className="space-y-7 lg:col-span-2 lg:space-y-8">
            {drafts.length > 0 && (
              <section>
                <div className="mb-3 flex items-center justify-between">
                  <SectionLabel>Unfinished drafts</SectionLabel>
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {drafts.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => navigate("reportDraft", { reportId: r.id })}
                      className="flex w-full items-center gap-3 rounded-2xl border border-border bg-card p-3 text-left transition-colors hover:bg-accent"
                    >
                      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
                        <FileText className="size-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{r.customerName}</p>
                        <p className="truncate text-xs text-muted-foreground">Resume where you left off</p>
                      </div>
                      <StatusBadge status={r.status} />
                    </button>
                  ))}
                </div>
              </section>
            )}

            <section>
              <div className="mb-3 flex items-center justify-between">
                <SectionLabel>Recent reports</SectionLabel>
                <button
                  onClick={() => navigate("reports")}
                  className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                >
                  View all <ArrowRight className="size-3" />
                </button>
              </div>
              <div className="grid gap-2.5 sm:grid-cols-2">
                {recent.map((r) => (
                  <ReportCard key={r.id} report={r} onClick={() => navigate("reportDetail", { reportId: r.id })} />
                ))}
              </div>
            </section>
          </div>

          {/* Side column */}
          <div className="space-y-7 lg:space-y-8">
            <section>
              <SectionLabel>Sync</SectionLabel>
              <button
                onClick={() => navigate("sync")}
                className="flex w-full items-center justify-between rounded-2xl border border-border bg-card px-4 py-3 text-left transition-colors hover:bg-accent"
              >
                <div className="flex items-center gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-warning/15 text-warning">
                    <RefreshCw className="size-4" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {pendingSync} report{pendingSync === 1 ? "" : "s"} to sync
                    </p>
                    <p className="text-xs text-muted-foreground">Review sync status</p>
                  </div>
                </div>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              </button>
            </section>

            <section>
              <SectionLabel>Latest visits</SectionLabel>
              <div className="space-y-2.5">
                {today.map((r) => (
                  <VisitCard key={r.id} report={r} onClick={() => navigate("reportDetail", { reportId: r.id })} />
                ))}
              </div>
            </section>

            {CURRENT_USER.role === "owner" && (
              <section>
                <SectionLabel>Team today</SectionLabel>
                <Card className="divide-y divide-border">
                  {teamMembers.map((m) => (
                    <div key={m.id} className="flex items-center gap-3 p-3">
                      <Avatar initials={m.initials} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{m.name}</p>
                        <p className="text-xs capitalize text-muted-foreground">{m.role}</p>
                      </div>
                      <span className="shrink-0 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                        {m.visitsToday} visit{m.visitsToday === 1 ? "" : "s"}
                      </span>
                    </div>
                  ))}
                </Card>
              </section>
            )}
          </div>
        </div>
      </Page>
    </>
  )
}

function StatTile({
  label,
  value,
  tone = "default",
}: {
  label: string
  value: string
  tone?: "default" | "warning"
}) {
  return (
    <Card className="p-4">
      <p
        className={
          "font-mono text-xl font-semibold tabular-nums lg:text-2xl " +
          (tone === "warning" ? "text-warning" : "text-foreground")
        }
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
    </Card>
  )
}

/* ------------------------------ REPORTS ------------------------------- */

const filters = [
  { key: "all", label: "All" },
  { key: "completed", label: "Completed" },
  { key: "unsigned", label: "Unsigned" },
  { key: "draft", label: "Drafts" },
]

export function ReportsScreen() {
  const { navigate } = useNav()
  const [query, setQuery] = useState("")
  const [filter, setFilter] = useState("all")
  const [reports, setReports] = useState<ReportResponse[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiFetch<ReportResponse[]>("/api/v1/reports")
      .then((items) => { if (!cancelled) setReports(items) })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Could not load reports.")
      })
    return () => { cancelled = true }
  }, [])

  const results = useMemo(() => {
    return reports.filter((r) => {
      const matchesFilter = filter === "all" || r.status === filter
      const matchesQuery =
        !query ||
        r.current_revision.work_completed.toLowerCase().includes(query.toLowerCase()) ||
        r.human_id.toLowerCase().includes(query.toLowerCase())
      return matchesFilter && matchesQuery
    })
  }, [query, filter, reports])

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle={`${reports.length} reports on record`}
        right={
          <Button icon={Plus} className="hidden lg:inline-flex" onClick={() => navigate("customers", { picking: true })}>
            New report
          </Button>
        }
      >
        <div className="mt-3 flex flex-col gap-3 lg:mt-5 lg:flex-row lg:items-center lg:justify-between">
          <SearchField
            placeholder="Search customer or report ID"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="lg:max-w-sm"
          />
          <div className="no-scrollbar flex gap-2 overflow-x-auto">
            {filters.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={
                  "shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors " +
                  (filter === f.key
                    ? "border-transparent bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:text-foreground")
                }
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </PageHeader>

      <Page width="wide">
        {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
        {results.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No reports found"
            description="Try a different search or filter to find the visit you are looking for."
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {results.map((r) => (
              <button key={r.id} onClick={() => navigate("reportDetail", { reportId: r.id })} className="text-left">
                <Card className="h-full p-4 transition-colors hover:bg-accent">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-mono text-xs text-muted-foreground">{r.human_id}</p>
                    <StatusBadge status={r.status as ReportStatus} />
                  </div>
                  <p className="mt-3 line-clamp-2 text-sm text-foreground">{r.current_revision.work_completed || "Report awaiting details"}</p>
                  <p className="mt-3 font-mono text-lg font-semibold text-foreground">
                    {r.current_revision.amount_cents === null ? "No price" : `${(r.current_revision.amount_cents / 100).toFixed(2)} ${r.current_revision.currency}`}
                  </p>
                </Card>
              </button>
            ))}
          </div>
        )}
      </Page>
    </>
  )
}

/* ------------------------------ CUSTOMERS ----------------------------- */

export function CustomersScreen({ picking = false }: { picking?: boolean }) {
  const { navigate, back, canGoBack, setDraft } = useNav()
  const [query, setQuery] = useState("")
  const [customers, setCustomers] = useState<CustomerResponse[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiFetch<CustomerResponse[]>("/api/v1/customers")
      .then((result) => {
        if (!cancelled) setCustomers(result)
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Could not load customers.")
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const results = customers.filter(
    (c) =>
      c.name.toLowerCase().includes(query.toLowerCase()) ||
      c.address.toLowerCase().includes(query.toLowerCase()),
  )

  function handleSelect(customer: CustomerResponse) {
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
      beforePhotoAssets: [],
      afterPhotoAssets: [],
      workCompleted: "",
      amount: "",
      signed: false,
    })
    if (picking) navigate("visitStart", { customerId: customer.id })
    else navigate("customerDetail", { customerId: customer.id })
  }

  const width = picking ? "form" : "wide"

  return (
    <>
      {picking ? (
        <ScreenHeader
          title="Select customer"
          subtitle="Step 1 · Who is this visit for?"
          onBack={canGoBack ? back : undefined}
          step={1}
          totalSteps={6}
        />
      ) : (
        <PageHeader
          title="Customers"
          subtitle={`${customers.length} on file`}
          right={
            <Button
              icon={Plus}
              className="hidden lg:inline-flex"
              onClick={() => navigate("addCustomer", { picking })}
            >
              Add customer
            </Button>
          }
        />
      )}

      <Page width={width}>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <SearchField
            placeholder="Search name or address"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="lg:max-w-sm"
          />
          <Button
            variant="secondary"
            size="md"
            icon={Plus}
            fullWidth
            className={picking ? "" : "lg:hidden"}
            onClick={() => navigate("addCustomer", { picking })}
          >
            Add new customer
          </Button>
        </div>

        <div className="mt-4">
          {error ? (
            <EmptyState icon={CircleAlert} title="Could not load customers" description={error} />
          ) : results.length === 0 ? (
            <EmptyState
              icon={UsersIcon}
              title="No customers yet"
              description="Add your first customer to start creating reports and tracking visits."
              action={
                <Button icon={Plus} onClick={() => navigate("addCustomer", { picking })}>
                  Add customer
                </Button>
              }
            />
          ) : (
            <div className={picking ? "space-y-2.5" : "grid gap-3 sm:grid-cols-2 xl:grid-cols-3"}>
              {results.map((c) => (
                <CustomerCard
                  key={c.id}
                  customer={{
                    id: c.id,
                    name: c.name,
                    address: c.address,
                    phone: c.phone,
                    type: c.service_type,
                    visits: 0,
                    lastVisit: null,
                  }}
                  onClick={() => handleSelect(c)}
                />
              ))}
            </div>
          )}
        </div>
      </Page>
    </>
  )
}

/* ------------------------------- PROFILE ------------------------------ */

export function ProfileScreen() {
  const { navigate, reset, session, setLocale, setSession, locale } = useNav()
  const [authMethods, setAuthMethods] = useState<AuthMethodsResponse | null>(null)
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [repeatPassword, setRepeatPassword] = useState("")
  const [securityMessage, setSecurityMessage] = useState("")
  const [securityError, setSecurityError] = useState("")
  const [savingPassword, setSavingPassword] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [savingLocale, setSavingLocale] = useState(false)
  const [localeError, setLocaleError] = useState("")
  const userLabel = session ? `User ${session.user_id.slice(0, 8)}` : "Signed-out user"
  const organizationLabel = session
    ? `Organization ${session.organization_id.slice(0, 8)}`
    : "No organization"
  const initials = session?.role.slice(0, 2).toUpperCase() ?? "--"

  useEffect(() => {
    let cancelled = false
    apiFetch<AuthMethodsResponse>("/api/v1/auth/methods")
      .then((methods) => {
        if (!cancelled) setAuthMethods(methods)
      })
      .catch(() => {
        if (!cancelled) setSecurityError("Could not load authentication methods.")
      })

    const linkResult = new URLSearchParams(window.location.search).get("auth_link")
    if (linkResult) {
      setSecurityMessage(
        linkResult === "google-success"
          ? "Google is now linked to this account."
          : "Google could not be linked. Please try again.",
      )
      window.history.replaceState({}, "", window.location.pathname)
    }
    return () => {
      cancelled = true
    }
  }, [])

  async function savePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSecurityError("")
    setSecurityMessage("")
    if (newPassword !== repeatPassword) {
      setSecurityError("Passwords do not match.")
      return
    }
    setSavingPassword(true)
    try {
      await apiFetch<void>("/api/v1/auth/password", {
        method: "PUT",
        body: JSON.stringify({
          current_password: authMethods?.password ? currentPassword : null,
          new_password: newPassword,
          repeat_password: repeatPassword,
        }),
      })
      setAuthMethods((current) => ({ password: true, google: current?.google ?? false }))
      setCurrentPassword("")
      setNewPassword("")
      setRepeatPassword("")
      setSecurityMessage(authMethods?.password ? "Password changed." : "Password added.")
    } catch (error) {
      setSecurityError(
        error instanceof JobActApiError
          ? error.response.detail
          : "Could not update the password.",
      )
    } finally {
      setSavingPassword(false)
    }
  }

  async function signOut() {
    setLoggingOut(true)
    try {
      await apiFetch<void>("/api/v1/auth/logout", { method: "POST" })
      setSession(null)
      reset("signin")
    } catch (error) {
      setSecurityError(
        error instanceof JobActApiError ? error.response.detail : "Could not sign out.",
      )
      setLoggingOut(false)
    }
  }

  async function changeLocale(nextLocale: AppLocale) {
    if (nextLocale === locale) return
    const previousLocale = locale
    setLocaleError("")
    setLocale(nextLocale)
    setSavingLocale(true)
    try {
      await apiFetch<void>("/api/v1/auth/locale", { method: "PUT", body: JSON.stringify({ locale: nextLocale }) })
      setSession(session ? { ...session, locale: nextLocale } : session)
    } catch {
      setLocale(previousLocale)
      setLocaleError(t(previousLocale, "languageSaveError"))
    } finally {
      setSavingLocale(false)
    }
  }

  const menu: {
    group: string
    items: { label: string; icon: LucideIcon; screen?: Parameters<typeof navigate>[0]; note?: string }[]
  }[] = [
    {
      group: "Workspace",
      items: [
        { label: "Team & employees", icon: UsersIcon, screen: "customers", note: `${teamMembers.length} people` },
        { label: "Sync & backups", icon: RefreshCw, screen: "sync" },
        { label: "Offline mode", icon: WifiOff, screen: "offline" },
      ],
    },
    {
      group: "App",
      items: [
        { label: "Permissions & states", icon: CircleAlert, screen: "states" },
        { label: t(locale, "preferences"), icon: SlidersHorizontal, note: "Units, currency" },
      ],
    },
  ]

  return (
    <>
      <PageHeader title="Account" subtitle={organizationLabel} width="form" />
      <Page width="form">
        <Card className="flex items-center gap-3 p-4 lg:p-5">
          <Avatar initials={initials} className="size-12 rounded-2xl text-base" />
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-foreground">{userLabel}</p>
            <p className="text-xs text-muted-foreground">{organizationLabel}</p>
          </div>
          <span className="shrink-0 rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium capitalize text-foreground">
            {session?.role ?? "signed out"}
          </span>
        </Card>

        <div className="mt-4 grid grid-cols-3 gap-2.5">
          {[
            { label: "This month", value: currency(2895) },
            { label: "Reports", value: "18" },
            { label: "Signed", value: "94%" },
          ].map((s) => (
            <Card key={s.label} className="p-3 text-center lg:p-4">
              <p className="font-mono text-lg font-semibold text-foreground lg:text-xl">{s.value}</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">{s.label}</p>
            </Card>
          ))}
        </div>

        <section className="mt-6">
          <SectionLabel>{t(locale, "preferences")}</SectionLabel>
          <Card className="p-4 lg:p-5">
            <label htmlFor="app-language" className="text-sm font-medium text-foreground">{t(locale, "language")}</label>
            <select
              id="app-language"
              value={locale}
              disabled={savingLocale}
              onChange={(event) => changeLocale(event.target.value as AppLocale)}
              className="mt-2 h-10 w-full rounded-xl border border-border bg-card px-3 text-sm text-foreground disabled:opacity-60"
            >
              {appLocales.map((option) => <option key={option} value={option}>{t(locale, option === "en-US" ? "english" : "russian")}</option>)}
            </select>
            <p aria-live="polite" className="mt-2 min-h-5 text-xs text-destructive">{savingLocale ? t(locale, "saving") : localeError}</p>
          </Card>
        </section>

        <section className="mt-6">
          <SectionLabel>Account security</SectionLabel>
          <Card className="p-4 lg:p-5">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-border px-2.5 py-1 text-foreground">
                Password {authMethods?.password ? "enabled" : "not set"}
              </span>
              <span className="rounded-full border border-border px-2.5 py-1 text-foreground">
                Google {authMethods?.google ? "linked" : "not linked"}
              </span>
            </div>

            <form className="mt-4 space-y-3" onSubmit={savePassword}>
              {authMethods?.password && (
                <Input
                  id="current-password"
                  label="Current password"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                />
              )}
              <Input
                id="new-password"
                label={authMethods?.password ? "New password" : "Set password"}
                type="password"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                hint="Use 12–128 characters."
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
              <Input
                id="repeat-new-password"
                label="Repeat new password"
                type="password"
                autoComplete="new-password"
                value={repeatPassword}
                onChange={(event) => setRepeatPassword(event.target.value)}
                error={
                  repeatPassword && newPassword !== repeatPassword
                    ? "Passwords do not match."
                    : undefined
                }
                required
              />
              <Button type="submit" icon={KeyRound} disabled={savingPassword}>
                {savingPassword ? "Saving…" : authMethods?.password ? "Change password" : "Set password"}
              </Button>
            </form>

            {!authMethods?.google && (
              <Button
                type="button"
                variant="secondary"
                icon={Link2}
                className="mt-3"
                onClick={() => window.location.assign("/api/v1/auth/google/link/start")}
              >
                Link Google
              </Button>
            )}
            <div aria-live="polite" className="mt-3 min-h-5 text-sm">
              {securityError ? (
                <span className="text-destructive">{securityError}</span>
              ) : (
                <span className="text-success">{securityMessage}</span>
              )}
            </div>
          </Card>
        </section>

        {menu.map((section) => (
          <section key={section.group} className="mt-6">
            <SectionLabel>{section.group}</SectionLabel>
            <Card className="divide-y divide-border">
              {section.items.map((item) => (
                <button
                  key={item.label}
                  onClick={() => item.screen && navigate(item.screen)}
                  className="flex w-full items-center gap-3 p-3.5 text-left transition-colors hover:bg-accent"
                >
                  <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
                    <item.icon className="size-4" />
                  </span>
                  <span className="flex-1 text-sm font-medium text-foreground">{item.label}</span>
                  {item.note && <span className="text-xs text-muted-foreground">{item.note}</span>}
                  <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                </button>
              ))}
            </Card>
          </section>
        ))}

        <Button
          variant="destructive"
          size="md"
          icon={LogOut}
          className="mt-6 w-full lg:w-auto"
          disabled={loggingOut}
          onClick={signOut}
        >
          {loggingOut ? "Signing out…" : "Sign out"}
        </Button>
        <p className="mt-4 text-xs text-muted-foreground">JobAct v1.0 · Made for the field</p>
      </Page>
    </>
  )
}
