# Preventive stability review

## Local launcher repair (version 1.0.1)

The original local Stop command reproduced `InvokeMethodOnNull`: Windows exposed PID 2216 and its creation time but returned null for its command line and executable path. The current shell was not elevated; the old server had been launched elevated. The original script called `.Contains()` on that missing command line. Start then reported already running because the server had never stopped.

The launchers now guard missing metadata and request Windows elevation only to verify and stop an older elevated instance. They validate the saved target and process start time, leave unrelated processes alone, report repeated operations clearly, retain CMD exit codes, and show network addresses even when already running. A second discovered edge case involved an exited packaged process briefly remaining enumerable; Stop now checks `HasExited` instead of treating enumeration alone as proof it is alive.

Validation: the original elevated server was stopped successfully with the repaired script and replaced by a normal-user instance. Actual CMD Start/Stop/Start passed. `python tools/test-launchers.py` passes metadata, alternate working-directory, path-with-spaces, repeated-operation, unrelated-PID and exited-record checks. The rebuilt 1.0.1 installer passed install/start/stop/uninstall and all 92 served asset hashes. The PS4 site files were not edited in this launcher repair.

The user has not yet tested the host on a PS4. No console crash was reproduced, and no crash-rate improvement is claimed. This pass addresses observable host failures and prevents serving missing or altered local assets. Hardware-specific exploit behavior remains unverified.

## Reproduced host failures

`node tools/test-host.cjs` initially passed 3 of 10 checks. It exercised the actual inline launcher while intercepting appended scripts so no exploit code ran. Missing AppCache threw `Cannot read properties of undefined (reading 'status')`. Unsupported cached firmware stayed at Loading. States 2–5 all appended a console script, and script insertion happened before the page's status element existed.

The cause was the launcher's broad `status != 0` branch, together with missing API/firmware fallback checks and eager execution before DOM readiness. The chosen preventive behavior is to wait during CHECKING/DOWNLOADING and require reopening after updates; this reduces overlapping host activity but is not proof that the previous overlap caused kernel panics. AppCache status values and event transitions were verified against the [W3C historical Application Cache specification](https://www.w3.org/TR/2011/WD-html5-20110525/offline.html#application-cache-api).

## Changes

- `dist/g2all/index.html`: wait for DOM readiness; reject unsupported route ranges; handle missing AppCache; launch only with an idle complete cache; wait for a cache check to finish; report update/obsolete/error states; prevent repeated launches. An unsuccessful offline update check can still use an existing complete idle cache. Entry scripts and firmware predicates within supported route ranges remain the same.
- All five `.manifest` files: a local revision comment makes the cache recognize this host update. Their resource lists remain unchanged.
- `server.py`: verify all 92 assets against acquisition hashes plus explicit reviewed overrides before opening a listening socket. Reject missing, truncated or same-size corrupted files. Serve the verified in-memory snapshot, so subsequent disk changes cannot turn a running installation into a mixture of file versions. Only inventoried files are served.
- `tools/verify.py`: verify both original assets and the six explicitly recorded host edits. `tools/acquire.py` refuses to overwrite these edits silently.

The original launcher and manifests are backed up in `evidence/original-launcher/`. Original provenance remains in `evidence/upstream-files.json`; approved local byte identities are separate in `evidence/local-overrides.json`. This integrity check detects accidental changes against the records; it is not a signature or an authenticity guarantee against someone who can alter both files and records.

## Validation

- `node tools/test-host.cjs`: **36/36 passed**, including route boundaries, unsupported gaps, cache event transitions, offline error recovery with an existing cache, script-load errors and duplicate-event handling. Appended exploit scripts were never evaluated.
- `python tools/test-server.py`: **6/6 passed**. Tests reject missing, truncated and same-size corrupted fixtures; accept valid/reviewed bytes; and confirm through HTTP that a running server retains the verified bytes after its underlying file changes.
- `python tools/verify.py`: **92/92 served hashes** and **99/99 manifest resource references** passed, plus MIME, query-string, backslash-path, redirect, HEAD and path-boundary checks.
- The restarted local server passed a fresh REA desktop-browser capture with no page errors. Full evidence is `evidence/rea-stability-browser.json`.

Kernel exploit timings, memory layouts, offsets, cleanup sequences, firmware modules and GoldHEN payload binaries were deliberately kept at their upstream bytes because no PS4 execution feedback is available to validate changes there. This review does not certify individual firmware builds, AppCache installation on PS4, native payload behavior, or freedom from crashes. Firmware versions marked untested in upstream offsets remain untested.

The host remains available at http://localhost:8088/g2all/ and on the PC's reachable network address. If an earlier revision was ever cached on a console, its cached copy must be updated before these launcher changes take effect.
