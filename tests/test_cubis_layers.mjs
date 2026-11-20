import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
import {groupedPlateRows} from '../tools/cubis/group_rows.mjs';
const source=fs.readFileSync(new URL('../bridge/Export Cubis.js',import.meta.url),'utf8');new vm.Script(source);
const start=source.indexOf('        function get('),end=source.indexOf('        // Query all panel materials');
function panel(code,layers){
 const points=[{x:0,y:0},{x:100,y:0},{x:100,y:50},{x:0,y:50}];
 return {Name:'Orizontala',Designation:code,MaterialName:'PAL base',Thickness:18,ContourWidth:100,ContourHeight:50,
  TextureOrientation:1,Contour:{Count:4,Min:points[0],Max:points[2],Objects:points.map((p,i)=>({IsLine:()=>true,AsLine:()=>({Pos1:p,Pos2:points[(i+1)%4]})}))},
  Butts:{Count:0},Plastics:{Count:layers.length,Plastics:layers},Count:0};
}
const layer={Material:'PAL different material',Thickness:18,Side:0,TextureOrientation:2};
const a=panel('A',[layer]),b=panel('A',[layer]),c=panel('B',[]);
const context={Model:{Name:'Model',Count:3,Objects:[a,b,c]},TextureOrientation:{None:0,Horizontal:1,Vertical:2}};
vm.createContext(context);vm.runInContext(source.slice(start,end),context);
const rows=JSON.parse(JSON.stringify(context.rows));
assert.equal(rows.length,5);assert.equal(rows[1].tip,'dublura');assert.equal(rows[1].dublura_pentru_nr,rows[0].nr);
assert.equal(rows[1].diagnostic_material.desemnare_piesa,'Dublură pentru A');
assert.equal(rows[1].material,layer.Material);assert.equal(rows[1].grosime_mm,18);assert.equal(rows[1].fibra,2);
assert.equal(rows[1].canturi.length,0);assert.equal(rows[0].straturi_native[0].fata,0);
assert.equal(rows[1].contur_x_mm,100);assert.equal(rows[1].cote_cubis.lungime_mm,100);
const transform=p=>[p.diagnostic_material.desemnare_piesa,p.material,p.contur_x_mm,p.contur_y_mm,1,p.fibra,'','','','',''];
const grouped=groupedPlateRows(rows,transform,{byMaterial:true});
assert.deepEqual(grouped.map(r=>[r[0],r[4]]),[['A',2],['Dublură pentru A',2],['B',1]]);
assert.throws(()=>groupedPlateRows([rows[1]],transform),/fara placa/);
// An unlayered instance cannot silently absorb a layered instance of the same code.
const plain={...rows[0],nr:99};const mixed=groupedPlateRows([...rows,plain],transform);
assert.equal(mixed.length,4);
// Native edging is deducted from both substrates; band ordering remains on base only.
const edged=panel('E',[layer]);edged.Butts={Count:1,0:{ElemIndex:0,Material:'ABS',Sign:'edge',Thickness:1.5,Width:43,ClipPanel:true,Allowance:0}};
const ctx={Model:{Name:'M',Count:1,Objects:[edged]},TextureOrientation:context.TextureOrientation};vm.createContext(ctx);vm.runInContext(source.slice(start,end),ctx);
assert.equal(ctx.rows[0].cote_cubis.latime_mm,48.5);assert.equal(ctx.rows[1].cote_cubis.latime_mm,48.5);
assert.equal(ctx.rows[0].canturi.length,1);assert.equal(ctx.rows[1].canturi.length,0);
assert.throws(()=>{const bad=panel('X',[{...layer,Thickness:0}]);const ctx={Model:{Count:1,Objects:[bad]},TextureOrientation:context.TextureOrientation};vm.createContext(ctx);vm.runInContext(source.slice(start,end),ctx);},/Grosime dublura/);
console.log('PASS: native layer material, thickness, side, grain, dimensions, band ownership and adjacent grouped rows');
