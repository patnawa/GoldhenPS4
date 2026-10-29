"""Create an explicit, machine-independent distribution inventory."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import sysconfig
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.4'
STAGE = ROOT / f'build/package-{VERSION}/GoldHEN-Server'


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main():
    (ROOT / f'release/v{VERSION}').mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'dist', STAGE / 'dist', dirs_exist_ok=True)
    for name in ('upstream-files.json', 'local-overrides.json'):
        copy(ROOT / 'evidence' / name, STAGE / 'evidence' / name)
    for name in ('Start-Host.cmd', 'Stop-Host.cmd'):
        copy(ROOT / name, STAGE / name)
    for source in (ROOT / 'packaging').iterdir():
        if source.suffix in ('.ps1', '.cmd') or source.name in ('README.txt', 'settings.json', 'THIRD-PARTY-NOTICES.txt'):
            copy(source, STAGE / source.name)
    copy(ROOT / 'server.py', STAGE / 'source/server.py')
    for source in (ROOT / 'tools').glob('*'):
        if source.suffix in ('.py', '.cjs'):
            copy(source, STAGE / 'source/tools' / source.name)
    for source in (ROOT / 'packaging').iterdir():
        if source.is_file() and source.suffix in ('.py', '.ps1'):
            copy(source, STAGE / 'source/packaging' / source.name)
    shutil.copytree(ROOT / 'evidence/original-launcher', STAGE / 'source/original-launcher', dirs_exist_ok=True)
    copy(Path(sys.base_prefix) / 'LICENSE.txt', STAGE / 'licenses/PYTHON-LICENSE.txt')
    license_source = Path(sysconfig.get_paths()['purelib']) / 'pyinstaller-6.22.3.dist-info/licenses'
    shutil.copytree(license_source, STAGE / 'licenses/pyinstaller', dirs_exist_ok=True)
    license_file = STAGE / 'licenses/AGPL-3.0.txt'
    if not license_file.exists():
        copy(ROOT / 'licenses/AGPL-3.0.txt', license_file)
    files = sorted(p for p in STAGE.rglob('*') if p.is_file())
    forbidden = [p for p in files if '.runtime' in p.parts or '__pycache__' in p.parts]
    if forbidden: raise RuntimeError('Runtime artifacts cannot be packaged: ' + str(forbidden))
    inventory = {p.relative_to(STAGE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (ROOT / 'packaging/payload-manifest.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
    with zipfile.ZipFile(ROOT / 'packaging/payload.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for source in files:
            archive.write(source, source.relative_to(STAGE).as_posix())
    with zipfile.ZipFile(ROOT / f'release/v{VERSION}/GoldHEN-Local-Host-Portable-{VERSION}-x64.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for source in files:
            archive.write(source, 'GoldHEN Local Host/' + source.relative_to(STAGE).as_posix())
    print(f'Staged {len(files)} files. Runtime logs, original machine addresses, and browser captures excluded.')


if __name__ == '__main__':
    main()
