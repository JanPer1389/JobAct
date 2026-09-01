"use client"

import { useState } from "react"
import { Button, Card, Input, Logo } from "../ui"
import { useNav } from "@/lib/jobact/store"
import { getStoredUserName, setStoredUserName } from "@/lib/jobact/local-prefs"
import { t } from "@/lib/jobact/i18n"

export function DemoEntryScreen() {
  const { reset, setUserName, locale } = useNav()
  const [name, setName] = useState(() => getStoredUserName() ?? "")

  function start() {
    const trimmed = name.trim() || t(locale, "yourNamePlaceholder")
    setStoredUserName(trimmed)
    setUserName(trimmed)
    reset("home")
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-10 text-center">
      <div className="animate-in fade-in zoom-in duration-700">
        <Logo size="lg" />
      </div>
      <h1 className="mt-6 text-2xl font-semibold tracking-tight text-foreground">JobAct</h1>
      <p className="mt-1.5 max-w-xs text-sm leading-relaxed text-muted-foreground">
        {t(locale, "demoEntryTagline")}
      </p>

      <Card className="mt-8 w-full max-w-xs p-5 text-left">
        <Input
          id="demo-user-name"
          label={t(locale, "yourNameLabel")}
          placeholder={t(locale, "yourNamePlaceholder")}
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") start()
          }}
        />
        <Button size="lg" fullWidth className="mt-5" onClick={start}>
          {t(locale, "demoContinueBtn")}
        </Button>
      </Card>

      <p className="mt-6 max-w-xs text-xs text-muted-foreground">{t(locale, "localDataNotice")}</p>
    </div>
  )
}
