# REA analysis: GamerHack g2all

**Historical acquisition report:** the original byte-parity observations below describe the first mirror. The subsequent preventive hardening changed `index.html` and revision comments in the five cache manifests, and added verified in-memory asset serving. See `STABILITY.md` and `evidence/local-overrides.json` for the current implementation. Original exploit scripts and native payload bytes remain unchanged.

## Result and scope

Inspected the deployed public page at https://gamerhack.github.io/g2all/ and recreated it locally in `dist/`. All 92 downloaded files (2,409,977 bytes) match their Git blob identities at repository commit `23c946a7f85f1338ea2b78163e72e0ce9bc82b68`. Per-file source URLs and SHA-256 hashes are recorded in `evidence/upstream-files.json`.

This is a preserved static mirror plus a local Windows launcher and HTTP server. No original site files were modified. The console exploit modules and native payloads were not executed during analysis.

## Observed browser behavior

REA launched a temporary Chrome instance, navigated to the original URL, waited 500 ms, and captured its DOM, accessibility tree and network events. The desktop page shows the PS4-only compatibility message. Its document, stylesheet and background image returned HTTP 200; no page errors were observed in that capture. REA terminated its temporary browser after capture.

The same scenario against `http://127.0.0.1:8088/g2all/` produced identical DOM and accessibility SHA-256 values and no page errors. The local screenshot is `evidence/local-preview.png`. Matching these observations establishes parity for the desktop branch, not for firmware-dependent execution.

| Evidence | Record |
| --- | --- |
| Original REA capture | `ev_c3d552ce17ddfadbb6f5bd41d911d912df474203ef431d5514c7ac2580623b95` in `evidence/rea-original-browser.json` |
| Local REA capture | `ev_78fcf6582a377a3b550c62f27b6ef3b03db7006165a7fe897ffc8a3db59a0c8b` in `evidence/rea-local-browser.json` |
| DOM SHA-256, both captures | `a736159c974e20eeeb2813ff647ac3944036b139629cc65ed1252bad775285a4` |
| Accessibility SHA-256, both captures | `fc5ae288920dc52c1bb8445806d50ece5e239c380447e9a8831d7fce94c0f4a2` |

REA captures cover only their observation windows. Network response bodies and request initiator stacks were not captured. Full limitations remain in the saved evidence.

## Static behavior and firmware routing

`dist/g2all/index.html` extracts firmware from the `PlayStation 4` user-agent string. Non-PS4 browsers receive a compatibility message. The PS4 branch reads `window.applicationCache.status`: when it is zero, the page redirects to the appropriate cache installer; otherwise it loads a firmware-specific script. The following is source routing, not a hardware compatibility certification.

| Firmware predicate | Cache installer | Cached entry script |
| --- | --- | --- |
| 5.05 or 5.07 | `cache505.html` | `505/exploit.js` |
| 7.00–8.52 | `cache700.html` | `700/alert.js` (module) |
| 9.00–9.60 | `cache900.html` | `900/alert.js` (module) |
| 10.00–11.02 | `cachecss.html` | `css/main.js`, then `doJb()` after 500 ms |
| 11.50–12.02 | `cacheslopkit.html` | `slopkit/chain_lapse.js` (module) |
| 12.50–13.00 | `cacheslopkit.html` | `slopkit/chain_poops.js` (module) |
| 13.02–13.52 | `cacheslopkit.html` | `slopkit/jb.js?v=19` (module) |

The cache selection broadly covers 11.50–13.52, while its execution branches have narrower predicates. The source has no final unsupported-firmware fallback in its cached execution branch. Therefore the headline is broader than the actual routing guarantees. `slopkit/ps4_offsets.js` also labels several offsets, including 11.52, 12.02 and 12.52, as untested on hardware.

The five cache installer pages use HTML Application Cache manifests and progress/completion/error events. They update history and ask the user to close and reopen the browser after installation. The PS4 branch directly depends on Application Cache with no availability guard. A modern desktop browser cannot validate that legacy console behavior.

## Dependency and hosting audit

All 99 CACHE entries resolve locally: 505 = 5, 700 = 31, 900 = 26, CSS = 17, Slopkit = 20. These totals count shared assets more than once. The manifests include the stylesheet, image, index page, payload and firmware assets; `NETWORK: *` permits network fallbacks.

Preserving `dist` as the server root keeps `../style.css` and the stylesheet's `img.jpg` reference correct. Query strings such as `core.js?v=10` and `jb.js?v=19` map to their unchanged files. The server also accepts backslash-separated paths used in the original manifests. JavaScript is served as `application/javascript`, manifests as `text/cache-manifest`, and binary payloads as `application/octet-stream`.

Static inspection of the HTML, JavaScript and manifests found no required remote service for ordinary asset loading. External URLs found were credits or source/license comments. This is a bounded static finding, not proof of all possible runtime behavior. Slopkit includes fire-and-forget diagnostic POSTs to `/t` or `/g2all/t`; the local static server does not implement these endpoints. The original source does not await or check their responses. An unused debug helper in `505/exploit.js` references absent `dumpFileMem.php`; debug uploading is not provided by this mirror.

## Local implementation and validation

The Python server serves only `dist/`, redirects `/` to `/g2all/`, disables directory listings, rejects explicit parent-directory traversal and revalidates resources with `Cache-Control: no-cache`. This header does not replace the console's Application Cache. No credentials, external backend, software installation, firewall change, router change or startup task was added. Original credit links remain clickable.

`tools/verify.py` successfully checked all 92 served file hashes, all 99 cache references, the manifest/module/binary content types, query-string handling, backslash paths, HEAD requests, the root redirect and isolation of server/evidence files. Detailed results are in `evidence/verification.json`. The start/stop scripts are intended to leave the server available in the background until stopped or the PC shuts down.

## Remaining unknowns

- Actual PS4 firmware execution, native payload behavior, exploit success and console stability were not tested.
- Offline cache installation and offline reopening require a compatible PS4 browser and were not tested on hardware.
- A separate console's network path and any Windows Firewall restriction remain unverified.
- The browser-control connector had no available browser for a visible handoff; REA's independent temporary-browser verification succeeded. Open the local URL manually.

All investigation questions needed for a local static mirror are answered. Hardware-specific compatibility and offline behavior remain explicitly unresolved.
