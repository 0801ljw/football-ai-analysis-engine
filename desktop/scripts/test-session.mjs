import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { test } from 'node:test';

const origin = 'http://127.0.0.1:8765';
const token = 'synthetic-session-for-test-only';
const source = readFileSync(new URL('../src-tauri/src/session.js', import.meta.url), 'utf8')
  .replace('__ORIGIN__', JSON.stringify(origin)).replace('__TOKEN__', JSON.stringify(token));
function bootstrap(pageOrigin = origin, subframe = false) {
  const requests = [];
  const window = { location: { origin: pageOrigin }, fetch: async r => { requests.push(r); return r; } };
  window.top = subframe ? {} : window;
  class BrowserRequest extends Request {
    constructor(input, init) { super(typeof input === 'string' ? new URL(input, origin) : input, init); }
  }
  vm.runInNewContext(source, { window, Request: BrowserRequest, Headers, URL });
  return { window, requests };
}
test('authorized fetch carries session and user header, never URL or redirects', async () => {
  const { window, requests } = bootstrap();
  await window.fetch('/api/matches', { headers: { 'X-API-Token': 'user-token' } });
  assert.equal(requests[0].headers.get('X-Desktop-Session'), token);
  assert.equal(requests[0].headers.get('X-API-Token'), 'user-token');
  assert.equal(requests[0].redirect, 'error');
  assert.ok(!requests[0].url.includes(token));
  assert.equal(Object.getOwnPropertyDescriptor(window, 'fetch').writable, false);
  assert.ok(!Object.values(window).includes(token));
});
test('cross origin fetch never receives desktop session', async () => {
  const { window, requests } = bootstrap();
  await window.fetch('https://example.com/api');
  assert.equal(requests[0].headers.get('X-Desktop-Session'), null);
});
test('initialization on foreign pages and report subframes does not expose credentials', async () => {
  for (const args of [['https://example.com', false], [origin, true]]) {
    const { window, requests } = bootstrap(...args);
    await window.fetch(new Request(origin + '/api/matches'));
    assert.equal(requests[0].headers.get('X-Desktop-Session'), null);
  }
});
