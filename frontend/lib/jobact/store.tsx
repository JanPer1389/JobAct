"use client"

import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"

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
  workCompleted: string
  amount: string
  signed: boolean
}

const initialDraft: DraftState = {
  beforePhotos: 0,
  afterPhotos: 0,
  workCompleted: "",
  amount: "",
  signed: false,
}

const Ctx = createContext<NavContext | null>(null)

export function NavProvider({ children }: { children: ReactNode }) {
  const [stack, setStack] = useState<Frame[]>([{ screen: "splash", params: {} }])
  const [draft, setDraftState] = useState<DraftState>(initialDraft)
  const [session, setSession] = useState<Session | null>(null)

  const value = useMemo<NavContext>(() => {
    const frame = stack[stack.length - 1]
    return {
      frame,
      stack,
      canGoBack: stack.length > 1,
      navigate: (screen, params = {}) =>
        setStack((s) => [...s, { screen, params }]),
      replace: (screen, params = {}) =>
        setStack((s) => [...s.slice(0, -1), { screen, params }]),
      back: () => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)),
      reset: (screen, params = {}) => setStack([{ screen, params }]),
      draft,
      setDraft: (patch) => setDraftState((d) => ({ ...d, ...patch })),
      session,
      setSession,
    }
  }, [stack, draft, session])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useNav() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error("useNav must be used within NavProvider")
  return ctx
}
