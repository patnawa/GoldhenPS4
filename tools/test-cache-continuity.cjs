// AppCache continuity: every file a *previous* release's manifest lists must
// still be served. PS4 AppCache fetches each manifest entry during an update and
// fails the whole update if one 404s, leaving the console stuck on the old cache
// until the user clears browser data. So dropping or renaming a payload/blob
// breaks upgrades for consoles that never came back online in between.
//
// Fixtures under tools/fixtures/legacy-manifests/<version>/ are the manifests as
// shipped, captured from git history at release time. Add a directory whenever a
// release changes payload names.
const fs = require('node:fs');
const path = require('node:path');

const DIST = path.join(__dirname, '../dist/g2all');
const FIXTURES = path.join(__dirname, 'fixtures/legacy-manifests');

let checks = 0;
let failures = 0;

function report(name, ok, detail) {
  checks++;
  if (ok) console.log('PASS ' + name);
  else { failures++; console.log('FAIL ' + name + (detail ? ': ' + detail : '')); }
}

function entries(manifest) {
  const out = [];
  for (const raw of manifest.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || line.endsWith(':') || line === 'CACHE MANIFEST' || line === '*') continue;
    out.push(line.replace(/\\/g, '/').split('?')[0]);
  }
  return out;
}

for (const version of fs.readdirSync(FIXTURES).sort()) {
  const dir = path.join(FIXTURES, version);
  for (const file of fs.readdirSync(dir).sort()) {
    const listed = entries(fs.readFileSync(path.join(dir, file), 'utf8'));
    const missing = listed.filter((p) => !fs.existsSync(path.join(DIST, p)));
    report(`${version}/${file} resources still served`, missing.length === 0, 'missing=[' + missing.join(',') + ']');
  }
}

// The payload a console has cached is also the one its manifest names; keep the
// previous payload on disk until a release that no longer needs the hop.
for (const bin of ['goldhen_2.4b18.13.bin', 'goldhen_2.4b18.14.bin']) {
  report(bin + ' served', fs.existsSync(path.join(DIST, bin)));
}

console.log(`${checks} checks, ${failures} failed.`);
process.exitCode = failures ? 1 : 0;
