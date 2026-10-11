import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const config = JSON.parse(readFileSync(new URL('../capacitor.config.json', import.meta.url)));
test('native shell ships no endpoint, credentials, plugins or cleartext exception', () => {
  assert.equal(config.server.url, undefined);
  assert.equal(config.server.cleartext, false);
  assert.equal(config.android.allowMixedContent, false);
  assert.equal(config.android.webContentsDebuggingEnabled, false);
  assert.equal(config.loggingBehavior, 'none');
  assert.deepEqual(config.android.includePlugins, []);
});
test('patched uuid preserves xcode identifier generation', () => {
  const require = createRequire(import.meta.url);
  const cliRequire = createRequire(require.resolve('@capacitor/cli/package.json'));
  const xcode = cliRequire('xcode');
  const project = xcode.project('unused-project.pbxproj');
  project.hash = {project: {objects: {}}};
  const identifiers = Array.from({length:1000}, () => project.generateUuid());
  assert.equal(new Set(identifiers).size,1000);
  assert.ok(identifiers.every(id => /^[A-F0-9]{24}$/.test(id)));
});
test('offline verification screen cannot impersonate a live queue', () => {
  const html = readFileSync(new URL('../www/index.html', import.meta.url), 'utf8');
  assert.match(html, /installation check/i);
  assert.match(html, /awaiting approval/i);
  assert.doesNotMatch(html, /<script|password.*value=|<iframe/i);
});
