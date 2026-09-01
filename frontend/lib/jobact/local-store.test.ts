import { describe, test } from "node:test"
import assert from "node:assert/strict"

import "fake-indexeddb/auto"

// `local-db.ts` opens the database lazily on first use and caches the
// connection promise at module scope, so every test in this file shares
// one fake-indexeddb-backed database -- draft/blob/check ids are always
// fresh UUIDs, so tests don't need isolation between them beyond that.
const {
  newDraft,
  saveDraft,
  loadDraft,
  deleteDraft,
  finalizeDraft,
  putBlob,
  getBlob,
  saveCheck,
  getCheck,
  listRecentChecks,
} = await import("./local-store.ts")

describe("local-store", () => {
  test("newDraft seeds a blank draft with the given resume screen", () => {
    const draft = newDraft("gps")

    assert.equal(draft.screen, "gps")
    assert.equal(draft.beforePhotoIds.length, 0)
    assert.equal(draft.amountConfirmed, false)
    assert.ok(draft.id)
  })

  test("saveDraft/loadDraft round-trip and bump updatedAt", async () => {
    const draft = newDraft("visitStart")
    const originalUpdatedAt = draft.updatedAt

    await saveDraft(draft)
    const loaded = await loadDraft(draft.id)

    assert.ok(loaded)
    assert.equal(loaded!.id, draft.id)
    assert.equal(loaded!.screen, "visitStart")
    // saveDraft always stamps a fresh updatedAt, even if the caller didn't.
    assert.ok(new Date(loaded!.updatedAt).getTime() >= new Date(originalUpdatedAt).getTime())
  })

  test("loadDraft returns undefined for an unknown id", async () => {
    const loaded = await loadDraft(crypto.randomUUID())
    assert.equal(loaded, undefined)
  })

  test("deleteDraft also deletes every blob attached to that draft", async () => {
    const draft = newDraft("beforePhotos")
    await saveDraft(draft)
    const blobId = await putBlob(draft.id, "before", new Blob(["fake-jpeg"]), "image/jpeg")

    await deleteDraft(draft.id)

    assert.equal(await loadDraft(draft.id), undefined)
    assert.equal(await getBlob(blobId), undefined)
  })

  test("finalizeDraft deletes only the draft record, keeping its blobs for the check that now owns them", async () => {
    // Regression test: a completed check's PDF/photo blobs are stored
    // under the draft's id as `draftId` (see `putBlob` call sites in
    // `SignatureScreen.finishReport`), and the check record references
    // those same blob ids afterward. Cascading blob deletion here (as
    // `deleteDraft` correctly does for an abandoned draft) would silently
    // corrupt every just-completed check -- caught via a live browser
    // walkthrough where "Открыть подписанный PDF" reported "PDF ещё не
    // готов" right after a successful signature.
    const draft = newDraft("signature")
    await saveDraft(draft)
    const pdfBlobId = await putBlob(draft.id, "pdf", new Blob(["fake-pdf"]), "application/pdf")
    await saveCheck({
      id: draft.id,
      humanId: "JA-TEST-FINALIZE",
      customerName: "Ada Lovelace",
      customerAddress: "12 Analytical Engine Way",
      customerPhone: "",
      customerServiceType: "Plumbing",
      gpsLat: null,
      gpsLon: null,
      workCompleted: "Replaced the valve.",
      materials: [],
      amountCents: 1000,
      currency: "RUB",
      visualComparison: null,
      aiConfidence: "high",
      signed: true,
      signerName: "Ada Lovelace",
      beforePhotoIds: [],
      afterPhotoIds: [],
      pdfBlobId,
      completedAt: new Date().toISOString(),
    })

    await finalizeDraft(draft.id)

    assert.equal(await loadDraft(draft.id), undefined)
    const pdfRecord = await getBlob(pdfBlobId)
    assert.ok(pdfRecord, "the PDF blob must survive finalizeDraft")
    const check = await getCheck(draft.id)
    assert.equal(check?.pdfBlobId, pdfBlobId)
  })

  test("putBlob/getBlob round-trip the blob and its content type", async () => {
    const draft = newDraft("beforePhotos")
    await saveDraft(draft)
    const content = new Blob(["fake-jpeg-bytes"], { type: "image/jpeg" })

    const blobId = await putBlob(draft.id, "before", content, "image/jpeg")
    const record = await getBlob(blobId)

    assert.ok(record)
    assert.equal(record!.draftId, draft.id)
    assert.equal(record!.kind, "before")
    assert.equal(record!.contentType, "image/jpeg")
    assert.equal(record!.blob.size, content.size)
  })

  test("listRecentChecks returns newest-first and respects the limit", async () => {
    // Other tests in this file also call `saveCheck` against the same
    // shared fake-indexeddb database (see the top-of-file note), so this
    // uses far-future timestamps to guarantee these three checks sort
    // ahead of anything else already in the store, then filters the
    // result down to just its own ids before asserting order.
    const ids: string[] = []
    for (let i = 0; i < 3; i += 1) {
      const id = crypto.randomUUID()
      ids.push(id)
      await saveCheck({
        id,
        humanId: `JA-TEST-${i}`,
        customerName: "Ada Lovelace",
        customerAddress: "12 Analytical Engine Way",
        customerPhone: "",
        customerServiceType: "Plumbing",
        gpsLat: null,
        gpsLon: null,
        workCompleted: "Replaced the valve.",
        materials: [],
        amountCents: 1000,
        currency: "RUB",
        visualComparison: null,
        aiConfidence: "high",
        signed: true,
        signerName: "Ada Lovelace",
        beforePhotoIds: [],
        afterPhotoIds: [],
        pdfBlobId: null,
        completedAt: new Date(2099, 0, 1 + i).toISOString(),
      })
    }

    const recent = (await listRecentChecks(50)).filter((check) => ids.includes(check.id))
    assert.deepEqual(
      recent.map((check) => check.id),
      [ids[2], ids[1], ids[0]],
    )

    // The 2099 dates above are later than anything else in the shared
    // store, so a limit of 1 must return exactly this test's newest check.
    const [newest] = await listRecentChecks(1)
    assert.equal(newest.id, ids[2])
  })
})
