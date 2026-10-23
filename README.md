# Local GoldHEN host

## Online website

Open **https://patnawa.github.io/GoldhenPS4/** in the PS4 browser. The root page forwards to the host at https://patnawa.github.io/GoldhenPS4/g2all/. The online version does not require the PC server to be running. Desktop browsers intentionally display the PS4-only message; console execution and offline cache installation still require PS4 hardware testing.

GitHub Pages publishes `dist/` through `.github/workflows/pages.yml`. Site changes pushed to `main` deploy automatically after file-integrity and launcher checks pass. You can also run **Deploy GitHub Pages** manually from the repository's Actions tab. Repository **Settings → Pages → Source** must be **GitHub Actions**. Only the static site is published; the Python server is used for local hosting.

## Install on another computer

Download **GoldHEN-Local-Host-Setup-1.0.1-x64.exe** from the [v1.0.1 release](https://github.com/patnawa/GoldhenPS4/releases/tag/v1.0.1) for Windows 10/11 x64. It bundles the runtime, working site, GoldHEN payload, shortcuts and uninstall support. No Python installation is needed on the destination PC. The release also includes a portable ZIP, a static site ZIP, `SHA256SUMS.txt`, and `START-HERE.txt` with transfer and network instructions. Built packages are release attachments and are not stored in Git. The package was tested through installation, all 92 HTTP asset hashes, start/stop, shortcut registration and uninstall in a separate folder with Python excluded from PATH. The original user reported that the PS4 host works; no firmware version was supplied.

A local copy of https://gamerhack.github.io/g2all/ with preventive launcher checks and a verified-file HTTP server. Firmware-specific scripts, native payloads, styling and background remain byte-for-byte upstream copies. The launcher, five cache installation pages, and five cache manifest revision comments have local edits, recorded in `evidence/local-overrides.json`. The original author credits are preserved.

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

- `dist/`: the 92 preserved site files, including eleven documented host edits, plus the GitHub Pages root redirect.
- `server.py`: standard-library HTTP server with the required JavaScript and AppCache MIME types.
- `ANALYSIS.md`: behavior, firmware routing, evidence and limitations.
- `evidence/`: downloaded-file hashes, REA captures, screenshot and HTTP verification result.
- `.runtime/`: process record and server logs, created on launch.

Run `python tools/verify.py` with the server running to verify every asset's served SHA-256 against the upstream record plus reviewed local overrides, all 99 manifest resource references, MIME types, query strings, redirects and server boundaries. `tools/acquire.py` refuses to overwrite a host with local stability edits; upstream updates must be acquired separately and reviewed.

Run `node tools/test-host.cjs` and `python tools/test-server.py` for the 42 preventive regression checks. The launcher tests intercept script insertion and do not run console exploit code. The server verifies all assets before listening and serves their immutable in-memory snapshot. After intentional site edits, review and update the relevant hash record and restart the server; simply changing a file on disk will not change the running site.

The launcher waits for its DOM and a complete idle cache, handles unsupported firmware and unavailable cache APIs, and prevents repeated entry-script launches. Cache checks that fail offline may still use an existing complete idle cache. New cache installations and cache updates require closing and reopening the browser. These checks do not establish crash-free execution on PS4 hardware. See `STABILITY.md` for findings and validation limits.

The mirror was acquired from upstream commit `23c946a7f85f1338ea2b78163e72e0ce9bc82b68`. It is not a new exploit implementation or an assertion of support for every firmware named in the original headline. Actual PS4 execution and offline caching require hardware testing.
