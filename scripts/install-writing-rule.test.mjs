import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, readdirSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const installer = fileURLToPath(new URL('./install-writing-rule.mjs', import.meta.url));
const make = () => mkdtempSync(join(tmpdir(), 'humanizer-rules-'));
const run = dir => execFileSync(process.execPath, [installer, dir], { encoding: 'utf8', stdio: 'pipe' });

test('preserves unrelated rules, backs up writing policy, and is idempotent', () => {
  const dir=make();writeFileSync(join(dir,'rules.md'),'# Existing rules\n\nKeep this instruction.\n');
  writeFileSync(join(dir,'writing.md'),'My previous writing policy.\n');run(dir);
  const first=readFileSync(join(dir,'rules.md'),'utf8');
  assert(first.startsWith('# Existing rules\n\nKeep this instruction.\n'));
  assert(readFileSync(join(dir,'writing.md'),'utf8').includes('humanizer'));
  const backups=readdirSync(join(dir,'backups'));assert.equal(backups.length,1);
  assert.equal(readFileSync(join(dir,'backups',backups[0]),'utf8'),'My previous writing policy.\n');
  run(dir);assert.equal(readFileSync(join(dir,'rules.md'),'utf8'),first);
  assert.equal(readdirSync(join(dir,'backups')).length,1);
});

test('a malformed block fails before changing either rule file', () => {
  const dir=make();const malformed='personal\n<!-- humanizer-writing-default:start -->\n';
  writeFileSync(join(dir,'rules.md'),malformed);writeFileSync(join(dir,'writing.md'),'preserve me');
  assert.throws(()=>run(dir),/Malformed Humanizer/);
  assert.equal(readFileSync(join(dir,'rules.md'),'utf8'),malformed);
  assert.equal(readFileSync(join(dir,'writing.md'),'utf8'),'preserve me');
});

test('linked writing rules are not overwritten', () => {
  const dir=make();const original=join(dir,'original.md');writeFileSync(original,'preserve target');
  symlinkSync(original,join(dir,'writing.md'));
  assert.throws(()=>run(dir),/Refusing to replace a linked rule/);
  assert.equal(readFileSync(original,'utf8'),'preserve target');
});
