"use client"

import { useEffect, useState } from "react"
import { ArrowRight, Camera, MapPin, Mic, ShieldCheck } from "lucide-react"
import { Button, Card, Logo } from "../ui"
import { apiFetch } from "@/lib/jobact/api"
import { useNav, type Session } from "@/lib/jobact/store"

export { Logo }

const features = [
  { icon: Camera, text: "Before & after photos, timestamped" },
  { icon: MapPin, text: "Automatic GPS location on arrival" },
  { icon: Mic, text: "Describe the work by voice, not typing" },
  { icon: ShieldCheck, text: "Customer signature, archived as proof" },
]

export function SplashScreen() {
  const { replace, setSession } = useNav()
  useEffect(() => {
    let cancelled = false

    apiFetch<Session>("/api/v1/auth/session")
      .then((session) => {
        if (cancelled) return
        setSession(session)
        replace("home")
      })
      .catch(() => {
        if (cancelled) return
        setSession(null)
        replace("signin")
      })

    return () => {
      cancelled = true
    }
  }, [replace, setSession])

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center bg-background">
      <div className="animate-in fade-in zoom-in duration-700">
        <Logo size="lg" />
      </div>
      <h1 className="mt-6 text-2xl font-semibold tracking-tight text-foreground">JobAct</h1>
      <p className="mt-1.5 text-sm text-muted-foreground">Proof of work, in 2 minutes</p>
      <div className="absolute bottom-16 flex items-center gap-2 text-xs text-muted-foreground">
        <div className="size-1.5 animate-pulse rounded-full bg-muted-foreground" />
        Loading your workspace
      </div>
    </div>
  )
}

export function SignInScreen() {
  const [step, setStep] = useState<"intro" | "form">("intro")

  if (step === "intro") {
    return (
      <div className="thin-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto">
        <div className="m-auto flex w-full max-w-5xl flex-col justify-between gap-10 px-6 pb-10 pt-10 lg:grid lg:grid-cols-2 lg:items-center lg:gap-16 lg:px-10 lg:py-16">
          <div>
            <Logo />
            <h1 className="mt-8 text-3xl font-semibold leading-tight tracking-tight text-foreground text-balance lg:mt-10 lg:text-5xl">
              Undeniable proof of every visit.
            </h1>
            <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground text-pretty lg:mt-5 lg:max-w-md lg:text-lg">
              Capture photos, location, and a signed report on-site — so a completed job can never be
              disputed.
            </p>
          </div>

          <Card className="p-6 lg:p-8">
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
              What every report carries
            </p>
            <ul className="mt-5 space-y-4">
              {features.map((f) => (
                <li key={f.text} className="flex items-center gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-elevated text-foreground">
                    <f.icon className="size-5" />
                  </span>
                  <span className="text-sm text-foreground">{f.text}</span>
                </li>
              ))}
            </ul>
            <Button
              size="lg"
              fullWidth
              iconRight={ArrowRight}
              className="mt-7"
              onClick={() => setStep("form")}
            >
              Get started
            </Button>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="thin-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="m-auto flex w-full max-w-md flex-col justify-center px-6 pb-10 pt-12 lg:py-16">
        <div className="lg:rounded-2xl lg:border lg:border-border lg:bg-card lg:p-8">
          <Logo />
          <h1 className="mt-8 text-2xl font-semibold tracking-tight text-foreground">
            Sign in to JobAct
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">Use your work email to continue.</p>
          <Button
            size="lg"
            fullWidth
            className="mt-8"
            onClick={() => window.location.assign("/api/v1/auth/google/start")}
          >
            Continue with Google
          </Button>
        </div>
        <p className="mt-8 text-center text-xs text-muted-foreground">
          Your workspace is selected from your Google account.
        </p>
      </div>
    </div>
  )
}
