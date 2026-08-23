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
import { Scroll } from "../shell"
import { useNav } from "@/lib/jobact/store"

/* ------------------------------ OFFLINE ------------------------------- */

export function OfflineScreen() {
  const { back } = useNav()
  const queue = [
    { id: "JA-2026-0482", name: "Ferrer Residence", photos: 2, state: "waiting" as const },
    { id: "JA-2026-0478", name: "Harbor View Offices", photos: 7, state: "waiting" as const },
  ]

  return (
    <>
      <ScreenHeader title="Offline mode" onBack={back} />
      <OfflineBanner />
      <Scroll className="px-5 py-4">
        <Card className="flex flex-col items-center p-6 text-center">
          <span className="grid size-14 place-items-center rounded-2xl border border-border bg-muted text-muted-foreground">
            <WifiOff className="size-6" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-foreground">You&apos;re working offline</h2>
          <p className="mt-1.5 max-w-[32ch] text-sm leading-relaxed text-muted-foreground text-pretty">
            Keep going — every report, photo and signature is saved on this device and will sync automatically when you reconnect.
          </p>
        </Card>

        <div className="mt-6 flex items-center justify-between">
          <SectionLabel>Waiting to upload</SectionLabel>
          <span className="text-xs text-muted-foreground">{queue.length} reports</span>
        </div>
        <div className="space-y-2.5">
          {queue.map((q) => (
            <Card key={q.id} className="flex items-center gap-3 p-3.5">
              <span className="grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground">
                <CloudUpload className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{q.name}</p>
                <p className="font-mono text-[11px] text-muted-foreground">{q.id} · {q.photos} photos</p>
              </div>
              <span className="rounded-full bg-muted px-2.5 py-1 text-[11px] text-muted-foreground">Queued</span>
            </Card>
          ))}
        </div>

        <p className="mt-6 rounded-xl border border-border bg-card p-3.5 text-xs leading-relaxed text-muted-foreground">
          The full visit flow — customer, photos, voice, and signature — works without a connection. Nothing is lost.
        </p>
      </Scroll>
    </>
  )
}

/* -------------------------------- SYNC -------------------------------- */

type ItemState = "syncing" | "synced" | "failed"

export function SyncScreen() {
  const { back } = useNav()
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
      <ScreenHeader title="Sync" onBack={back} />
      <Scroll className="px-5 py-4">
        <Card className="flex flex-col items-center p-6 text-center">
          {syncing ? (
            <>
              <span className="grid size-14 place-items-center rounded-2xl bg-muted text-foreground">
                <RefreshCw className="size-6 animate-spin" />
              </span>
              <h2 className="mt-4 text-base font-semibold text-foreground">Syncing your visits</h2>
              <p className="mt-1 text-sm text-muted-foreground">{done} of {items.length} uploaded</p>
            </>
          ) : failed ? (
            <>
              <span className="grid size-14 place-items-center rounded-2xl bg-destructive/10 text-destructive">
                <TriangleAlert className="size-6" />
              </span>
              <h2 className="mt-4 text-base font-semibold text-foreground">Some uploads failed</h2>
              <p className="mt-1 text-sm text-muted-foreground">Your data is safe. Retry when you have a better connection.</p>
            </>
          ) : (
            <>
              <span className="grid size-14 place-items-center rounded-2xl bg-success/15 text-success">
                <CircleCheck className="size-6" />
              </span>
              <h2 className="mt-4 text-base font-semibold text-foreground">All synced</h2>
              <p className="mt-1 text-sm text-muted-foreground">Every report is backed up and secured.</p>
            </>
          )}
          <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Wifi className="size-3.5" /> Connected · Wi-Fi
          </div>
        </Card>

        <SectionLabel>
          <span className="mt-6 block">Queue</span>
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
                  Retry
                </Button>
              ) : (
                <SyncIndicator state={i.state === "syncing" ? "syncing" : "synced"} />
              )}
            </Card>
          ))}
        </div>
      </Scroll>
    </>
  )
}

/* -------------------- PERMISSIONS & ERROR GALLERY --------------------- */

export function StatesScreen() {
  const { back } = useNav()

  const permissionCards = [
    {
      icon: CameraOff,
      title: "Camera access needed",
      description: "JobAct needs your camera to capture before and after photos as proof of the visit.",
      cta: "Open settings",
    },
    {
      icon: MicOff,
      title: "Microphone access needed",
      description: "Allow the microphone so you can describe the work by voice instead of typing.",
      cta: "Open settings",
    },
    {
      icon: MapPinOff,
      title: "Location access needed",
      description: "Location confirms where the visit happened. Enable it to attach GPS proof.",
      cta: "Open settings",
    },
    {
      icon: MapPinOff,
      title: "GPS unavailable",
      description: "We couldn't get a fix right now. You can continue and attach the location later.",
      cta: "Retry",
    },
    {
      icon: CloudUpload,
      title: "Upload failed",
      description: "Photos couldn't be uploaded. They're saved on your device and will retry automatically.",
      cta: "Retry now",
    },
    {
      icon: Sparkles,
      title: "Couldn't process voice note",
      description: "The report couldn't be generated from your recording. Try again or type the description.",
      cta: "Try again",
    },
  ]

  return (
    <>
      <ScreenHeader title="Permissions & states" subtitle="Preview of edge-case screens" onBack={back} />
      <Scroll className="px-5 py-4">
        <p className="mb-4 text-xs leading-relaxed text-muted-foreground">
          These are the states JobAct shows when hardware access is blocked or something goes wrong in the field.
        </p>
        <div className="space-y-4">
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
      </Scroll>
    </>
  )
}
