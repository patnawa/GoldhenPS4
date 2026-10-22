"""Regression checks for incomplete/corrupt assets; never run console code."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from functools import partial
from urllib.request import urlopen

spec = importlib.util.spec_from_file_location('host', Path(__file__).resolve().parents[1] / 'server.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dist = self.root / 'dist'
        self.dist.mkdir()
        self.data = b'known binary fixture\x00\xff'
        (self.dist / 'payload.bin').write_bytes(self.data)
        self.upstream = self.root / 'upstream.json'
        self.upstream.write_text(json.dumps({'files': [{'path': 'payload.bin',
            'bytes': len(self.data), 'sha256': hashlib.sha256(self.data).hexdigest()}]}))
        self.overrides = self.root / 'overrides.json'
        self.overrides.write_text(json.dumps({'files': []}))

    def load(self):
        return host.load_verified_assets(self.dist, self.upstream, self.overrides)

    def test_valid_bytes(self):
        self.assertEqual(self.load()['payload.bin'], self.data)

    def test_truncated_file_rejected(self):
        (self.dist / 'payload.bin').write_bytes(self.data[:-1])
        with self.assertRaises(ValueError): self.load()

    def test_same_length_corruption_rejected(self):
        (self.dist / 'payload.bin').write_bytes(b'X' + self.data[1:])
        with self.assertRaises(ValueError): self.load()

    def test_missing_file_rejected(self):
        (self.dist / 'payload.bin').unlink()
        with self.assertRaises(ValueError): self.load()

    def test_reviewed_override_accepted(self):
        new = b'reviewed host edit'
        (self.dist / 'payload.bin').write_bytes(new)
        self.overrides.write_text(json.dumps({'files': [{'path': 'payload.bin',
            'bytes': len(new), 'sha256': hashlib.sha256(new).hexdigest()}]}))
        self.assertEqual(self.load()['payload.bin'], new)

    def test_server_keeps_verified_bytes_after_disk_changes(self):
        assets = self.load()
        server = host.Server(('127.0.0.1', 0), partial(host.Handler, directory=str(self.dist), assets=assets))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            (self.dist / 'payload.bin').write_bytes(b'bad')
            with urlopen(f'http://127.0.0.1:{server.server_port}/payload.bin') as response:
                self.assertEqual(response.read(), self.data)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main(verbosity=2)
