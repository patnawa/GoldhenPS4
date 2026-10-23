// Run the shipped 11.50 entry module with inert imports. The primitive stub
// always throws, so no console exploit, memory operation or payload executes.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname,
  '../dist/g2all/slopkit/chain_lapse.js'), 'utf8').replace(/^import .*;\r?\n/gm, '');

async function run({failedAsset, status = 503, empty = false, network = false} = {}) {
  const elements = {};
  function element() {
    return {innerHTML: '', textContent: '', style: {}, setAttribute(name, value) {
      this[name] = value;
    }};
  }
  elements.msgs = element();
  let primitiveCalls = 0;
  const requests = [];
  const context = {
    document: {getElementById: id => elements[id], createElement: element,
      body: {appendChild: el => { elements[el.id] = el; }}},
    navigator: {userAgent: 'Mozilla/5.0 (PlayStation 4 11.50)'},
    location: {search: ''}, URLSearchParams,
    setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
    XMLHttpRequest: class { open() {} setRequestHeader() {} send() {} },
    offsetsFor: () => ({key: '11.50', off: {kpatch: '1150.bin'}}),
    establishPrimitive: async () => { primitiveCalls++;
      throw new Error('fixture: primitive unavailable'); },
    installWindowP: () => { throw new Error('must not install primitive'); },
    fetch: async url => {
      requests.push(url);
      if (url === failedAsset && network) throw new Error('fixture: network offline');
      const failed = url === failedAsset;
      return {ok: !failed || empty, status: failed && !empty ? status : 200,
        arrayBuffer: async () => new Uint8Array(failed && empty ? [] : [0xe9, 1, 2, 3]).buffer};
    },
  };
  context.window = context;
  vm.createContext(context);
  await vm.runInContext(source, context, {timeout: 1000});
  return {elements, primitiveCalls, requests, context,
    message: elements.msgs.textContent || elements.msgs.innerHTML};
}

const tests = [
  ...['slopkit/patches/1150.bin', 'goldhen_2.4b18.12.bin'].flatMap(asset =>
    [{status: 404}, {status: 503}, {empty: true}, {network: true}].map(failure => [
      `Unavailable ${asset} ${JSON.stringify(failure)} stops before primitive`, async () => {
        const r = await run({failedAsset: asset, ...failure});
        assert.equal(r.primitiveCalls, 0, `entered primitive; UI: ${r.message}`);
        assert.ok(r.message.includes(asset), r.message);
        assert.doesNotMatch(r.message, /restart your console/i);
      }
    ])),
  ['Primitive failure retains restart advice and shows the actual reason', async () => {
    const r = await run();
    assert.equal(r.primitiveCalls, 1);
    assert.match(r.message, /restart.*console/i);
    assert.match(r.message, /fixture: primitive unavailable/);
    assert.ok(!String(r.elements.out.style).includes('left:-9999px'), 'log stays hidden');
  }],
  ['Later failure reporting preserves the original exception', async () => {
    const r = await run();
    r.context.hostFail();
    assert.match(r.elements.msgs.textContent, /fixture: primitive unavailable/);
    assert.match(r.elements.msgs.textContent, /restart.*console/i);
  }],
  ['Failure details are rendered as text, not HTML', async () => {
    const r = await run();
    r.context.hostFail('<img src=x onerror=alert(1)>');
    assert.match(r.elements.msgs.textContent, /<img/);
    assert.doesNotMatch(r.elements.msgs.innerHTML, /<img/);
  }],
];
(async () => {
  let failures = 0;
  for (const [name, test] of tests) {
    try { await test(); console.log('PASS ' + name); }
    catch (error) { failures++; console.error('FAIL ' + name + ': ' + error.message); }
  }
  console.log(`${tests.length - failures}/${tests.length} passed; console primitives were stubbed.`);
  process.exitCode = failures ? 1 : 0;
})();
