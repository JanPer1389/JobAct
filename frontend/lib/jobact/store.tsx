"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import type { VisualAuditResult } from "@/lib/jobact/api"
import {
  getStoredCurrency,
  getStoredLocale,
  setActiveDraftId,
  setStoredCurrency,
  setStoredLocale,
} from "@/lib/jobact/local-prefs"
import { saveDraft, type LocalMaterial } from "@/lib/jobact/local-store"
import type { AppCurrency, AppLocale } from "@/lib/jobact/i18n"

export type Screen =
  | "demoEntry"
  | "home"
  | "addCustomer"
  | "visitStart"
  | "gps"
  | "beforePhotos"
  | "notes"
  | "afterPhotos"
  | "analysisProcessing"
  | "reportDraft"
  | "editReport"
  | "signature"
  | "completed"
  | "checkDetail"

export interface NavParams {
  checkId?: string
  manual?: boolean
  [key: string]: unknown
}

interface Frame {
  screen: Screen
  params: NavParams
}

interface NavContext {
  frame: Frame
  stack: Frame[]
  navigate: (screen: Screen, params?: NavParams) => void
  replace: (screen: Screen, params?: NavParams) => void
  back: () => void
  reset: (screen: Screen, params?: NavParams) => void
  canGoBack: boolean
  // session-level draft state so the create flow feels connected; also
  // written through to IndexedDB (see the effect in `NavProvider`) so a
  // page reload can resume it.
  draft: DraftState
  setDraft: (patch: Partial<DraftState>) => void
  resetDraft: () => void
  userName: string
  setUserName: (name: string) => void
  locale: AppLocale
  setLocale: (locale: AppLocale) => void
  currency: AppCurrency
  setCurrency: (currency: AppCurrency) => void
}

export interface DraftState {
  id: string
  customerName: string
  customerAddress: string
  customerPhone: string
  customerServiceType: string
  gpsLat?: number
  gpsLon?: number
  gpsAccuracyM?: number
  // Local blob ids -- the backend never sees or stores these; the
  // backend derives readiness and the before/after comparison from
  // however many pairs are actually posted to `/demo/analyze`.
  beforePhotoAssets: DraftPhoto[]
  afterPhotoAssets: DraftPhoto[]
  rawNotes: string
  notesSource: "typed" | "voice"
  workCompleted: string
  materials: LocalMaterial[]
  amountCents: number | null
  currency: AppCurrency
  estimatedWorkUnits: number | null
  aiConfidence: "high" | "medium" | "low" | null
  visualComparison: VisualAuditResult | null
  amountConfirmed: boolean
  signed: boolean
  signerName: string | null
  pdfBlobId: string | null
  humanId: string | null
  completed: boolean
}

export interface DraftPhoto {
  assetId: string
  previewUrl: string
}

function newDraftId(): string {
  return crypto.randomUUID()
}

export function emptyDraft(): DraftState {
  return {
    id: newDraftId(),
    customerName: "",
    customerAddress: "",
    customerPhone: "",
    customerServiceType: "",
    beforePhotoAssets: [],
    afterPhotoAssets: [],
    rawNotes: "",
    notesSource: "typed",
    workCompleted: "",
    materials: [],
    amountCents: null,
    currency: "RUB",
    estimatedWorkUnits: null,
    aiConfidence: null,
    visualComparison: null,
    amountConfirmed: false,
    signed: false,
    signerName: null,
    pdfBlobId: null,
    humanId: null,
    completed: false,
  }
}

function humanReportId(id: string): string {
  return `JA-${id.slice(0, 8).toUpperCase()}`
}

const Ctx = createContext<NavContext | null>(null)

export function NavProvider({ children }: { children: ReactNode }) {
  const [stack, setStack] = useState<Frame[]>([{ screen: "demoEntry", params: {} }])
  const [draft, setDraftState] = useState<DraftState>(emptyDraft)
  const [userName, setUserNameState] = useState("")
  const [locale, setLocaleState] = useState<AppLocale>("ru-RU")
  const [currency, setCurrencyState] = useState<AppCurrency>("RUB")
  const hydrated = useRef(false)

  // Preferences live in localStorage; hydrate once on mount (SSR has no
  // localStorage, so the initial render always uses the ru-RU/RUB
  // defaults above, then the client immediately syncs to whatever was
  // saved last).
  useEffect(() => {
    if (hydrated.current) return
    hydrated.current = true
    setLocaleState(getStoredLocale())
    setCurrencyState(getStoredCurrency())
  }, [])

  const navigate = useCallback((screen: Screen, params: NavParams = {}) => {
    setStack((current) => [...current, { screen, params }])
  }, [])
  const replace = useCallback((screen: Screen, params: NavParams = {}) => {
    setStack((current) => [...current.slice(0, -1), { screen, params }])
  }, [])
  const back = useCallback(() => {
    setStack((current) =>
      current.length > 1 ? current.slice(0, -1) : current,
    )
  }, [])
  const reset = useCallback((screen: Screen, params: NavParams = {}) => {
    setStack([{ screen, params }])
  }, [])
  const setDraft = useCallback((patch: Partial<DraftState>) => {
    setDraftState((current) => ({ ...current, ...patch }))
  }, [])
  const resetDraft = useCallback(() => {
    setDraftState(emptyDraft())
  }, [])
  const setLocale = useCallback((next: AppLocale) => {
    setLocaleState(next)
    setStoredLocale(next)
  }, [])
  const setCurrency = useCallback((next: AppCurrency) => {
    setCurrencyState(next)
    setStoredCurrency(next)
  }, [])
  const setUserName = useCallback((name: string) => {
    setUserNameState(name)
  }, [])

  // Write-through persistence: every draft change is saved to IndexedDB
  // immediately, keyed by `frame.screen` as the resume point, so a page
  // reload mid-flow can restore exactly where the technician left off
  // (see `HomeScreen`'s "Продолжить черновик" and `demoEntry`'s resume
  // check). Only persists once the flow has actually started (customer
  // name set), so an untouched fresh draft never litters the store.
  const frame = stack[stack.length - 1]
  useEffect(() => {
    if (!draft.customerName.trim() || draft.completed) return
    setActiveDraftId(draft.id)
    void saveDraft({
      id: draft.id,
      screen: frame.screen,
      customerName: draft.customerName,
      customerAddress: draft.customerAddress,
      customerPhone: draft.customerPhone,
      customerServiceType: draft.customerServiceType,
      gpsLat: draft.gpsLat ?? null,
      gpsLon: draft.gpsLon ?? null,
      gpsAccuracyM: draft.gpsAccuracyM ?? null,
      beforePhotoIds: draft.beforePhotoAssets.map((p) => p.assetId),
      afterPhotoIds: draft.afterPhotoAssets.map((p) => p.assetId),
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
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, frame.screen])

  const value = useMemo<NavContext>(() => {
    return {
      frame,
      stack,
      canGoBack: stack.length > 1,
      navigate,
      replace,
      back,
      reset,
      draft,
      setDraft,
      resetDraft,
      userName,
      setUserName,
      locale,
      setLocale,
      currency,
      setCurrency,
    }
  }, [back, currency, draft, frame, locale, navigate, replace, reset, resetDraft, setDraft, setCurrency, setLocale, setUserName, stack, userName])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useNav() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useNav must be used within NavProvider")
  return ctx
}

export { humanReportId }
