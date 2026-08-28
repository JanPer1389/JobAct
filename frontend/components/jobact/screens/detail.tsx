"use client"

import { useEffect, useState } from "react"

import {
  MapPin,
  Phone,
  Calendar,
  Clock,
  Share2,
  Download,
  User,
  ShieldCheck,
  Plus,
  FileText,
} from "lucide-react"
import {
  Button,
  Card,
  ScreenHeader,
  SectionLabel,
  StatusBadge,
  SyncIndicator,
  PhotoThumb,
  EmptyState,
} from "../ui"
import { Page, ActionBar } from "../shell"
import { Avatar, ReportCard, customerInitials } from "../cards"
import {
  customers as allCustomers,
  reports as allReports,
  currency,
  type ReportStatus,
} from "@/lib/jobact/data"
import { useNav } from "@/lib/jobact/store"
import { apiFetch, type ReportResponse } from "@/lib/jobact/api"
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatTime,
  statusLabel,
  syncLabel,
  t,
  tPlural,
  verdictLabel,
} from "@/lib/jobact/i18n"

/* -------------------------- CUSTOMER DETAIL --------------------------- */

export function CustomerDetailScreen() {
  const { back, navigate, frame, locale } = useNav()
  const customer = allCustomers.find((c) => c.id === frame.params.customerId) ?? allCustomers[0]
  const history = allReports.filter((r) => r.customerId === customer.id)

  return (
    <>
      <ScreenHeader
        title={customer.name}
        subtitle={customer.type}
        onBack={back}
        width="wide"
        right={
          <Button
            icon={Plus}
            className="hidden lg:inline-flex"
            onClick={() => navigate("visitStart", { customerId: customer.id })}
          >
            {t(locale, "newReport")}
          </Button>
        }
      />
      <Page width="wide">
        <div className="grid gap-6 lg:grid-cols-3 lg:gap-8">
          {/* Contact panel */}
          <div className="lg:order-2 lg:col-span-1">
            <Card className="p-4 lg:p-5">
              <div className="flex items-center gap-3">
                <Avatar initials={customerInitials(customer.name)} className="size-12 rounded-2xl text-base" />
                <div className="min-w-0 flex-1">
                  <p className="text-base font-semibold text-foreground">{customer.name}</p>
                  <p className="text-xs text-muted-foreground">{tPlural(locale, "visitsOnRecord", customer.visits)}</p>
                </div>
              </div>
              <div className="mt-4 space-y-2.5 text-sm">
                <div className="flex items-start gap-2.5 text-muted-foreground">
                  <MapPin className="mt-0.5 size-4 shrink-0" />
                  <span className="text-foreground">{customer.address}</span>
                </div>
                <div className="flex items-center gap-2.5 text-muted-foreground">
                  <Phone className="size-4 shrink-0" />
                  <span className="text-foreground">{customer.phone}</span>
                </div>
                {customer.lastVisit && (
                  <div className="flex items-center gap-2.5 text-muted-foreground">
                    <Calendar className="size-4 shrink-0" />
                    <span className="text-foreground">{t(locale, "lastVisitLabel", { date: formatDate(locale, customer.lastVisit) })}</span>
                  </div>
                )}
              </div>
            </Card>

            <Button
              size="lg"
              fullWidth
              icon={Plus}
              className="mt-4 lg:hidden"
              onClick={() => navigate("visitStart", { customerId: customer.id })}
            >
              {t(locale, "newReportForCustomer")}
            </Button>
          </div>

          {/* History */}
          <section className="lg:order-1 lg:col-span-2">
            <SectionLabel>{t(locale, "visitHistoryLabel")}</SectionLabel>
            {history.length === 0 ? (
              <EmptyState icon={FileText} title={t(locale, "noVisitsYet")} description={t(locale, "noVisitsYetDesc")} />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {history.map((r) => (
                  <ReportCard key={r.id} report={r} onClick={() => navigate("reportDetail", { reportId: r.id })} />
                ))}
              </div>
            )}
          </section>
        </div>
      </Page>
    </>
  )
}

/* --------------------------- REPORT DETAIL ---------------------------- */

export function ReportDetailScreen() {
  const { back, frame, locale } = useNav()
  const report = allReports.find((r) => r.id === frame.params.reportId) ?? allReports[0]

  return (
    <>
      <ScreenHeader
        title={report.customerName}
        subtitle={report.id}
        onBack={back}
        width="wide"
        right={
          <div className="flex items-center gap-3">
            <StatusBadge status={report.status} />
            <div className="hidden gap-2 lg:flex">
              <Button variant="secondary" icon={Download}>
                Export PDF
              </Button>
              <Button icon={Share2}>Share</Button>
            </div>
          </div>
        }
      />
      <Page width="wide">
        <div className="grid gap-6 lg:grid-cols-3 lg:gap-8">
          {/* Main column */}
          <div className="space-y-6 lg:col-span-2">
            <section>
              <SectionLabel>Work completed</SectionLabel>
              <Card className="p-4 lg:p-5">
                <p className="text-sm leading-relaxed text-foreground">{report.workCompleted}</p>
              </Card>
            </section>

            {report.materials.length > 0 && (
              <section>
                <SectionLabel>Materials / consumables</SectionLabel>
                <Card className="divide-y divide-border">
                  {report.materials.map((m) => (
                    <div key={m.id} className="flex items-center justify-between p-3.5 text-sm">
                      <span className="text-foreground">{m.label}</span>
                      <span className="text-muted-foreground">×{m.qty}</span>
                    </div>
                  ))}
                </Card>
              </section>
            )}

            <section>
              <SectionLabel>Before photos ({report.beforePhotos})</SectionLabel>
              <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-4 xl:grid-cols-5">
                {Array.from({ length: report.beforePhotos }).map((_, i) => (
                  <PhotoThumb key={i} tone="before" index={i + 1} />
                ))}
              </div>
            </section>

            <section>
              <SectionLabel>After photos ({report.afterPhotos})</SectionLabel>
              {report.afterPhotos === 0 ? (
                <Card className="p-4 text-sm text-muted-foreground">No after photos captured yet.</Card>
              ) : (
                <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-4 xl:grid-cols-5">
                  {Array.from({ length: report.afterPhotos }).map((_, i) => (
                    <PhotoThumb key={i} tone="after" index={i + 1} />
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* Side column */}
          <div className="space-y-6">
            <section>
              <SectionLabel>Amount</SectionLabel>
              <Card className="flex items-center justify-between p-4">
                <span className="text-sm text-muted-foreground">Total charged</span>
                <span className="font-mono text-2xl font-semibold text-foreground">
                  {currency(report.amount)}
                </span>
              </Card>
            </section>

            <section>
              <SectionLabel>Visit details</SectionLabel>
              <Card className="divide-y divide-border">
                <DetailRow icon={User} label="Technician" value={report.technician} />
                <DetailRow icon={MapPin} label="Address" value={report.address} />
                <DetailRow icon={Calendar} label="Date" value={formatDate(locale, report.visitedAt)} />
                <DetailRow icon={Clock} label="Time" value={formatTime(locale, report.visitedAt)} />
                <DetailRow icon={MapPin} label="Coordinates" value={report.coords} mono />
              </Card>
            </section>

            <section>
              <SectionLabel>Customer signature</SectionLabel>
              <Card className="flex items-center gap-3 p-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
                  <ShieldCheck className="size-5" />
                </span>
                {report.signed ? (
                  <div>
                    <p className="text-sm font-medium text-foreground">Signed on-site</p>
                    <p className="text-xs text-muted-foreground">{formatDateTime(locale, report.visitedAt)}</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium text-foreground">Awaiting signature</p>
                    <p className="text-xs text-muted-foreground">A signing link was sent to the customer.</p>
                  </div>
                )}
              </Card>
            </section>

            <div className="flex items-center justify-between px-1">
              <span className="text-xs text-muted-foreground">Sync status</span>
              <SyncIndicator state={report.sync} />
            </div>
          </div>
        </div>
      </Page>

      {/* Actions live in the header on desktop */}
      <div className="lg:hidden">
        <ActionBar width="wide">
          <div className="flex gap-3">
            <Button variant="secondary" size="lg" fullWidth icon={Download}>
              Export PDF
            </Button>
            <Button size="lg" fullWidth icon={Share2}>
              Share
            </Button>
          </div>
        </ActionBar>
      </div>
    </>
  )
}

export function BackendReportDetailScreen() {
  const { back, frame, locale } = useNav()
  const reportId = frame.params.reportId as string
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    apiFetch<ReportResponse>(`/api/v1/reports/${reportId}`)
      .then((nextReport) => {
        if (!cancelled) setReport(nextReport)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : t(locale, "couldNotLoadReport"))
      })
    return () => { cancelled = true }
  }, [reportId, locale])

  if (!report) {
    return (
      <>
        <ScreenHeader title={t(locale, "reportTitleFallback")} subtitle={reportId} onBack={back} width="wide" />
        <Page width="wide"><Card className="p-5 text-sm text-muted-foreground">{error ?? t(locale, "loadingReportEllipsis")}</Card></Page>
      </>
    )
  }

  const revision = report.current_revision
  return (
    <>
      <ScreenHeader
        title={report.human_id}
        subtitle={t(locale, "revisionNumberLabel", { n: revision.revision_no })}
        onBack={back}
        width="wide"
        right={<StatusBadge status={report.status as ReportStatus} />}
      />
      <Page width="wide">
        <div className="grid gap-6 lg:grid-cols-3 lg:gap-8">
          <div className="space-y-6 lg:col-span-2">
            <section>
              <SectionLabel>{t(locale, "workCompletedLabel")}</SectionLabel>
              <Card className="mt-2 p-5 text-sm leading-relaxed text-foreground">{revision.work_completed}</Card>
            </section>
            {revision.materials.length > 0 && (
              <section>
                <SectionLabel>{t(locale, "materialsLabel")}</SectionLabel>
                <Card className="mt-2 divide-y divide-border">
                  {revision.materials.map((material) => (
                    <div key={`${material.label}-${material.qty}`} className="flex justify-between p-3.5 text-sm">
                      <span>{material.label}</span><span className="text-muted-foreground">×{material.qty}</span>
                    </div>
                  ))}
                </Card>
              </section>
            )}
            <section>
              <SectionLabel>{t(locale, "beforeAfterComparisonLabel")}</SectionLabel>
              {revision.visual_comparison === null ? (
                <Card className="mt-2 p-4 text-sm text-muted-foreground">
                  {t(locale, "noPhotoComparisonMessage")}
                </Card>
              ) : (
                <Card className="mt-2 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-foreground">
                      {verdictLabel(locale, revision.visual_comparison.verdict)}
                    </p>
                    <span className="text-xs text-muted-foreground">
                      {t(locale, "qualityLabel", { score: revision.visual_comparison.quality_assessment.score })} ·{" "}
                      {t(locale, "confidencePercentLabel", { pct: revision.visual_comparison.confidence })}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {revision.visual_comparison.summary}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {t(locale, "priceLabel", { verdict: verdictLabel(locale, revision.visual_comparison.price_assessment.price_verdict) })}
                  </p>
                </Card>
              )}
            </section>
          </div>
          <div className="space-y-6">
            <section>
              <SectionLabel>{t(locale, "amountLabel")}</SectionLabel>
              <Card className="mt-2 p-4 font-mono text-2xl font-semibold text-foreground">
                {revision.amount_cents === null
                  ? t(locale, "notSpecified")
                  : formatCurrency(locale, revision.amount_cents / 100, revision.currency)}
              </Card>
            </section>
            <section>
              <SectionLabel>{t(locale, "reportDetailsLabel")}</SectionLabel>
              <Card className="mt-2 divide-y divide-border">
                <DetailRow icon={FileText} label={t(locale, "reportIdLabel")} value={report.human_id} mono />
                <DetailRow icon={Calendar} label={t(locale, "revisionLabel")} value={String(revision.revision_no)} />
                <DetailRow icon={ShieldCheck} label={t(locale, "workflowLabel")} value={report.workflow_state ?? report.status} />
                <DetailRow icon={ShieldCheck} label={t(locale, "signatureLabel3")} value={report.signed_at ? new Date(report.signed_at).toLocaleString(locale) : t(locale, "awaitingSignature")} />
              </Card>
            </section>
          </div>
        </div>
      </Page>
    </>
  )
}

function DetailRow({
  icon: Icon,
  label,
  value,
  mono,
}: {
  icon: typeof User
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
