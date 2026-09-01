"use client"

import { NavProvider, useNav, type Screen } from "@/lib/jobact/store"
import { AppShell } from "./shell"
import { DemoEntryScreen } from "./screens/demo-entry"
import { HomeScreen } from "./screens/main"
import {
  AddCustomerScreen,
  VisitStartScreen,
  GpsScreen,
  PhotosScreen,
  NotesScreen,
  AnalysisProcessingScreen,
  ReportDraftScreen,
  EditReportScreen,
  SignatureScreen,
  CompletedScreen,
} from "./screens/flow"
import { CheckDetailScreen } from "./screens/detail"

function Router() {
  const { frame } = useNav()
  return (
    <AppShell>
      <div className="flex min-h-0 flex-1 flex-col">
        <ScreenView screen={frame.screen} />
      </div>
    </AppShell>
  )
}

function ScreenView({ screen }: { screen: Screen }) {
  switch (screen) {
    case "demoEntry":
      return <DemoEntryScreen />
    case "home":
      return <HomeScreen />
    case "addCustomer":
      return <AddCustomerScreen />
    case "visitStart":
      return <VisitStartScreen />
    case "gps":
      return <GpsScreen />
    case "beforePhotos":
      return <PhotosScreen phase="before" />
    case "afterPhotos":
      return <PhotosScreen phase="after" />
    case "notes":
      return <NotesScreen />
    case "analysisProcessing":
      return <AnalysisProcessingScreen />
    case "reportDraft":
      return <ReportDraftScreen />
    case "editReport":
      return <EditReportScreen />
    case "signature":
      return <SignatureScreen />
    case "completed":
      return <CompletedScreen />
    case "checkDetail":
      return <CheckDetailScreen />
    default:
      return <HomeScreen />
  }
}

export function JobActApp() {
  return (
    <NavProvider>
      <Router />
    </NavProvider>
  )
}
