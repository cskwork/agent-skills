#!/usr/bin/env node
// Install the shared prose policy without replacing unrelated rules.
import { readFileSync, writeFileSync, mkdirSync, existsSync, copyFileSync, lstatSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const target = process.argv[2];
if (!target) throw new Error('Usage: node scripts/install-writing-rule.mjs <rules-directory>');
const source = fileURLToPath(new URL('../rules/writing.md', import.meta.url));
const dir = resolve(target);
const writingPath = join(dir, 'writing.md');
const rulesPath = join(dir, 'rules.md');
for (const path of [writingPath, rulesPath]) {
  if (lstatSync(path, { throwIfNoEntry: false })?.isSymbolicLink()) {
    throw new Error(`Refusing to replace a linked rule; inspect its target first: ${path}`);
  }
}
const wanted = readFileSync(source, 'utf8');
const current = existsSync(writingPath) ? readFileSync(writingPath, 'utf8') : null;
const rules = existsSync(rulesPath) ? readFileSync(rulesPath, 'utf8') : '';
const start = '<!-- humanizer-writing-default:start -->';
const end = '<!-- humanizer-writing-default:end -->';
const block = `${start}\n\n## 기본 글쓰기\n\n- 글을 작성하거나 다듬을 때는 Humanizer를 기본으로 사용한다. 이 디렉터리의 writing.md를 따른다. Unslop 등 다른 문체 교정 스킬은 명시적 요청이 있을 때만 사용한다.\n\n${end}`;
const begin = rules.indexOf(start);
const finish = rules.indexOf(end);
if ((begin === -1) !== (finish === -1) || (begin >= 0 && (finish < begin || rules.indexOf(start, begin + start.length) >= 0 || rules.indexOf(end, finish + end.length) >= 0))) {
  throw new Error('Malformed Humanizer rule block; no rules were changed');
}
const updated = begin < 0
  ? `${rules.trimEnd()}${rules.trim() ? '\n\n' : ''}${block}\n`
  : rules.slice(0, begin) + block + rules.slice(finish + end.length);
mkdirSync(dir, { recursive: true });
if (current !== wanted) {
  if (current !== null) {
    const backups = join(dir, 'backups');
    mkdirSync(backups, { recursive: true });
    copyFileSync(writingPath, join(backups, `writing.md.${Date.now()}.bak`));
  }
  writeFileSync(writingPath, wanted);
}
if (updated !== rules) writeFileSync(rulesPath, updated);
console.log(`Humanizer writing policy installed in ${dir}`);
