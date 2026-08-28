interface AnalysisInput {
  visitId: string | undefined
  rawNotes: string
  beforePhotoCount: number
  afterPhotoCount: number
}


/** Identity of evidence that is safe to use as the processing effect dependency. */
export function analysisInputKey(input: AnalysisInput): string {
  return JSON.stringify([
    input.visitId,
    input.rawNotes,
    input.beforePhotoCount,
    input.afterPhotoCount,
  ])
}
