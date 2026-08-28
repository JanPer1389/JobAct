"use client"

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import type { ReportResponse } from "@/lib/jobact/api"
import type { AppCurrency, AppLocale } from "@/lib/jobact/i18n"

export type Screen =
  | "splash"
  | "signin"
  | "home"
  | "customers"
  | "addCustomer"
  | "customerDetail"
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
  | "reports"
  | "reportDetail"
  | "offline"
  | "sync"
  | "profile"
  | "states"

export interface NavParams {
  customerId?: string
  reportId?: string
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
  // session-level draft state so the create flow feels connected
  draft: DraftState
  setDraft: (patch: Partial<DraftState>) => void
  session: Session | null
  setSession: (session: Session | null) => void
  locale: AppLocale
  setLocale: (locale: AppLocale) => void
  currency: AppCurrency
  setCurrency: (currency: AppCurrency) => void
}

export interface Session {
  user_id: string
  organization_id: string
  role: string
  locale: AppLocale
  currency: AppCurrency
}

export interface DraftState {
  customerId?: string
  customerName?: string
  address?: string
  gpsLat?: number
  gpsLon?: number
  gpsAccuracyM?: number
  // Real attached uploads -- the backend derives readiness and the
  // before/after comparison from these, not from a count.
  beforePhotoAssets: DraftPhoto[]
  afterPhotoAssets: DraftPhoto[]
  workCompleted: string
  amount: string
  signed: boolean
  visitId?: string
  reportId?: string
  revisionId?: string
  signatureAssetId?: string
  rawNotes: string
  report?: ReportResponse
}

export interface DraftPhoto {
  assetId: string
  previewUrl: string
}

const initialDraft: DraftState = {
  beforePhotoAssets: [],
  afterPhotoAssets: [],
  workCompleted: "",
  amount: "",
  signed: false,
  rawNotes: "",
}

const Ctx = createContext<NavContext | null>(null)

export function NavProvider({ children }: { children: ReactNode }) {
  const [stack, setStack] = useState<Frame[]>([{ screen: "splash", params: {} }])
  const [draft, setDraftState] = useState<DraftState>(initialDraft)
  const [session, setSession] = useState<Session | null>(null)
  const [locale, setLocale] = useState<AppLocale>("en-US")
  const [currency, setCurrency] = useState<AppCurrency>("RUB")

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

  const value = useMemo<NavContext>(() => {
    const frame = stack[stack.length - 1]
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
      session,
      setSession,
      locale,
      setLocale,
      currency,
      setCurrency,
    }
  }, [back, currency, draft, locale, navigate, replace, reset, session, setDraft, setSession, stack])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useNav() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useNav must be used within NavProvider")
  return ctx
}
