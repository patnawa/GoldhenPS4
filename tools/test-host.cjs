// Exercise only the real HTML launcher. Appended console scripts are recorded,
// never evaluated. These tests cannot reproduce a PS4 kernel panic.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../dist/g2all/index.html'), 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function run({firmware = '9.00', status = 1, appCache = true, ready = false,
              dirtySession = null} = {}) {
  const listeners = {};
  const cacheListeners = {};
  const scripts = [];
  const redirects = [];
  const message = {innerHTML: 'Loading GoldHEN', textContent: '', style: {}};
  const document = {
    readyState: ready ? 'complete' : 'loading',
    getElementById: () => ready ? message : null,
    addEventListener: (name, callback) => { (listeners[name] ||= []).push(callback); },
    createElement: () => ({}),
    head: {appendChild: script => scripts.push(script)},
  };
  const context = {document, navigator: {userAgent: firmware ? `Mozilla/5.0 (PlayStation 4 ${firmware})` : 'Chrome'},
    location: {replace: url => redirects.push(url)}, setTimeout: fn => fn()};
  context.window = context;
  if (appCache) context.applicationCache = {status, addEventListener(name, callback) {
    (cacheListeners[name] ||= []).push(callback);
  }};
  if (ready) context.msgs = message;
  if (dirtySession !== null) {
    context.sessionStorage = {getItem: () => (dirtySession ? '1700000000000' : null)};
  }
  vm.createContext(context);
  vm.runInContext(source, context, {timeout: 1000});
  return {scripts, redirects, message, context,
    cacheEvent(name, status) { context.applicationCache.status = status;
      for (const callback of cacheListeners[name] || []) callback(); },
    ready() { ready = true; context.msgs = message; document.readyState = 'complete';
      for (const callback of listeners.DOMContentLoaded || []) callback(); }};
}

const tests = [
  ['Missing AppCache stops with a visible explanation', () => {
    const host = run({appCache: false}); host.ready();
    assert.equal(host.scripts.length, 0);
    assert.match(host.message.innerHTML + host.message.textContent, /cache|browser/i);
  }],
  ['Unsupported cached firmware cannot remain at Loading', () => {
    const host = run({firmware: '6.72'}); host.ready();
    assert.equal(host.scripts.length, 0);
    assert.match(host.message.innerHTML + host.message.textContent, /unsupported/i);
  }],
  ...[2, 3, 4, 5].map(status => [`Cache state ${status} cannot launch a console script`, () => {
    const host = run({status}); host.ready();
    assert.equal(host.scripts.length, 0);
    assert.match(host.message.innerHTML + host.message.textContent, /cache|reopen|re-open|updat/i);
  }]),
  ['Launcher waits for its status element before loading console code', () => {
    const host = run(); assert.equal(host.scripts.length, 0);
    host.ready(); assert.equal(host.scripts.length, 1);
  }],
  ['Script load error is visible and does not retry', () => {
    const host = run(); host.ready(); host.scripts[0].onerror();
    assert.equal(host.scripts.length, 1);
    assert.match(host.message.innerHTML + host.message.textContent, /not found|failed|missing/i);
  }],
  ['Desktop never loads console code', () => {
    const host = run({firmware: null, appCache: false}); host.ready();
    assert.equal(host.scripts.length, 0); assert.match(host.message.innerHTML, /PS4/);
  }],
  ['A session flagged dirty by a committed Lapse run cannot relaunch the chain', () => {
    const host = run({firmware: '11.50', dirtySession: true}); host.ready();
    assert.equal(host.scripts.length, 0);
    assert.match(host.message.innerHTML, /power the ps4 off/i);
  }],
  ['A clean session storage still launches the Lapse chain', () => {
    const host = run({firmware: '11.50', dirtySession: false}); host.ready();
    assert.equal(host.scripts.length, 1);
    assert.equal(host.scripts[0].src, 'slopkit/chain_lapse.js');
  }],
  ['Uncached supported console opens the cache installer', () => {
    const host = run({status: 0}); host.ready();
    assert.deepEqual(host.redirects, ['cache900.html']); assert.equal(host.scripts.length, 0);
  }],
  ['Completed unchanged cache launches once despite duplicate events', () => {
    const host = run({status: 2}); host.ready();
    host.cacheEvent('noupdate', 1); host.cacheEvent('noupdate', 1); host.ready();
    assert.equal(host.scripts.length, 1);
  }],
  ['Offline update failure can use an existing complete idle cache', () => {
    const host = run({status: 2}); host.ready(); host.cacheEvent('error', 1);
    assert.equal(host.scripts.length, 1);
  }],
  ['Failed incomplete cache never launches', () => {
    const host = run({status: 3}); host.ready(); host.cacheEvent('error', 0);
    assert.equal(host.scripts.length, 0);
    assert.match(host.message.textContent, /failed/i);
  }],
  ...['cached', 'updateready'].map(event => [event + ' requires reopening before launch', () => {
    const host = run({status: 3}); host.ready(); host.cacheEvent(event, event === 'cached' ? 1 : 4);
    assert.equal(host.scripts.length, 0); assert.match(host.message.textContent, /re-open/i);
  }]),
  ...[['5.05','505/exploit.js'],['5.07','505/exploit.js'],['7.00','700/alert.js'],
    ['8.52','700/alert.js'],['9.00','900/alert.js'],['9.60','900/alert.js'],
    ['10.00','css/main.js'],['11.02','css/main.js'],['11.50','slopkit/chain_lapse.js'],
    ['12.02','slopkit/chain_lapse.js'],['12.50','slopkit/chain_poops.js'],
    ['13.00','slopkit/chain_poops.js'],['13.02','slopkit/jb.js?v=19'],
    ['13.52','slopkit/jb.js?v=19']].map(([firmware, src]) => [firmware + ' preserves its entry script', () => {
      const host = run({firmware}); host.ready();
      assert.equal(host.scripts.length, 1); assert.equal(host.scripts[0].src, src);
    }]),
  ...['6.72','8.60','9.99','11.03','12.10','13.01','99.00'].map(firmware => [firmware + ' stops before code loads', () => {
    const host = run({firmware}); host.ready(); assert.equal(host.scripts.length, 0);
    assert.match(host.message.textContent, /unsupported/i);
  }]),
];
let failures = 0;
for (const [name, check] of tests) {
  try { check(); console.log('PASS ' + name); }
  catch (error) { failures++; console.log('FAIL ' + name + ': ' + error.message); }
}
console.log(`${tests.length - failures}/${tests.length} passed; console scripts were not executed.`);
process.exitCode = failures ? 1 : 0;
