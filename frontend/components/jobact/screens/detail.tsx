"use client"

import {
  MapPin,
  Phone,
  Calendar,
  Clock,
  Camera,
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
import { Scroll } from "../shell"
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
      <ScreenHeader title={customer.name} subtitle={customer.type} onBack={back} />
      <Scroll className="px-5 py-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <Avatar initials={customerInitials(customer.name)} className="size-12 rounded-2xl text-base" />
            <div className="min-w-0 flex-1">
              <p className="text-base font-semibold text-foreground">{customer.name}</p>
              <p className="text-xs text-muted-foreground">{customer.visits} visits on record</p>
            </div>
          </div>
          <div className="mt-4 space-y-2.5 text-sm">
            <div className="flex items-center gap-2.5 text-muted-foreground">
              <MapPin className="size-4 shrink-0" /> <span className="text-foreground">{customer.address}</span>
            </div>
            <div className="flex items-center gap-2.5 text-muted-foreground">
              <Phone className="size-4 shrink-0" /> <span className="text-foreground">{customer.phone}</span>
            </div>
          </div>
        </Card>

        <Button size="lg" fullWidth icon={Plus} className="mt-4" onClick={() => navigate("visitStart", { customerId: customer.id })}>
          New report for this customer
        </Button>

        <section className="mt-7">
          <SectionLabel>Visit history</SectionLabel>
          {history.length === 0 ? (
            <EmptyState icon={FileText} title="No visits yet" description="Create the first report for this customer." />
          ) : (
            <div className="space-y-2.5">
              {history.map((r) => (
                <ReportCard key={r.id} report={r} onClick={() => navigate("reportDetail", { reportId: r.id })} />
              ))}
            </div>
          )}
        </section>
      </Scroll>
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
        right={<StatusBadge status={report.status} />}
      />
      <Scroll className="px-5 py-4">
        {/* Meta grid */}
        <Card className="divide-y divide-border">
          <DetailRow icon={User} label="Technician" value={report.technician} />
          <DetailRow icon={MapPin} label="Address" value={report.address} />
          <DetailRow icon={Calendar} label="Date" value={report.date} />
          <DetailRow icon={Clock} label="Time" value={report.time} />
          <DetailRow icon={MapPin} label="Coordinates" value={report.coords} mono />
        </Card>

        <section className="mt-6">
          <SectionLabel>Work completed</SectionLabel>
          <Card className="p-4">
            <p className="text-sm leading-relaxed text-foreground">{report.workCompleted}</p>
          </Card>
        </section>

        {report.materials.length > 0 && (
          <section className="mt-6">
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

        <section className="mt-6">
          <SectionLabel>Amount</SectionLabel>
          <Card className="flex items-center justify-between p-4">
            <span className="text-sm text-muted-foreground">Total charged</span>
            <span className="font-mono text-2xl font-semibold text-foreground">{currency(report.amount)}</span>
          </Card>
        </section>

        <section className="mt-6">
          <SectionLabel>Before photos ({report.beforePhotos})</SectionLabel>
          <div className="grid grid-cols-3 gap-2.5">
            {Array.from({ length: report.beforePhotos }).map((_, i) => (
              <PhotoThumb key={i} tone="before" index={i + 1} />
            ))}
          </div>
        </section>

        <section className="mt-6">
          <SectionLabel>After photos ({report.afterPhotos})</SectionLabel>
          {report.afterPhotos === 0 ? (
            <Card className="p-4 text-sm text-muted-foreground">No after photos captured yet.</Card>
          ) : (
            <div className="grid grid-cols-3 gap-2.5">
              {Array.from({ length: report.afterPhotos }).map((_, i) => (
                <PhotoThumb key={i} tone="after" index={i + 1} />
              ))}
            </div>
          )}
        </section>

        <section className="mt-6">
          <SectionLabel>Customer signature</SectionLabel>
          <Card className="flex items-center gap-3 p-4">
            <span className="grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground">
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

        <div className="mt-4 flex items-center justify-between px-1">
          <span className="text-xs text-muted-foreground">Sync status</span>
          <SyncIndicator state={report.sync} />
        </div>
      </Scroll>

      <div className="shrink-0 border-t border-border bg-background/80 px-5 pb-8 pt-3 backdrop-blur-xl">
        <div className="flex gap-3">
          <Button variant="secondary" size="lg" fullWidth icon={Download}>
            Export PDF
          </Button>
          <Button size="lg" fullWidth icon={Share2}>
            Share
          </Button>
        </div>
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
      <span className="grid size-9 place-items-center rounded-xl bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </span>
      <span className="flex-1 text-sm text-muted-foreground">{label}</span>
      <span className={"text-sm font-medium text-foreground " + (mono ? "font-mono text-xs" : "")}>{value}</span>
    </div>
  )
}
