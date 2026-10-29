"""Offline, per-user Windows installer for the self-contained GoldHEN host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import winreg
import zipfile

APP = 'GoldHENLocalHost'
VERSION = '1.0.3'
REGISTRY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldHENLocalHost'
RESOURCE = Path(__file__).resolve().parent


def powershell(script, *arguments):
    return subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                           '-File', str(script), *map(str, arguments)],
                          capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW,
                          check=True)


def install(directory, desktop=True, integrate=True):
    destination = Path(directory).expanduser().resolve()
    if destination == destination.parent:
        raise ValueError('Choose a dedicated application folder, not a drive root.')
    if integrate:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
                existing = winreg.QueryValueEx(key, 'InstallLocation')[0]
            raise ValueError('GoldHEN Local Host is already installed at ' + existing + '. Uninstall it first.')
        except FileNotFoundError:
            pass
    if destination.exists():
        allowed = {'settings.json', '.runtime'}
        if any(item.name not in allowed for item in destination.iterdir()):
            raise ValueError('Choose an empty folder, or uninstall its previous GoldHEN installation first.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RESOURCE / 'payload-manifest.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='goldhen-install-', dir=str(destination.parent)) as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(RESOURCE / 'payload.zip') as archive:
            if set(archive.namelist()) != set(manifest):
                raise ValueError('Package inventory mismatch.')
            for name, digest in manifest.items():
                output = (staging / name).resolve()
                if not output.is_relative_to(staging.resolve()):
                    raise ValueError('Invalid package path.')
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError('Package integrity check failed: ' + name)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
        check = subprocess.run([str(staging / 'GoldHEN-Server.exe'), '--check'],
                               capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if check.returncode:
            raise ValueError('Bundled site validation failed: ' + check.stdout + check.stderr)
        destination.mkdir(exist_ok=True)
        for name in manifest:
            output = destination / name
            if name == 'settings.json' and output.exists():
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staging / name, output)
    record = {'app': APP, 'version': VERSION, 'directory': str(destination), 'files': list(manifest)}
    (destination / 'installation.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    if integrate:
        powershell(destination / 'Integrate.ps1', '-InstallDirectory', destination, *(['-Desktop'] if desktop else []))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
            values = {'DisplayName': 'GoldHEN Local Host', 'DisplayVersion': VERSION,
                      'Publisher': 'Local host package', 'InstallLocation': str(destination),
                      'DisplayIcon': str(destination / 'GoldHEN-Server.exe'),
                      'UninstallString': 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + str(destination / 'Uninstall.ps1') + '"'}
            for name, value in values.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            winreg.SetValueEx(key, 'NoModify', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, 'NoRepair', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, 'EstimatedSize', 0, winreg.REG_DWORD,
                              sum((destination / name).stat().st_size for name in manifest) // 1024)
    return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install-dir')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--no-integration', action='store_true')
    parser.add_argument('--no-desktop', action='store_true')
    parser.add_argument('--ui-check', action='store_true')
    args = parser.parse_args()
    default = args.install_dir or str(Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'GoldHEN Local Host')
    if args.quiet:
        try:
            target = install(default, not args.no_desktop, not args.no_integration)
            (target / 'setup-result.json').write_text(json.dumps({'status': 'installed', 'version': VERSION}))
            return 0
        except Exception as error:
            Path(str(default) + '-setup-error.txt').write_text(str(error), encoding='utf-8')
            return 1

    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    window = tk.Tk()
    if args.ui_check: window.withdraw()
    window.title('GoldHEN Local Host Setup')
    frame = ttk.Frame(window, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='GoldHEN Local Host', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Version ' + VERSION + '  |  Windows 10/11 (64-bit)', font=('Segoe UI', 10)).pack(anchor='w', pady=(2, 20))
    ttk.Label(frame, text='Install the complete offline host, bundled runtime and GoldHEN payload.\nNo Python installation or internet download is needed.', wraplength=560).pack(anchor='w')
    ttk.Label(frame, text='Installation folder').pack(anchor='w', pady=(20, 6))
    path = tk.StringVar(value=default)
    row = ttk.Frame(frame); row.pack(fill='x')
    ttk.Entry(row, textvariable=path, width=62).pack(side='left', fill='x', expand=True)
    def browse():
        selected = filedialog.askdirectory(title='Choose a parent folder')
        if selected: path.set(str(Path(selected) / 'GoldHEN Local Host'))
    ttk.Button(row, text='Browse...', command=browse).pack(side='left', padx=(8, 0))
    desktop = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text='Create a desktop Start shortcut', variable=desktop).pack(anchor='w', pady=(12, 8))
    ttk.Label(frame, text='Network access is optional and can be enabled after installation.\nInstalls for your current Windows user.', wraplength=560).pack(anchor='w')
    status = tk.StringVar(value='Ready to install.')
    ttk.Label(frame, textvariable=status, wraplength=560).pack(anchor='w', pady=(16, 8))
    buttons = ttk.Frame(frame); buttons.pack(fill='x')
    cancel = ttk.Button(buttons, text='Cancel', command=window.destroy); cancel.pack(side='right')
    result = {}
    def poll():
        if 'error' in result:
            status.set('Installation did not finish.')
            messagebox.showerror('Setup', result['error'])
            install_button.config(state='normal'); cancel.config(state='normal')
            window.protocol('WM_DELETE_WINDOW', window.destroy)
        elif 'target' in result:
            status.set('Installed. Start GoldHEN Host from your Start menu or desktop.')
            install_button.config(text='Done', state='normal', command=window.destroy)
            cancel.config(state='disabled')
            window.protocol('WM_DELETE_WINDOW', window.destroy)
            messagebox.showinfo('Installation complete', 'Start GoldHEN Host, then open the network address it prints in your PS4 browser.\n\nIf needed, use Allow PS4 Network Access from the Start menu.')
        else: window.after(100, poll)
    def begin():
        target = path.get(); make_desktop = desktop.get()
        result.clear(); status.set('Verifying and installing bundled files...')
        install_button.config(state='disabled'); cancel.config(state='disabled')
        window.protocol('WM_DELETE_WINDOW', lambda: None)
        def work():
            try: result['target'] = install(target, make_desktop, True)
            except Exception as error: result['error'] = str(error)
        threading.Thread(target=work, daemon=True).start()
        window.after(100, poll)
    install_button = ttk.Button(buttons, text='Install', command=begin)
    install_button.pack(side='right', padx=8)
    window.update_idletasks()
    window.minsize(max(640, frame.winfo_reqwidth()), frame.winfo_reqheight())
    if args.ui_check:
        # Exercise bundled Tk without opening a visible window or installing files.
        assert install_button.winfo_reqheight() > 0
        window.destroy()
        return 0
    window.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
