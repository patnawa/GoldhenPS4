// Offsets coverage: every key a chain dereferences must exist for every
// firmware that chain is routed to. The 1.0.7 loader sync replaced the whole
// offsets table with upstream's, so this is the guard that the sync did not
// silently drop keys our local chains still read.
//
// Keys that the chains only touch behind an `!== undefined` guard are listed in
// GUARDED and may legitimately be missing; anything else must resolve.
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const SLOPKIT = path.join(__dirname, '../dist/g2all/slopkit');

// chain file -> firmwares the launcher sends to it (index.html route ranges)
const ROUTES = {
  'chain_lapse.js': ['11.50', '11.52', '12.00', '12.02'],
  'chain_poops.js': ['12.50', '12.52', '13.00'],
  'jb.js': ['13.02', '13.04', '13.50', '13.52', '14.00', '14.02'],
};

// jb.js with afterglow is the 14.x path: the kernel stage lives in afterglow,
// so the legacy kernel keys are deliberately undefined there.
const AFTERGLOW_FW = new Set(['14.00', '14.02']);
const AFTERGLOW_GUARDED = /^k_(idt_rsvd|oid|arg1|prison0|rootvnode|sysent|jmp_rsi|kl_lock|evf_cv|stubs|pthread_create)/;

// kpatch has an explicit `|| fw + '.bin'` fallback in every chain, so a base
// entry may legitimately omit it.
const ALWAYS_OPTIONAL = new Set(['kpatch']);

// The firmware jb.js advertises a real afterglow stage for (its SUPPORTED list).
// 14.01 is routed by the launcher but has no stage, so jb.js must refuse it.
const MUST_REFUSE = ['14.01'];

let failures = 0;
let checks = 0;

function report(name, ok, detail) {
  checks++;
  if (ok) {
    console.log('PASS ' + name);
  } else {
    failures++;
    console.log('FAIL ' + name + (detail ? ': ' + detail : ''));
  }
}

function referencedKeys(file) {
  const src = fs.readFileSync(path.join(SLOPKIT, file), 'utf8');
  const keys = new Set();
  for (const m of src.matchAll(/\b(?:off|KOFF|koff)\.([A-Za-z_][A-Za-z0-9_]*)/g)) keys.add(m[1]);
  return [...keys].sort();
}

const fatalKeys = new Map();

(async () => {
  const mod = await import(pathToFileURL(path.join(SLOPKIT, 'ps4_offsets.js')).href);

  for (const [file, firmwares] of Object.entries(ROUTES)) {
    const keys = referencedKeys(file);
    fatalKeys.set(file, await guardedKeys(file));
    report(file + ' dereferences offsets keys', keys.length > 0, 'none found');
    for (const fw of firmwares) {
      const { off } = mod.offsetsFor('Mozilla/5.0 (PlayStation 4 ' + fw + ') AppleWebKit/601.2');
      report(fw + ' resolves an offsets table for ' + file, !!off);
      if (!off) continue;
      const missing = keys.filter((k) => {
        if (off[k] !== undefined) return false;
        if (AFTERGLOW_FW.has(fw) && AFTERGLOW_GUARDED.test(k)) return false;
        if (ALWAYS_OPTIONAL.has(k)) return false;
        return true;
      });
      // Keys read on a bare line must resolve.
      const required = fatalKeys.get(file);
      const fatal = missing.filter((k) => required.has(k));
      report(fw + ' full offset coverage for ' + file, fatal.length === 0, 'missing=[' + fatal.join(',') + ']');
    }
  }

  // The patch blob must exist on disk for every firmware that reaches a kpatch read.
  for (const fw of ['11.50', '12.00', '12.50', '13.00', '13.02', '13.50', '13.52', '14.00', '14.02']) {
    const { off } = mod.offsetsFor('Mozilla/5.0 (PlayStation 4 ' + fw + ')');
    const blob = (off && off.kpatch) || fw.replace('.', '') + '.bin';
    report(fw + ' patch blob on disk (' + blob + ')', fs.existsSync(path.join(SLOPKIT, 'patches', blob)));
  }

  // 14.01 is routed but has no afterglow stage: jb.js must refuse before the kernel.
  const jb = fs.readFileSync(path.join(SLOPKIT, 'jb.js'), 'utf8');
  for (const fw of MUST_REFUSE) {
    report('jb.js SUPPORTED refuses ' + fw, !new RegExp('"' + fw.replace('.', '\\.') + '"').test(jb.match(/const SUPPORTED = \[([^\]]*)\]/)[1]));
    report(fw + ' still has an offsets entry so the gate is reachable',
      !!mod.offsetsFor('Mozilla/5.0 (PlayStation 4 ' + fw + ')').off);
  }
  // Every firmware the launcher routes to jb.js is either supported or must-refuse.
  for (const fw of ROUTES['jb.js']) {
    const supported = /const SUPPORTED = \[([^\]]*)\]/.exec(jb)[1];
    report(fw + ' is supported or explicitly refused by jb.js',
      supported.includes('"' + fw + '"') || MUST_REFUSE.includes(fw));
  }

  // jb.js must import the afterglow stage by an existing, cached path.
  const agImport = /import\(\s*["']\.\/(afterglow\.js)["']\s*\)/.exec(jb);
  report('jb.js imports ./afterglow.js dynamically', !!agImport);
  report('afterglow.js exists on disk', fs.existsSync(path.join(SLOPKIT, 'afterglow.js')));
  // afterglow builds its own blob path; it must agree with the site layout.
  if (fs.existsSync(path.join(SLOPKIT, 'afterglow.js'))) {
    const ag = fs.readFileSync(path.join(SLOPKIT, 'afterglow.js'), 'utf8');
    report('afterglow patch path matches the served layout', /"slopkit\/patches\/" \+ fwBin/.test(ag));
  }
  // Launcher ceiling must equal the newest firmware jb.js has a stage for.
  const index = fs.readFileSync(path.join(__dirname, '../dist/g2all/index.html'), 'utf8');
  const maxSupported = ROUTES['jb.js'].slice(-1)[0];
  report('launcher route ceiling is ' + maxSupported,
    index.includes('fwNum <= ' + maxSupported));

  // The manifest has to cache everything the 14.x path imports.
  const manifest = fs.readFileSync(path.join(__dirname, '../dist/g2all/slopkit.manifest'), 'utf8');
  for (const need of ['slopkit\\afterglow.js', 'slopkit\\int64.js']) {
    report('slopkit.manifest caches ' + need.replace('\\', '/'), manifest.includes(need));
  }

  console.log(`${checks} checks, ${failures} failed.`);
  process.exitCode = failures ? 1 : 0;
})();

// Keys are optional only when EVERY line that mentions them guards the read
// (`!== undefined`, `|| fallback`, `?:`). One bare line makes the key fatal.
async function guardedKeys(file) {
  const lines = fs.readFileSync(path.join(SLOPKIT, file), 'utf8').split('\n');
  const fatal = new Set();
  for (const line of lines) {
    const keys = [...line.matchAll(/\b(?:off|KOFF|koff)\.([A-Za-z_][A-Za-z0-9_]*)/g)].map((m) => m[1]);
    if (!keys.length) continue;
    const guarded = /undefined|\|\||\?:|!off\.|===\s*undefined/.test(line);
    for (const k of keys) if (!guarded) fatal.add(k);
  }
  return fatal;   // the caller treats these as required
}
