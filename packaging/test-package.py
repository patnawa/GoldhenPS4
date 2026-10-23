"""Exercise the actual frozen installer, installed host, and uninstall path."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import build_opener, ProxyHandler
import winreg

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'build/Install Test 1.0.2'
SETUP = ROOT / 'release/v1.0.2/GoldHEN-Local-Host-Setup-1.0.2-x64.exe'
PORT = 18188
REGISTRY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldHENLocalHost'
ENV = {**os.environ, 'PATH': os.environ['WINDIR'] + r'\System32;' + os.environ['WINDIR'] + r'\System32\WindowsPowerShell\v1.0'}
RESULT = {}


def command(args, expected=0):
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        result = subprocess.run(list(map(str, args)), env=ENV, stdin=subprocess.DEVNULL,
                                stdout=output, stderr=errors,
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=90)
        output.seek(0); errors.seek(0)
        stdout = output.read().decode(errors='replace')
        stderr = errors.read().decode(errors='replace')
    if result.returncode != expected:
        raise AssertionError(f'Exit {result.returncode}: {stdout}\n{stderr}')
    return stdout.strip()


def ps(name, *args):
    return command(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', TARGET / name, *args])


def main():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY):
            raise RuntimeError('An installed host already exists; refusing to change its registration.')
    except FileNotFoundError:
        pass
    if TARGET.exists() and any(p.name not in {'settings.json', '.runtime', 'setup-result.json'} for p in TARGET.iterdir()):
        raise RuntimeError('Test directory is occupied; inspect it before rerunning.')
    # Quiet setup creates a small result file; remove only our prior test receipt.
    receipt = TARGET / 'setup-result.json'
    if receipt.exists(): receipt.unlink()
    command([SETUP, '--quiet', '--install-dir', TARGET, '--no-desktop'])
    RESULT['offline_install_without_python_on_path'] = 'passed'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
        assert Path(winreg.QueryValueEx(key, 'InstallLocation')[0]) == TARGET
    RESULT['installed_apps_registration'] = 'passed'
    # Assert shortcuts through the Windows shell using the actual current user's Programs location.
    shortcut_check = "$g=Join-Path ([Environment]::GetFolderPath('Programs')) 'GoldHEN Local Host'; @(Get-ChildItem -LiteralPath $g -Filter '*.lnk').Count"
    count = command(['powershell.exe', '-NoProfile', '-Command', shortcut_check])
    assert int(count) == 7, count
    RESULT['start_menu_shortcuts'] = 7
    RESULT['packaged_asset_check'] = command([TARGET / 'GoldHEN-Server.exe', '--check'])
    (TARGET / 'settings.json').write_text(json.dumps({'port': PORT}))
    print(ps('Start-Host.ps1'))
    try:
        opener = build_opener(ProxyHandler({}))
        manifest = json.loads((TARGET / 'evidence/upstream-files.json').read_text())['files']
        overrides = {item['path']: item for item in json.loads((TARGET / 'evidence/local-overrides.json').read_text())['files']}
        for original in manifest:
            item = overrides.get(original['path'], original)
            with opener.open(f'http://127.0.0.1:{PORT}/' + item['path'], timeout=5) as response:
                assert response.status == 200
                assert hashlib.sha256(response.read()).hexdigest() == item['sha256'], item['path']
        RESULT['served_assets_verified'] = len(manifest)
        before = json.loads((TARGET / '.runtime/server.json').read_text(encoding='utf-8-sig'))['pid']
        ps('Start-Host.ps1')
        after = json.loads((TARGET / '.runtime/server.json').read_text(encoding='utf-8-sig'))['pid']
        assert before == after
        RESULT['duplicate_start_reuses_same_process'] = 'passed'
    finally:
        ps('Stop-Host.ps1')
    RESULT['stop_host'] = 'passed'
    # Leave a user-created file to ensure uninstall does not remove unrelated data.
    sentinel = TARGET / 'user-note.txt'
    sentinel.write_text('retain me')
    ps('Uninstall.ps1', '-Quiet')
    assert sentinel.read_text() == 'retain me'
    assert (TARGET / 'settings.json').exists()
    assert not (TARGET / 'GoldHEN-Server.exe').exists()
    assert not (TARGET / 'installation.json').exists()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY):
            raise AssertionError('Uninstall registry record remains')
    except FileNotFoundError:
        pass
    sentinel.unlink()
    RESULT['uninstall_and_preserve_user_files'] = 'passed'
    RESULT['firewall_rule_execution'] = 'not run; opt-in helper syntax checked only'
    RESULT['other_computer_execution'] = 'not available; isolated install tested on this PC'
    (ROOT / 'release/v1.0.2/package-test.json').write_text(json.dumps(RESULT, indent=2))
    print(json.dumps(RESULT, indent=2))


if __name__ == '__main__':
    main()
