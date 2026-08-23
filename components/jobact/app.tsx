"use client"

import { NavProvider, useNav, type Screen } from "@/lib/jobact/store"
import { PhoneShell, BottomNav } from "./shell"
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
  SignatureScreen,
  CompletedScreen,
} from "./screens/flow"
import { CustomerDetailScreen, ReportDetailScreen } from "./screens/detail"
import { OfflineScreen, SyncScreen, StatesScreen } from "./screens/states"

const tabScreens: Screen[] = ["home", "reports", "customers", "profile"]

function Router() {
  const { frame } = useNav()
  const { screen, params } = frame
  const picking = Boolean(params.picking)
  const showNav = tabScreens.includes(screen) && !picking

  return (
    <PhoneShell>
      <div className="flex min-h-0 flex-1 flex-col">
        <ScreenView screen={screen} />
      </div>
      {showNav && <BottomNav active={screen} />}
    </PhoneShell>
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
    case "signature":
      return <SignatureScreen />
    case "completed":
      return <CompletedScreen />
    case "reportDetail":
      return <ReportDetailScreen />
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
