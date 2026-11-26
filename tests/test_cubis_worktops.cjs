const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(require('path').join(__dirname,'../bridge/Export Cubis.js'),'utf8');
const start=source.indexOf('        function get('),end=source.indexOf('        // Query all panel materials');
const points=[{x:0,y:0},{x:100,y:0},{x:100,y:50},{x:0,y:50}];
const panel={Name:'Blat',Designation:'BL01',MaterialName:'Blat de bucătărie căntuit EGGER 26+, Stejar Casella Natur, H1385 ST40\r50144/1385',Thickness:38,ContourWidth:100,ContourHeight:50,TextureOrientation:1,
 Contour:{Count:4,Min:points[0],Max:points[2],Objects:points.map((p,i)=>({IsLine:()=>true,AsLine:()=>({Pos1:p,Pos2:points[(i+1)%4]})}))},Butts:{Count:0},Plastics:{Count:0},Count:0};
const context={Model:{Name:'M',Count:1,Objects:[panel]},TextureOrientation:{None:0,Horizontal:1,Vertical:2}};
vm.createContext(context);vm.runInContext(source.slice(start,end),context);
assert.equal(context.rows.length,1);assert.equal(context.rows[0].grosime_mm,38);assert.equal(context.rows[0].material,panel.MaterialName);
const renderer=fs.readFileSync(require('path').join(__dirname,'../tools/cubis/export_cubis.mjs'),'utf8');
const predicate=renderer.match(/export function isPalPanel\(p\)\{[^\n]+\}/)[0].replace('export ','');
vm.runInContext(predicate,context);
assert(context.isPalPanel({material:panel.MaterialName}));assert(context.isPalPanel({material:'PAL test'}));assert(!context.isPalPanel({material:'MDF test\rBlat articol'}));assert(!context.isPalPanel({material:'MDF test'}));
console.log('PASS: native 38 mm worktop and renderer selection include Blat without changing PAL behavior');
