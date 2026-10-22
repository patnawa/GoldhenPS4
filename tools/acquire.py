"""Acquire the public g2all site, retaining provenance and byte identities."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
EVIDENCE = ROOT / 'evidence'
ORIGIN = 'https://gamerhack.github.io/'

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'Goldhen-Local-Mirror'}), timeout=60) as response:
        return response.read()

def main():
    if (EVIDENCE / 'local-overrides.json').exists():
        raise RuntimeError('Local stability edits exist. Acquire a fresh upstream copy in a separate directory and review changes before replacing this host.')
    tree = json.loads(fetch('https://api.github.com/repos/GamerHack/GamerHack.github.io/git/trees/main?recursive=1'))
    if tree.get('truncated'):
        raise RuntimeError('Incomplete upstream inventory')
    entries = [item for item in tree['tree'] if item['type'] == 'blob' and
               (item['path'].startswith('g2all/') or item['path'] in ('style.css', 'img.jpg'))]
    DIST.mkdir(exist_ok=True)
    EVIDENCE.mkdir(exist_ok=True)

    def acquire(item):
        name = item['path']
        data = fetch(ORIGIN + name)
        git_sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if git_sha != item['sha']:
            raise RuntimeError('Deployed file differs from repository snapshot: ' + name)
        target = DIST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                'git_blob_sha': git_sha, 'source_url': ORIGIN + name}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        files = sorted(pool.map(acquire, entries), key=lambda item: item['path'])
    record = {'source': ORIGIN + 'g2all/', 'repository_commit': tree['sha'],
              'acquired_utc': datetime.now(timezone.utc).isoformat(), 'files': files}
    (EVIDENCE / 'upstream-files.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({'commit': tree['sha'], 'files': len(files), 'bytes': sum(f['bytes'] for f in files)}))

if __name__ == '__main__':
    main()
