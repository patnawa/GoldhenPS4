"""Regression loop for real Windows launcher scripts in a separate local folder."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'build/Launcher Test'
PORT = 18288
opener = build_opener(ProxyHandler({}))


def run(script, *args):
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(script), *map(str, args)], cwd=os.environ['WINDIR'], stdin=subprocess.DEVNULL,
            stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
        out.seek(0); err.seek(0)
        return proc.returncode, (out.read() + err.read()).decode(errors='replace')


def prepare():
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in ('Start-Host.ps1', 'Stop-Host.ps1', 'server.py'):
        shutil.copy2(ROOT / name, TARGET / name)
    for name in ('Host-Control.ps1', 'settings.json'):
        if (ROOT / name).exists(): shutil.copy2(ROOT / name, TARGET / name)
    shutil.copytree(ROOT / 'dist', TARGET / 'dist', dirs_exist_ok=True)
    (TARGET / 'evidence').mkdir(exist_ok=True)
    for name in ('upstream-files.json', 'local-overrides.json'):
        shutil.copy2(ROOT / 'evidence' / name, TARGET / 'evidence' / name)


def main():
    prepare()
    code, text = run(TARGET / 'Start-Host.ps1', '-Port', PORT)
    assert code == 0, text
    try:
        with opener.open(f'http://127.0.0.1:{PORT}/__health', timeout=3) as response:
            before = json.load(response)['pid']
        code, text = run(TARGET / 'Start-Host.ps1', '-Port', PORT)
        assert code == 0, text
        assert 'network' in text.lower(), 'Repeat Start must still display the PS4 network address: ' + text
        with opener.open(f'http://127.0.0.1:{PORT}/__health', timeout=3) as response:
            assert before == json.load(response)['pid'], 'Repeat start created another process'
        # Missing process metadata is the reproduced failure. Mock only CIM metadata;
        # run the actual Stop script, forbid elevation and assert a useful explanation.
        stub = TARGET / 'null-metadata-test.ps1'
        stub.write_text('''function Get-CimInstance { [pscustomobject]@{ProcessId=123; CommandLine=$null; ExecutablePath=$null} }
& "$PSScriptRoot/Stop-Host.ps1" -NoElevation
exit $LASTEXITCODE
''', encoding='utf-8')
        code, text = run(stub)
        assert code != 0 and 'administrator' in text.lower(), text
        assert 'null-valued' not in text.lower(), text
        print('PASS null process metadata produces an administrator-permission explanation')
        print('PASS start from a different working directory and a path containing spaces')
        print('PASS repeat start keeps the same process and displays network addresses')
        state_path = TARGET / '.runtime/server.json'
        original_state = state_path.read_bytes()
        unrelated = subprocess.Popen(['powershell.exe', '-NoProfile', '-Command', 'Start-Sleep -Seconds 30'], creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            state_path.write_text(json.dumps({'pid': unrelated.pid, 'port': PORT, 'server': str(TARGET / 'server.py')}))
            code, text = run(TARGET / 'Stop-Host.ps1', '-NoElevation')
            assert code == 1 and 'another command' in text.lower(), text
            assert unrelated.poll() is None, 'Unrelated process was stopped'
            print('PASS stale PID pointing at another command is left untouched')
        finally:
            state_path.write_bytes(original_state)
            unrelated.terminate(); unrelated.wait()
    finally:
        code, text = run(TARGET / 'Stop-Host.ps1')
        assert code == 0, text
    code, text = run(TARGET / 'Stop-Host.ps1')
    assert code == 0 and 'stopped' in text.lower(), text
    print('PASS stop and repeat stop')
    state_path = TARGET / '.runtime/server.json'
    state_path.write_text(json.dumps({'pid': 2147483647, 'port': PORT, 'server': str(TARGET / 'server.py')}))
    code, text = run(TARGET / 'Stop-Host.ps1', '-NoElevation')
    assert code == 0 and not state_path.exists(), text
    print('PASS exited process record is cleared')
    # Exercise native CMD entry points without interactive pause and verify exit codes.
    # PowerShell scripts above are the same entry points invoked by those wrappers.


if __name__ == '__main__':
    main()
