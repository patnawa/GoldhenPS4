# Changelog

Local host builds. The bundled GoldHEN payload version is listed per build; the
site is a mirror of GamerHack's g2all loader with the local hardening on top.
Detailed safety reasoning for each change lives in `STABILITY.md`.

## 1.0.7 (2026-11-18)

- Web loader synced with upstream GamerHack's current build: `jb.js` hands the kernel stage to the new `afterglow.js` (APM use-after-free, one stage per firmware), and `ps4_offsets.js` carries upstream's own tables.
- Real per-firmware patch blobs shipped: `1400.bin`, `1402.bin`, `1304.bin`, `1252.bin`, `1202.bin`. The 1.0.6 habit of feeding `1352.bin` to a 14.x kernel is gone.
- FW 14.00/14.02 now run upstream's measured kernel data instead of local aliases. 14.01 has no afterglow stage and refuses cleanly before any kernel write (`jb.js` `SUPPORTED` list is upstream's — don't extend it locally).
- Cache revisions: slopkit manifest 15, `jb.js?v=21`, `ps4_offsets.js?v=4`; `EXPECTED_BLOB_BYTES` extended to the five new 641-byte blobs.
- Local hardening on the 11.50–13.00 chains, `core.js`, `mem.js` and every race parameter is untouched — upstream's `core.js` is behind ours.
- Validation: launcher 45/45 (incl. manifest coverage check), Lapse 11/11, server integrity 6/6, served hashes 98/98, manifest resources 106/106.
- Bug hunt after the sync: new `tools/test-offsets.cjs` (52 checks, wired into Pages CI) proves every unguarded offset key resolves for every routed firmware and that every routed firmware has its blob; it caught the 11.50 table surviving only because the keys are read guarded. Fixed a wrong-message path: 14.01 had no offsets entry at all, so jb.js bailed as "not a PS4 browser" before its `SUPPORTED` gate — a local 14.01 alias now lets the gate refuse it explicitly.
- Route smoke without a console (`evidence/route-smoke-1.0.7.json`): 11.50 reaches the attempt stage with the right blob and payload size and zero page errors; 14.02 passes every table check and resolves 1402.bin, then stops at the WebKit primitive (desktop Chrome).
- Unproven on hardware: 14.x behaviour under afterglow.

## 1.0.6 (2026-11-18)

- Bundled GoldHEN payload upgraded to official beta **v2.4b18.14** (`goldhen_2.4b18.14.bin`, 298,776 bytes, sha256 `c5480587…7d57e9ba8b`); the whole upstream changelog is "added support for 14.02".
- Firmware **14.02** is now a routed target: launcher gate, SlopKit cache page, `jb.js` route and `slopkit.manifest` selection accept up to 14.02. 14.01 is routed through the same path; 14.03+ still stop as unsupported.
- New `PS4["14.02"]` offsets entry, aliased through `PS4["14.00"]` to the 13.52 table, and `PS4["14.01"]` aliased to 14.00. All PENDING-HW-TEST — no 14.00/14.02 dump measured here.
- Cache-busters: `ps4_offsets.js?v=3` on all three SlopKit chains, `jb.js?v=20`; all five cache manifests bumped (slopkit revision 14) so console AppCache refreshes.
- Blob size check moved to 298,776 bytes; every payload reference renamed.
- Launcher harness 44/44, Lapse harness 11/11, server integrity 6/6, served-hash verify 92/92, manifest resources 100/100.
- Unproven on hardware: payload behaviour on 14.00–14.02 and the aliased offsets.

## 1.0.5 (2026-11-03)

- Bundled GoldHEN payload upgraded to official beta v2.4b18.13 (297,496 bytes; adds firmware 14.00, fixes the FTP `SIZE` issue).
- Firmware 14.00 routed through the site with a `PS4["14.00"]` offsets alias from the 13.52 set (PENDING-HW-TEST).
- Pre-execution size checks, integrity records and AppCache revisions updated.

## 1.0.4 (2026-10-29)

- HTTP/1.1 keep-alive server for faster first-time cache installs.
- Already-loaded session guard; bounded clean-failure auto-retry (max 2, never after a kernel commit).
- Patch blob and payload size checks before any kernel stage; 1 MB diagnostics log rotation.

## 1.0.3 (2026-10-29)

- Failed primitive attempts release their ~130 MB of grooming memory before retrying (fixes the intermittent freeze).
- A session whose last run left the kernel unsafe refuses to relaunch and asks for a power cycle.
- Stage-2 leak diagnostics, reboot banner naming the last diagnostic, success banner.

## 1.0.2

- Preventive launcher checks, verified in-memory asset server, professional dark console layout.

## 1.0.0

- First packaged Windows host: installer, portable ZIP, static site ZIP, uninstall support.

## Payload line (upstream GoldHEN)

- v2.4b18.14 — 14.02. v2.4b18.13 — 14.00, FTP SIZE fix. v2.4b18.12 — 13.02/13.04/13.50.
  v2.4b18.11 — 13.52. Earlier entries: see the upstream archive `CHANGELOG.md`.
