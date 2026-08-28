import assert from "node:assert/strict"
import test from "node:test"

import { analysisInputKey } from "./analysis-run.ts"


test("a queued report result does not change the active analysis input", () => {
  const beforeQueue = analysisInputKey({
    visitId: "visit-1",
    rawNotes: "Replaced the leaking pipe and tested the repair.",
    beforePhotoCount: 1,
    afterPhotoCount: 1,
  })
  const afterQueue = analysisInputKey({
    visitId: "visit-1",
    rawNotes: "Replaced the leaking pipe and tested the repair.",
    beforePhotoCount: 1,
    afterPhotoCount: 1,
  })

  assert.equal(afterQueue, beforeQueue)
})


test("changing evidence produces a new analysis input", () => {
  const original = analysisInputKey({
    visitId: "visit-1",
    rawNotes: "Replaced the leaking pipe and tested the repair.",
    beforePhotoCount: 1,
    afterPhotoCount: 1,
  })
  const changed = analysisInputKey({
    visitId: "visit-1",
    rawNotes: "Replaced the leaking pipe and tested the repair.",
    beforePhotoCount: 2,
    afterPhotoCount: 2,
  })

  assert.notEqual(changed, original)
})
