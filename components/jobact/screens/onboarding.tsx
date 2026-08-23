"use client"

import { useEffect, useState } from "react"
import { ArrowRight, Camera, MapPin, Mic, ShieldCheck } from "lucide-react"
import { Button, Input } from "../ui"
import { useNav } from "@/lib/jobact/store"

export function Logo({ size = "md" }: { size?: "md" | "lg" }) {
  const s = size === "lg" ? "size-16 rounded-3xl" : "size-11 rounded-2xl"
  return (
    <div className={`grid ${s} place-items-center border border-white/10 bg-gradient-to-br from-elevated to-background shadow-inner`}>
      <svg viewBox="0 0 24 24" className={size === "lg" ? "size-8" : "size-6"} fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    </div>
  )
}

export function SplashScreen() {
  const { replace } = useNav()
  useEffect(() => {
    const t = setTimeout(() => replace("signin"), 1600)
    return () => clearTimeout(t)
  }, [replace])

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-background">
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
  const { reset } = useNav()
  const [step, setStep] = useState<"intro" | "form">("intro")

  if (step === "intro") {
    return (
      <div className="flex flex-1 flex-col justify-between px-6 pb-10 pt-10">
        <div>
          <Logo />
          <h1 className="mt-8 text-3xl font-semibold leading-tight tracking-tight text-foreground text-balance">
            Undeniable proof of every visit.
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground text-pretty">
            Capture photos, location, and a signed report on-site — so a completed
            job can never be disputed.
          </p>
          <ul className="mt-8 space-y-4">
            {[
              { icon: Camera, text: "Before & after photos, timestamped" },
              { icon: MapPin, text: "Automatic GPS location on arrival" },
              { icon: Mic, text: "Describe the work by voice, not typing" },
              { icon: ShieldCheck, text: "Customer signature, archived as proof" },
            ].map((f) => (
              <li key={f.text} className="flex items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-border bg-card text-foreground">
                  <f.icon className="size-5" />
                </span>
                <span className="text-sm text-foreground">{f.text}</span>
              </li>
            ))}
          </ul>
        </div>
        <Button size="lg" fullWidth iconRight={ArrowRight} onClick={() => setStep("form")}>
          Get started
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col justify-between px-6 pb-10 pt-12">
      <div>
        <Logo />
        <h1 className="mt-8 text-2xl font-semibold tracking-tight text-foreground">
          Sign in to JobAct
        </h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Use your work email to continue.
        </p>
        <form
          className="mt-8 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            reset("home")
          }}
        >
          <Input
            id="email"
            label="Work email"
            type="email"
            placeholder="you@company.com"
            defaultValue="marco@reyesclimate.com"
            autoComplete="email"
          />
          <Input
            id="password"
            label="Password"
            type="password"
            placeholder="Your password"
            defaultValue="password"
            autoComplete="current-password"
          />
          <Button size="lg" fullWidth type="submit" className="mt-2">
            Sign in
          </Button>
        </form>
      </div>
      <p className="text-center text-xs text-muted-foreground">
        New team?{" "}
        <button onClick={() => reset("home")} className="font-medium text-foreground underline underline-offset-4">
          Create a workspace
        </button>
      </p>
    </div>
  )
}
