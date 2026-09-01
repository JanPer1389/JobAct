"use client"

import { useEffect, useState } from "react"
import { ChevronRight, FileText, Plus } from "lucide-react"
import { Button, Card, EmptyState, Logo } from "../ui"
import { Page } from "../shell"
import { CheckCard } from "../cards"
import { useNav, type DraftPhoto } from "@/lib/jobact/store"
import { getActiveDraftId } from "@/lib/jobact/local-prefs"
import { getBlob, listRecentChecks, loadDraft, type LocalCheck } from "@/lib/jobact/local-store"
import { greeting, t } from "@/lib/jobact/i18n"

async function photosFromIds(ids: string[]): Promise<DraftPhoto[]> {
  const photos = await Promise.all(
    ids.map(async (id) => {
      const record = await getBlob(id)
      return record ? { assetId: id, previewUrl: URL.createObjectURL(record.blob) } : null
    }),
  )
  return photos.filter((photo): photo is DraftPhoto => photo !== null)
}

export function HomeScreen() {
  const { navigate, setDraft, resetDraft, userName, locale, setLocale, currency, setCurrency } = useNav()
  const [resumable, setResumable] = useState<{ id: string; customerName: string } | null>(null)
  const [recentChecks, setRecentChecks] = useState<LocalCheck[] | null>(null)

  useEffect(() => {
    let cancelled = false
    const activeId = getActiveDraftId()
    if (activeId) {
      void loadDraft(activeId).then((draft) => {
        if (!cancelled && draft) {
          setResumable({ id: draft.id, customerName: draft.customerName || t(locale, "checkFallback") })
        }
      })
    }
    void listRecentChecks(5).then((checks) => {
      if (!cancelled) setRecentChecks(checks)
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function startNewCheck() {
    resetDraft()
    navigate("addCustomer")
  }

  async function resumeDraft() {
    const activeId = getActiveDraftId()
    if (!activeId) return
    const draft = await loadDraft(activeId)
    if (!draft) return
    const [beforePhotoAssets, afterPhotoAssets] = await Promise.all([
      photosFromIds(draft.beforePhotoIds),
      photosFromIds(draft.afterPhotoIds),
    ])
    setDraft({
      id: draft.id,
      customerName: draft.customerName,
      customerAddress: draft.customerAddress,
      customerPhone: draft.customerPhone,
      customerServiceType: draft.customerServiceType,
      gpsLat: draft.gpsLat ?? undefined,
      gpsLon: draft.gpsLon ?? undefined,
      gpsAccuracyM: draft.gpsAccuracyM ?? undefined,
      beforePhotoAssets,
      afterPhotoAssets,
      rawNotes: draft.rawNotes,
      notesSource: draft.notesSource,
      workCompleted: draft.workCompleted,
      materials: draft.materials,
      amountCents: draft.amountCents,
      currency: draft.currency,
      estimatedWorkUnits: draft.estimatedWorkUnits,
      aiConfidence: draft.aiConfidence,
      visualComparison: draft.visualComparison,
      amountConfirmed: draft.amountConfirmed,
      signerName: draft.signerName,
    })
    navigate(draft.screen)
  }

  const hour = new Date().getHours()

  return (
    <>
      <header className="shrink-0 border-b border-border">
        <div className="mx-auto flex w-full max-w-2xl items-center justify-between gap-3 px-5 py-4 lg:px-10 lg:py-6">
          <div className="flex items-center gap-3">
            <Logo />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-tight text-foreground">JobAct</p>
              <p className="truncate text-xs text-muted-foreground">{greeting(locale, hour, userName)}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <div className="flex overflow-hidden rounded-lg border border-border text-xs font-medium">
              <button
                onClick={() => setLocale("ru-RU")}
                className={
                  "px-2 py-1.5 " + (locale === "ru-RU" ? "bg-accent text-foreground" : "text-muted-foreground")
                }
              >
                RU
              </button>
              <button
                onClick={() => setLocale("en-US")}
                className={
                  "px-2 py-1.5 " + (locale === "en-US" ? "bg-accent text-foreground" : "text-muted-foreground")
                }
              >
                EN
              </button>
            </div>
            <div className="flex overflow-hidden rounded-lg border border-border text-xs font-medium">
              <button
                onClick={() => setCurrency("RUB")}
                className={
                  "px-2 py-1.5 " + (currency === "RUB" ? "bg-accent text-foreground" : "text-muted-foreground")
                }
              >
                ₽
              </button>
              <button
                onClick={() => setCurrency("USD")}
                className={
                  "px-2 py-1.5 " + (currency === "USD" ? "bg-accent text-foreground" : "text-muted-foreground")
                }
              >
                $
              </button>
            </div>
          </div>
        </div>
      </header>

      <Page width="form">
        <button
          onClick={startNewCheck}
          className="flex w-full flex-col items-center justify-center gap-3 rounded-3xl border border-border bg-card py-12 text-center transition-colors hover:bg-accent"
        >
          <span className="grid size-16 place-items-center rounded-2xl bg-primary text-primary-foreground">
            <Plus className="size-7" strokeWidth={2.4} />
          </span>
          <span className="text-lg font-semibold text-foreground">{t(locale, "createCheckCta")}</span>
        </button>

        {resumable && (
          <Card className="mt-4 flex items-center justify-between gap-3 p-4">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {t(locale, "resumeDraftLabel")}
              </p>
              <p className="mt-0.5 truncate text-sm font-medium text-foreground">{resumable.customerName}</p>
            </div>
            <Button size="sm" iconRight={ChevronRight} onClick={resumeDraft}>
              {t(locale, "demoContinueBtn")}
            </Button>
          </Card>
        )}

        <div className="mt-8">
          <p className="mb-3 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {t(locale, "recentChecksTitle")}
          </p>
          {recentChecks === null ? null : recentChecks.length === 0 ? (
            <EmptyState
              icon={FileText}
              title={t(locale, "noChecksYet")}
              description={t(locale, "noChecksYetDesc")}
            />
          ) : (
            <div className="space-y-2.5">
              {recentChecks.map((check) => (
                <CheckCard
                  key={check.id}
                  check={check}
                  onClick={() => navigate("checkDetail", { checkId: check.id })}
                />
              ))}
            </div>
          )}
        </div>
      </Page>
    </>
  )
}
