import assert from "node:assert/strict"
import test from "node:test"

import { formatGpsEvidence } from "./location-evidence.ts"


test("captured GPS evidence reports the real coordinates and accuracy", () => {
  assert.equal(
    formatGpsEvidence({ lat: 55.75222, lon: 37.61556, accuracy: 12.4 }),
    "55.75222, 37.61556 · ±12m",
  )
})
