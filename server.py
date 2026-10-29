"""Serve the preserved GoldHEN host over HTTP using only Python's standard library."""
import argparse
import hashlib
import io
import json
import socket
import sys
import threading
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

ROOT = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent

DIAG_LOCK = threading.Lock()
DIAG_ROUTES = {'/g2all/t', '/t'}


def load_verified_assets(directory, upstream_path, overrides_path):
    expected = {item['path']: item for item in json.loads(upstream_path.read_text(encoding='utf-8'))['files']}
    overrides = json.loads(overrides_path.read_text(encoding='utf-8'))['files']
    for item in overrides:
        if item['path'] not in expected:
            raise ValueError('Unknown override: ' + item['path'])
        expected[item['path']] = item
    assets = {}
    for name, item in expected.items():
        target = (directory / name).resolve()
        if not target.is_relative_to(directory.resolve()):
            raise ValueError('Asset escapes the site directory: ' + name)
        try:
            data = target.read_bytes()
        except OSError as error:
            raise ValueError('Missing or unreadable asset: ' + name) from error
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Asset integrity check failed: ' + name)
        assets[name] = data
    return assets


class Server(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, assets, **kwargs):
        self.assets = assets
        super().__init__(*args, **kwargs)

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        '.manifest': 'text/cache-manifest',
        '.js': 'application/javascript',
        '.bin': 'application/octet-stream',
        '.elf': 'application/octet-stream',
    }

    def do_POST(self):
        # The console scripts fire-and-forget diagnostic POSTs to /t (and
        # /g2all/t). Absorb them instead of answering 501 and keep the trace in
        # .runtime/console-diag.log so an intermittent console failure leaves
        # evidence instead of an unknown.
        self.path = self.path.replace('\\', '/')
        route = urlsplit(self.path).path
        if route not in DIAG_ROUTES:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            length = 0
        body = self.rfile.read(min(length, 65536)) if length > 0 else b''
        tag, detail = '', ''
        try:
            fields = dict(parse_qsl(body.decode('utf-8', 'replace'), keep_blank_values=True))
            tag = fields.get('tag', '')
            detail = fields.get('detail', '')
        except Exception:
            pass
        try:
            log_dir = ROOT / '.runtime'
            log_dir.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
            client = self.client_address[0] if self.client_address else '?'
            line = (f'{stamp} {client} {route} tag={tag} detail={detail}\n'
                    if tag or detail else
                    f'{stamp} {client} {route} raw={body[:512].decode("utf-8", "replace")!r}\n')
            with DIAG_LOCK:
                with open(log_dir / 'console-diag.log', 'a', encoding='utf-8') as handle:
                    handle.write(line)
        except OSError:
            pass
        self.send_response(204)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        self.path = self.path.replace('\\', '/')
        if urlsplit(self.path).path == '/__health':
            body = json.dumps({'app': 'goldhen-local', 'pid': __import__('os').getpid()}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def send_head(self):
        self.path = self.path.replace('\\', '/')
        pathname = unquote(urlsplit(self.path).path).replace('\\', '/')
        if pathname == '/':
            self.send_response(302)
            self.send_header('Location', '/g2all/')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        if '..' in pathname.split('/'):
            self.send_error(403)
            return None
        self.path = self.path.replace('%5C', '/').replace('%5c', '/')
        translated = Path(self.translate_path(self.path))
        try:
            name = translated.relative_to(Path(self.directory)).as_posix()
        except ValueError:
            self.send_error(403)
            return None
        if name not in self.assets and name.rstrip('/') + '/index.html' in self.assets:
            if not pathname.endswith('/'):
                self.send_response(302)
                self.send_header('Location', urlsplit(self.path).path + '/')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return None
            name = name.rstrip('/') + '/index.html'
        data = self.assets.get(name)
        if data is None:
            self.send_error(404)
            return None
        self.send_response(200)
        self.send_header('Content-Type', self.guess_type(name))
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        return io.BytesIO(data)

    def list_directory(self, path):
        self.send_error(404, 'Directory listing is disabled')
        return None

    def end_headers(self):
        # Revalidate manifests; AppCache itself controls its offline resource store.
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bind', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8088)
    parser.add_argument('--check', action='store_true', help='Verify packaged assets and exit')
    args = parser.parse_args()
    assets = load_verified_assets(ROOT / 'dist', ROOT / 'evidence/upstream-files.json',
                                  ROOT / 'evidence/local-overrides.json')
    if args.check:
        print(f'OK: verified {len(assets)} site files, including the GoldHEN payload.', flush=True)
        return
    handler = partial(Handler, directory=str(ROOT / 'dist'), assets=assets)
    with Server((args.bind, args.port), handler) as server:
        print(f'GoldHEN local host: http://localhost:{args.port}/g2all/', flush=True)
        print('Keep this server running while the PS4 installs its offline cache.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
