"use client"

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import type { ReportResponse, VisualAuditAttemptResponse } from "@/lib/jobact/api"

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
  | "voice"
  | "voiceProcessing"
  | "afterPhotos"
  | "auditProcessing"
  | "auditResult"
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
}

export interface Session {
  user_id: string
  organization_id: string
  role: string
}

export interface DraftState {
  customerId?: string
  customerName?: string
  address?: string
  beforePhotos: number
  afterPhotos: number
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
  audit?: VisualAuditAttemptResponse
}

export interface DraftPhoto {
  assetId: string
  previewUrl: string
}

const initialDraft: DraftState = {
  beforePhotos: 0,
  afterPhotos: 0,
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
    }
  }, [back, draft, navigate, replace, reset, session, setDraft, setSession, stack])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useNav() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useNav must be used within NavProvider")
  return ctx
}
