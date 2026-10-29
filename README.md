# Local GoldHEN host

## Online website

Open **https://patnawa.github.io/GoldhenPS4/** in the PS4 browser. The root page forwards to the host at https://patnawa.github.io/GoldhenPS4/g2all/. The online version does not require the PC server to be running. Desktop browsers intentionally display the PS4-only message; console execution and offline cache installation still require PS4 hardware testing.

GitHub Pages publishes `dist/` through `.github/workflows/pages.yml`. Site changes pushed to `main` deploy automatically after file-integrity and launcher checks pass. You can also run **Deploy GitHub Pages** manually from the repository's Actions tab. Repository **Settings → Pages → Source** must be **GitHub Actions**. Only the static site is published; the Python server is used for local hosting.

## Install on another computer

Version 1.0.4 adds load performance and robustness on top of the 1.0.3 hardening: HTTP/1.1 keep-alive makes first-time cache installation faster over the LAN, an already-loaded session guard skips pointless re-runs of the primitive, clean failures auto-retry (bounded to two attempts, never after a kernel commit), the patch blob and payload are size-checked before any kernel stage, and the diagnostics log rotates at 1 MB. Version 1.0.3 hardened the load path itself: failed primitive attempts release their ~130 MB of grooming memory before retrying (the intermittent freeze while loading), a session whose last run left the kernel unsafe refuses to relaunch and asks for a power cycle, stage-2 leak failures report their exact reason, the reboot banner names the last diagnostic, the success banner asks you to close the browser before shutting down, and the local server records the console's diagnostic posts in `.runtime/console-diag.log`.

Download **GoldHEN-Local-Host-Setup-1.0.4-x64.exe** from the [v1.0.4 release](https://github.com/patnawa/GoldhenPS4/releases/tag/v1.0.4) for Windows 10/11 x64. It bundles the runtime, working site, GoldHEN payload, shortcuts and uninstall support. No Python installation is needed on the destination PC. The release also includes a portable ZIP, a static site ZIP, `SHA256SUMS.txt`, and `START-HERE.txt` with transfer and network instructions. Built packages are release attachments and are not stored in Git. The package was tested through installation, all 92 HTTP asset hashes, start/stop, shortcut registration and uninstall in a separate folder with Python excluded from PATH (see `package-test.json`).

A local copy of https://gamerhack.github.io/g2all/ with preventive launcher checks and a verified-file HTTP server. Native payload bytes, offsets and race parameters remain byte-for-byte upstream copies; everything around them is locally maintained. The launcher, five cache installer pages, five cache manifest revision comments, and the Lapse entry script have local edits, recorded in `evidence/local-overrides.json`. What the local code adds on top of upstream:

- **Launcher (index.html, shared by all firmwares):** waits for its DOM and an idle complete cache, rejects unsupported route ranges, handles missing AppCache, prevents repeated launches, refuses to rerun the Lapse chain in a session the last run left kernel-unsafe (asks for a power cycle), refuses to rerun in a session that already loaded GoldHEN, and reports cache update/error states.
- **Lapse entry script (firmware 11.50-12.02):** stops on failed, empty or wrong-size required downloads before console execution (the patch blob and payload are checked against exact expected byte sizes), makes failure diagnostics visible on screen, releases the primitive's ~130 MB of grooming memory between retries, stops the race heartbeat when execution fails, reports stage-2 leak-loop telemetry (submit return codes and window contents) on failure, names the real last diagnostic on the reboot banner, marks the session loaded on success, and auto-reloads up to twice on clean failures only (never after a kernel commit).
- **Console pages:** a professional dark layout tuned for the PS4 browser, with the host build version visible on the page.
- **Local server (server.py):** verifies all 92 assets against the hash records before listening and serves an immutable in-memory snapshot, answers the console's fire-and-forget diagnostic POSTs with 204 and logs them to `.runtime/console-diag.log` (rotated at 1 MB), and speaks HTTP/1.1 keep-alive so first-time cache installation reuses one connection instead of opening ~20.

The original author credits are preserved.

## Open and run

- On this PC: http://localhost:8088/g2all/
- On a device connected to the PC's network: `http://<PC-IP-address>:8088/g2all/`.
- Double-click **Start-Host.cmd** to start the server in the background.
- Double-click **Stop-Host.cmd** to stop this project's server.

Start-Host prints the PC's current network addresses. Running from source requires Python 3; the packaged release includes its own runtime. No npm dependencies or build step are needed to run from source. The default port is 8088.

From PowerShell, `./Start-Host.ps1 -Port 8088` starts it, and `./Stop-Host.ps1` stops it. To run in the foreground instead, first stop the background server, then run `python server.py --port 8088`; Ctrl+C stops it.

Launch normally, without Run as administrator. If an older host was started elevated, Stop may request Windows administrator permission once to stop it safely. Version 1.0.1 guards missing process metadata, verifies the saved target and process start time, reports repeated starts/stops, and preserves CMD exit codes. Regression command: `python tools/test-launchers.py`.

## Use from a PS4

Open the network URL in the PS4 browser while the PC server is running. The preserved site detects the firmware, chooses the matching offline cache, and displays installation progress. Follow its close-and-reopen message after successful installation. Desktop browsers intentionally show the original PS4-only message.

Use a network address that the console can reach. If the PC page opens but the PS4 cannot connect, check that both devices are on a reachable network and that Windows Firewall permits inbound TCP 8088 on that network. Firewall and router settings were not changed. Connectivity from a separate device has not been verified.

## Files

- `dist/`: the 92 inventoried site files, including twelve documented host edits, plus the GitHub Pages root redirect.
- `server.py`: standard-library HTTP server with the required JavaScript and AppCache MIME types; console diagnostic POSTs to `/t` or `/g2all/t` are answered 204 and logged to `.runtime/console-diag.log` (rotated at 1 MB); HTTP/1.1 keep-alive for faster first-time cache installs.
- `ANALYSIS.md`: behavior, firmware routing, evidence and limitations.
- `evidence/`: downloaded-file hashes, REA captures, screenshot and HTTP verification result.
- `.runtime/`: process record and server logs, created on launch.

Run `python tools/verify.py` with the server running to verify every asset's served SHA-256 against the upstream record plus reviewed local overrides, all 99 manifest resource references, MIME types, query strings, redirects and server boundaries. `tools/acquire.py` refuses to overwrite a host with local stability edits; upstream updates must be acquired separately and reviewed.

Run `node tools/test-host.cjs` (40 checks), `node tools/test-lapse-host.cjs` (11 checks) and `python tools/test-server.py` (6 checks) for the preventive regression checks. The launcher tests intercept script insertion and do not run console exploit code. The server verifies all assets before listening and serves their immutable in-memory snapshot. After intentional site edits, review and update the relevant hash record and restart the server; simply changing a file on disk will not change the running site.

Run `node tools/test-lapse-host.cjs` for 11 additional checks of the 11.50 Lapse entry script with inert primitive imports. Failed HTTP requests, network errors and empty required files must stop before the primitive starts. Execution failures retain restart advice and display their actual error plus an on-screen log. These tests do not reproduce the console's intermittent kernel/primitive failure. After the online host updates, allow the PS4 cache update to finish and follow its close-and-reopen instruction. If loading still fails, record the displayed reason and the last diagnostic lines.

The launcher waits for its DOM and a complete idle cache, handles unsupported firmware and unavailable cache APIs, and prevents repeated entry-script launches. Cache checks that fail offline may still use an existing complete idle cache. New cache installations and cache updates require closing and reopening the browser. These checks do not establish crash-free execution on PS4 hardware. See `STABILITY.md` for findings and validation limits.

The mirror was acquired from upstream commit `23c946a7f85f1338ea2b78163e72e0ce9bc82b68`. It is not a new exploit implementation or an assertion of support for every firmware named in the original headline. Actual PS4 execution and offline caching require hardware testing.
