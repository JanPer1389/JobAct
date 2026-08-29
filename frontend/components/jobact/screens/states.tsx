"use client"

import { useEffect, useState } from "react"
import {
  WifiOff,
  Wifi,
  RefreshCw,
  CircleCheck,
  CloudUpload,
  TriangleAlert,
  Camera,
  CameraOff,
  MicOff,
  MapPinOff,
  Sparkles,
  Check,
  LoaderCircle,
} from "lucide-react"
import {
  Button,
  Card,
  ScreenHeader,
  SectionLabel,
  ErrorState,
  SyncIndicator,
  OfflineBanner,
} from "../ui"
import { Page } from "../shell"
import { useNav } from "@/lib/jobact/store"
import { t, tPlural } from "@/lib/jobact/i18n"

/* ------------------------------ OFFLINE ------------------------------- */

export function OfflineScreen() {
  const { back, locale } = useNav()
  const queue = [
    { id: "JA-2026-0482", name: "Ferrer Residence", photos: 2, state: "waiting" as const },
    { id: "JA-2026-0478", name: "Harbor View Offices", photos: 7, state: "waiting" as const },
  ]

  return (
    <>
      <ScreenHeader title={t(locale, "offlineModeTitle")} onBack={back} />
      <OfflineBanner />
      <Page width="form">
        <Card className="flex flex-col items-center p-6 text-center">
          <span className="grid size-14 place-items-center rounded-2xl border border-border bg-muted text-muted-foreground">
            <WifiOff className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-foreground">{t(locale, "workingOfflineTitle")}</h2>
          <p className="mt-1.5 max-w-[32ch] text-sm leading-relaxed text-muted-foreground text-pretty">
            {t(locale, "workingOfflineDesc")}
          </p>
        </Card>

        <div className="mt-6 flex items-center justify-between">
          <SectionLabel>{t(locale, "waitingToUpload")}</SectionLabel>
          <span className="text-xs text-muted-foreground">{tPlural(locale, "reportsCount", queue.length)}</span>
        </div>
        <div className="space-y-2.5">
          {queue.map((q) => (
            <Card key={q.id} className="flex items-center gap-3 p-3.5">
              <span className="grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground">
                <CloudUpload className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{q.name}</p>
                <p className="font-mono text-[11px] text-muted-foreground">{q.id} · {tPlural(locale, "photosCount", q.photos)}</p>
              </div>
              <span className="rounded-full bg-muted px-2.5 py-1 text-[11px] text-muted-foreground">{t(locale, "queuedLabel")}</span>
            </Card>
          ))}
        </div>

        <p className="mt-6 rounded-xl border border-border bg-card p-3.5 text-xs leading-relaxed text-muted-foreground">
          {t(locale, "offlineFooterNote")}
        </p>
      </Page>
    </>
  )
}

/* -------------------------------- SYNC -------------------------------- */

type ItemState = "syncing" | "synced" | "failed"

export function SyncScreen() {
  const { back, locale } = useNav()
  const [items, setItems] = useState<{ id: string; name: string; state: ItemState }[]>([
    { id: "JA-2026-0482", name: "Ferrer Residence", state: "syncing" },
    { id: "JA-2026-0478", name: "Harbor View Offices", state: "syncing" },
    { id: "JA-2026-0481", name: "Bright Bean Cafe", state: "synced" },
  ])

  useEffect(() => {
    const t1 = setTimeout(
      () => setItems((prev) => prev.map((i) => (i.id === "JA-2026-0482" ? { ...i, state: "synced" } : i))),
      1500,
    )
    const t2 = setTimeout(
      () => setItems((prev) => prev.map((i) => (i.id === "JA-2026-0478" ? { ...i, state: "failed" } : i))),
      2600,
    )
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [])

  const done = items.filter((i) => i.state === "synced").length
  const failed = items.some((i) => i.state === "failed")
  const syncing = items.some((i) => i.state === "syncing")

  function retry(id: string) {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, state: "syncing" } : i)))
    setTimeout(() => setItems((prev) => prev.map((i) => (i.id === id ? { ...i, state: "synced" } : i))), 1400)
  }

  return (
    <>
      <ScreenHeader title={t(locale, "syncTitle")} onBack={back} />
      <Page width="form">
        <Card className="flex flex-col items-center p-6 text-center">
          {syncing ? (
            <>
              <span className="grid size-14 place-items-center rounded-2xl bg-muted text-foreground">
                <RefreshCw className="size-6 animate-spin" />
              </span>
              <h2 className="mt-4 text-base font-semibold text-foreground">{t(locale, "syncingVisits")}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{done} / {items.length}</p>
            </>
          ) : failed ? (
            <>
              <span className="grid size-14 place-items-center rounded-2xl bg-destructive/10 text-destructive">
                <TriangleAlert className="size-6" />
              </span>
              <h2 className="mt-4 text-base font-semibold text-foreground">{t(locale, "someUploadsFailed")}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t(locale, "dataIsSafeRetry")}</p>
            </>
          ) : (
            <>
              <span className="grid size-14 place-items-center rounded-2xl bg-success/15 text-success">
                <CircleCheck className="size-6" />
              </span>
              <h2 className="mt-4 text-base font-semibold text-foreground">{t(locale, "allSynced")}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t(locale, "everyReportBackedUp")}</p>
            </>
          )}
          <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Wifi className="size-3.5" /> {t(locale, "connectedWifi")}
          </div>
        </Card>

        <SectionLabel>
          <span className="mt-6 block">{t(locale, "queueLabel")}</span>
        </SectionLabel>
        <div className="space-y-2.5">
          {items.map((i) => (
            <Card key={i.id} className="flex items-center gap-3 p-3.5">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{i.name}</p>
                <p className="font-mono text-[11px] text-muted-foreground">{i.id}</p>
              </div>
              {i.state === "failed" ? (
                <Button size="sm" variant="secondary" icon={RefreshCw} onClick={() => retry(i.id)}>
                  {t(locale, "retry")}
                </Button>
              ) : (
                <SyncIndicator state={i.state === "syncing" ? "syncing" : "synced"} />
              )}
            </Card>
          ))}
        </div>
      </Page>
    </>
  )
}

/* -------------------- PERMISSIONS & ERROR GALLERY --------------------- */

export function StatesScreen() {
  const { back, locale } = useNav()

  const permissionCards = [
    {
      icon: CameraOff,
      title: t(locale, "cameraAccessTitle"),
      description: t(locale, "cameraAccessDesc"),
      cta: t(locale, "openSettingsCta"),
    },
    {
      icon: MicOff,
      title: t(locale, "micAccessTitle"),
      description: t(locale, "micAccessDesc"),
      cta: t(locale, "openSettingsCta"),
    },
    {
      icon: MapPinOff,
      title: t(locale, "locationAccessTitle"),
      description: t(locale, "locationAccessDesc"),
      cta: t(locale, "openSettingsCta"),
    },
    {
      icon: MapPinOff,
      title: t(locale, "gpsUnavailableTitle"),
      description: t(locale, "gpsUnavailableDesc"),
      cta: t(locale, "retry"),
    },
    {
      icon: CloudUpload,
      title: t(locale, "uploadFailedTitle"),
      description: t(locale, "uploadFailedDesc"),
      cta: t(locale, "retryNowCta"),
    },
    {
      icon: Sparkles,
      title: t(locale, "voiceProcessFailedTitle"),
      description: t(locale, "voiceProcessFailedDesc"),
      cta: t(locale, "tryAgain"),
    },
  ]

  return (
    <>
      <ScreenHeader
        title={t(locale, "permissionsStatesTitle")}
        subtitle={t(locale, "previewEdgeCase")}
        onBack={back}
        width="wide"
      />
      <Page width="wide">
        <p className="mb-4 max-w-prose text-xs leading-relaxed text-muted-foreground">
          {t(locale, "statesIntro")}
        </p>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {permissionCards.map((c) => (
            <Card key={c.title} className="overflow-hidden">
              <ErrorState
                icon={c.icon}
                title={c.title}
                description={c.description}
                retryLabel={c.cta}
                onRetry={() => {}}
              />
            </Card>
          ))}
        </div>
      </Page>
    </>
  )
}
