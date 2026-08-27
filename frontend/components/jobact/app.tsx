"use client"

import { NavProvider, useNav, type Screen } from "@/lib/jobact/store"
import { AppShell } from "./shell"
import { SplashScreen, SignInScreen } from "./screens/onboarding"
import {
  HomeScreen,
  ReportsScreen,
  CustomersScreen,
  ProfileScreen,
} from "./screens/main"
import {
  AddCustomerScreen,
  VisitStartScreen,
  GpsScreen,
  PhotosScreen,
  VoiceScreen,
  VoiceProcessingScreen,
  ReportDraftScreen,
  EditReportScreen,
  AuditProcessingScreen,
  AuditResultScreen,
  SignatureScreen,
  CompletedScreen,
} from "./screens/flow"
import { BackendReportDetailScreen, CustomerDetailScreen } from "./screens/detail"
import { OfflineScreen, SyncScreen, StatesScreen } from "./screens/states"

const tabScreens: Screen[] = ["home", "reports", "customers", "profile"]

/* Screens shown before the user is inside the workspace — no app chrome */
const chromelessScreens: Screen[] = ["splash", "signin"]

function Router() {
  const { frame } = useNav()
  const { screen, params } = frame
  const picking = Boolean(params.picking)

  // The sidebar stays put across the whole workspace, including the visit flow;
  // the bottom tab bar keeps its narrower mobile rules.
  const chrome = !chromelessScreens.includes(screen)
  const bottomNav = tabScreens.includes(screen) && !picking

  return (
    <AppShell chrome={chrome} bottomNav={bottomNav} active={screen}>
      <div className="flex min-h-0 flex-1 flex-col">
        <ScreenView screen={screen} />
      </div>
    </AppShell>
  )
}

function ScreenView({ screen }: { screen: Screen }) {
  switch (screen) {
    case "splash":
      return <SplashScreen />
    case "signin":
      return <SignInScreen />
    case "home":
      return <HomeScreen />
    case "reports":
      return <ReportsScreen />
    case "customers":
      return <CustomersScreenWrapper />
    case "addCustomer":
      return <AddCustomerScreen />
    case "customerDetail":
      return <CustomerDetailScreen />
    case "visitStart":
      return <VisitStartScreen />
    case "gps":
      return <GpsScreen />
    case "beforePhotos":
      return <PhotosScreen phase="before" />
    case "afterPhotos":
      return <PhotosScreen phase="after" />
    case "voice":
      return <VoiceScreen />
    case "voiceProcessing":
      return <VoiceProcessingScreen />
    case "reportDraft":
      return <ReportDraftScreen />
    case "editReport":
      return <EditReportScreen />
    case "auditProcessing":
      return <AuditProcessingScreen />
    case "auditResult":
      return <AuditResultScreen />
    case "signature":
      return <SignatureScreen />
    case "completed":
      return <CompletedScreen />
    case "reportDetail":
      return <BackendReportDetailScreen />
    case "profile":
      return <ProfileScreen />
    case "offline":
      return <OfflineScreen />
    case "sync":
      return <SyncScreen />
    case "states":
      return <StatesScreen />
    default:
      return <HomeScreen />
  }
}

function CustomersScreenWrapper() {
  const { frame } = useNav()
  return <CustomersScreen picking={Boolean(frame.params.picking)} />
}

export function JobActApp() {
  return (
    <NavProvider>
      <Router />
    </NavProvider>
  )
}
