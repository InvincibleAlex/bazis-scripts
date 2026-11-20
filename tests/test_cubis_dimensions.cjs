const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(require('path').join(__dirname,'../bridge/Export Cubis.js'),'utf8');
new vm.Script(source);
const start=source.indexOf('        function exportDimension(');
const end=source.indexOf('        function str(',start);
const context={};vm.createContext(context);vm.runInContext(source.slice(start,end),context);
const normalize=context.exportDimension;
assert.equal(normalize(971.9982617042044),972);
assert.equal(normalize(149.99652340840908),150);
assert.equal(normalize(300.00000000000006),300);
assert.equal(normalize(972.008),972);
for(const n of [971.98,972.02,582.5,300.8,300.25,0.008])assert.equal(normalize(n),n);
// Normalize the contour before edging deductions: keep fractional cut sizes.
assert.equal(normalize(971.9982617042044)-3,969);
assert.equal(normalize(582)-1.5,580.5);
if(process.argv[2]){
 const report=JSON.parse(fs.readFileSync(process.argv[2],'utf8').replace(/^\uFEFF/,''));
 const matches=report.placi.filter(p=>p.diagnostic_material.desemnare_piesa==='00.01.02.00.002');
 assert.equal(matches.length,2);
 for(const p of matches){
  assert.equal(normalize(p.contur_y_mm),972);
  assert.equal(normalize(p.contur_y_mm)-p.cote_cubis.scadere_y_mm,969);
  assert.equal(normalize(p.contur_x_mm)-p.cote_cubis.scadere_x_mm,297);
 }
 console.log('PASS: actual v3 duplicate dimensions agree; native edging deductions retained');
}
console.log('PASS: near-integer normalization, real fractions and script syntax');
