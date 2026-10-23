GoldHEN Local Host 1.0.2 - Windows 10/11 x64

ONLINE WEBSITE
https://patnawa.github.io/GoldhenPS4/g2all/
The path is case-sensitive: use GoldhenPS4 exactly as shown.

Version 1.0.2 updates the site to GoldHEN v2.4b18.12 Host by patnawa,
corrects the displayed firmware ranges, and refreshes the offline cache revision.

INSTALL
Run GoldHEN-Local-Host-Setup-1.0.2-x64.exe. Choose a writable installation folder
and click Install. Everything is bundled: no Python installation, internet
download, or development tools are needed. It installs for your Windows user
with Start menu shortcuts and an optional desktop shortcut.
The portable ZIP can instead be extracted into a writable folder. Keep its
entire contents together and run Start-Host.cmd; installation is not required.

USE
1. Run Start GoldHEN Host (or Start-Host.cmd).
2. Read the PS4 network address printed in the window. It uses THIS computer's
   current IP, not the original computer's IP. Addresses are also saved in
   .runtime\addresses.txt. Choose the adapter on your PS4's network.
3. Open that exact http://address:8088/g2all/ URL in the PS4 browser.
4. Keep the PC awake. Wait for caching to finish and close/reopen the PS4 browser
   when the page tells you to. A new PC/address may require a fresh cache.
5. Run Stop GoldHEN Host when finished. Closing the launcher window does not
   stop the background server. Restart the host after rebooting the PC.

Version 1.0.1 fixes stopping a host previously started with administrator rights.
If Windows hides that process's details, Stop requests administrator permission
once to stop it. Launch normally afterward; ordinary start/stop needs no elevation.
Repeated Start shows the network address, and repeated Stop reports already stopped.

NETWORK ACCESS
If the PC page works but the console cannot reach it, run Allow PS4 Network
Access. Windows asks for administrator permission. This adds one inbound rule
limited to this executable, the configured TCP port, Private networks, and
devices on the local subnet. Use your trusted home network. No router changes,
port forwarding, Public-network rules, or automatic startup tasks are added.
Remove Network Access removes this installation's rule. Firewall changes are
optional and are not applied silently by installation.

PORT / TROUBLESHOOTING
The default port is 8088. If occupied, stop the other host or edit settings.json
to a free port from 1024 to 65535, restart, and rerun Allow PS4 Network Access if
you used that option. Each PC has its own address. VPN and multiple network
adapters may print additional addresses; choose the PS4's local network.
Check Files validates all 92 assets. Logs are in .runtime. Reinstall if validation
fails. The server serves a verified in-memory snapshot; restart after file edits.

UNINSTALL
If you enabled the optional firewall rule, run Remove Network Access first.
Then uninstall GoldHEN Local Host through Windows Installed apps or Uninstall.cmd.
The uninstaller stops this host and removes only files recorded by the installer.
Custom settings, logs, or other user-created files are retained. The portable
edition can be removed by stopping it and deleting its extracted folder after
removing its firewall rule.

CONTENTS / PROVENANCE
GoldHEN v2.4b18.12 payload and the same console scripts as the working host.
Preventive cache/launcher checks, startup integrity verification, Python runtime,
source, source notices and original author credits are included. Third-party
components retain their own terms; see THIRD-PARTY-NOTICES.txt and licenses.
Original public host: https://gamerhack.github.io/g2all/
Upstream commit: 23c946a7f85f1338ea2b78163e72e0ce9bc82b68

The original user reported successful use. This does not guarantee every firmware
or console will behave identically. Console exploit code and native payloads were
not changed for packaging. This locally built installer is not code-signed.
