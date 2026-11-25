// BAZIS 2022 / Node 8. Read-only assembly illustration prototype.
(function () {
 'use strict';
 var jobLog=null,jobState=null,timer=null,nativeDone=false;
 function text(v){return v==null?'':String(v);}
 function progress(message){if(jobLog)fs.appendFileSync(jobLog,new Date().toLocaleTimeString()+' | '+message+'\n','utf8');}
 try {
  var fs=require('fs'),path=require('path'),os=require('os'),cp=require('child_process');
  function get(o,k){try{return o[k];}catch(e){return undefined;}}
  function vec(v){if(!v)return null;var a=[v.x,v.y,v.z];return a.every(function(n){return typeof n==='number'&&isFinite(n);})?a:null;}
  function positive(n){return typeof n==='number'&&isFinite(n)&&n>0;}
  function objectFrame(o){
   if(typeof get(o,'ToGlobal')!=='function')return null;
   var origin=vec(o.ToGlobal(NewVector(0,0,0))),axes=[];if(!origin)return null;
   for(var i=0;i<3;i++){var v=[0,0,0];v[i]=1;var p=vec(o.ToGlobal(NewVector(v[0],v[1],v[2])));if(!p)return null;axes.push(p.map(function(n,j){return n-origin[j];}));}
   return {origin:origin,axes:axes,source:'BAZIS ToGlobal'};
  }
  function validBounds(o){var b={min:vec(get(o,'GabMin')),max:vec(get(o,'GabMax'))};return b.min&&b.max?b:null;}
  function boundsEdges(b){
   var v=[],out=[];for(var i=0;i<8;i++)v.push([b[i&1?'max':'min'][0],b[i&2?'max':'min'][1],b[i&4?'max':'min'][2]]);
   for(var j=0;j<8;j++)for(var a=0;a<3;a++)if(!(j&(1<<a)))out.push([v[j],v[j^(1<<a)]]);return out;
  }
  // BAZIS T3DEdge.GVertices are already in global coordinates. They retain
  // the sampled native curves; do not apply ToGlobal a second time.
  function nativeEdges(o){
   var result=[],n=get(o,'EdgesCount'),list=get(o,'Edges');
   if(typeof n!=='number'||n<1||n>20000||n!==Math.floor(n))return result;
   var b=validBounds(o),eps=.1;
   try{
    for(var i=0;i<n;i++){
     var edge=get(list,i),count=get(edge,'Count'),vertices=get(edge,'GVertices');
     if(typeof count!=='number'||count<0||count>20000||count!==Math.floor(count))return [];
     // Native fittings include point-only construction edges before their
     // circular polylines. They have no drawable segment; keep the other edges.
     if(count<2)continue;
     var previous=null;
     for(var j=0;j<count;j++){
      var point=vec(get(vertices,j));if(!point)return [];
      if(b&&point.some(function(v,a){return v<b.min[a]-eps||v>b.max[a]+eps;}))return [];
      if(previous&&point.some(function(v,a){return Math.abs(v-previous[a])>1e-8;}))result.push([previous,point]);
      previous=point;
      if(result.length>100000)return [];
     }
    }
   }catch(ignore){return [];}
   return result;
  }
  function point2(v){var x=get(v,'x'),y=get(v,'y');return typeof x==='number'&&isFinite(x)&&typeof y==='number'&&isFinite(y)?{x:x,y:y}:null;}
  function scalarFields(o,names){
   var result={};names.forEach(function(k){var v=get(o,k);if(typeof v==='string'||typeof v==='boolean'||typeof v==='number'&&isFinite(v))result[k]=v;});return result;
  }
  function readContour(contour,depth){
   var out={elements:[],complete:true},n=get(contour,'Count'),list=get(contour,'Objects');
   if(typeof n!=='number'||n<0||n>10000||depth>8)return {elements:[],complete:false};
   for(var i=0;i<n;i++){
    var e=get(list||contour,i),item={type:'unsupported',raw_type:get(e,'ElType')};
    try{
     if(typeof get(e,'IsLine')==='function'&&e.IsLine()){var l=e.AsLine();item={type:'line',start:point2(l.Pos1),end:point2(l.Pos2)};}
     else if(typeof get(e,'IsCircle')==='function'&&e.IsCircle()){var c=e.AsCircle();item={type:'circle',center:point2(c.Center),radius:get(c,'CirRadius'),direction:get(c,'Dir')};}
     else if(typeof get(e,'IsArc')==='function'&&e.IsArc()){var a=e.AsArc();item={type:'arc',start:point2(a.Pos1),end:point2(a.Pos2),center:point2(a.Center),counterclockwise:get(a,'ArcDir')};}
     else if(typeof get(e,'IsEllipse')==='function'&&e.IsEllipse()){var ell=e.AsEllipse();item={type:'ellipse',center:point2(ell.Center),parameters:scalarFields(ell,['MajorRadius','MinorRadius','MajorAxisAngle','Dir'])};}
     else if(typeof get(e,'IsList')==='function'&&e.IsList()){var nested=readContour(e.AsList(),depth+1);item={type:'list',contour:nested};if(!nested.complete)out.complete=false;}
    }catch(error){item={type:'unreadable',error:text(error.message||error)};}
    if(item.type==='unsupported'||item.type==='unreadable'||item.start===null||item.end===null||item.center===null)out.complete=false;
    out.elements.push(item);
   }
   return out;
  }
  function panelMachining(panel){
   var collection=get(panel,'Cuts'),n=get(collection,'Count'),items=get(collection,'Cuts'),result=[];
   if(typeof n!=='number'||n<0||n>10000)return {source:'BAZIS panel.Cuts',complete:false,cuts:[]};
   for(var i=0;i<n;i++){
    var cut=get(items||collection,i),params=get(cut,'Params');
    result.push({index:i,source:'BAZIS panel.Cuts['+i+']',
     properties:scalarFields(cut,['Name','Sign','CutType','FrontSide','Thickness']),
     params:params?scalarFields(params,['Name','Sign','SignFormula','CutType','Depth','Offset','Offset2','Radius','Width','Angle','Fragment']):null,
     trajectory:readContour(get(cut,'Trajectory'),0),section:readContour(get(cut,'Contour'),0),
     coordinate_space:'BAZIS native 2D cut trajectory and section; panel frame stored separately',
     drawing_geometry_inferred:false});
   }
   return {source:'BAZIS panel.Cuts',complete:true,cuts:result};
  }
  function calculatePanelHoles(panelRefs,articleByUid){
   if(typeof NewHoleDrilling!=='function')throw Error('NewHoleDrilling indisponibil; gaurile nu pot fi confirmate.');
   var calculator=NewHoleDrilling(),total=0;
   panelRefs.forEach(function(entry){calculator.AddBody(entry.object);});
   calculator.AddFasteners(Model);calculator.DrillHoles();
   panelRefs.forEach(function(entry){
    var p=entry.record,info=calculator.Bodies.FindBodyInfo(entry.object),list=get(info,'Holes'),n=get(list,'Count'),items=get(list,'Items');
    if(typeof n!=='number'||n<0||n!==Math.floor(n))throw Error('Lista de gauri calculata indisponibila: '+p.designation);
    total+=n;if(total>50000)throw Error('Prea multe gauri pentru export.');
    p.holes=[];p.drilling_source='BAZIS NewHoleDrilling';
    for(var i=0;i<n;i++){
     var h=get(items||list,i),body=get(h,'Body'),fastener=get(h,'Fastener'),position=vec(get(h,'Position')),direction=vec(get(h,'Direction')),depth=get(h,'Depth');
     if(get(body,'UID')!==p.uid||!position||!direction||typeof depth!=='number'||!isFinite(depth)||depth<0)throw Error('Date de gaurire invalide: '+p.designation);
     if(Math.abs(direction.reduce(function(sum,v){return sum+v*v;},0)-1)>1e-5)throw Error('Directie de gaurire neconfirmata: '+p.designation);
     // Native TDrilledHole Position/Direction are global. Confirm both endpoints
     // remain in the receiving body's bounds before accepting them for drawing.
     [0,depth].forEach(function(distance){
      if(position.some(function(v,a){var q=v+distance*direction[a];return q<p.bounds.min[a]-.05||q>p.bounds.max[a]+.05;}))throw Error('Coordonate de gaurire neconfirmate: '+p.designation);
     });
     var fastenerUid=get(fastener,'UID'),article=articleByUid[String(fastenerUid)],local=null,localDirection=null;
     if(typeof get(entry.object,'ToObject')==='function')local=vec(entry.object.ToObject(get(h,'Position')));
     if(typeof get(entry.object,'NToObject')==='function')localDirection=vec(entry.object.NToObject(get(h,'Direction')));
     if(!localDirection&&p.frame)localDirection=p.frame.axes.map(function(axis){return axis.reduce(function(sum,v,a){return sum+v*direction[a];},0);});
     p.holes.push({source:'BAZIS NewHoleDrilling',panel_uid:p.uid,fastener_uid:fastenerUid,fastener_name:text(get(fastener,'Name')),
      fastener_article_id:article?article.id:null,diameter_mm:get(h,'Diameter'),radius_mm:get(h,'Radius'),depth_mm:depth,drill_mode:get(h,'DrillMode'),
      position_global_mm:position,direction_global:direction,position_panel_local_mm:local,direction_panel_local:localDirection,
      coordinate_space_verified:true,contour_element_count:get(get(h,'Contour'),'Count')});
     if(article&&article.connected_panel_uids.indexOf(p.uid)<0)article.connected_panel_uids.push(p.uid);
    }
   });
   return {source:'BAZIS NewHoleDrilling',hole_count:total,panel_count:panelRefs.length,coordinate_space:'global',panel_assignment:'native Body reference'};
  }
  function hardwareGeometry(root){
   var edges=[],todo=[root],visited=new WeakSet(),approximate=0,objectCount=0,shaftAxes=[],nativeComponents=0;
   while(todo.length){
    var o=todo.pop();if(!o||visited.has(o))continue;visited.add(o);
    if(++objectCount>10000)throw Error('Feronerie prea complexa.');
    var name=text(get(o,'Name'));
    if(/^(gaur|g\u0103ur|hole\b|linie de|caset\u0103 de)/i.test(name))continue;
    var contour=get(o,'Contour'),n=get(contour,'Count'),t=get(o,'Thickness'),before=edges.length;
    var direct=nativeEdges(o);if(direct.length){edges=edges.concat(direct);nativeComponents++;}
    if(!direct.length&&typeof n==='number'&&n>0&&n<10000&&positive(t)&&typeof get(o,'ToGlobal')==='function'){
     var elems=get(contour,'Objects');
     for(var i=0;i<n;i++){
      var e=get(elems||contour,i),segments=[];
      if(e&&typeof e.IsLine==='function'&&e.IsLine()){var l=e.AsLine();segments.push([l.Pos1,l.Pos2]);}
      else if(e&&typeof e.IsCircle==='function'&&e.IsCircle()){
       var circle=e.AsCircle(),r=get(circle,'CirRadius'),c=get(circle,'Center');
       if(positive(r)&&c)for(var k=0;k<24;k++)segments.push([{x:c.x+r*Math.cos(k*Math.PI/12),y:c.y+r*Math.sin(k*Math.PI/12)},{x:c.x+r*Math.cos((k+1)*Math.PI/12),y:c.y+r*Math.sin((k+1)*Math.PI/12)}]);
      }
      for(var s=0;s<segments.length;s++){
       var p=segments[s][0],q=segments[s][1];
       var p0=vec(o.ToGlobal(NewVector(p.x,p.y,0))),q0=vec(o.ToGlobal(NewVector(q.x,q.y,0))),p1=vec(o.ToGlobal(NewVector(p.x,p.y,t))),q1=vec(o.ToGlobal(NewVector(q.x,q.y,t)));
       if(p0&&q0&&p1&&q1)edges.push([p0,q0],[p1,q1],[p0,p1]);
      }
     }
    }
    var count=get(o,'Count');
    if(!count&&/surub|\u0219urub|diblu/i.test(name)){
     var lo=vec(get(o,'GMin')),hi=vec(get(o,'GMax')),frame=objectFrame(o);
     if(lo&&hi&&frame){
      var sizes=hi.map(function(n,i){return n-lo[i];}),order=[0,1,2].sort(function(a,b){return sizes[b]-sizes[a];});
      if(sizes[order[0]]>sizes[order[1]]*1.5){var axis=frame.axes[order[0]],length=Math.sqrt(axis.reduce(function(s,v){return s+v*v;},0));if(length>0)shaftAxes.push(axis.map(function(v){return v/length;}));}
     }
    }
    if(typeof count==='number'&&count>0&&count<10000&&!direct.length){var list=get(o,'Objects');for(var j=count-1;j>=0;j--)todo.push(get(list||o,j));}
    else if(edges.length===before){var b=validBounds(o);if(b){edges=edges.concat(boundsEdges(b));approximate++;}}
    if(edges.length>100000)throw Error('Feronerie prea complexa pentru export.');
   }
   var axis=shaftAxes.length?shaftAxes[0]:null;
   if(axis&&!shaftAxes.every(function(a){return Math.abs(a.reduce(function(s,v,i){return s+v*axis[i];},0))>.995;}))axis=null;
   return {edges:edges,approximate_components:approximate,native_edge_components:nativeComponents,insertion_axis:axis};
  }
  var cfg=JSON.parse(fs.readFileSync(path.join(os.homedir(),'.bazis-mcp','material-db-reader.json'),'utf8'));
  var helper=path.join(os.homedir(),'Documents','BazisMCP','tools','assembly','export_dimensions.py');
  if(!fs.existsSync(helper))throw Error('Lipseste generatorul: '+helper);
  var now=new Date();
  function pad(n){return ('0'+n).slice(-2);}
  var stamp=now.getFullYear()+'-'+pad(now.getMonth()+1)+'-'+pad(now.getDate())+' '+pad(now.getHours())+'-'+pad(now.getMinutes())+'-'+pad(now.getSeconds());
  var suggested='Cote placi - '+stamp+'.pdf';
  var ps="$ErrorActionPreference='Stop'; Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.SaveFileDialog; $d.Title='Salveaza cotele placilor'; $d.Filter='PDF (*.pdf)|*.pdf'; $d.FileName=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+Buffer.from(suggested,'utf8').toString('base64')+"')); $d.OverwritePrompt=$true; $owner=New-Object System.Windows.Forms.Form; $owner.TopMost=$true; $owner.ShowInTaskbar=$false; $owner.Opacity=0; $owner.Show(); if($d.ShowDialog($owner) -eq 'OK'){[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($d.FileName))}; $d.Dispose(); $owner.Dispose()";
  var input=path.join(os.tmpdir(),'bazis-dimensions-'+process.pid+'-'+Date.now()+'.json');
  var job=input+'.job',consoleHelper=path.join(path.dirname(helper),'dimensions_console.py');
  if(!fs.existsSync(consoleHelper))throw Error('Lipseste consola: '+consoleHelper);
  jobLog=job+'.log';jobState=job+'.state';fs.writeFileSync(jobLog,'EXPORT COTE\nPornire script. Se asteapta alegerea fisierului PDF...\n','utf8');
  function psValue(value){return "[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+Buffer.from(value,'utf8').toString('base64')+"'))";}
  var terminal="$Host.UI.RawUI.WindowTitle='BAZIS - Export cote'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; Write-Host 'Pornire export BAZIS...'; & ("+psValue(cfg.python)+") '-u' ("+psValue(consoleHelper)+") '--job' ("+psValue(job)+") '--input' ("+psValue(input)+"); Write-Host ''; Write-Host 'Apasa Enter sau orice alta tasta pentru inchidere.' -ForegroundColor Cyan; while([Console]::KeyAvailable){[void][Console]::ReadKey($true)}; [void][Console]::ReadKey($true)";
  var encoded=Buffer.from(terminal,'utf16le').toString('base64');
  var launch="$ErrorActionPreference='Stop'; Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-EncodedCommand','"+encoded+"') -WindowStyle Normal; $ack="+psValue(job+'.opened')+"; $until=[DateTime]::UtcNow.AddSeconds(12); while(!(Test-Path -LiteralPath $ack) -and [DateTime]::UtcNow -lt $until){Start-Sleep -Milliseconds 100}; if(!(Test-Path -LiteralPath $ack)){throw 'Terminalul de progres nu a pornit. Citirea modelului nu a inceput.'}";
  // No inherited stdout/stderr pipes: the visible terminal outlives this
  // launcher. Waiting for its pipe EOF would keep BAZIS blocked indefinitely.
  cp.execFileSync('powershell.exe',['-NoProfile','-EncodedCommand',Buffer.from(launch,'utf16le').toString('base64')],{stdio:'ignore',windowsHide:true,timeout:15000});
  var raw=cp.execFileSync('powershell.exe',['-NoProfile','-STA','-EncodedCommand',Buffer.from(ps,'utf16le').toString('base64')],{encoding:'utf8',timeout:600000,windowsHide:true}).trim();
  if(!raw){progress('Export anulat din dialogul de salvare.');fs.writeFileSync(jobState,'cancelled','utf8');return;}
  var destination=Buffer.from(raw,'base64').toString('utf8');
  fs.writeFileSync(job+'.output',destination,'utf8');
  if(typeof Model==='undefined'||!Model)throw Error('Deschideti un model.');
  var filename=typeof ModelFilename==='string'?ModelFilename:text(get(Action,'ModelFilename'));
  progress('Citire model: '+filename);
  var modelAtStart=Model;
  var nodes=[],panels=[],hardware=[],panelRefs=[],articleByUid=Object.create(null),seen=new WeakSet(),stack=[{o:Model,parent:null,ancestors:[],hidden:false}],visited=0;
  function scanBatch(){
   try{
   if(Model!==modelAtStart)throw Error('Modelul a fost schimbat in timpul citirii. Reluati exportul.');
   var batchCount=0,batchStart=Date.now();
  while(stack.length&&batchCount++<20&&Date.now()-batchStart<60){
   var item=stack.pop(),o=item.o;if(!o||seen.has(o))continue;seen.add(o);
   if(++visited>100000)throw Error('Prea multe obiecte.');
   if(visited%100===0)progress('Citire: '+visited+' obiecte; '+panels.length+' placi; '+hardware.length+' articole de feronerie');
   var id='p'+visited,name=text(get(o,'Name')),hidden=item.hidden||get(o,'Visible')===false;
   var material=text(get(o,'MaterialName')).split('\r')[0],w=get(o,'ContourWidth'),h=get(o,'ContourHeight'),t=get(o,'Thickness');
   var isPanel=positive(w)&&positive(h)&&positive(t),count=get(o,'Count');
   // BAZIS Block.IsFastener() identifies composite fittings. They are atomic:
   // never recurse into panels used only to draw a purchased fitting.
   var composite=typeof get(o,'IsFastener')==='function'&&o.IsFastener()===true;
   var hole=/^(gaur|g\u0103ur|hole\b|linie de|caset\u0103 de)/i.test(name);
   var article=!isPanel&&!hole&&(/\r\s*\S/.test(name)||(!count&&/surub|\u0219urub|diblu|balama|glisier|picior|clem|m\u00e2ner|maner|suport|t\u0103lpici|talpici/i.test(name)));
   if(composite||article){
    progress('Feronerie '+visited+': '+name.replace(/\r/g,' | ')+' - identificare pentru gaurire');
    var b=validBounds(o),geometry=hardwareGeometry(o),connected=[];
    // Do not search the entire model for every fitting. Receiving panels are
    // assigned once below by native NewHoleDrilling, using Body/Fastener UIDs.
    hardware.push({id:id,uid:get(o,'UID'),parent:item.parent,ancestors:item.ancestors,name:name,article:name.indexOf('\r')>=0?name.split('\r').slice(1).join(' ').trim():'',designation:text(get(o,'Designation')),hidden:false,source_hidden:hidden,bounds:b||{min:null,max:null},edges:geometry.edges,approximate_components:geometry.approximate_components,native_edge_components:geometry.native_edge_components,insertion_axis:geometry.insertion_axis,connected_panel_uids:connected});
    var articleRecord=hardware[hardware.length-1],memberStack=[o],membersSeen=new WeakSet(),membersCount=0;
    while(memberStack.length){
     var member=memberStack.pop();if(!member||membersSeen.has(member))continue;membersSeen.add(member);
     if(++membersCount>10000)throw Error('Feronerie prea complexa pentru asocierea gaurilor.');
     var memberUid=get(member,'UID');if(typeof memberUid==='number'||typeof memberUid==='string')articleByUid[String(memberUid)]=articleRecord;
     var memberCount=get(member,'Count'),memberList=get(member,'Objects');
     if(typeof memberCount==='number'&&memberCount>0&&memberCount<10000)for(var mi=0;mi<memberCount;mi++)memberStack.push(get(memberList||member,mi));
    }
    continue;
   }
   nodes.push({id:id,parent:item.parent,name:name,designation:text(get(o,'Designation')),frame:objectFrame(o)});
   // Only furniture boards, excluding panels used to model fittings.
   if(isPanel&&/\b(PAL|MDF|HDF|PFL|placaj|plywood)\b/i.test(material)){
    progress('Placa '+visited+': '+text(get(o,'Designation'))+' | '+name);
    var p={id:id,uid:get(o,'UID'),parent:item.parent,ancestors:item.ancestors,name:name,designation:text(get(o,'Designation')),material:material,width:w,height:h,thickness:t,frame:objectFrame(o),bounds:{min:vec(get(o,'GabMin')),max:vec(get(o,'GabMax'))},edges:[],warnings:[],machining:panelMachining(o)};
    var contour=get(o,'Contour'),n=get(contour,'Count'),objects=get(contour,'Objects');
    p.native_contour=readContour(contour,0);
    p.local_bounds={min:point2(get(contour,'Min')),max:point2(get(contour,'Max'))};
    p.z_limits=scalarFields(o,['LowZ','HighZ','FrontFace']);
    p.dimension_properties=scalarFields(o,['Bent']);
    if(typeof get(o,'ToGlobal')!=='function')throw Error('ToGlobal indisponibil pentru '+name);
    function globalPoint(q,z){return vec(o.ToGlobal(NewVector(q.x,q.y,z)));}
    if(typeof n==='number'&&n>0&&n<10000){
     for(var e=0;e<n;e++){
      var elem=get(objects||contour,e);
      if(elem&&typeof elem.IsLine==='function'&&elem.IsLine()){
       var line=elem.AsLine(),a=line.Pos1,b=line.Pos2;
       var a0=globalPoint(a,0),b0=globalPoint(b,0),a1=globalPoint(a,t),b1=globalPoint(b,t);
       if(!a0||!b0||!a1||!b1)throw Error('Coordonate invalide: '+name);
       p.edges.push([a0,b0],[a1,b1],[a0,a1]);
      }else p.warnings.push('Contur cu arce: reprezentare prin gabarit.');
     }
    }
    if(p.warnings.length||!p.edges.length){p.edges=[];p.warnings=['Reprezentare prin gabarit, conturul nu este redat integral.'];}
    var panelEdges=nativeEdges(o);
    if(panelEdges.length){p.edges=panelEdges;p.geometry_source='BAZIS Edges.GVertices';p.warnings=[];}
    else p.geometry_source=p.edges.length?'BAZIS contour extrusion':'bounding box';
    // Preserve machining parameters as data. Do not invent 3D grooves from
    // parameter names or assume every section follows the same convention.
    if(p.machining.cuts.length&&!panelEdges.length)p.warnings.push('Frezari citite ca parametri BAZIS; forma 3D a prelucrarilor nu este confirmata.');
    if(!p.bounds.min||!p.bounds.max)throw Error('Gabarit indisponibil: '+name);
    // Cuts are not safely serialized yet. Keep those boards as individual steps.
    var cutCount=get(get(o,'Cuts'),'Count'),butts=get(o,'Butts'),buttCount=get(butts,'Count');
    p.duplicate_signature=null;
    if(cutCount===0&&typeof buttCount==='number'&&buttCount>=0&&buttCount<10000&&!p.warnings.length){
     var bands=[];
     for(var bi=0;bi<buttCount;bi++){
      var band=get(butts,bi);bands.push({element:get(band,'ElemIndex'),material:text(get(band,'Material')),sign:text(get(band,'Sign')),thickness:get(band,'Thickness'),clip:get(band,'ClipPanel')});
     }
     var texture=get(o,'TextureOrientation');
     p.duplicate_signature={bands:bands,cuts:0,texture:typeof texture==='number'||typeof texture==='string'?texture:null};
    }
    // Full native feature snapshot for conservative whole-module equivalence.
    var plastics=get(o,'Plastics'),plasticCount=get(plastics,'Count'),plasticItems=get(plastics,'Plastics')||plastics;
    p.module_comparison={version:1,complete:typeof buttCount==='number'&&buttCount>=0&&buttCount<10000&&typeof plasticCount==='number'&&plasticCount>=0&&plasticCount<1000,bands:[],layers:[],texture:scalarFields(o,['TextureOrientation','TextureAngle','FrontFace'])};
    if(p.module_comparison.complete){
     for(var mb=0;mb<buttCount;mb++){var edgeBand=get(butts,mb);if(!edgeBand){p.module_comparison.complete=false;break;}p.module_comparison.bands.push(scalarFields(edgeBand,['ElemIndex','Material','Sign','Thickness','Width','ClipPanel','Allowance']));}
     for(var ml=0;ml<plasticCount;ml++){var faceLayer=get(plasticItems,ml);if(!faceLayer){p.module_comparison.complete=false;break;}p.module_comparison.layers.push(scalarFields(faceLayer,['Material','Thickness','Side','TextureOrientation','MaterialWidth']));}
    }
    if(p.module_comparison.complete){
     p.module_comparison.bands.forEach(function(b){['ElemIndex','Material','Thickness','Width','ClipPanel'].forEach(function(k){if(typeof b[k]==='undefined')p.module_comparison.complete=false;});});
     p.module_comparison.layers.forEach(function(l){['Material','Thickness','Side','TextureOrientation'].forEach(function(k){if(typeof l[k]==='undefined')p.module_comparison.complete=false;});});
     if(typeof p.module_comparison.texture.TextureOrientation==='undefined')p.module_comparison.complete=false;
    }
    panels.push(p);
    panelRefs.push({object:o,record:p});
   }
   var count=get(o,'Count');
   if(typeof count==='number'&&count>=0&&count<=100000){var list=get(o,'Objects');for(var i=count-1;i>=0;i--)stack.push({o:get(list||o,i),parent:id,ancestors:item.ancestors.concat([id]),hidden:hidden});}
  }
  if(stack.length){timer=setTimeout(scanBatch,20);return;}
  if(!panels.length)throw Error('Nu am gasit placi PAL/MDF/HDF/PFL/placaj.');
  progress('Citire terminata: '+panels.length+' placi; '+hardware.length+' articole de feronerie');
  progress('Calcul nativ al gaurilor in BAZIS...');
  var drilling=calculatePanelHoles(panelRefs,articleByUid);
  progress('Calcul gauri terminat: '+(drilling.hole_count||0)+' gauri');
  var report={schema:1,model:filename,nodes:nodes,panels:panels,hardware:hardware,drilling:drilling,geometry_source:'BAZIS native edges / contour extrusion / NewHoleDrilling global coordinates'};
  progress('Pregatire date pentru PDF...');
  fs.writeFileSync(input,JSON.stringify(report),'utf8');
  progress('Date pregatite. Generarea PDF continua in terminal; BAZIS poate fi folosit.');
  fs.writeFileSync(jobState,'ready','utf8');
  nativeDone=true;Action.Finish();
   }catch(e){nativeDone=true;reportError(e);try{Action.Finish();}catch(ignore){}}
  }
  if(!Action||typeof Action.Continue!=='function'||typeof Action.Finish!=='function'||typeof setTimeout!=='function')throw Error('Citirea pe loturi necesita Action.Continue/Finish si temporizator BAZIS.');
  Action.OnFinish=function(){
   if(timer!==null)clearTimeout(timer);
   if(!nativeDone){nativeDone=true;progress('Citire oprita in BAZIS.');fs.writeFileSync(jobState,'cancelled','utf8');}
  };
  Action.Continue();timer=setTimeout(scanBatch,20);
 }catch(e){
  reportError(e);
 }
 function reportError(e){
  try{progress('EROARE BAZIS: '+text(e.message||e));if(jobState)fs.writeFileSync(jobState,'error','utf8');}catch(ignore){}
  alert('Export cote nereusit: '+text(e.message||e));
 }
}());
