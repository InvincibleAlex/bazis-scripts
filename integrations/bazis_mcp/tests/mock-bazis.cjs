// Isolated BAZIS mock. This never launches or controls the native application.
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');

function createEnvironment(home, realTimers = false) {
  const configFile = path.join(home, '.bazis-mcp', 'config.json');
  const config = JSON.parse(fs.readFileSync(configFile, 'utf8'));
  const runtime = config.bridge_dir;
  const source = fs.readFileSync(path.join(__dirname, '../bridge/Codex_Bazis_Bridge.js'), 'utf8');
  let nextUID = 1, pending = null, blockStack = [], tick = null;
  const counters = {commits:0,reverts:0,edits:0,continued:0};
  const notifications = [];
  function object(name, children) {
    const o={Name:name,UID:nextUID++,Position:{x:0,y:0,z:0},Visible:true,Selected:false,ArtPos:'',Designation:''};
    if (children) {o.Objects=children;Object.defineProperty(o,'Count',{get:()=>o.Objects.length});}
    Object.defineProperties(o,{
      GMin:{get:()=>({...o.Position})},GMax:{get:()=>({x:o.Position.x+100,y:o.Position.y+200,z:o.Position.z+18})},
      GabMin:{get:()=>({...o.Position})},GabMax:{get:()=>({x:o.Position.x+100,y:o.Position.y+200,z:o.Position.z+18})}
    });
    o.TranslateGCS = v=>{o.Position.x+=v.x;o.Position.y+=v.y;o.Position.z+=v.z;if(o.failNative)throw Error('Injected native failure');};
    o.RotateGCS = (axis,angle)=>{o.lastRotation={axis,angle};};
    o.Build=()=>{if(o.failBuild)throw Error('Injected build failure');};
    return o;
  }
  const root=object('Mock model',[]);
  Object.defineProperty(root,'SelectionCount',{get:()=>all().filter(o=>o.Selected).length});
  function all() {const out=[];function walk(o){for(const c of o.Objects||[]){out.push(c);walk(c);}}walk(context.Model);return out;}
  root.UnSelectAll=()=>all().forEach(o=>{o.Selected=false;});
  function add(o,owner=blockStack[blockStack.length-1]||context.Model){owner.Objects.push(o);o.Owner=owner;return o;}
  const first=add(object('Verticală'),root);first.MaterialName='Panou lemn, 18mm';first.Thickness=18;
  const group=add(object('Corp test',[]),root);const nested=add(object('Poliță'),group);nested.Thickness=18;
  function capture(){return [context.Model,...all()].map(o=>({o,Name:o.Name,Position:{...o.Position},Visible:o.Visible,ArtPos:o.ArtPos,Designation:o.Designation,Objects:o.Objects?o.Objects.slice():undefined}));}
  const context={Model:root,ModelFilename:'mock.b3d',ActiveMaterial:{Name:'Mock material',Thickness:18},
    system:{apiVersion:2341},process,console,Buffer,WeakMap,WeakSet,
    require:n=>n==='os'?{...os,homedir:()=>home}:require(n),
    alert:m=>notifications.push(m),
    setInterval:realTimers?setInterval:fn=>{tick=fn;return 1;},clearInterval:realTimers?clearInterval:()=>{tick=null;},
    StartEditing:()=>{pending=capture();counters.edits++;},
    Action:{KeyPreview:false,Continue:()=>counters.continued++,Commit:()=>{pending=null;counters.commits++;},
      Revert:()=>{if(pending)for(const s of pending){s.o.Name=s.Name;s.o.Position={...s.Position};s.o.Visible=s.Visible;s.o.ArtPos=s.ArtPos;s.o.Designation=s.Designation;if(s.Objects)s.o.Objects=s.Objects;}pending=null;counters.reverts++;},
      Finish:()=>{if(context.Action.OnFinish)context.Action.OnFinish();},
      SaveModel:p=>{fs.writeFileSync(p,'BZ85-mock-file');context.ModelFilename=p;}}
  };
  context.NewVector=(x,y,z)=>({x,y,z});
  function panel(kind,a,b,c,d,e){const o=object('Panel');o.MaterialName='Mock material';o.Thickness=18;o.ContourWidth=c-a;o.ContourHeight=d-b;o.kind=kind;return add(o);}
  context.AddFrontPanel=(...args)=>panel('front',...args);
  context.AddHorizPanel=(...args)=>panel('horizontal',...args);
  context.AddVertPanel=(...args)=>panel('vertical',...args);
  context.BeginBlock=name=>{const b=add(object(name,[]));blockStack.push(b);return b;};
  context.EndBlock=()=>blockStack.pop();
  context.AddCopy=o=>{const copy=object(o.Name);copy.Position={...o.Position};copy.Thickness=o.Thickness;return add(copy,o.Owner);};
  context.DeleteObject=o=>{const owner=o.Owner;owner.Objects.splice(owner.Objects.indexOf(o),1);};
  context.SetCamera=v=>{context.camera=v;};context.ViewAll=()=>{};
  ['Front','Back','Left','Right','Top','Bottom','Isometric'].forEach((s,i)=>{context['p3d'+s]=i;});
  vm.createContext(context);vm.runInContext(source,context,{timeout:5000});
  return {context,root,first,group,nested,counters,notifications,runtime,tick:()=>{if(tick)tick();},all,
    setNow:ms=>{context.testNow=ms;vm.runInContext('Date.now = function () { return testNow; };',context);}};
}
module.exports={createEnvironment};
if(require.main===module){
  const env=createEnvironment(process.argv[2],true);
  if(env.notifications.length)throw Error(env.notifications.join('\n'));
  const shutdown=()=>{env.context.Action.Finish();process.exit(0);};
  process.on('SIGTERM',shutdown);process.on('SIGINT',shutdown);
}
