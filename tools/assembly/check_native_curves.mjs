import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../../bridge/Export Asamblare.js',import.meta.url),'utf8');
const ctx={};vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('  function get('),source.indexOf('  function point2(')),ctx);
if(!process.argv[2])throw Error('Provide a saved native MCP hardware response');
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
for(const item of data.items){
 const native=item.native_hardware.geometry;
 const object={GabMin:item.bounds_global_mm.min,GabMax:item.bounds_global_mm.max,EdgesCount:native.count,
  Edges:native.edges.map(e=>({Count:e.points_global_mm.length,GVertices:e.points_global_mm}))};
 const edges=ctx.nativeEdges(object),expected=native.edges.reduce((n,e)=>n+e.points_global_mm.slice(1).filter((p,i)=>['x','y','z'].some(k=>Math.abs(p[k]-e.points_global_mm[i][k])>1e-8)).length,0);
 assert.equal(edges.length,expected);assert(edges.length>12,'Native curved fitting must not become a 12-edge bounding box');
 assert.equal(edges.flat().some(p=>p.some(v=>!Number.isFinite(v))),false);
 console.log(item.name.split('\r')[0]+': '+edges.length+' native segments, no bounding box');
}
console.log('PASS: actual BAZIS screw, dowel and hinge curves survive point-only construction edges');
