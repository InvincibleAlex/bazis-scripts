// Verify metadata-only behavior without native BAZIS or user files.
const fs=require('fs'),path=require('path'),os=require('os'),vm=require('vm'),assert=require('assert');
const home=fs.mkdtempSync(path.join(os.tmpdir(),'bazis-drawing-probe-'));
fs.mkdirSync(path.join(home,'Documents','Bazis','Scripts'),{recursive:true});
let getterCalls=0,methodCalls=0,factoryCalls=0,constructorCalls=0;
function NativeSettings(){constructorCalls++;throw Error('Must not construct native settings');}
Object.defineProperty(NativeSettings.prototype,'DrawingStyle',{get(){getterCalls++;throw Error('Must not read host getters');}});
NativeSettings.prototype.GenerateDrawings=function(){methodCalls++;};
const action={Hint:'leave unchanged',Commit(){methodCalls++;},Finish(){methodCalls++;}};
Object.defineProperty(action,'CurrentDrawing',{get(){getterCalls++;throw Error('Must not read native documents');}});
const model={Count:2,Name:'unchanged'};
const context={Model:model,Action:action,TUserSettings:NativeSettings,IDrawingManager:function(){constructorCalls++;},
    NewImportExport(){factoryCalls++;return {Save(){methodCalls++;},Load(){methodCalls++;}};},
    require:n=>n==='os'?{homedir:()=>home}:require(n),alert(){}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../bridge/Codex_Bazis_DrawingAPI_Probe.js'),'utf8'),context,{timeout:5000});
const result=JSON.parse(fs.readFileSync(path.join(home,'Documents/Bazis/Scripts/Codex_Bazis_DrawingAPI.report.json'),'utf8'));
assert.equal(getterCalls,0);assert.equal(methodCalls,0);assert.equal(constructorCalls,0);assert.equal(factoryCalls,1);
assert.equal(action.Hint,'leave unchanged');assert.deepEqual(model,{Count:2,Name:'unchanged'});
const settings=result.roots.find(r=>r.name==='TUserSettings');
assert(settings.instance_prototype.relevant_members.some(m=>m.name==='DrawingStyle' && m.kind==='accessor; not read'));
assert(settings.instance_prototype.relevant_members.some(m=>m.name==='GenerateDrawings' && m.kind==='function'));
assert.equal(result.roots.find(r=>r.name==='TScaledGraphicDrawer').available,false);
const resolved=fs.realpathSync(home);assert.equal(path.dirname(resolved),fs.realpathSync(os.tmpdir()));assert(path.basename(resolved).startsWith('bazis-drawing-probe-'));
fs.rmSync(resolved,{recursive:true,force:true});
console.log('PASS: drawing probe inspects metadata without reading native getters, invoking drawing methods or modifying models/settings');
