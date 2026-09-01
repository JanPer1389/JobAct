"use client"

import { useEffect, useState } from "react"

import { MapPin, ShieldCheck, FileText, Share2 } from "lucide-react"
import { Button, Card, ScreenHeader, SectionLabel, StatusBadge } from "../ui"
import { Page, ActionBar } from "../shell"
import { useNav } from "@/lib/jobact/store"
import { getBlob, getCheck, type LocalCheck } from "@/lib/jobact/local-store"
import { formatCurrency, formatDateTime, t, verdictLabel } from "@/lib/jobact/i18n"

/** The local-history detail view: a completed, signed check read back
 * from IndexedDB, including its stored before/after photos and PDF. */
export function CheckDetailScreen() {
  const { back, frame, locale } = useNav()
  const checkId = frame.params.checkId as string
  const [check, setCheck] = useState<LocalCheck | null | undefined>(undefined)
  const [beforeUrls, setBeforeUrls] = useState<string[]>([])
  const [afterUrls, setAfterUrls] = useState<string[]>([])
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void getCheck(checkId).then(async (loaded) => {
      if (cancelled) return
      setCheck(loaded ?? null)
      if (!loaded) return
      const [before, after, pdf] = await Promise.all([
        Promise.all(loaded.beforePhotoIds.map((id) => getBlob(id))),
        Promise.all(loaded.afterPhotoIds.map((id) => getBlob(id))),
        loaded.pdfBlobId ? getBlob(loaded.pdfBlobId) : Promise.resolve(undefined),
      ])
      if (cancelled) return
      setBeforeUrls(before.filter(Boolean).map((record) => URL.createObjectURL(record!.blob)))
      setAfterUrls(after.filter(Boolean).map((record) => URL.createObjectURL(record!.blob)))
      setPdfUrl(pdf ? URL.createObjectURL(pdf.blob) : null)
    })
    return () => {
      cancelled = true
    }
  }, [checkId])

  if (check === undefined) {
    return (
      <>
        <ScreenHeader title={t(locale, "checkFallback")} onBack={back} width="wide" />
        <Page width="wide"><Card className="p-5 text-sm text-muted-foreground">{t(locale, "loadingReportEllipsis")}</Card></Page>
      </>
    )
  }
  if (check === null) {
    return (
      <>
        <ScreenHeader title={t(locale, "checkFallback")} onBack={back} width="wide" />
        <Page width="wide"><Card className="p-5 text-sm text-muted-foreground">{t(locale, "couldNotLoadReport")}</Card></Page>
      </>
    )
  }

  return (
    <>
      <ScreenHeader
        title={check.humanId}
        subtitle={check.customerName}
        onBack={back}
        width="wide"
        right={<StatusBadge status="completed" />}
      />
      <Page width="wide">
        <div className="grid gap-6 lg:grid-cols-3 lg:gap-8">
          <div className="space-y-6 lg:col-span-2">
            <section>
              <SectionLabel>{t(locale, "workCompletedLabel")}</SectionLabel>
              <Card className="mt-2 p-5 text-sm leading-relaxed text-foreground">{check.workCompleted}</Card>
            </section>
            {check.materials.length > 0 && (
              <section>
                <SectionLabel>{t(locale, "materialsLabel")}</SectionLabel>
                <Card className="mt-2 divide-y divide-border">
                  {check.materials.map((material) => (
                    <div key={`${material.label}-${material.qty}`} className="flex justify-between p-3.5 text-sm">
                      <span>{material.label}</span><span className="text-muted-foreground">×{material.qty}</span>
                    </div>
                  ))}
                </Card>
              </section>
            )}
            <section>
              <SectionLabel>{t(locale, "beforeLabel")}</SectionLabel>
              <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-4 xl:grid-cols-5">
                {beforeUrls.map((url, i) => (
                  <img key={url} src={url} alt={`${t(locale, "beforeLabel")} ${i + 1}`} className="aspect-square w-full rounded-lg border border-border object-cover" />
                ))}
              </div>
            </section>
            <section>
              <SectionLabel>{t(locale, "afterLabel")}</SectionLabel>
              <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-4 xl:grid-cols-5">
                {afterUrls.map((url, i) => (
                  <img key={url} src={url} alt={`${t(locale, "afterLabel")} ${i + 1}`} className="aspect-square w-full rounded-lg border border-border object-cover" />
                ))}
              </div>
            </section>
            {check.visualComparison && (
              <section>
                <SectionLabel>{t(locale, "beforeAfterComparisonLabel")}</SectionLabel>
                <Card className="mt-2 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-foreground">
                      {verdictLabel(locale, check.visualComparison.verdict)}
                    </p>
                    <span className="text-xs text-muted-foreground">
                      {t(locale, "qualityLabel", { score: check.visualComparison.quality_assessment.score })} ·{" "}
                      {t(locale, "confidencePercentLabel", { pct: check.visualComparison.confidence })}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{check.visualComparison.summary}</p>
                </Card>
              </section>
            )}
          </div>

          <div className="space-y-6">
            <section>
              <SectionLabel>{t(locale, "amountLabel")}</SectionLabel>
              <Card className="mt-2 p-4 font-mono text-2xl font-semibold text-foreground">
                {check.amountCents === null
                  ? t(locale, "notSpecified")
                  : formatCurrency(locale, check.amountCents / 100, check.currency)}
              </Card>
            </section>
            <section>
              <SectionLabel>{t(locale, "reportDetailsLabel")}</SectionLabel>
              <Card className="mt-2 divide-y divide-border">
                <DetailRow icon={FileText} label={t(locale, "reportIdLabel")} value={check.humanId} mono />
                <DetailRow icon={MapPin} label={t(locale, "addressLabel")} value={check.customerAddress} />
                <DetailRow icon={ShieldCheck} label={t(locale, "signatureLabel3")} value={formatDateTime(locale, check.completedAt)} />
              </Card>
            </section>
          </div>
        </div>
      </Page>
      <div className="lg:hidden">
        <ActionBar width="wide">
          <Button
            size="lg"
            fullWidth
            icon={Share2}
            disabled={!pdfUrl}
            onClick={() => pdfUrl && window.open(pdfUrl, "_blank")}
          >
            {t(locale, "openSignedPdfBtn")}
          </Button>
        </ActionBar>
      </div>
    </>
  )
}

function DetailRow({
  icon: Icon,
  label,
  value,
  mono,
}: {
  icon: typeof MapPin
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-center gap-3 p-3.5">
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </span>
      <span className="flex-1 text-sm text-muted-foreground">{label}</span>
      <span className={"text-right text-sm font-medium text-foreground " + (mono ? "font-mono text-xs" : "")}>
        {value}
      </span>
    </div>
  )
}
