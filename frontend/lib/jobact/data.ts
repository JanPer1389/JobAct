export type Role = "technician" | "owner"

export type ReportStatus = "draft" | "unsigned" | "completed" | "offline"

export type SyncState = "synced" | "pending" | "syncing" | "failed" | "offline"

export interface Customer {
  id: string
  name: string
  address: string
  phone: string
  type: string
  visits: number
  /** ISO 8601 date (no time) -- render with `formatDate`. */
  lastVisit: string | null
}

export interface Material {
  id: string
  label: string
  qty: string
}

export interface Report {
  id: string
  customerId: string
  customerName: string
  address: string
  technician: string
  /** ISO 8601 visit timestamp -- render with `formatDate`/`formatTime` from
   *  `lib/jobact/i18n`, never as a pre-formatted string, so it follows the
   *  selected interface language. */
  visitedAt: string
  location: string
  coords: string
  workCompleted: string
  materials: Material[]
  amount: number
  beforePhotos: number
  afterPhotos: number
  status: ReportStatus
  sync: SyncState
  signed: boolean
}

export const CURRENT_USER = {
  name: "Marco Reyes",
  role: "owner" as Role,
  company: "Reyes Climate & Repair",
  initials: "MR",
}

export const customers: Customer[] = [
  {
    id: "c1",
    name: "Aurora Dental Clinic",
    address: "142 Larkspur Ave, Unit 4",
    phone: "+1 (415) 555-0142",
    type: "AC maintenance",
    visits: 7,
    lastVisit: "2026-08-14",
  },
  {
    id: "c2",
    name: "Northside Apartments",
    address: "88 Beacon St",
    phone: "+1 (415) 555-0188",
    type: "Pool service",
    visits: 12,
    lastVisit: "2026-08-19",
  },
  {
    id: "c3",
    name: "Ferrer Residence",
    address: "23 Cypress Hollow Rd",
    phone: "+1 (415) 555-0223",
    type: "HVAC repair",
    visits: 3,
    lastVisit: "2026-07-30",
  },
  {
    id: "c4",
    name: "Bright Bean Cafe",
    address: "551 Market St",
    phone: "+1 (415) 555-0551",
    type: "Cleaning",
    visits: 21,
    lastVisit: "2026-08-20",
  },
  {
    id: "c5",
    name: "Harbor View Offices",
    address: "9 Quay Terrace, Floor 2",
    phone: "+1 (415) 555-0099",
    type: "Installation",
    visits: 1,
    lastVisit: "2026-06-12",
  },
]

export const reports: Report[] = [
  {
    id: "JA-2026-0481",
    customerId: "c4",
    customerName: "Bright Bean Cafe",
    address: "551 Market St",
    technician: "Marco Reyes",
    visitedAt: "2026-08-20T09:42:00",
    location: "551 Market St, San Francisco",
    coords: "37.7897, -122.4001",
    workCompleted:
      "Deep-cleaned espresso machine group heads and backflushed all three lines. Descaled boiler and replaced two worn gaskets. Sanitized steam wands and calibrated grind settings.",
    materials: [
      { id: "m1", label: "Group head gaskets", qty: "2" },
      { id: "m2", label: "Descaling solution", qty: "1 bottle" },
    ],
    amount: 185,
    beforePhotos: 2,
    afterPhotos: 3,
    status: "completed",
    sync: "synced",
    signed: true,
  },
  {
    id: "JA-2026-0480",
    customerId: "c2",
    customerName: "Northside Apartments",
    address: "88 Beacon St",
    technician: "Diego Salas",
    visitedAt: "2026-08-19T14:10:00",
    location: "88 Beacon St, San Francisco",
    coords: "37.7921, -122.3968",
    workCompleted:
      "Balanced pool chemistry, added chlorine and pH adjuster. Cleared skimmer baskets and backwashed the sand filter. Checked pump pressure.",
    materials: [
      { id: "m1", label: "Chlorine tablets", qty: "6" },
      { id: "m2", label: "pH minus", qty: "2 kg" },
    ],
    amount: 120,
    beforePhotos: 3,
    afterPhotos: 3,
    status: "completed",
    sync: "synced",
    signed: true,
  },
  {
    id: "JA-2026-0479",
    customerId: "c1",
    customerName: "Aurora Dental Clinic",
    address: "142 Larkspur Ave, Unit 4",
    technician: "Marco Reyes",
    visitedAt: "2026-08-14T11:05:00",
    location: "142 Larkspur Ave, San Francisco",
    coords: "37.7833, -122.4090",
    workCompleted:
      "Replaced clogged condensate drain line and cleared the trap. Cleaned evaporator coils and swapped the return-air filter. Verified cooling at 18°C output.",
    materials: [{ id: "m1", label: "Air filter 20x25", qty: "1" }],
    amount: 240,
    beforePhotos: 2,
    afterPhotos: 2,
    status: "completed",
    sync: "synced",
    signed: true,
  },
  {
    id: "JA-2026-0482",
    customerId: "c3",
    customerName: "Ferrer Residence",
    address: "23 Cypress Hollow Rd",
    technician: "Marco Reyes",
    visitedAt: "2026-08-22T08:20:00",
    location: "23 Cypress Hollow Rd, San Francisco",
    coords: "37.7710, -122.4330",
    workCompleted:
      "Diagnosed intermittent compressor fault. Replaced start capacitor and cleaned contactor points.",
    materials: [{ id: "m1", label: "Start capacitor 45µF", qty: "1" }],
    amount: 160,
    beforePhotos: 2,
    afterPhotos: 0,
    status: "draft",
    sync: "pending",
    signed: false,
  },
  {
    id: "JA-2026-0478",
    customerId: "c5",
    customerName: "Harbor View Offices",
    address: "9 Quay Terrace, Floor 2",
    technician: "Diego Salas",
    visitedAt: "2026-08-12T16:45:00",
    location: "9 Quay Terrace, San Francisco",
    coords: "37.7955, -122.3936",
    workCompleted:
      "Installed two wall-mounted split units and ran refrigerant lines. Pressure-tested and vacuumed the system before charging.",
    materials: [
      { id: "m1", label: "Split unit 12k BTU", qty: "2" },
      { id: "m2", label: "Copper line set", qty: "8 m" },
    ],
    amount: 1450,
    beforePhotos: 3,
    afterPhotos: 4,
    status: "unsigned",
    sync: "offline",
    signed: false,
  },
]

export const teamMembers = [
  { id: "t1", name: "Marco Reyes", role: "owner" as Role, initials: "MR", visitsToday: 2 },
  { id: "t2", name: "Diego Salas", role: "technician" as Role, initials: "DS", visitsToday: 3 },
  { id: "t3", name: "Priya Nair", role: "technician" as Role, initials: "PN", visitsToday: 1 },
]

export function currency(n: number) {
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 0 })
}
