/**
 * Central localization layer for the technician-facing application UI.
 *
 * `locale` (the interface-language preference) controls every string this
 * module renders. `currency` is a completely independent preference (see
 * `formatCurrency`) -- neither one is allowed to imply the other. See
 * `PAPERCUT.md`'s "Full application localization audit" entry for the
 * broader rationale.
 */

export const appLocales = ["en-US", "ru-RU"] as const
export type AppLocale = (typeof appLocales)[number]

export const appCurrencies = ["USD", "RUB"] as const
export type AppCurrency = (typeof appCurrencies)[number]

type Params = Record<string, string | number>

function interpolate(template: string, params?: Params): string {
  if (!params) return template
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in params ? String(params[key]) : match,
  )
}

/* ------------------------------------------------------------------ */
/*  Simple (non-plural) dictionary                                     */
/* ------------------------------------------------------------------ */

type TranslationKey = keyof typeof translations["en-US"]

const translations = {
  "en-US": {
    // Common
    ok: "OK",
    cancel: "Cancel",
    save: "Save",
    add: "Add",
    retry: "Retry",
    tryAgain: "Try again",
    tryAgainAction: "Try again",
    loading: "Loading",
    loadingEllipsis: "Loading…",
    continueLabel: "Continue",
    done: "Done",
    goBack: "Go back",
    notifications: "Notifications",
    profile: "Profile",
    clear: "Clear",

    // Preferences
    language: "Language",
    english: "English",
    russian: "Russian",
    saving: "Saving…",
    languageSaveError: "Could not save language preference.",
    preferences: "Preferences",
    currency: "Currency",
    usdOption: "US Dollar ($)",
    rubOption: "Russian Ruble (₽)",
    currencySaveError: "Could not save currency preference.",

    // Shell / navigation
    workspace: "Workspace",
    operations: "Operations",
    overview: "Overview",
    reports: "Reports",
    customers: "Customers",
    newReport: "New report",
    createReportAction: "Create report",
    account: "Account",
    signOut: "Sign out",
    home: "Home",
    more: "More",
    syncAndBackups: "Sync & backups",
    offlineQueue: "Offline queue",
    permissionsNav: "Permissions",

    // Home
    goodMorning: "Good morning, {name}",
    goodAfternoon: "Good afternoon, {name}",
    goodEvening: "Good evening, {name}",
    startNow: "Start now",
    createReportHeading: "Create report",
    createReportSubtitle: "Photos, location & signature in ~2 min",
    photosLabel: "Photos",
    voiceLabel: "Voice",
    gpsLabel: "GPS",
    signatureLabel: "Signature",
    billedThisMonth: "Billed this month",
    reportsStat: "Reports",
    signedOnSiteStat: "Signed on-site",
    awaitingSync: "Awaiting sync",
    unfinishedDrafts: "Unfinished drafts",
    resumeWhereYouLeftOff: "Resume where you left off",
    recentReports: "Recent reports",
    viewAll: "View all",
    syncSection: "Sync",
    reviewSyncStatus: "Review sync status",
    latestVisits: "Latest visits",
    teamToday: "Team today",

    // Reports screen
    reportsTitle: "Reports",
    newReportBtn: "New report",
    searchCustomerOrId: "Search customer or report ID",
    filterAll: "All",
    filterCompleted: "Completed",
    filterUnsigned: "Unsigned",
    filterDraft: "Drafts",
    noReportsFound: "No reports found",
    noReportsFoundDesc: "Try a different search or filter to find the visit you are looking for.",
    noPrice: "No price",
    reportAwaitingDetails: "Report awaiting details",
    couldNotLoadReports: "Could not load reports.",

    // Customers screen
    customersTitle: "Customers",
    searchNameOrAddress: "Search name or address",
    addCustomer: "Add customer",
    addNewCustomer: "Add new customer",
    couldNotLoadCustomers: "Could not load customers.",
    noCustomersYet: "No customers yet",
    noCustomersYetDesc: "Add your first customer to start creating reports and tracking visits.",
    selectCustomer: "Select customer",
    stepWhoIsThisFor: "Step 1 · Who is this visit for?",

    // Profile screen
    accountTitle: "Account",
    signedOutUser: "Signed-out user",
    noOrganization: "No organization",
    signedOutRole: "signed out",
    thisMonthStat: "This month",
    reportsStatLabel: "Reports",
    signedStatLabel: "Signed",
    accountSecurity: "Account security",
    passwordEnabledBadge: "Password enabled",
    passwordNotSetBadge: "Password not set",
    googleLinkedBadge: "Google linked",
    googleNotLinkedBadge: "Google not linked",
    currentPasswordLabel: "Current password",
    newPasswordLabel: "New password",
    setPasswordLabel: "Set password",
    repeatNewPasswordLabel: "Repeat new password",
    passwordHint: "Use 12–128 characters.",
    changePasswordBtn: "Change password",
    setPasswordBtn: "Set password",
    linkGoogleBtn: "Link Google",
    googleLinkedMessage: "Google is now linked to this account.",
    googleLinkFailedMessage: "Google could not be linked. Please try again.",
    teamAndEmployees: "Team & employees",
    permissionsAndStates: "Permissions & states",
    signOutBtn: "Sign out",
    signingOut: "Signing out…",
    appVersionFooter: "JobAct v1.0 · Made for the field",
    couldNotLoadAuthMethods: "Could not load authentication methods.",
    couldNotUpdatePassword: "Could not update the password.",
    passwordAdded: "Password added.",
    passwordChanged: "Password changed.",
    couldNotSignOut: "Could not sign out.",
    passwordsDoNotMatch: "Passwords do not match.",
    workspaceGroup: "Workspace",
    appGroup: "App",
    offlineModeItem: "Offline mode",

    // Onboarding
    proofOfWorkTagline: "Proof of work, in 2 minutes",
    loadingWorkspace: "Loading your workspace",
    undeniableProofHeading: "Undeniable proof of every visit.",
    featureBeforeAfter: "Before & after photos, timestamped",
    featureGps: "Automatic GPS location on arrival",
    featureVoice: "Describe the work by voice, not typing",
    featureSignature: "Customer signature, archived as proof",
    createAccountHeading: "Create account",
    signInHeading: "Sign in",
    createAccountSubtitle: "Create your personal JobAct workspace.",
    welcomeBackSubtitle: "Welcome back to JobAct.",
    emailLabel: "Email",
    passwordLabel: "Password",
    repeatPasswordLabel: "Repeat password",
    alreadyHaveAccount: "Already have an account?",
    needAccount: "Need an account?",
    orDivider: "or",
    continueWithGoogle: "Continue with Google",
    enterValidEmail: "Enter a valid email address.",
    authUnavailable: "Authentication is unavailable. Please try again.",
    googleLinkRequiredMessage:
      "An account already uses that email. Sign in first, then link Google from Account security.",

    // Visit flow — add customer
    addCustomerTitle: "Add customer",
    customerNameLabel: "Customer name",
    customerNamePlaceholder: "e.g. Aurora Dental Clinic",
    addressLabel: "Address",
    addressPlaceholder: "Street, unit, city",
    phoneLabel: "Phone",
    serviceTypeLabel: "Service type",
    serviceTypePlaceholder: "AC maintenance, cleaning, repair…",
    serviceTypeHint: "Optional — helps you find them later",
    saveAndContinue: "Save & continue",
    saveCustomerBtn: "Save customer",
    couldNotSaveCustomer: "Could not save customer.",
    defaultServiceType: "Service visit",
    newCustomerFallback: "New customer",
    addressOnFileFallback: "Address on file",

    // Visit flow — start visit
    startVisitTitle: "Start visit",
    stepConfirmDetails: "Step 2 · Confirm the details",
    visitMetadata: "Visit metadata",
    dateLabel: "Date",
    startTimeLabel: "Start time",
    locationLabel: "Location",
    locatingEllipsis: "Locating…",
    autoBadge: "auto",
    dateTimeGpsNote: "Date, time and GPS are captured automatically and attached to the report as proof.",
    confirmLocationBtn: "Confirm location",
    startingVisitEllipsis: "Starting visit…",
    couldNotStartVisit: "Could not start visit.",

    // Visit flow — GPS
    locationTitle: "Location",
    gpsLocationLabel: "GPS location",
    confirmedLabel: "Confirmed",
    locationNeededLabel: "Location needed",
    locatingLabel: "Locating",
    locationUnavailable: "Location unavailable",
    acquiringSatellites: "Acquiring satellites…",
    locationConfirmedBtn: "Location confirmed",
    couldNotSaveLocation: "Could not save location.",
    locErrUnsupported: "This browser can't share your location. Try a different browser or device.",
    locErrDenied: "Location access was denied. Allow location access for this site, then try again.",
    locErrUnavailable: "Your location couldn't be determined. Try moving somewhere with a clearer signal.",
    locErrTimeout: "Finding your location took too long. Try again.",
    locErrGeneric: "Couldn't get your location. Try again.",

    // Visit flow — photos
    beforePhotosTitle: "Before photos",
    afterPhotosTitle: "After photos",
    stepCaptureStart: "Step 3 · Capture the starting state",
    stepShowFinishedWork: "Step 5 · Show the finished work",
    pairLabel: "Pair {n}",
    beforePhotosHint: "Photograph the problem area before you start. These become part of the proof archive.",
    afterPhotosHint: "Capture exactly {n} completed-work photos, in the same order and angles as the before photos.",
    normalizingUploading: "Normalizing and uploading photo…",
    couldNotUploadPhoto: "Could not upload photo.",
    startAiAnalysisBtn: "Start AI analysis",

    // Visit flow — notes
    describeWorkTitle: "Describe the work",
    stepDescribeWork: "Step 4 · What did you complete?",
    whatDidYouDo: "What did you do on this visit?",
    whatDidYouDoDesc:
      "Mention what you repaired or serviced, any materials used, and the amount charged. The AI turns this and your photos into one report.",
    workNotesLabel: "Work notes",
    workNotesPlaceholder:
      "e.g. Diagnosed an intermittent compressor fault. Replaced the start capacitor and cleaned the contactor points. Used one 45uF capacitor. Charged 160.",
    tooShortHint: "Add a little more detail — at least 20 characters.",
    roughNotesFine: "Rough notes are fine; the AI cleans them up.",
    couldNotSaveNotes: "Could not save your notes.",
    voiceNotes: "Voice note",
    typedNotes: "Type notes",
    recordVoice: "Record voice",
    chooseInputMethod: "Choose how to add the work details",
    startRecording: "Start recording",
    stopRecording: "Stop recording",
    recordingInProgress: "Recording…",
    preparingRecording: "Preparing recording…",
    uploadingRecording: "Uploading recording…",
    recordingUploaded: "Voice note uploaded. Continue to add the after photo; transcription starts automatically after that.",
    continueToAfterPhoto: "Continue to after photo",
    microphoneUnavailable: "Microphone recording is not supported by this browser.",

    // Visit flow — analysis processing
    uploadingEvidence: "Uploading visit evidence",
    draftingReport: "Drafting the work report",
    comparingPhotos: "Comparing before & after photos",
    analysingVisit: "Analysing this visit",
    analysingVisitDesc: "Reading your notes and comparing the photos",
    returnToWorkspace: "Return to workspace",
    analysisNeedsAttention: "Analysis needs attention",
    reviewPhotosBtn: "Review photos",
    writeManuallyBtn: "Write it manually",
    visitNotesMissing: "Visit notes are missing.",
    photosMustFormPairs: "Before and after photos must form equal pairs.",
    analysisIncompleteError: "The AI analysis could not be completed. Please try again.",
    analysisTimedOutError: "The AI analysis timed out. Please try again.",
    analysisProviderConfigurationError:
      "The AI service is not configured correctly. Enter the report manually or contact an administrator.",
    couldNotAnalyseVisit: "Could not analyse this visit.",
    analysisTakingLongerError:
      "The analysis is taking longer than expected. It is still running — check again in a moment.",

    // Visit flow — report draft / review
    reportDraftTitle: "Report draft",
    stepReviewReport: "Step 6 · Review the generated report",
    aiDraftNotice: "AI draft — check the amount and edit anything before signing.",
    reviewConfirmNotice: "Review and confirm the report before signing.",
    visitLabel: "Visit",
    workCompletedLabel: "Work completed",
    materialsLabel: "Materials / consumables",
    amountLabel: "Amount",
    notSpecified: "Not specified",
    visitEvidenceLabel: "Visit evidence",
    beforeLabel: "Before",
    afterLabel: "After",
    beforeAfterComparisonLabel: "Before / after comparison",
    visuallyConfirmed: "Visually confirmed",
    doneWell: "Done well",
    issuesSuspicious: "Issues & suspicious items",
    unverified: "Unverified",
    priceAssessmentLabel: "Price assessment",
    analysisLimitations: "Analysis limitations",
    recommendedNextSteps: "Recommended next steps",
    visualAssessmentDisclaimer:
      "This visual assessment does not substitute for a legal opinion, technical acceptance inspection, or construction expert review.",
    noComparisonAttached: "No photo comparison is attached",
    noComparisonAttachedDesc:
      "Nothing was fabricated. You can rerun the analysis or continue with the written report alone.",
    confirmAndSignBtn: "Confirm & sign",
    confirmingEllipsis: "Confirming…",
    editBtn: "Edit",
    recaptureBtn: "Recapture",
    rerunBtn: "Rerun",
    couldNotConfirmReport: "Could not confirm report.",
    couldNotRerunAnalysis: "Could not rerun the analysis.",

    // Visit flow — edit report
    editReportTitle: "Edit report",
    aiCouldNotFinish: "AI analysis could not finish",
    aiCouldNotFinishDesc:
      "Your notes and photos are saved. Fill the report in yourself, run the analysis again, or take better photos first.",
    retryAnalysisBtn: "Retry analysis",
    retryingEllipsis: "Retrying…",
    materialPlaceholder: "Material",
    removeMaterialLabel: "Remove material",
    addBtn: "Add",
    amountChargedLabel: "Amount charged",
    useTheseNotesBtn: "Use these notes",
    savingChangesEllipsis: "Saving…",
    saveChangesBtn: "Save changes",
    couldNotRetryAnalysis: "Could not retry the analysis.",
    couldNotSaveReport: "Could not save report.",

    // Visit flow — signature
    customerConfirmationTitle: "Customer confirmation",
    signingConfirmsText: "By signing, {name} confirms the work described was completed to their satisfaction.",
    signedByLabel: "Signed by",
    defaultSignerName: "On-site manager",
    signerNamePlaceholder: "Name of person signing",
    signatureStoredNote: "The signature is stored with the timestamp and GPS location as tamper-evident proof.",
    confirmAndFinishBtn: "Confirm & finish",
    finalizingEllipsis: "Finalizing…",
    sendLinkInsteadBtn: "Send link to sign instead",
    signatureRequired: "Draw a signature before continuing.",
    signatureUploadFailed: "Signature upload failed.",
    pdfTimedOut: "PDF generation timed out. The report remains saved.",
    couldNotSignReport: "Could not sign report.",

    // Visit flow — completed
    reportCompletedTitle: "Report completed",
    reportCompletedSubtitle: "Proof of this visit is saved and secured.",
    dateTimeLabel: "Date & time",
    locationCapturedLabel: "Captured · ±5m",
    signatureStatusLabel: "Signature",
    signedOnSiteLabel: "Signed on-site",
    linkSentLabel: "Link sent",
    reportFallback: "Report",
    openSignedPdfBtn: "Open signed PDF",
    viewReportBtn: "View report",
    doneAction: "Done",
    pdfNotAvailable: "The PDF is not available yet.",
    couldNotOpenPdf: "Could not open PDF.",

    // Shared status / sync / verdict labels
    statusDraft: "Draft",
    statusUnsigned: "Unsigned",
    statusCompleted: "Completed",
    statusOffline: "Offline",
    syncSynced: "Synced",
    syncPending: "Pending upload",
    syncSyncing: "Syncing",
    syncFailed: "Sync failed",
    syncOffline: "Saved offline",
    confidenceHigh: "High confidence",
    confidenceMedium: "Medium confidence",
    confidenceLow: "Low confidence",
    verdictHighQuality: "High quality",
    verdictPartiallyCompleted: "Partially completed",
    verdictPoorQuality: "Poor quality",
    verdictInsufficientData: "Insufficient data",
    priceVerdictNotProvided: "Not provided",
    priceVerdictReasonable: "Reasonable",
    priceVerdictOverpriced: "Overpriced",
    priceVerdictSignificantlyOverpriced: "Significantly overpriced",
    priceVerdictSuspiciouslyLow: "Suspiciously low",
    priceVerdictCannotAssess: "Cannot assess",
    roleOwner: "Owner",
    roleTechnician: "Technician",

    // Shared ui.tsx components
    beforeShort: "Before",
    afterShort: "After",
    removePhotoLabel: "Remove {label} {n}",
    capturePhotoLabel: "Capture photo",
    signHereHint: "Sign here with your mouse or finger",
    offlineBannerText: "Offline — your work is saved on this device",
    stepCustomer: "Customer",
    stepDetails: "Details",
    stepBeforeShort: "Before",
    stepVoiceShort: "Voice",
    stepAfterShort: "After",
    stepReviewShort: "Review",

    // states.tsx
    offlineModeTitle: "Offline mode",
    workingOfflineTitle: "You're working offline",
    workingOfflineDesc:
      "Keep going — every report, photo and signature is saved on this device and will sync automatically when you reconnect.",
    waitingToUpload: "Waiting to upload",
    queuedLabel: "Queued",
    offlineFooterNote:
      "The full visit flow — customer, photos, voice, and signature — works without a connection. Nothing is lost.",
    syncTitle: "Sync",
    syncingVisits: "Syncing your visits",
    someUploadsFailed: "Some uploads failed",
    dataIsSafeRetry: "Your data is safe. Retry when you have a better connection.",
    allSynced: "All synced",
    everyReportBackedUp: "Every report is backed up and secured.",
    connectedWifi: "Connected · Wi-Fi",
    queueLabel: "Queue",
    permissionsStatesTitle: "Permissions & states",
    previewEdgeCase: "Preview of edge-case screens",
    statesIntro: "These are the states JobAct shows when hardware access is blocked or something goes wrong in the field.",
    cameraAccessTitle: "Camera access needed",
    cameraAccessDesc: "JobAct needs your camera to capture before and after photos as proof of the visit.",
    micAccessTitle: "Microphone access needed",
    micAccessDesc: "Allow the microphone so you can describe the work by voice instead of typing.",
    locationAccessTitle: "Location access needed",
    locationAccessDesc: "Location confirms where the visit happened. Enable it to attach GPS proof.",
    gpsUnavailableTitle: "GPS unavailable",
    gpsUnavailableDesc: "We couldn't get a fix right now. You can continue and attach the location later.",
    uploadFailedTitle: "Upload failed",
    uploadFailedDesc: "Photos couldn't be uploaded. They're saved on your device and will retry automatically.",
    voiceProcessFailedTitle: "Couldn't process voice note",
    voiceProcessFailedDesc: "The report couldn't be generated from your recording. Try again or type the description.",
    openSettingsCta: "Open settings",
    retryNowCta: "Retry now",

    // detail.tsx
    lastVisitLabel: "Last visit {date}",
    newReportForCustomer: "New report for this customer",
    visitHistoryLabel: "Visit history",
    noVisitsYet: "No visits yet",
    noVisitsYetDesc: "Create the first report for this customer.",
    noPhotoComparisonMessage: "No photo comparison is attached to this report.",
    qualityLabel: "Quality {score}/10",
    confidencePercentLabel: "Confidence {pct}%",
    priceLabel: "Price: {verdict}",
    reportDetailsLabel: "Report details",
    reportIdLabel: "Report ID",
    revisionLabel: "Revision",
    workflowLabel: "Workflow",
    signatureLabel3: "Signature",
    awaitingSignature: "Awaiting signature",
    couldNotLoadReport: "Could not load report.",
    loadingReportEllipsis: "Loading report…",
    reportTitleFallback: "Report",
    revisionNumberLabel: "Revision {n}",
  },
  "ru-RU": {
    ok: "ОК",
    cancel: "Отмена",
    save: "Сохранить",
    add: "Добавить",
    retry: "Повторить",
    tryAgain: "Повторить",
    tryAgainAction: "Повторить попытку",
    loading: "Загрузка",
    loadingEllipsis: "Загрузка…",
    continueLabel: "Продолжить",
    done: "Готово",
    goBack: "Назад",
    notifications: "Уведомления",
    profile: "Профиль",
    clear: "Очистить",

    language: "Язык",
    english: "English",
    russian: "Русский",
    saving: "Сохранение…",
    languageSaveError: "Не удалось сохранить язык.",
    preferences: "Настройки",
    currency: "Валюта",
    usdOption: "Доллар США ($)",
    rubOption: "Российский рубль (₽)",
    currencySaveError: "Не удалось сохранить валюту.",

    workspace: "Рабочее пространство",
    operations: "Операции",
    overview: "Обзор",
    reports: "Отчёты",
    customers: "Клиенты",
    newReport: "Новый отчёт",
    createReportAction: "Создать отчёт",
    account: "Аккаунт",
    signOut: "Выйти",
    home: "Главная",
    more: "Ещё",
    syncAndBackups: "Синхронизация и копии",
    offlineQueue: "Офлайн-очередь",
    permissionsNav: "Разрешения",

    goodMorning: "Доброе утро, {name}",
    goodAfternoon: "Добрый день, {name}",
    goodEvening: "Добрый вечер, {name}",
    startNow: "Начать сейчас",
    createReportHeading: "Создать отчёт",
    createReportSubtitle: "Фото, геолокация и подпись за ~2 минуты",
    photosLabel: "Фото",
    voiceLabel: "Голос",
    gpsLabel: "GPS",
    signatureLabel: "Подпись",
    billedThisMonth: "Выставлено за месяц",
    reportsStat: "Отчёты",
    signedOnSiteStat: "Подписано на месте",
    awaitingSync: "Ожидает синхронизации",
    unfinishedDrafts: "Незавершённые черновики",
    resumeWhereYouLeftOff: "Продолжить с того места",
    recentReports: "Недавние отчёты",
    viewAll: "Смотреть все",
    syncSection: "Синхронизация",
    reviewSyncStatus: "Проверить статус синхронизации",
    latestVisits: "Последние визиты",
    teamToday: "Команда сегодня",

    reportsTitle: "Отчёты",
    newReportBtn: "Новый отчёт",
    searchCustomerOrId: "Поиск клиента или номера отчёта",
    filterAll: "Все",
    filterCompleted: "Завершено",
    filterUnsigned: "Не подписано",
    filterDraft: "Черновики",
    noReportsFound: "Отчёты не найдены",
    noReportsFoundDesc: "Попробуйте изменить поиск или фильтр, чтобы найти нужный визит.",
    noPrice: "Цена не указана",
    reportAwaitingDetails: "Отчёт ожидает деталей",
    couldNotLoadReports: "Не удалось загрузить отчёты.",

    customersTitle: "Клиенты",
    searchNameOrAddress: "Поиск по имени или адресу",
    addCustomer: "Добавить клиента",
    addNewCustomer: "Добавить нового клиента",
    couldNotLoadCustomers: "Не удалось загрузить клиентов.",
    noCustomersYet: "Пока нет клиентов",
    noCustomersYetDesc: "Добавьте первого клиента, чтобы начать создавать отчёты и отслеживать визиты.",
    selectCustomer: "Выберите клиента",
    stepWhoIsThisFor: "Шаг 1 · Для кого этот визит?",

    accountTitle: "Аккаунт",
    signedOutUser: "Пользователь не вошёл",
    noOrganization: "Нет организации",
    signedOutRole: "не в сети",
    thisMonthStat: "За этот месяц",
    reportsStatLabel: "Отчёты",
    signedStatLabel: "Подписано",
    accountSecurity: "Безопасность аккаунта",
    passwordEnabledBadge: "Пароль установлен",
    passwordNotSetBadge: "Пароль не установлен",
    googleLinkedBadge: "Google привязан",
    googleNotLinkedBadge: "Google не привязан",
    currentPasswordLabel: "Текущий пароль",
    newPasswordLabel: "Новый пароль",
    setPasswordLabel: "Задать пароль",
    repeatNewPasswordLabel: "Повторите новый пароль",
    passwordHint: "Используйте от 12 до 128 символов.",
    changePasswordBtn: "Изменить пароль",
    setPasswordBtn: "Задать пароль",
    linkGoogleBtn: "Привязать Google",
    googleLinkedMessage: "Google теперь привязан к этому аккаунту.",
    googleLinkFailedMessage: "Не удалось привязать Google. Попробуйте снова.",
    teamAndEmployees: "Команда и сотрудники",
    permissionsAndStates: "Разрешения и состояния",
    signOutBtn: "Выйти",
    signingOut: "Выход…",
    appVersionFooter: "JobAct v1.0 · Создано для полевой работы",
    couldNotLoadAuthMethods: "Не удалось загрузить способы аутентификации.",
    couldNotUpdatePassword: "Не удалось обновить пароль.",
    passwordAdded: "Пароль добавлен.",
    passwordChanged: "Пароль изменён.",
    couldNotSignOut: "Не удалось выйти.",
    passwordsDoNotMatch: "Пароли не совпадают.",
    workspaceGroup: "Рабочее пространство",
    appGroup: "Приложение",
    offlineModeItem: "Офлайн-режим",

    proofOfWorkTagline: "Подтверждение работы за 2 минуты",
    loadingWorkspace: "Загружаем ваше рабочее пространство",
    undeniableProofHeading: "Неопровержимое доказательство каждого визита.",
    featureBeforeAfter: "Фото до и после, с меткой времени",
    featureGps: "Автоматическая GPS-геолокация по прибытии",
    featureVoice: "Опишите работу голосом, а не текстом",
    featureSignature: "Подпись клиента, сохранённая как доказательство",
    createAccountHeading: "Создать аккаунт",
    signInHeading: "Войти",
    createAccountSubtitle: "Создайте личное рабочее пространство JobAct.",
    welcomeBackSubtitle: "С возвращением в JobAct.",
    emailLabel: "Email",
    passwordLabel: "Пароль",
    repeatPasswordLabel: "Повторите пароль",
    alreadyHaveAccount: "Уже есть аккаунт?",
    needAccount: "Нужен аккаунт?",
    orDivider: "или",
    continueWithGoogle: "Продолжить с Google",
    enterValidEmail: "Введите корректный email.",
    authUnavailable: "Аутентификация недоступна. Попробуйте снова.",
    googleLinkRequiredMessage:
      "Этот email уже используется аккаунтом. Сначала войдите, затем привяжите Google в разделе «Безопасность аккаунта».",

    addCustomerTitle: "Добавить клиента",
    customerNameLabel: "Имя клиента",
    customerNamePlaceholder: "напр. Aurora Dental Clinic",
    addressLabel: "Адрес",
    addressPlaceholder: "Улица, помещение, город",
    phoneLabel: "Телефон",
    serviceTypeLabel: "Вид услуги",
    serviceTypePlaceholder: "Обслуживание кондиционеров, уборка, ремонт…",
    serviceTypeHint: "Необязательно — поможет найти клиента позже",
    saveAndContinue: "Сохранить и продолжить",
    saveCustomerBtn: "Сохранить клиента",
    couldNotSaveCustomer: "Не удалось сохранить клиента.",
    defaultServiceType: "Визит по обслуживанию",
    newCustomerFallback: "Новый клиент",
    addressOnFileFallback: "Адрес в базе",

    startVisitTitle: "Начать визит",
    stepConfirmDetails: "Шаг 2 · Подтвердите детали",
    visitMetadata: "Данные визита",
    dateLabel: "Дата",
    startTimeLabel: "Время начала",
    locationLabel: "Местоположение",
    locatingEllipsis: "Определение…",
    autoBadge: "авто",
    dateTimeGpsNote: "Дата, время и GPS фиксируются автоматически и прикрепляются к отчёту как доказательство.",
    confirmLocationBtn: "Подтвердить местоположение",
    startingVisitEllipsis: "Начинаем визит…",
    couldNotStartVisit: "Не удалось начать визит.",

    locationTitle: "Местоположение",
    gpsLocationLabel: "GPS-местоположение",
    confirmedLabel: "Подтверждено",
    locationNeededLabel: "Нужно местоположение",
    locatingLabel: "Определение",
    locationUnavailable: "Местоположение недоступно",
    acquiringSatellites: "Поиск спутников…",
    locationConfirmedBtn: "Местоположение подтверждено",
    couldNotSaveLocation: "Не удалось сохранить местоположение.",
    locErrUnsupported: "Этот браузер не может передать ваше местоположение. Попробуйте другой браузер или устройство.",
    locErrDenied: "Доступ к местоположению запрещён. Разрешите доступ к геолокации для этого сайта и попробуйте снова.",
    locErrUnavailable: "Не удалось определить местоположение. Попробуйте переместиться туда, где сигнал лучше.",
    locErrTimeout: "Определение местоположения заняло слишком много времени. Попробуйте снова.",
    locErrGeneric: "Не удалось получить местоположение. Попробуйте снова.",

    beforePhotosTitle: "Фото до",
    afterPhotosTitle: "Фото после",
    stepCaptureStart: "Шаг 3 · Зафиксируйте исходное состояние",
    stepShowFinishedWork: "Шаг 5 · Покажите выполненную работу",
    pairLabel: "Пара {n}",
    beforePhotosHint: "Сфотографируйте проблемный участок перед началом работы. Эти фото становятся частью архива доказательств.",
    afterPhotosHint: "Сделайте ровно {n} фото завершённой работы, в том же порядке и ракурсах, что и фото «до».",
    normalizingUploading: "Обработка и загрузка фото…",
    couldNotUploadPhoto: "Не удалось загрузить фото.",
    startAiAnalysisBtn: "Начать анализ ИИ",

    describeWorkTitle: "Опишите работу",
    stepDescribeWork: "Шаг 4 · Что вы сделали?",
    whatDidYouDo: "Что вы сделали во время этого визита?",
    whatDidYouDoDesc:
      "Укажите, что вы отремонтировали или обслужили, какие материалы использовали и какую сумму взяли. ИИ превратит это и ваши фото в один отчёт.",
    workNotesLabel: "Заметки о работе",
    workNotesPlaceholder:
      "напр. Диагностирована перемежающаяся неисправность компрессора. Заменён пусковой конденсатор, очищены контакты пускателя. Использован один конденсатор 45 мкФ. Стоимость 160.",
    tooShortHint: "Добавьте немного больше деталей — минимум 20 символов.",
    roughNotesFine: "Черновые заметки — это нормально; ИИ их доработает.",
    couldNotSaveNotes: "Не удалось сохранить заметки.",
    voiceNotes: "Голосовая заметка",
    typedNotes: "Ввести текст",
    recordVoice: "Записать голос",
    chooseInputMethod: "Выберите, как добавить описание работы",
    startRecording: "Начать запись",
    stopRecording: "Остановить запись",
    recordingInProgress: "Идёт запись…",
    preparingRecording: "Подготовка записи…",
    uploadingRecording: "Загрузка записи…",
    recordingUploaded: "Голосовая заметка загружена. Продолжите к фото «после» — расшифровка начнётся автоматически.",
    continueToAfterPhoto: "К фото после",
    microphoneUnavailable: "Запись с микрофона не поддерживается этим браузером.",

    uploadingEvidence: "Загрузка доказательств визита",
    draftingReport: "Составление отчёта о работе",
    comparingPhotos: "Сравнение фото до и после",
    analysingVisit: "Анализ визита",
    analysingVisitDesc: "Читаем ваши заметки и сравниваем фото",
    returnToWorkspace: "Вернуться в рабочее пространство",
    analysisNeedsAttention: "Анализ требует внимания",
    reviewPhotosBtn: "Проверить фото",
    writeManuallyBtn: "Написать вручную",
    visitNotesMissing: "Отсутствуют заметки о визите.",
    photosMustFormPairs: "Фото до и после должны образовывать равные пары.",
    analysisIncompleteError: "Не удалось завершить анализ ИИ. Попробуйте снова.",
    analysisTimedOutError: "Время ожидания анализа ИИ истекло. Попробуйте снова.",
    analysisProviderConfigurationError:
      "Сервис ИИ настроен некорректно. Введите отчёт вручную или обратитесь к администратору.",
    couldNotAnalyseVisit: "Не удалось проанализировать визит.",
    analysisTakingLongerError:
      "Анализ занимает больше времени, чем ожидалось. Он всё ещё выполняется — проверьте через минуту.",

    reportDraftTitle: "Черновик отчёта",
    stepReviewReport: "Шаг 6 · Проверьте сформированный отчёт",
    aiDraftNotice: "Черновик ИИ — проверьте сумму и внесите правки перед подписанием.",
    reviewConfirmNotice: "Проверьте и подтвердите отчёт перед подписанием.",
    visitLabel: "Визит",
    workCompletedLabel: "Выполненная работа",
    materialsLabel: "Материалы / расходники",
    amountLabel: "Сумма",
    notSpecified: "Не указано",
    visitEvidenceLabel: "Доказательства визита",
    beforeLabel: "До",
    afterLabel: "После",
    beforeAfterComparisonLabel: "Сравнение до / после",
    visuallyConfirmed: "Визуально подтверждено",
    doneWell: "Хорошо выполнено",
    issuesSuspicious: "Проблемы и подозрительные моменты",
    unverified: "Не проверено",
    priceAssessmentLabel: "Оценка стоимости",
    analysisLimitations: "Ограничения анализа",
    recommendedNextSteps: "Рекомендуемые следующие шаги",
    visualAssessmentDisclaimer:
      "Эта визуальная оценка не заменяет юридическое заключение, техническую приёмку или экспертизу.",
    noComparisonAttached: "Сравнение фото не прикреплено",
    noComparisonAttachedDesc:
      "Ничего не было придумано. Вы можете повторить анализ или продолжить только с письменным отчётом.",
    confirmAndSignBtn: "Подтвердить и подписать",
    confirmingEllipsis: "Подтверждение…",
    editBtn: "Изменить",
    recaptureBtn: "Переснять",
    rerunBtn: "Повторить",
    couldNotConfirmReport: "Не удалось подтвердить отчёт.",
    couldNotRerunAnalysis: "Не удалось повторить анализ.",

    editReportTitle: "Изменить отчёт",
    aiCouldNotFinish: "Анализ ИИ не удалось завершить",
    aiCouldNotFinishDesc:
      "Ваши заметки и фото сохранены. Заполните отчёт самостоятельно, запустите анализ снова или сделайте фото лучше.",
    retryAnalysisBtn: "Повторить анализ",
    retryingEllipsis: "Повтор…",
    materialPlaceholder: "Материал",
    removeMaterialLabel: "Удалить материал",
    addBtn: "Добавить",
    amountChargedLabel: "Сумма к оплате",
    useTheseNotesBtn: "Использовать эти заметки",
    savingChangesEllipsis: "Сохранение…",
    saveChangesBtn: "Сохранить изменения",
    couldNotRetryAnalysis: "Не удалось повторить анализ.",
    couldNotSaveReport: "Не удалось сохранить отчёт.",

    customerConfirmationTitle: "Подтверждение клиента",
    signingConfirmsText: "Подписывая, {name} подтверждает, что описанная работа выполнена к их удовлетворению.",
    signedByLabel: "Подписал(а)",
    defaultSignerName: "Ответственный на месте",
    signerNamePlaceholder: "Имя подписывающего",
    signatureStoredNote: "Подпись сохраняется вместе с меткой времени и GPS-местоположением как защищённое от подделки доказательство.",
    confirmAndFinishBtn: "Подтвердить и завершить",
    finalizingEllipsis: "Завершение…",
    sendLinkInsteadBtn: "Отправить ссылку для подписания",
    signatureRequired: "Поставьте подпись, прежде чем продолжить.",
    signatureUploadFailed: "Не удалось загрузить подпись.",
    pdfTimedOut: "Формирование PDF заняло слишком много времени. Отчёт остался сохранён.",
    couldNotSignReport: "Не удалось подписать отчёт.",

    reportCompletedTitle: "Отчёт завершён",
    reportCompletedSubtitle: "Доказательство этого визита сохранено и защищено.",
    dateTimeLabel: "Дата и время",
    locationCapturedLabel: "Зафиксировано · ±5м",
    signatureStatusLabel: "Подпись",
    signedOnSiteLabel: "Подписано на месте",
    linkSentLabel: "Ссылка отправлена",
    reportFallback: "Отчёт",
    openSignedPdfBtn: "Открыть подписанный PDF",
    viewReportBtn: "Посмотреть отчёт",
    doneAction: "Готово",
    pdfNotAvailable: "PDF ещё не готов.",
    couldNotOpenPdf: "Не удалось открыть PDF.",

    statusDraft: "Черновик",
    statusUnsigned: "Не подписано",
    statusCompleted: "Завершено",
    statusOffline: "Офлайн",
    syncSynced: "Синхронизировано",
    syncPending: "Ожидает загрузки",
    syncSyncing: "Синхронизация",
    syncFailed: "Ошибка синхронизации",
    syncOffline: "Сохранено офлайн",
    confidenceHigh: "Высокая уверенность",
    confidenceMedium: "Средняя уверенность",
    confidenceLow: "Низкая уверенность",
    verdictHighQuality: "Высокое качество",
    verdictPartiallyCompleted: "Частично выполнено",
    verdictPoorQuality: "Низкое качество",
    verdictInsufficientData: "Недостаточно данных",
    priceVerdictNotProvided: "Не указано",
    priceVerdictReasonable: "Обоснованно",
    priceVerdictOverpriced: "Завышено",
    priceVerdictSignificantlyOverpriced: "Значительно завышено",
    priceVerdictSuspiciouslyLow: "Подозрительно занижено",
    priceVerdictCannotAssess: "Невозможно оценить",
    roleOwner: "Владелец",
    roleTechnician: "Техник",

    beforeShort: "До",
    afterShort: "После",
    removePhotoLabel: "Удалить фото «{label}» {n}",
    capturePhotoLabel: "Сделать фото",
    signHereHint: "Распишитесь мышью или пальцем",
    offlineBannerText: "Офлайн — ваша работа сохранена на этом устройстве",
    stepCustomer: "Клиент",
    stepDetails: "Детали",
    stepBeforeShort: "До",
    stepVoiceShort: "Голос",
    stepAfterShort: "После",
    stepReviewShort: "Проверка",

    offlineModeTitle: "Офлайн-режим",
    workingOfflineTitle: "Вы работаете офлайн",
    workingOfflineDesc:
      "Продолжайте — каждый отчёт, фото и подпись сохраняются на этом устройстве и синхронизируются автоматически при восстановлении соединения.",
    waitingToUpload: "Ожидает загрузки",
    queuedLabel: "В очереди",
    offlineFooterNote:
      "Весь процесс визита — клиент, фото, голос и подпись — работает без подключения к интернету. Ничего не теряется.",
    syncTitle: "Синхронизация",
    syncingVisits: "Синхронизация визитов",
    someUploadsFailed: "Некоторые загрузки не удались",
    dataIsSafeRetry: "Ваши данные в безопасности. Повторите попытку при лучшем соединении.",
    allSynced: "Всё синхронизировано",
    everyReportBackedUp: "Каждый отчёт сохранён и защищён.",
    connectedWifi: "Подключено · Wi-Fi",
    queueLabel: "Очередь",
    permissionsStatesTitle: "Разрешения и состояния",
    previewEdgeCase: "Предпросмотр экранов для нестандартных ситуаций",
    statesIntro: "Это состояния, которые JobAct показывает, когда доступ к оборудованию заблокирован или что-то идёт не так в полевых условиях.",
    cameraAccessTitle: "Нужен доступ к камере",
    cameraAccessDesc: "JobAct нужна камера, чтобы снять фото до и после как доказательство визита.",
    micAccessTitle: "Нужен доступ к микрофону",
    micAccessDesc: "Разрешите доступ к микрофону, чтобы описывать работу голосом вместо ввода текста.",
    locationAccessTitle: "Нужен доступ к местоположению",
    locationAccessDesc: "Местоположение подтверждает, где произошёл визит. Включите его, чтобы прикрепить GPS-доказательство.",
    gpsUnavailableTitle: "GPS недоступен",
    gpsUnavailableDesc: "Не удалось определить местоположение сейчас. Можно продолжить и прикрепить его позже.",
    uploadFailedTitle: "Загрузка не удалась",
    uploadFailedDesc: "Не удалось загрузить фото. Они сохранены на устройстве и будут отправлены автоматически.",
    voiceProcessFailedTitle: "Не удалось обработать голосовую заметку",
    voiceProcessFailedDesc: "Не удалось сформировать отчёт из записи. Попробуйте снова или введите описание текстом.",
    openSettingsCta: "Открыть настройки",
    retryNowCta: "Повторить сейчас",

    lastVisitLabel: "Последний визит {date}",
    newReportForCustomer: "Новый отчёт для этого клиента",
    visitHistoryLabel: "История визитов",
    noVisitsYet: "Пока нет визитов",
    noVisitsYetDesc: "Создайте первый отчёт для этого клиента.",
    noPhotoComparisonMessage: "К этому отчёту не прикреплено сравнение фото.",
    qualityLabel: "Качество {score}/10",
    confidencePercentLabel: "Уверенность {pct}%",
    priceLabel: "Цена: {verdict}",
    reportDetailsLabel: "Детали отчёта",
    reportIdLabel: "Номер отчёта",
    revisionLabel: "Версия",
    workflowLabel: "Статус процесса",
    signatureLabel3: "Подпись",
    awaitingSignature: "Ожидает подписи",
    couldNotLoadReport: "Не удалось загрузить отчёт.",
    loadingReportEllipsis: "Загрузка отчёта…",
    reportTitleFallback: "Отчёт",
    revisionNumberLabel: "Версия {n}",
  },
} as const

export function t(locale: AppLocale, key: TranslationKey, params?: Params): string {
  return interpolate(translations[locale][key], params)
}

/* ------------------------------------------------------------------ */
/*  Pluralization                                                      */
/* ------------------------------------------------------------------ */

type PluralForm = "one" | "few" | "many"

function pluralFormFor(locale: AppLocale, n: number): PluralForm {
  const count = Math.abs(n)
  if (locale === "ru-RU") {
    const mod10 = count % 10
    const mod100 = count % 100
    if (mod10 === 1 && mod100 !== 11) return "one"
    if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return "few"
    return "many"
  }
  return count === 1 ? "one" : "many"
}

type PluralKey = keyof typeof pluralTemplates["en-US"]

const pluralTemplates = {
  "en-US": {
    visitsScheduled: { one: "{n} visit scheduled", many: "{n} visits scheduled" },
    reportsToSync: { one: "{n} report to sync", many: "{n} reports to sync" },
    reportsCount: { one: "{n} report", many: "{n} reports" },
    photosCaptured: { one: "{n} photo captured", many: "{n} photos captured" },
    photosCount: { one: "{n} photo", many: "{n} photos" },
    visitsToday: { one: "{n} visit", many: "{n} visits" },
    visitsCount: { one: "{n} visit", many: "{n} visits" },
    visitsOnRecord: { one: "{n} visit on record", many: "{n} visits on record" },
    reportsOnRecord: { one: "{n} report on record", many: "{n} reports on record" },
    customersOnFile: { one: "{n} on file", many: "{n} on file" },
    peopleCount: { one: "{n} person", many: "{n} people" },
  },
  "ru-RU": {
    visitsScheduled: {
      one: "{n} визит запланирован",
      few: "{n} визита запланировано",
      many: "{n} визитов запланировано",
    },
    reportsToSync: {
      one: "{n} отчёт для синхронизации",
      few: "{n} отчёта для синхронизации",
      many: "{n} отчётов для синхронизации",
    },
    reportsCount: { one: "{n} отчёт", few: "{n} отчёта", many: "{n} отчётов" },
    photosCaptured: { one: "{n} фото снято", few: "{n} фото снято", many: "{n} фото снято" },
    photosCount: { one: "{n} фото", few: "{n} фото", many: "{n} фото" },
    visitsToday: { one: "{n} визит", few: "{n} визита", many: "{n} визитов" },
    visitsCount: { one: "{n} визит", few: "{n} визита", many: "{n} визитов" },
    visitsOnRecord: {
      one: "{n} визит в истории",
      few: "{n} визита в истории",
      many: "{n} визитов в истории",
    },
    reportsOnRecord: {
      one: "{n} отчёт в базе",
      few: "{n} отчёта в базе",
      many: "{n} отчётов в базе",
    },
    customersOnFile: { one: "{n} в базе", few: "{n} в базе", many: "{n} в базе" },
    peopleCount: { one: "{n} человек", few: "{n} человека", many: "{n} человек" },
  },
} as const

export function tPlural(locale: AppLocale, key: PluralKey, n: number): string {
  const forms = pluralTemplates[locale][key] as Partial<Record<PluralForm, string>>
  const form = pluralFormFor(locale, n)
  const template = forms[form] ?? forms.many ?? forms.one ?? ""
  return interpolate(template, { n })
}

/* ------------------------------------------------------------------ */
/*  Dynamic date / time / greeting                                     */
/* ------------------------------------------------------------------ */

export function formatDate(locale: AppLocale, iso: string, opts?: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat(
    locale,
    opts ?? { year: "numeric", month: "short", day: "numeric" },
  ).format(new Date(iso))
}

export function formatTime(locale: AppLocale, iso: string): string {
  return new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit" }).format(new Date(iso))
}

export function formatDateTime(locale: AppLocale, iso: string): string {
  return `${formatDate(locale, iso)} · ${formatTime(locale, iso)}`
}

export function formatWeekdayDate(locale: AppLocale, date: Date): string {
  return new Intl.DateTimeFormat(locale, { weekday: "long", month: "long", day: "numeric" }).format(date)
}

/** "Good morning/afternoon/evening, {name}" — picked from the given hour (0-23). */
export function greeting(locale: AppLocale, hour: number, name: string): string {
  const key = hour < 12 ? "goodMorning" : hour < 18 ? "goodAfternoon" : "goodEvening"
  return t(locale, key, { name })
}

/* ------------------------------------------------------------------ */
/*  Canonical-value → localized-label lookups                          */
/*                                                                       */
/*  These take a machine value (e.g. `report.status === "draft"`) and   */
/*  return display text only -- the machine value itself is never       */
/*  translated or persisted differently per locale.                     */
/* ------------------------------------------------------------------ */

export function statusLabel(locale: AppLocale, status: string): string {
  switch (status) {
    case "draft":
      return t(locale, "statusDraft")
    case "unsigned":
      return t(locale, "statusUnsigned")
    case "completed":
      return t(locale, "statusCompleted")
    case "offline":
      return t(locale, "statusOffline")
    default:
      return status
  }
}

export function syncLabel(locale: AppLocale, state: string): string {
  switch (state) {
    case "synced":
      return t(locale, "syncSynced")
    case "pending":
      return t(locale, "syncPending")
    case "syncing":
      return t(locale, "syncSyncing")
    case "failed":
      return t(locale, "syncFailed")
    case "offline":
      return t(locale, "syncOffline")
    default:
      return state
  }
}

export function confidenceLabel(locale: AppLocale, level: string): string {
  switch (level) {
    case "high":
      return t(locale, "confidenceHigh")
    case "medium":
      return t(locale, "confidenceMedium")
    case "low":
      return t(locale, "confidenceLow")
    default:
      return level
  }
}

export function roleLabel(locale: AppLocale, role: string): string {
  switch (role) {
    case "owner":
      return t(locale, "roleOwner")
    case "technician":
      return t(locale, "roleTechnician")
    default:
      return role
  }
}

/** Covers both `VisualAuditResult.verdict` and `PriceAssessment.price_verdict` --
 * the two enums never overlap, so one lookup is enough. Falls back to a
 * humanized version of the raw value for anything not yet mapped, rather
 * than silently dropping an AI-supplied enum value. */
export function verdictLabel(locale: AppLocale, verdict: string): string {
  switch (verdict) {
    case "high_quality":
      return t(locale, "verdictHighQuality")
    case "partially_completed":
      return t(locale, "verdictPartiallyCompleted")
    case "poor_quality":
      return t(locale, "verdictPoorQuality")
    case "insufficient_data":
      return t(locale, "verdictInsufficientData")
    case "not_provided":
      return t(locale, "priceVerdictNotProvided")
    case "reasonable":
      return t(locale, "priceVerdictReasonable")
    case "overpriced":
      return t(locale, "priceVerdictOverpriced")
    case "significantly_overpriced":
      return t(locale, "priceVerdictSignificantlyOverpriced")
    case "suspiciously_low":
      return t(locale, "priceVerdictSuspiciouslyLow")
    case "cannot_assess":
      return t(locale, "priceVerdictCannotAssess")
    default:
      return verdict.replaceAll("_", " ")
  }
}

/* ------------------------------------------------------------------ */
/*  Currency -- an independent preference, never derived from `locale`  */
/* ------------------------------------------------------------------ */

/** Formats `value` as money in `currency` ($ / ₽ and symbol placement
 * follow `currency`); `locale` only affects digit grouping/decimal
 * conventions, exactly like `Intl.NumberFormat` always has. Currency
 * selection must never be inferred from the interface language. */
export function formatCurrency(locale: AppLocale, value: number, currency: string = "USD"): string {
  // `currencyDisplay: "narrowSymbol"` is required so the currency symbol
  // itself (e.g. ₽) stays the same regardless of the interface language --
  // ICU's default "symbol" display falls back to the ISO code ("RUB") for
  // currencies a given locale doesn't customarily pair with a glyph, which
  // would make the amount look like it was rendered in the wrong currency.
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    currencyDisplay: "narrowSymbol",
    maximumFractionDigits: 0,
  }).format(value)
}
