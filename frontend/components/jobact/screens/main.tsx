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
import {
  appCurrencies,
  appLocales,
  formatCurrency,
  formatWeekdayDate,
  greeting,
  roleLabel,
  statusLabel,
  t,
  tPlural,
  type AppCurrency,
  type AppLocale,
} from "@/lib/jobact/i18n"

/* -------------------------------- HOME -------------------------------- */

export function HomeScreen() {
  const { navigate, locale, currency: appCurrency } = useNav()
  const drafts = allReports.filter((r) => r.status === "draft" || r.status === "unsigned")
  const recent = allReports.filter((r) => r.status === "completed").slice(0, 3)
  const today = allReports.slice(0, 2)
  const pendingSync = allReports.filter((r) => r.sync !== "synced").length
  const now = new Date()

  return (
    <>
      <PageHeader
        title={greeting(locale, now.getHours(), CURRENT_USER.name.split(" ")[0])}
        subtitle={`${formatWeekdayDate(locale, now)} · ${tPlural(locale, "visitsScheduled", today.length)}`}
        right={
          <div className="flex items-center gap-1">
            <IconButton icon={Bell} label={t(locale, "notifications")} />
            <button onClick={() => navigate("profile")} aria-label={t(locale, "profile")} className="lg:hidden">
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
                {t(locale, "startNow")}
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-foreground lg:text-3xl">
                {t(locale, "createReportHeading")}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {t(locale, "createReportSubtitle")}
              </p>
            </div>
            <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-primary text-primary-foreground transition-transform group-hover:scale-105 lg:size-16">
              <Plus className="size-7" strokeWidth={2.5} />
            </span>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground lg:mt-7 lg:gap-x-7 lg:text-sm">
            <span className="inline-flex items-center gap-1.5"><Camera className="size-3.5" /> {t(locale, "photosLabel")}</span>
            <span className="inline-flex items-center gap-1.5"><Mic className="size-3.5" /> {t(locale, "voiceLabel")}</span>
            <span className="inline-flex items-center gap-1.5"><MapPin className="size-3.5" /> {t(locale, "gpsLabel")}</span>
            <span className="inline-flex items-center gap-1.5"><ShieldCheck className="size-3.5" /> {t(locale, "signatureLabel")}</span>
          </div>
        </button>

        {/* At-a-glance numbers */}
        <div className="mt-5 grid grid-cols-2 gap-3 lg:mt-6 lg:grid-cols-4">
          <StatTile label={t(locale, "billedThisMonth")} value={formatCurrency(locale, 2895, appCurrency)} />
          <StatTile label={t(locale, "reportsStat")} value="18" />
          <StatTile label={t(locale, "signedOnSiteStat")} value="94%" />
          <StatTile label={t(locale, "awaitingSync")} value={String(pendingSync)} tone={pendingSync ? "warning" : "default"} />
        </div>

        <div className="mt-7 grid gap-7 lg:mt-8 lg:grid-cols-3 lg:gap-8">
          {/* Main column */}
          <div className="space-y-7 lg:col-span-2 lg:space-y-8">
            {drafts.length > 0 && (
              <section>
                <div className="mb-3 flex items-center justify-between">
                  <SectionLabel>{t(locale, "unfinishedDrafts")}</SectionLabel>
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
                        <p className="truncate text-xs text-muted-foreground">{t(locale, "resumeWhereYouLeftOff")}</p>
                      </div>
                      <StatusBadge status={r.status} />
                    </button>
                  ))}
                </div>
              </section>
            )}

            <section>
              <div className="mb-3 flex items-center justify-between">
                <SectionLabel>{t(locale, "recentReports")}</SectionLabel>
                <button
                  onClick={() => navigate("reports")}
                  className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                >
                  {t(locale, "viewAll")} <ArrowRight className="size-3" />
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
              <SectionLabel>{t(locale, "syncSection")}</SectionLabel>
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
                      {tPlural(locale, "reportsToSync", pendingSync)}
                    </p>
                    <p className="text-xs text-muted-foreground">{t(locale, "reviewSyncStatus")}</p>
                  </div>
                </div>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              </button>
            </section>

            <section>
              <SectionLabel>{t(locale, "latestVisits")}</SectionLabel>
              <div className="space-y-2.5">
                {today.map((r) => (
                  <VisitCard key={r.id} report={r} onClick={() => navigate("reportDetail", { reportId: r.id })} />
                ))}
              </div>
            </section>

            {CURRENT_USER.role === "owner" && (
              <section>
                <SectionLabel>{t(locale, "teamToday")}</SectionLabel>
                <Card className="divide-y divide-border">
                  {teamMembers.map((m) => (
                    <div key={m.id} className="flex items-center gap-3 p-3">
                      <Avatar initials={m.initials} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground">{m.name}</p>
                        <p className="text-xs text-muted-foreground">{roleLabel(locale, m.role)}</p>
                      </div>
                      <span className="shrink-0 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                        {tPlural(locale, "visitsToday", m.visitsToday)}
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

const filterKeys = ["all", "completed", "unsigned", "draft"] as const

function filterLabel(locale: AppLocale, key: (typeof filterKeys)[number]): string {
  switch (key) {
    case "completed":
      return t(locale, "filterCompleted")
    case "unsigned":
      return t(locale, "filterUnsigned")
    case "draft":
      return t(locale, "filterDraft")
    default:
      return t(locale, "filterAll")
  }
}

export function ReportsScreen() {
  const { navigate, locale, currency: appCurrency } = useNav()
  const [query, setQuery] = useState("")
  const [filter, setFilter] = useState<(typeof filterKeys)[number]>("all")
  const [reports, setReports] = useState<ReportResponse[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiFetch<ReportResponse[]>("/api/v1/reports")
      .then((items) => { if (!cancelled) setReports(items) })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : t(locale, "couldNotLoadReports"))
      })
    return () => { cancelled = true }
  }, [locale])

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
        title={t(locale, "reportsTitle")}
        subtitle={tPlural(locale, "reportsOnRecord", reports.length)}
        right={
          <Button icon={Plus} className="hidden lg:inline-flex" onClick={() => navigate("customers", { picking: true })}>
            {t(locale, "newReportBtn")}
          </Button>
        }
      >
        <div className="mt-3 flex flex-col gap-3 lg:mt-5 lg:flex-row lg:items-center lg:justify-between">
          <SearchField
            placeholder={t(locale, "searchCustomerOrId")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="lg:max-w-sm"
          />
          <div className="no-scrollbar flex gap-2 overflow-x-auto">
            {filterKeys.map((key) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={
                  "shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors " +
                  (filter === key
                    ? "border-transparent bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:text-foreground")
                }
              >
                {filterLabel(locale, key)}
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
            title={t(locale, "noReportsFound")}
            description={t(locale, "noReportsFoundDesc")}
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
                  <p className="mt-3 line-clamp-2 text-sm text-foreground">{r.current_revision.work_completed || t(locale, "reportAwaitingDetails")}</p>
                  <p className="mt-3 font-mono text-lg font-semibold text-foreground">
                    {r.current_revision.amount_cents === null
                      ? t(locale, "noPrice")
                      : formatCurrency(locale, r.current_revision.amount_cents / 100, r.current_revision.currency)}
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
  const { navigate, back, canGoBack, setDraft, locale } = useNav()
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
          setError(reason instanceof Error ? reason.message : t(locale, "couldNotLoadCustomers"))
        }
      })
    return () => {
      cancelled = true
    }
  }, [locale])

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
          title={t(locale, "selectCustomer")}
          subtitle={t(locale, "stepWhoIsThisFor")}
          onBack={canGoBack ? back : undefined}
          step={1}
          totalSteps={6}
        />
      ) : (
        <PageHeader
          title={t(locale, "customersTitle")}
          subtitle={tPlural(locale, "customersOnFile", customers.length)}
          right={
            <Button
              icon={Plus}
              className="hidden lg:inline-flex"
              onClick={() => navigate("addCustomer", { picking })}
            >
              {t(locale, "addCustomer")}
            </Button>
          }
        />
      )}

      <Page width={width}>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <SearchField
            placeholder={t(locale, "searchNameOrAddress")}
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
            {t(locale, "addNewCustomer")}
          </Button>
        </div>

        <div className="mt-4">
          {error ? (
            <EmptyState icon={CircleAlert} title={t(locale, "couldNotLoadCustomers")} description={error} />
          ) : results.length === 0 ? (
            <EmptyState
              icon={UsersIcon}
              title={t(locale, "noCustomersYet")}
              description={t(locale, "noCustomersYetDesc")}
              action={
                <Button icon={Plus} onClick={() => navigate("addCustomer", { picking })}>
                  {t(locale, "addCustomer")}
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
  const { navigate, reset, session, setLocale, setSession, locale, currency: appCurrency, setCurrency } = useNav()
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
  const [savingCurrency, setSavingCurrency] = useState(false)
  const [currencyError, setCurrencyError] = useState("")
  const userLabel = session ? `User ${session.user_id.slice(0, 8)}` : t(locale, "signedOutUser")
  const organizationLabel = session
    ? `Organization ${session.organization_id.slice(0, 8)}`
    : t(locale, "noOrganization")
  const initials = session?.role.slice(0, 2).toUpperCase() ?? "--"

  useEffect(() => {
    let cancelled = false
    apiFetch<AuthMethodsResponse>("/api/v1/auth/methods")
      .then((methods) => {
        if (!cancelled) setAuthMethods(methods)
      })
      .catch(() => {
        if (!cancelled) setSecurityError(t(locale, "couldNotLoadAuthMethods"))
      })

    const linkResult = new URLSearchParams(window.location.search).get("auth_link")
    if (linkResult) {
      setSecurityMessage(
        linkResult === "google-success"
          ? t(locale, "googleLinkedMessage")
          : t(locale, "googleLinkFailedMessage"),
      )
      window.history.replaceState({}, "", window.location.pathname)
    }
    return () => {
      cancelled = true
    }
  }, [locale])

  async function savePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSecurityError("")
    setSecurityMessage("")
    if (newPassword !== repeatPassword) {
      setSecurityError(t(locale, "passwordsDoNotMatch"))
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
      setSecurityMessage(authMethods?.password ? t(locale, "passwordChanged") : t(locale, "passwordAdded"))
    } catch (error) {
      setSecurityError(
        error instanceof JobActApiError
          ? error.response.detail
          : t(locale, "couldNotUpdatePassword"),
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
        error instanceof JobActApiError ? error.response.detail : t(locale, "couldNotSignOut"),
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

  async function changeCurrency(nextCurrency: AppCurrency) {
    if (nextCurrency === appCurrency) return
    const previousCurrency = appCurrency
    setCurrencyError("")
    setCurrency(nextCurrency)
    setSavingCurrency(true)
    try {
      await apiFetch<void>("/api/v1/auth/currency", { method: "PUT", body: JSON.stringify({ currency: nextCurrency }) })
      setSession(session ? { ...session, currency: nextCurrency } : session)
    } catch {
      setCurrency(previousCurrency)
      setCurrencyError(t(locale, "currencySaveError"))
    } finally {
      setSavingCurrency(false)
    }
  }

  const menu: {
    group: string
    items: { label: string; icon: LucideIcon; screen?: Parameters<typeof navigate>[0]; note?: string }[]
  }[] = [
    {
      group: t(locale, "workspaceGroup"),
      items: [
        { label: t(locale, "teamAndEmployees"), icon: UsersIcon, screen: "customers", note: tPlural(locale, "peopleCount", teamMembers.length) },
        { label: t(locale, "syncAndBackups"), icon: RefreshCw, screen: "sync" },
        { label: t(locale, "offlineModeItem"), icon: WifiOff, screen: "offline" },
      ],
    },
    {
      group: t(locale, "appGroup"),
      items: [
        { label: t(locale, "permissionsAndStates"), icon: CircleAlert, screen: "states" },
        { label: t(locale, "preferences"), icon: SlidersHorizontal, note: `${t(locale, "language")} · ${t(locale, "currency")}` },
      ],
    },
  ]

  return (
    <>
      <PageHeader title={t(locale, "accountTitle")} subtitle={organizationLabel} width="form" />
      <Page width="form">
        <Card className="flex items-center gap-3 p-4 lg:p-5">
          <Avatar initials={initials} className="size-12 rounded-2xl text-base" />
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-foreground">{userLabel}</p>
            <p className="text-xs text-muted-foreground">{organizationLabel}</p>
          </div>
          <span className="shrink-0 rounded-full border border-border bg-muted px-2.5 py-1 text-xs font-medium capitalize text-foreground">
            {session ? roleLabel(locale, session.role) : t(locale, "signedOutRole")}
          </span>
        </Card>

        <div className="mt-4 grid grid-cols-3 gap-2.5">
          {[
            { label: t(locale, "thisMonthStat"), value: formatCurrency(locale, 2895, appCurrency) },
            { label: t(locale, "reportsStatLabel"), value: "18" },
            { label: t(locale, "signedStatLabel"), value: "94%" },
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

            <label htmlFor="app-currency" className="mt-4 block text-sm font-medium text-foreground">{t(locale, "currency")}</label>
            <select
              id="app-currency"
              value={appCurrency}
              disabled={savingCurrency}
              onChange={(event) => changeCurrency(event.target.value as AppCurrency)}
              className="mt-2 h-10 w-full rounded-xl border border-border bg-card px-3 text-sm text-foreground disabled:opacity-60"
            >
              {appCurrencies.map((option) => <option key={option} value={option}>{t(locale, option === "USD" ? "usdOption" : "rubOption")}</option>)}
            </select>
            <p aria-live="polite" className="mt-2 min-h-5 text-xs text-destructive">{savingCurrency ? t(locale, "saving") : currencyError}</p>
          </Card>
        </section>

        <section className="mt-6">
          <SectionLabel>{t(locale, "accountSecurity")}</SectionLabel>
          <Card className="p-4 lg:p-5">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-border px-2.5 py-1 text-foreground">
                {authMethods?.password ? t(locale, "passwordEnabledBadge") : t(locale, "passwordNotSetBadge")}
              </span>
              <span className="rounded-full border border-border px-2.5 py-1 text-foreground">
                {authMethods?.google ? t(locale, "googleLinkedBadge") : t(locale, "googleNotLinkedBadge")}
              </span>
            </div>

            <form className="mt-4 space-y-3" onSubmit={savePassword}>
              {authMethods?.password && (
                <Input
                  id="current-password"
                  label={t(locale, "currentPasswordLabel")}
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                />
              )}
              <Input
                id="new-password"
                label={authMethods?.password ? t(locale, "newPasswordLabel") : t(locale, "setPasswordLabel")}
                type="password"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                hint={t(locale, "passwordHint")}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
              <Input
                id="repeat-new-password"
                label={t(locale, "repeatNewPasswordLabel")}
                type="password"
                autoComplete="new-password"
                value={repeatPassword}
                onChange={(event) => setRepeatPassword(event.target.value)}
                error={
                  repeatPassword && newPassword !== repeatPassword
                    ? t(locale, "passwordsDoNotMatch")
                    : undefined
                }
                required
              />
              <Button type="submit" icon={KeyRound} disabled={savingPassword}>
                {savingPassword ? t(locale, "saving") : authMethods?.password ? t(locale, "changePasswordBtn") : t(locale, "setPasswordBtn")}
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
                {t(locale, "linkGoogleBtn")}
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
          {loggingOut ? t(locale, "signingOut") : t(locale, "signOutBtn")}
        </Button>
        <p className="mt-4 text-xs text-muted-foreground">{t(locale, "appVersionFooter")}</p>
      </Page>
    </>
  )
}
