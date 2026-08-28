"use client"

import { useEffect, useState, type FormEvent } from "react"
import { Camera, LoaderCircle, MapPin, Mic, ShieldCheck } from "lucide-react"
import { Button, Card, Input, Logo } from "../ui"
import { apiFetch, JobActApiError } from "@/lib/jobact/api"
import { useNav, type Session } from "@/lib/jobact/store"

export { Logo }

const features = [
  { icon: Camera, text: "Before & after photos, timestamped" },
  { icon: MapPin, text: "Automatic GPS location on arrival" },
  { icon: Mic, text: "Describe the work by voice, not typing" },
  { icon: ShieldCheck, text: "Customer signature, archived as proof" },
]

export function SplashScreen() {
  const { replace, setLocale, setSession } = useNav()
  useEffect(() => {
    let cancelled = false

    apiFetch<Session>("/api/v1/auth/session")
      .then((session) => {
        if (cancelled) return
        setSession(session)
        setLocale(session.locale)
        const linkingResult = new URLSearchParams(window.location.search).get("auth_link")
        replace(linkingResult ? "profile" : "home")
      })
      .catch(() => {
        if (cancelled) return
        setSession(null)
        replace("signin")
      })

    return () => {
      cancelled = true
    }
  }, [replace, setLocale, setSession])

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

type AuthMode = "register" | "login"

export function SignInScreen() {
  const { reset, setLocale, setSession } = useNav()
  const [mode, setMode] = useState<AuthMode>("register")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [repeatPassword, setRepeatPassword] = useState("")
  const [emailError, setEmailError] = useState("")
  const [passwordError, setPasswordError] = useState("")
  const [repeatError, setRepeatError] = useState("")
  const [submitError, setSubmitError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const authError = new URLSearchParams(window.location.search).get("auth_error")
    if (authError === "google-link-required") {
      setMode("login")
      setSubmitError(
        "An account already uses that email. Sign in first, then link Google from Account security.",
      )
      window.history.replaceState({}, "", window.location.pathname)
    }
  }, [])

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode)
    setEmailError("")
    setPasswordError("")
    setRepeatError("")
    setSubmitError("")
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedEmail = email.trim()
    const malformedEmail = !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)
    const invalidPassword = mode === "register" && (password.length < 12 || password.length > 128)
    const mismatch = mode === "register" && password !== repeatPassword
    setEmailError(malformedEmail ? "Enter a valid email address." : "")
    setPasswordError(invalidPassword ? "Use 12–128 characters." : "")
    setRepeatError(mismatch ? "Passwords do not match." : "")
    setSubmitError("")
    if (malformedEmail || invalidPassword || mismatch) return

    setSubmitting(true)
    try {
      const session = await apiFetch<Session>(
        mode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/login",
        {
          method: "POST",
          body: JSON.stringify(
            mode === "register"
              ? { email: normalizedEmail, password, repeat_password: repeatPassword }
              : { email: normalizedEmail, password },
          ),
        },
      )
      setSession(session)
      setLocale(session.locale)
      reset("home")
    } catch (error) {
      if (error instanceof JobActApiError) {
        const errors = error.response.errors
        const messageFor = (field: string) =>
          errors.find((item) => item.loc.at(-1) === field)?.message
        setEmailError(messageFor("email") ?? "")
        setPasswordError(messageFor("password") ?? "")
        setRepeatError(messageFor("repeat_password") ?? "")
        setSubmitError(
          errors.length > 0 && (messageFor("email") || messageFor("password") || messageFor("repeat_password"))
            ? ""
            : error.response.detail,
        )
      } else {
        setSubmitError("Authentication is unavailable. Please try again.")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="thin-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="m-auto grid w-full max-w-5xl gap-10 px-6 py-10 lg:grid-cols-2 lg:items-center lg:gap-16 lg:px-10 lg:py-16">
        <div>
          <Logo />
          <h1 className="mt-8 text-3xl font-semibold leading-tight tracking-tight text-foreground text-balance lg:text-5xl">
            Undeniable proof of every visit.
          </h1>
          <ul className="mt-6 hidden space-y-3 lg:block">
            {features.map((feature) => (
              <li key={feature.text} className="flex items-center gap-3 text-sm text-muted-foreground">
                <feature.icon className="size-4" />
                {feature.text}
              </li>
            ))}
          </ul>
        </div>

        <Card className="p-6 lg:p-8">
          <h2 className="text-2xl font-semibold text-foreground">
            {mode === "register" ? "Create account" : "Sign in"}
          </h2>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {mode === "register" ? "Create your personal JobAct workspace." : "Welcome back to JobAct."}
          </p>

          <form className="mt-7 space-y-4" onSubmit={submit} noValidate>
            <Input
              id="auth-email"
              label="Email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              error={emailError}
              required
            />
            <Input
              id="auth-password"
              label="Password"
              type="password"
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              error={passwordError}
              hint={mode === "register" ? "Use 12–128 characters." : undefined}
              minLength={mode === "register" ? 12 : undefined}
              maxLength={128}
              required
            />
            {mode === "register" && (
              <Input
                id="auth-repeat-password"
                label="Repeat password"
                type="password"
                autoComplete="new-password"
                value={repeatPassword}
                onChange={(event) => setRepeatPassword(event.target.value)}
                error={repeatError}
                required
              />
            )}
            <div aria-live="polite" className="min-h-5 text-sm text-destructive">
              {submitError}
            </div>
            <Button type="submit" size="lg" fullWidth disabled={submitting}>
              {submitting && <LoaderCircle className="size-5 animate-spin" />}
              {mode === "register" ? "Create account" : "Sign in"}
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-muted-foreground">
            {mode === "register" ? "Already have an account?" : "Need an account?"}{" "}
            <button
              type="button"
              className="font-medium text-foreground underline underline-offset-4"
              onClick={() => switchMode(mode === "register" ? "login" : "register")}
            >
              {mode === "register" ? "Sign in" : "Create account"}
            </button>
          </p>

          <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wider text-muted-foreground">
            <span className="h-px flex-1 bg-border" />
            or
            <span className="h-px flex-1 bg-border" />
          </div>
          <Button
            type="button"
            size="lg"
            variant="secondary"
            fullWidth
            onClick={() => window.location.assign("/api/v1/auth/google/start")}
          >
            Continue with Google
          </Button>
        </Card>
      </div>
    </div>
  )
}
