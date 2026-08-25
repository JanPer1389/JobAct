"use client"

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
} from "@/lib/jobact/data"
import { useNav } from "@/lib/jobact/store"

/* -------------------------- CUSTOMER DETAIL --------------------------- */

export function CustomerDetailScreen() {
  const { back, navigate, frame } = useNav()
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
            New report
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
                  <p className="text-xs text-muted-foreground">{customer.visits} visits on record</p>
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
                    <span className="text-foreground">Last visit {customer.lastVisit}</span>
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
              New report for this customer
            </Button>
          </div>

          {/* History */}
          <section className="lg:order-1 lg:col-span-2">
            <SectionLabel>Visit history</SectionLabel>
            {history.length === 0 ? (
              <EmptyState icon={FileText} title="No visits yet" description="Create the first report for this customer." />
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
  const { back, frame } = useNav()
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
                <DetailRow icon={Calendar} label="Date" value={report.date} />
                <DetailRow icon={Clock} label="Time" value={report.time} />
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
                    <p className="text-xs text-muted-foreground">{report.date} · {report.time}</p>
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
