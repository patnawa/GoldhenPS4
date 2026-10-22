"""Verify local served bytes, manifest resources, MIME types and server boundaries."""
import concurrent.futures
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8088/'


def get(path, method='GET'):
    opener = build_opener(ProxyHandler({}))
    with opener.open(Request(urljoin(BASE, path), method=method), timeout=10) as response:
        return response.status, response.headers, response.read(), response.url


def main():
    upstream = json.loads((ROOT / 'evidence/upstream-files.json').read_text(encoding='utf-8'))
    overrides = {item['path']: item for item in json.loads(
        (ROOT / 'evidence/local-overrides.json').read_text(encoding='utf-8'))['files']}

    def check(item):
        item = overrides.get(item['path'], item)
        status, headers, body, _ = get(item['path'])
        assert status == 200, item['path']
        assert hashlib.sha256(body).hexdigest() == item['sha256'], item['path']
        if item['path'].endswith('.js'):
            assert headers.get_content_type() == 'application/javascript', item['path']
        if item['path'].endswith(('.bin', '.elf')):
            assert headers.get_content_type() == 'application/octet-stream', item['path']
        return item['path']

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        assets = list(pool.map(check, upstream['files']))
    manifests = {}
    for manifest in sorted((ROOT / 'dist/g2all').glob('*.manifest')):
        _, headers, body, _ = get('g2all/' + manifest.name)
        assert headers.get_content_type() == 'text/cache-manifest', manifest.name
        entries = []
        section = 'CACHE:'
        for raw in body.decode().splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or line == 'CACHE MANIFEST':
                continue
            if line.endswith(':'):
                section = line
                continue
            if section != 'CACHE:':
                continue
            url = urljoin('g2all/', line.replace('\\', '/'))
            assert get(url)[0] == 200, url
            entries.append(url)
        manifests[manifest.name] = len(entries)
    assert get('')[3].endswith('/g2all/'), 'Root redirect'
    assert get('g2all/index.html', 'HEAD')[2] == b'', 'HEAD response'
    assert get('g2all/slopkit/jb.js?v=19')[2] == (ROOT / 'dist/g2all/slopkit/jb.js').read_bytes()
    assert get('g2all/700%5Calert.js')[2] == (ROOT / 'dist/g2all/700/alert.js').read_bytes()
    expected_errors = {'server.py': 404, 'evidence/upstream-files.json': 404,
                       'g2all/700/': 404, '%2e%2e/server.py': 403}
    for path, status in expected_errors.items():
        try:
            get(path)
            raise AssertionError('Unexpectedly accessible: ' + path)
        except HTTPError as error:
            assert error.code == status, (path, error.code)
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'base_url': BASE,
              'assets_verified': len(assets), 'manifest_resources': manifests,
              'root_redirect': 'passed', 'mime_types': 'passed', 'head': 'passed',
              'query_strings': 'passed', 'backslash_paths': 'passed', 'server_boundaries': 'passed',
              'console_execution': 'not tested; requires PS4 hardware'}
    (ROOT / 'evidence/verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
