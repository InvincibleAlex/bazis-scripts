import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
const source=fs.readFileSync(new URL('../../bridge/Export Cote.js',import.meta.url),'utf8');
const code=source.slice(source.indexOf('// The complete package'),source.indexOf('  var now=new Date();'));
const win=path.win32,shared=String.raw`\\RG\Bazis\Scripts\Export Cote`;
function run(scriptDir,valid,env={},partial=null){
 const context={__dirname:scriptDir,path:win,process:{env},get:(o,k)=>o?.[k],fs:{
  existsSync:file=>valid.some(root=>win.normalize(file).startsWith(win.normalize(root)+'\\')) || (partial&&win.normalize(file).startsWith(partial+'\\')&&!file.endsWith('dimension_sections.py')),
  readFileSync:()=>{throw Error('Must not read per-user configuration');}}};
 vm.runInNewContext(code,context);return context;
}
const local=String.raw`D:\Alte fisiere\Scripts\Export Cote`;
let result=run(String.raw`D:\Alte fisiere\Scripts`,[local]);assert.equal(result.cfg.python,win.join(local,'runtime/python/python.exe'));
result=run(String.raw`C:\Users\OtherUser\Scripts`,[shared]);assert.equal(result.packageRoot,shared);
result=run(String.raw`C:\Users\OtherUser\Scripts`,[shared,local],{BAZIS_EXPORT_COTE_HOME:local});assert.equal(result.packageRoot,local);
result=run(String.raw`D:\Alte fisiere\Scripts`,[shared],{},local);assert.equal(result.packageRoot,shared,'incomplete local package falls back to complete shared package');
assert.throws(()=>run('C:\\Missing',[]),/Pachetul Export Cote/);
assert(!source.includes('material-db-reader.json'));assert(!source.includes("'Documents','BazisMCP'"));
console.log('PASS: relocatable local package, different Windows user, shared fallback and missing-package diagnostics; no MCP config dependency');
