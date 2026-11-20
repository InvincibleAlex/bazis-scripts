import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../../bridge/Export Asamblare.js',import.meta.url),'utf8');
const line=(a,b)=>({IsLine:()=>true,AsLine:()=>({Pos1:{x:a[0],y:a[1]},Pos2:{x:b[0],y:b[1]}})});
const panel={UID:42,Name:'Poliță',Visible:true,MaterialName:'PAL, alb',ContourWidth:600,ContourHeight:300,Thickness:18,Designation:'001',
 GabMin:{x:10,y:20,z:30},GabMax:{x:610,y:38,z:330},
 ToGlobal:p=>({x:p.x+10,y:p.z+20,z:p.y+30}),
 Contour:{Count:4,Objects:[line([0,0],[600,0]),line([600,0],[600,300]),line([600,300],[0,300]),line([0,300],[0,0])]}};
panel.Cuts={Count:1,Cuts:[{Name:'Canal test',Sign:'G=6',CutType:7,FrontSide:false,Thickness:-6,
 Params:{Depth:6,Offset:12,Offset2:0,Radius:2,Width:4,Angle:0,CutType:3},
 Trajectory:{Count:1,Objects:[line([12,0],[12,300])]},Contour:{Count:1,Objects:[line([0,0],[4,-6])]},
 CreateParams:()=>{throw Error('Reading must never create machining parameters');}}]};
const hardware={Name:'Composite foot',IsFastener:()=>true,Count:1,Objects:[{...panel,Name:'Internal fitting board',MaterialName:'PAL, alb'}],GabMin:panel.GabMin,GabMax:panel.GabMax,FindFastenedObjects:()=>[{UID:42}]};
const hinge={Name:'Hettich Balama tipar de g\u0103urire\r9073567',GabMin:{x:10,y:20,z:30},GabMax:{x:30,y:40,z:50}};
const curvePoints=[{x:11,y:20,z:30},{x:10,y:21,z:30},{x:9,y:20,z:30},{x:10,y:19,z:30},{x:11,y:20,z:30}];
const nativeFitting={UID:77,Name:'Native screw\rTEST',GabMin:{x:9,y:19,z:30},GabMax:{x:11,y:21,z:30},EdgesCount:1,Edges:[{Count:5,GVertices:curvePoints}],ToGlobal:()=>{throw Error('Native GVertices must not be transformed again');}};
const hidden={Name:'Hidden group',Visible:false,Count:1,Objects:[{...panel,Name:'Hidden panel'}]};
let report,alerts=[],model={Name:'Model',Count:1,Objects:[{Name:'M1',Count:5,Objects:[panel,hardware,hidden,hinge,nativeFitting]}]};
const before=JSON.stringify(model),files=new Map();
const fakeFs={existsSync:()=>true,readFileSync:()=>JSON.stringify({python:'python'}),writeFileSync:(p,data)=>{files.set(p,data);if(p.endsWith('.json'))report=JSON.parse(data);},appendFileSync:(p,data)=>files.set(p,(files.get(p)||'')+data),unlinkSync:p=>files.delete(p),statSync:()=>({size:10})};
let shellCalls=0;
const cp={execFileSync:(exe,args)=>{assert.equal(exe,'powershell.exe','PDF generation must not block the native script');shellCalls++;return shellCalls===1?Buffer.from('C:/assembly.pdf').toString('base64'):'';}};
const NewHoleDrilling=()=>({AddBody:()=>{},AddFasteners:()=>{},DrillHoles:()=>{},Bodies:{FindBodyInfo:o=>({Holes:{Count:1,Items:[{Body:o,Fastener:nativeFitting,Diameter:5,Radius:2.5,Depth:5,DrillMode:2,Position:{x:10,y:20,z:35},Direction:{x:1,y:0,z:0}}]}})}});
vm.runInNewContext(source,{Model:model,ModelFilename:'C:/test.b3d',Action:{},NewHoleDrilling,NewVector:(x,y,z)=>({x,y,z}),Buffer,WeakSet,Date,process:{pid:123},alert:s=>alerts.push(s),require:k=>k==='fs'?fakeFs:k==='child_process'?cp:k==='os'?{homedir:()=>'/home',tmpdir:()=>'/tmp'}:path});
assert.equal(report.panels.length,2,'include temporarily hidden boards, exclude fitting internals');
assert.equal(report.hardware.length,3,'keep composite fitting atomic and read plain hinge with drilling in its name');
assert.equal(report.hardware[0].edges.length,12,'extract composite internal geometry once');
assert.deepEqual(report.hardware[0].connected_panel_uids,[42]);
assert.equal(report.hardware[1].article,'9073567');
assert.equal(report.hardware[1].edges.length,12,'bounds fallback for CAD leaf');
assert.equal(report.hardware[2].edges.length,4,'preserve native curve vertices instead of a bounding box');
assert.equal(report.hardware[2].approximate_components,0);
assert.equal(report.hardware[2].native_edge_components,1);
assert.deepEqual(report.hardware[2].edges[0],[[11,20,30],[10,21,30]],'native global vertices remain unchanged');
assert.deepEqual(report.panels[0].edges[0],[[10,20,30],[610,20,30]],'global point transform');
assert.deepEqual(report.panels[0].edges[1],[[10,38,30],[610,38,30]],'extrusion follows transformed thickness axis');
assert.equal(report.panels[0].edges.length,12);
assert.equal(report.drilling.hole_count,2);
assert.equal(report.panels[0].holes[0].diameter_mm,5);
assert.equal(report.panels[0].holes[0].panel_uid,42);
assert.deepEqual(report.panels[0].holes[0].position_global_mm,[10,20,35]);
assert.equal(report.panels[0].holes[0].coordinate_space_verified,true);
assert.equal(report.panels[0].holes[0].fastener_article_id,report.hardware[2].id);
assert.deepEqual(report.hardware[2].connected_panel_uids,[42]);
const cut=report.panels[0].machining.cuts[0];
assert.equal(cut.params.Depth,6,'read BAZIS G directly');
assert.equal(cut.params.Offset,12,'read BAZIS dx directly');
assert.equal(cut.params.Offset2,0,'preserve zero-valued BAZIS parameters');
assert.equal(cut.properties.Thickness,-6,'preserve signed depth rather than guessing the machining side');
assert.equal(cut.properties.FrontSide,false);
assert.equal(cut.params.Radius,2);
assert.equal(cut.params.Diameter,undefined,'never treat radius as diameter');
assert.deepEqual(cut.trajectory.elements[0].start,{x:12,y:0});
assert.deepEqual(cut.section.elements[0].end,{x:4,y:-6});
assert.equal(cut.drawing_geometry_inferred,false);
assert.equal(JSON.stringify(model),before,'read only');
assert.equal(files.size,3,'worker owns the input, log and state until PDF generation completes');
assert([...files.entries()].some(([p,v])=>p.endsWith('.state')&&v==='ready'));
assert([...files.entries()].some(([p,v])=>p.endsWith('.log')&&v.includes('BAZIS poate fi folosit')));
assert.equal(shellCalls,2,'save dialog and terminal launch only');assert.equal(alerts.length,0);
console.log('Native export: geometry, drilling, read-only model and independent console handoff OK.');
