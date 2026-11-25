// BAZIS MCP Bridge 0.2.2. Compatible with the embedded Node 8.11 runtime.
// Start manually in BAZIS Script Editor. Stop with ` or bazis_stop_bridge.
// No arbitrary eval, shell commands, network listener or automatic model saves.
(function () {
    'use strict';
    var fs = require('fs'), path = require('path'), os = require('os');
    var crypto = require('crypto');
    var VERSION = '0.2.2', PROTOCOL = 1;
    var configPath = path.join(os.homedir(), '.bazis-mcp', 'config.json');
    var config, folder, session, timer, lockPath, stopped = false, busy = false, stopRequested = false;
    var handles = {}, byRef = new WeakMap(), nextHandle = 1;
    var modelRef = null, modelStamp = null, filename = null, epoch = 0;
    var completed = 0, lastError = null, lastHeartbeat = 0;
    var lastClientRequestMs = null, lastHint = null;
    var escapeGuard = {installed:false,ignored_events:0,error:null};
    var stopKey = {label:'`',virtual_key:192,events:0};
    var previousKeyboard = null;

    function fail(code, message) { var e = new Error(message); e.code = code; throw e; }
    function message(e) { return String(e && e.message || e); }
    function jsonFile(p) { return JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '')); }
    function atomic(p, value) {
        var temp = p + '.' + crypto.randomBytes(6).toString('hex') + '.tmp';
        try { fs.writeFileSync(temp, JSON.stringify(value), {encoding:'utf8', flag:'wx'}); fs.renameSync(temp, p); }
        finally { try { if (fs.existsSync(temp)) fs.unlinkSync(temp); } catch (_) {} }
    }
    function prop(obj, name) { try { return obj ? obj[name] : undefined; } catch (_) { return undefined; } }
    function scalar(value) { return value === null || typeof value === 'string' || typeof value === 'boolean' || (typeof value === 'number' && isFinite(value)); }
    function identity(obj) {
        var uid = prop(obj, 'UID');
        if ((typeof uid === 'number' && uid !== 0) || (typeof uid === 'string' && uid)) return uid;
        return null;
    }
    function currentModel() { return typeof Model !== 'undefined' ? Model : null; }
    function modelFile() {
        if (typeof ModelFilename === 'string') return ModelFilename;
        var f = typeof Action !== 'undefined' ? prop(Action, 'ModelFilename') : undefined;
        return typeof f === 'string' ? f : null;
    }
    function refreshModel() {
        var m = currentModel(), stamp = identity(m), file = modelFile();
        if (m !== modelRef || stamp !== modelStamp || file !== filename) {
            modelRef = m; modelStamp = stamp; filename = file; epoch++;
            handles = {}; byRef = new WeakMap(); nextHandle = 1;
        }
        return m;
    }
    function modelToken() { return session + ':' + epoch; }
    function requireModel() { var m = refreshModel(); if (!m) fail('NO_MODEL', 'Open a model in BAZIS'); return m; }
    function count(obj) { var n = prop(obj, 'Count'); return typeof n === 'number' && n >= 0 && n <= 100000 ? Math.floor(n) : 0; }
    function child(obj, i) { var list = prop(obj, 'Objects'); return list ? prop(list, i) : prop(obj, i); }
    function vector(v) {
        if (!v) return null;
        var result = {}, names = ['x','y','z'];
        for (var i=0;i<3;i++) { var value = prop(v,names[i]); if (typeof value !== 'number' || !isFinite(value)) return null; result[names[i]]=value; }
        return result;
    }
    function numeric(v, name, min, max, defaultValue) {
        if (typeof v === 'undefined' && typeof defaultValue !== 'undefined') v=defaultValue;
        if (typeof v !== 'number' || !isFinite(v) || v<min || v>max) fail('INVALID_ARGUMENT', name+' must be finite and between '+min+' and '+max);
        return v;
    }
    function text(v, name, allowEmpty) {
        if (typeof v !== 'string' || (!allowEmpty && !v.length) || v.length>500 || /[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(v)) fail('INVALID_ARGUMENT','Invalid '+name);
        return v;
    }
    function register(obj, indexes) {
        var existing = byRef.get(obj);
        if (existing && handles[existing]) { handles[existing].indexes=indexes.slice(); return existing; }
        if (nextHandle>100000) fail('LIMIT', 'Object handle limit reached; restart bridge');
        var id = 'o'+nextHandle++;
        handles[id]={ref:obj, uid:identity(obj), indexes:indexes.slice()}; byRef.set(obj,id);
        return id;
    }
    function locate(id) {
        if (typeof id !== 'string' || !Object.prototype.hasOwnProperty.call(handles,id)) fail('STALE_OBJECT','List objects again; unknown handle '+id);
        var entry=handles[id], obj=requireModel();
        // refreshModel may have invalidated all handles.
        if (!Object.prototype.hasOwnProperty.call(handles,id)) fail('STALE_OBJECT','Model changed; list objects again');
        for(var i=0;i<entry.indexes.length;i++) { obj=child(obj,entry.indexes[i]); if(!obj) break; }
        if(!obj || (entry.uid!==null ? identity(obj)!==entry.uid : obj!==entry.ref)) fail('STALE_OBJECT','Object order/identity changed; list objects again');
        return {obj:obj, entry:entry, id:id};
    }
    function readNativeHoles(obj) {
        var out={source:'BAZIS object.Holes',available:false,count:null,items:[],complete:false,
            meaning:'Fastener hole definitions, not computed drilling in a receiving panel',
            coordinate_note:'Position and Direction are preserved raw. ToGlobal results are candidates until their reference system is verified.'};
        var list;
        try {list=obj.Holes;}catch(e){out.error=message(e);return out;}
        if(list===null || typeof list==='undefined')return out;
        out.available=true;
        var size=prop(list,'Count');if(typeof size!=='number')size=prop(list,'length');
        if(typeof size!=='number'||!isFinite(size)||size<0||size!==Math.floor(size)){
            try{out.collection_members=Object.getOwnPropertyNames(Object.getPrototypeOf(list)||list).slice(0,100);}catch(ignore){}
            return out;
        }
        out.count=size;out.truncated=size>1000;out.complete=!out.truncated;
        var items=prop(list,'Items');
        if(!items)items=prop(list,'Holes');
        for(var i=0;i<Math.min(size,1000);i++){
            var hole=items?prop(items,i):prop(list,i),item={index:i,properties:{},position_raw:null,direction_raw:null};
            if(!hole){item.error='Native hole item unavailable';out.complete=false;out.items.push(item);continue;}
            ['Diameter','Depth','Radius','DrillMode'].forEach(function(k){var v=prop(hole,k);if(scalar(v)&&typeof v!=='undefined')item.properties[k]=v;});
            var position=prop(hole,'Position'),direction=prop(hole,'Direction');
            item.position_raw=vector(position);item.direction_raw=vector(direction);
            item.contour_element_count=prop(prop(hole,'Contour'),'Count');
            try{if(item.position_raw&&typeof prop(obj,'ToGlobal')==='function')item.position_to_global_candidate=vector(obj.ToGlobal(position));}catch(e){item.position_transform_error=message(e);}
            try{if(item.direction_raw&&typeof prop(obj,'NToGlobal')==='function')item.direction_to_global_candidate=vector(obj.NToGlobal(direction));}catch(e){item.direction_transform_error=message(e);}
            if(!item.position_raw||!item.direction_raw||typeof item.properties.Diameter!=='number'||typeof item.properties.Depth!=='number'){
                out.complete=false;
                try{item.native_members=Object.getOwnPropertyNames(Object.getPrototypeOf(hole)||hole).slice(0,100);}catch(ignore){}
            }
            out.items.push(item);
        }
        return out;
    }
    // Read native data only: never call GetParams/Build or infer a fitting from its holes.
    function nativeData(value, depth, seen, budget) {
        budget=budget||{remaining:300};if(--budget.remaining<0)return {truncated:true};
        if(scalar(value))return typeof value==='string'?value.slice(0,2000):value;
        if(!value || typeof value!=='object')return null;
        if(seen.indexOf(value)>=0)return {reference:true};
        var names=[], current=value, levels=0;
        while(current&&levels++<3){
            try{Object.getOwnPropertyNames(current).forEach(function(k){if(k!=='__proto__'&&k!=='constructor'&&names.indexOf(k)<0&&names.length<100)names.push(k);});current=Object.getPrototypeOf(current);}catch(ignore){break;}
        }
        var out={members:names,values:{}};
        if(depth<=0)return out;
        seen=seen.concat([value]);
        names.forEach(function(k){var v=prop(value,k);if(typeof v!=='function'&&typeof v!=='undefined')out.values[k]=nativeData(v,depth-1,seen,budget);});
        return out;
    }
    function readNativeHardware(obj) {
        var out={source:'BAZIS native object properties and Edges.GVertices',properties:{},
            parameters:{},geometry:{coordinate_space:'global',edges:[],complete:false},
            note:'Raw native data. Hole dimensions are not hardware dimensions; missing geometry is not replaced by a bounding box.'};
        try{out.is_fastener=typeof prop(obj,'IsFastener')==='function'?!!obj.IsFastener():null;}catch(e){out.classification_error=message(e);}
        ['ParamType','ParamOffset','RotationAngle','LAngle','FirstRotHole','DatumMode','Symmetrized','Symmetrizable','EdgesCount','TriListsCount'].forEach(function(k){var v=prop(obj,k);if(scalar(v)&&typeof v!=='undefined')out.properties[k]=v;});
        ['AdvParamData','Params','Source'].forEach(function(k){var v=prop(obj,k);out.parameters[k]={available:v!==null&&typeof v!=='undefined',data:nativeData(v,2,[])};});
        var size=prop(obj,'EdgesCount'), list=prop(obj,'Edges'),total=0;
        if(typeof size!=='number'||!isFinite(size)||size<0||Math.floor(size)!==size)return out;
        out.geometry.count=size;out.geometry.complete=size>0&&size<=1000;
        for(var i=0;i<Math.min(size,1000);i++){
            var edge=prop(list,i),n=prop(edge,'Count'),vertices=prop(edge,'GVertices'),item={index:i,points_global_mm:[]};
            if(typeof n==='number'&&isFinite(n)&&n>=0&&Math.floor(n)===n&&n<=2000&&total+n<=20000){
                for(var j=0;j<n;j++){var p=vector(prop(vertices,j));if(p)item.points_global_mm.push(p);else out.geometry.complete=false;}
                total+=n;
            }
            if(item.points_global_mm.length<2){out.geometry.complete=false;item.native_data=nativeData(edge,1,[]);}
            out.geometry.edges.push(item);
        }
        out.geometry.vertex_count=total;
        return out;
    }
    function readNativeLayers(obj) {
        var list=prop(obj,'Plastics'),size=prop(list,'Count');
        var out={source:'BAZIS panel.Plastics',available:list!==null&&typeof list!=='undefined',count:null,items:[],complete:false};
        if(typeof size!=='number'||!isFinite(size)||size<0||size!==Math.floor(size))return out;
        out.count=size;out.complete=size<=100;
        var items=prop(list,'Plastics')||prop(list,'Items')||list;
        for(var i=0;i<Math.min(size,100);i++){
            var layer=prop(items,i),row={index:i,properties:{}};
            if(!layer){row.error='Native layer unavailable';out.complete=false;out.items.push(row);continue;}
            ['Material','Thickness','MaterialWidth','Side','TextureOrientation'].forEach(function(k){var v=prop(layer,k);if(scalar(v)&&typeof v!=='undefined')row.properties[k]=v;});
            if(typeof row.properties.Material!=='string'||typeof row.properties.Thickness!=='number')out.complete=false;
            out.items.push(row);
        }
        return out;
    }
    function readNativeEdgeBands(obj) {
        var list=prop(obj,'Butts'),size=prop(list,'Count'),contour=prop(obj,'Contour');
        var out={source:'BAZIS panel.Butts + panel.Contour',available:list!==null&&typeof list!=='undefined',count:null,items:[],complete:false,
            coordinate_space:'panel local XY, mm',side_note:'X_min/X_max/Y_min/Y_max refer to the native panel contour, not global front/back or grain direction.'};
        function xy(p){var x=prop(p,'x'),y=prop(p,'y');return typeof x==='number'&&isFinite(x)&&typeof y==='number'&&isFinite(y)?{x:x,y:y}:null;}
        function near(a,b){return Math.abs(a-b)<0.01;}
        if(typeof size!=='number'||!isFinite(size)||size<0||size!==Math.floor(size))return out;
        out.count=size;out.complete=size<=1000;
        var elements=prop(contour,'Objects')||contour,lo=xy(prop(contour,'Min')),hi=xy(prop(contour,'Max'));
        out.contour_bounds_local_mm={min:lo,max:hi};
        for(var i=0;i<Math.min(size,1000);i++){
            var band=prop(list,i),row={index:i,properties:{},contour_element_index:null,local_side:null};
            if(!band){row.error='Native edge band unavailable';out.complete=false;out.items.push(row);continue;}
            ['Material','Sign','Thickness','Width','ClipPanel','Allowance','ElemIndex'].forEach(function(k){var v=prop(band,k);if(scalar(v)&&typeof v!=='undefined')row.properties[k]=v;});
            var index=prop(band,'ElemIndex');row.contour_element_index=typeof index==='number'?index:null;
            var elem=typeof index==='number'&&index>=0&&Math.floor(index)===index?prop(elements,index):null;
            try{
                if(elem&&typeof prop(elem,'IsLine')==='function'&&elem.IsLine()){
                    var line=elem.AsLine(),a=xy(prop(line,'Pos1')),b=xy(prop(line,'Pos2'));
                    row.contour_type='line';row.start_local_mm=a;row.end_local_mm=b;
                    if(a&&b){
                        row.segment_length_mm=Math.sqrt(Math.pow(a.x-b.x,2)+Math.pow(a.y-b.y,2));
                        if(lo&&hi){
                            if(near(a.x,lo.x)&&near(b.x,lo.x))row.local_side='X_min';
                            else if(near(a.x,hi.x)&&near(b.x,hi.x))row.local_side='X_max';
                            else if(near(a.y,lo.y)&&near(b.y,lo.y))row.local_side='Y_min';
                            else if(near(a.y,hi.y)&&near(b.y,hi.y))row.local_side='Y_max';
                        }
                    }else out.complete=false;
                }else if(elem){row.contour_type='nonlinear_or_unknown';row.contour_native_data=nativeData(elem,1,[]);}
                else{row.geometry_error='Referenced contour element unavailable';out.complete=false;}
            }catch(e){row.geometry_error=message(e);out.complete=false;}
            if(typeof row.properties.Material!=='string'||typeof row.properties.Thickness!=='number'||row.contour_element_index===null)out.complete=false;
            out.items.push(row);
        }
        return out;
    }
    function readLocalFrame(obj) {
        var out={source:'BAZIS object.ToGlobal',available:typeof prop(obj,'ToGlobal')==='function',complete:false,
            convention:'global = origin_global_mm + x*axis_x_global + y*axis_y_global + z*axis_z_global; matrix rows, column vectors',units:'mm'};
        if(!out.available)return out;
        try{
            var o=vector(obj.ToGlobal(NewVector(0,0,0))),axes=[];
            if(!o)throw Error('Invalid native origin');
            for(var i=0;i<3;i++){
                var v=[0,0,0];v[i]=1;
                var q=vector(obj.ToGlobal(NewVector(v[0],v[1],v[2])));
                if(!q)throw Error('Invalid native basis point');
                axes.push({x:q.x-o.x,y:q.y-o.y,z:q.z-o.z});
            }
            out.origin_global_mm=o;out.axis_x_global=axes[0];out.axis_y_global=axes[1];out.axis_z_global=axes[2];
            var a=axes[0],b=axes[1],c=axes[2];
            var det=a.x*(b.y*c.z-b.z*c.y)-b.x*(a.y*c.z-a.z*c.y)+c.x*(a.y*b.z-a.z*b.y);
            out.determinant=det;
            out.local_to_global_matrix=[[a.x,b.x,c.x,o.x],[a.y,b.y,c.y,o.y],[a.z,b.z,c.z,o.z],[0,0,0,1]];
            if(Math.abs(det)<1e-12)throw Error('Singular native coordinate frame');
            var inv=[[(b.y*c.z-b.z*c.y)/det,(b.z*c.x-b.x*c.z)/det,(b.x*c.y-b.y*c.x)/det],
                [(c.y*a.z-c.z*a.y)/det,(c.z*a.x-c.x*a.z)/det,(c.x*a.y-c.y*a.x)/det],
                [(a.y*b.z-a.z*b.y)/det,(a.z*b.x-a.x*b.z)/det,(a.x*b.y-a.y*b.x)/det]];
            inv.forEach(function(r){r.push(-(r[0]*o.x+r[1]*o.y+r[2]*o.z));});inv.push([0,0,0,1]);
            out.global_to_local_matrix=inv;out.complete=true;
        }catch(e){out.error=message(e);}
        return out;
    }
    function readNativeContour(contour,depth,budget) {
        var size=prop(contour,'Count'),out={available:!!contour,count:null,elements:[],complete:false};
        function xy(p){var x=prop(p,'x'),y=prop(p,'y');return typeof x==='number'&&isFinite(x)&&typeof y==='number'&&isFinite(y)?{x:x,y:y}:null;}
        if(typeof size!=='number'||!isFinite(size)||size<0||Math.floor(size)!==size||depth>8)return out;
        out.count=size;out.complete=true;out.bounds_local_mm={min:xy(prop(contour,'Min')),max:xy(prop(contour,'Max'))};
        var list=prop(contour,'Objects')||contour;
        for(var i=0;i<size;i++){
            if(--budget.remaining<0){out.complete=false;out.truncated=true;break;}
            var e=prop(list,i),row={index:i,type:'unsupported',raw_type:prop(e,'ElType')};
            try{
                if(typeof prop(e,'IsLine')==='function'&&e.IsLine()){
                    var line=e.AsLine();row.type='line';row.start_local_mm=xy(prop(line,'Pos1'));row.end_local_mm=xy(prop(line,'Pos2'));
                    if(!row.start_local_mm||!row.end_local_mm)out.complete=false;
                }else if(typeof prop(e,'IsArc')==='function'&&e.IsArc()){
                    var arc=e.AsArc();row.type='arc';row.start_local_mm=xy(prop(arc,'Pos1'));row.end_local_mm=xy(prop(arc,'Pos2'));row.center_local_mm=xy(prop(arc,'Center'));
                    var direction=prop(arc,'ArcDir');if(scalar(direction)&&typeof direction!=='undefined')row.arc_dir_native=direction;
                    if(!row.start_local_mm||!row.end_local_mm||!row.center_local_mm||typeof direction==='undefined')out.complete=false;
                }else if(typeof prop(e,'IsCircle')==='function'&&e.IsCircle()){
                    var circle=e.AsCircle();row.type='circle';row.center_local_mm=xy(prop(circle,'Center'));row.radius_mm=prop(circle,'CirRadius');
                    if(!row.center_local_mm||typeof row.radius_mm!=='number'||!isFinite(row.radius_mm)||row.radius_mm<=0)out.complete=false;
                }else if(typeof prop(e,'IsList')==='function'&&e.IsList()){
                    row.type='list';row.contour=readNativeContour(e.AsList(),depth+1,budget);if(!row.contour.complete)out.complete=false;
                }else{
                    row.native_data=nativeData(e,1,[]);out.complete=false;
                }
            }catch(error){row.error=message(error);out.complete=false;}
            out.elements.push(row);
        }
        return out;
    }
    function readPanelContour(obj) {
        var out={source:'BAZIS panel.Contour',coordinate_space:'panel local XY, mm',
            note:'Native element order and indices retained for Butts.ElemIndex. Unsupported curves are explicit; no bounding rectangle substitution.',
            contour:readNativeContour(prop(obj,'Contour'),0,{remaining:10000}),properties:{}};
        ['ContourWidth','ContourHeight','Thickness','LowZ','HighZ','MiddleZ','Bent','IsContourRectangle','TextureOrientation','TextureAngle','FrontFace'].forEach(function(k){var v=prop(obj,k);if(scalar(v)&&typeof v!=='undefined')out.properties[k]=v;});
        out.complete=out.contour.complete;
        if(out.properties.Bent===true){out.complete=false;out.note+=' Bent panel: flat XY contour alone does not describe the bent surface.';}
        return out;
    }
    function readNativeAppearance(obj) {
        var out={source:'BAZIS native panel/material texture properties',properties:{},orientation_enum:{},
            note:'Raw native orientation and angle. No assumed numeric enum meanings or angle units; material texture metadata is distinct from panel grain.'};
        ['TextureOrientation','TextureAngle','FrontFace','MaterialName','TextureWidth','TextureHeight','TextureFileName','TextureName','Color'].forEach(function(k){var v=prop(obj,k);if(scalar(v)&&typeof v!=='undefined')out.properties[k]=v;});
        var enumeration=typeof TextureOrientation!=='undefined'?TextureOrientation:null;
        ['None','Horizontal','Vertical'].forEach(function(k){var v=prop(enumeration,k);if(scalar(v)&&typeof v!=='undefined'){out.orientation_enum[k]=v;if(v===out.properties.TextureOrientation)out.orientation_name=k;}});
        out.material=nativeData(prop(obj,'Material'),1,[]);
        out.texture=nativeData(prop(obj,'Texture'),1,[]);
        out.local_coordinate_note='TextureOrientation refers to the native local panel XY, not global model axes.';
        out.available=typeof out.properties.TextureOrientation!=='undefined';
        return out;
    }
    // Inspect inherited native surface interfaces without invoking unknown methods.
    function inspectSurfaceAPI(obj) {
        var out={members:[],collections:{},note:'Metadata only. No FillElements, Build, AddDrawData or Triangulate invoked.'};
        var seen={},current=obj,level=0;
        while(current&&level<12&&out.members.length<400){
            var names=[];try{names=Object.getOwnPropertyNames(current);}catch(e){out.error=message(e);break;}
            for(var i=0;i<names.length&&out.members.length<400;i++){
                var key=names[i];if(seen[key]||key==='constructor'||key==='__proto__')continue;seen[key]=true;
                try{
                    var d=Object.getOwnPropertyDescriptor(current,key),row={name:key,prototype_level:level};
                    if(d&&typeof d.value==='function'){row.kind='method';row.declared_arguments=d.value.length;}
                    else if(d&&(d.get||d.set)){row.kind='accessor';row.readable=!!d.get;row.writable=!!d.set;}
                    else{row.kind=typeof (d&&d.value);if(d&&scalar(d.value))row.value=d.value;}
                    out.members.push(row);
                }catch(e){out.members.push({name:key,error:message(e)});}
            }
            try{current=Object.getPrototypeOf(current);}catch(e){break;}level++;
        }
        ['DrawData','AdditionalDrawData','Elements','Meshes','Surfaces','Faces','Solids','Geometry','TriLists','Source'].forEach(function(k){
            var v=prop(obj,k);if(v===null||typeof v==='undefined'||typeof v==='function')return;
            var info={type:typeof v};['Count','TriListsCount','EdgesCount','FaceCount','VertexCount'].forEach(function(n){var x=prop(v,n);if(typeof x==='number'&&isFinite(x))info[n]=x;});
            out.collections[k]=info;
        });
        return out;
    }
    function readNativeSolidInfo(obj) {
        var out={source:'BAZIS native mesh properties',available:false,complete:false,
            note:'Triangle availability only. Wire edges do not define a closed solid; no shape is inferred from hardware names or holes.'};
        try{
            var mesh=obj;
            if(typeof prop(obj,'IsMesh')==='function')out.is_mesh=!!obj.IsMesh();
            if(out.is_mesh&&typeof prop(obj,'AsMesh')==='function')mesh=obj.AsMesh();
            var n=prop(mesh,'TriListsCount');out.tri_lists_count=typeof n==='number'?n:null;
            out.available=typeof n==='number'&&n>0;
            // Expose native surface API members for objects without the expected triangle lists.
            if(!out.available)out.surface_api=inspectSurfaceAPI(mesh);
            out.geometry_reader='read_geometry';
        }catch(e){out.error=message(e);}
        return out;
    }
    function readNativeCuts(obj) {
        var list=prop(obj,'Cuts'),size=prop(list,'Count');
        var out={source:'BAZIS panel.Cuts',available:list!==null&&typeof list!=='undefined',count:null,items:[],complete:false,
            coordinate_note:'Trajectory uses the native panel local XY frame. Section is the native tool/cut profile, not a panel XY contour. Local/global panel matrices are returned separately.',
            interpretation_note:'CutType, FrontSide and Angle remain native values; no guessed enum meanings, angle units or derived depth. Missing parameters are not zero.'};
        if(typeof size!=='number'||!isFinite(size)||size<0||size!==Math.floor(size))return out;
        out.count=size;out.complete=size<=1000;
        var items=prop(list,'Cuts')||list,budget={remaining:10000};
        function fields(o,names){var result={};names.forEach(function(k){var v=prop(o,k);if(scalar(v)&&typeof v!=='undefined')result[k]=v;});return result;}
        for(var i=0;i<Math.min(size,1000);i++){
            var cut=prop(items,i),row={index:i,properties:{},parameters:null,complete:false};
            if(!cut){row.error='Native cut unavailable';out.complete=false;out.items.push(row);continue;}
            row.properties=fields(cut,['Name','Sign','CutType','FrontSide','Thickness','Depth','Offset','Offset2','Radius','Width','Angle']);
            var params=prop(cut,'Params');
            if(params!==null&&typeof params!=='undefined')row.parameters=fields(params,['Name','Sign','SignFormula','CutType','Depth','Offset','Offset2','Radius','Width','Angle','Fragment']);
            row.trajectory=readNativeContour(prop(cut,'Trajectory'),0,budget);
            row.section=readNativeContour(prop(cut,'Contour'),0,budget);
            row.complete=row.trajectory.complete&&row.section.complete;
            if(!row.complete)out.complete=false;
            out.items.push(row);
        }
        return out;
    }
    function snapshot(obj, indexes, details) {
        var out={object_id:register(obj,indexes), parent_id:indexes.length>1?parentHandle(indexes):null,
                 name:prop(obj,'Name'), child_count:count(obj), position_parent_mm:vector(prop(obj,'Position'))};
        var fields={art_pos:'ArtPos',designation:'Designation',material:'MaterialName',thickness_mm:'Thickness',visible:'Visible',selected:'Selected',uid:'UID',contour_width_mm:'ContourWidth',contour_height_mm:'ContourHeight'};
        for(var key in fields) if(Object.prototype.hasOwnProperty.call(fields,key)) {
            var value=prop(obj,fields[key]); if(scalar(value) && typeof value!=='undefined') out[key]=value;
        }
        out.bounds_parent_mm={min:vector(prop(obj,'GMin')),max:vector(prop(obj,'GMax'))};
        out.bounds_global_mm={min:vector(prop(obj,'GabMin')),max:vector(prop(obj,'GabMax'))};
        if(details) {
            out.native_holes=readNativeHoles(obj);
            out.native_hardware=readNativeHardware(obj);
            out.native_layers=readNativeLayers(obj);
            out.native_edge_bands=readNativeEdgeBands(obj);
            out.local_coordinate_system=readLocalFrame(obj);
            out.native_panel_contour=readPanelContour(obj);
            out.native_cuts=readNativeCuts(obj);
            out.native_appearance=readNativeAppearance(obj);
            out.native_solid=readNativeSolidInfo(obj);
            out.edge_band_count=count(prop(obj,'Butts')); out.cut_count=count(prop(obj,'Cuts'));
            out.plastic_count=count(prop(obj,'Plastics'));
            out.methods={translate_global:typeof prop(obj,'TranslateGCS')==='function',rotate_global:typeof prop(obj,'RotateGCS')==='function',build:typeof prop(obj,'Build')==='function'};
        }
        return out;
    }
    function parentHandle(indexes) {
        var obj=requireModel(), prefix=indexes.slice(0,-1);
        for(var i=0;i<prefix.length;i++) obj=child(obj,prefix[i]);
        return obj ? register(obj,prefix) : null;
    }
    function scan(parent, prefix, recursive) {
        var rows=[], stack=[], i, visited=new WeakSet();
        for(i=count(parent)-1;i>=0;i--) stack.push({obj:child(parent,i),indexes:prefix.concat([i])});
        while(stack.length) {
            var item=stack.pop();
            if(!item.obj || (typeof item.obj!=='object' && typeof item.obj!=='function')) continue;
            if(visited.has(item.obj)) continue; visited.add(item.obj);
            rows.push(item);
            if(rows.length>50000) fail('LIMIT','More than 50000 objects; list a specific parent instead');
            if(item.indexes.length>50) fail('LIMIT','Model hierarchy exceeds 50 levels');
            if(recursive) for(i=count(item.obj)-1;i>=0;i--) stack.push({obj:child(item.obj,i),indexes:item.indexes.concat([i])});
        }
        return rows;
    }
    function findRef(obj) {
        var rows=scan(requireModel(),[],true), uid=identity(obj);
        for(var i=0;i<rows.length;i++) if(rows[i].obj===obj || (uid!==null && identity(rows[i].obj)===uid)) return rows[i];
        fail('NOT_IN_MODEL','Object was not found in current model');
    }
    function committedSnapshot(obj,details) {
        // Native BAZIS can publish a committed object only after returning to its
        // event loop. Failure to find it immediately must not suggest retrying
        // a creation that has already committed. Never repeat the mutation here.
        var located;
        try{located=findRef(obj);}catch(e){if(e.code==='NOT_IN_MODEL')return null;throw e;}
        return snapshot(located.obj,located.indexes,details);
    }
    function creationReceipt(out,pending) {
        out.committed=true;out.object_lookup_pending=pending;
        if(pending)out.notice='Creation committed; object lookup is not yet available. Read list_objects on the next call. Do not repeat creation.';
        return out;
    }
    function requireFunction(fn, label) { if(typeof fn!=='function') fail('UNSUPPORTED',label+' is unavailable in this BAZIS runtime'); }
    function targets(p) {
        if(!Array.isArray(p.object_ids) || p.object_ids.length<1 || p.object_ids.length>100) fail('INVALID_ARGUMENT','Expected 1..100 object_ids');
        var out=[], seen={};
        for(var i=0;i<p.object_ids.length;i++) {
            var target=locate(p.object_ids[i]);
            if(seen[target.id]) fail('INVALID_ARGUMENT','Duplicate object ID'); seen[target.id]=true; out.push(target);
        }
        for(i=0;i<out.length;i++) for(var j=i+1;j<out.length;j++) {
            var a=out[i].entry.indexes,b=out[j].entry.indexes,shorter=Math.min(a.length,b.length),same=true;
            for(var k=0;k<shorter;k++) if(a[k]!==b[k]) {same=false;break;}
            if(same) fail('INVALID_ARGUMENT','Do not combine a parent with its descendant in one command');
        }
        return out;
    }
    function editGuard(p) {
        requireModel();
        if(config.allow_edits!==true) fail('READ_ONLY','Edits are disabled in the local configuration');
        if(p.model_token!==modelToken()) fail('MODEL_CHANGED','Read bazis_get_model again and use its model_token');
    }
    function transaction(label, operation) {
        requireFunction(typeof StartEditing!=='undefined'?StartEditing:null,'StartEditing');
        requireFunction(prop(Action,'Commit'),'Action.Commit');
        requireFunction(prop(Action,'Revert'),'Action.Revert');
        StartEditing(requireModel());
        var result;
        try { result=operation(); Action.Commit(label); }
        catch(e) {
            try { Action.Revert(); } catch(rollbackError) { e.message += '; rollback failed: '+message(rollbackError); }
            throw e;
        }
        return result;
    }
    function offsets(p) { return {x:numeric(p.dx,'dx',-1000000,1000000,0),y:numeric(p.dy,'dy',-1000000,1000000,0),z:numeric(p.dz,'dz',-1000000,1000000,0)}; }
    function newVector(v) { requireFunction(typeof NewVector!=='undefined'?NewVector:null,'NewVector'); return NewVector(v.x,v.y,v.z); }
    function panelSpec(p) {
        if(['front','horizontal','vertical'].indexOf(p.orientation)<0) fail('INVALID_ARGUMENT','Invalid panel orientation');
        return {name:text(p.name,'name'),orientation:p.orientation,width:numeric(p.width,'width',0.01,100000),height:numeric(p.height,'height',0.01,100000),
            thickness:numeric(p.thickness,'thickness',0.01,200),x:numeric(p.x,'x',-1000000,1000000,0),y:numeric(p.y,'y',-1000000,1000000,0),z:numeric(p.z,'z',-1000000,1000000,0),
            material:p.material===null || typeof p.material==='undefined'?null:text(p.material,'material')};
    }
    function panelFunctions() {
        requireFunction(typeof AddFrontPanel!=='undefined'?AddFrontPanel:null,'AddFrontPanel');
        requireFunction(typeof AddHorizPanel!=='undefined'?AddHorizPanel:null,'AddHorizPanel');
        requireFunction(typeof AddVertPanel!=='undefined'?AddVertPanel:null,'AddVertPanel');
    }
    function addPanel(s) {
        var panel;
        if(s.orientation==='front') panel=AddFrontPanel(s.x,s.y,s.x+s.width,s.y+s.height,s.z);
        else if(s.orientation==='horizontal') panel=AddHorizPanel(s.x,s.z,s.x+s.width,s.z+s.height,s.y);
        else panel=AddVertPanel(s.z,s.y,s.z+s.width,s.y+s.height,s.x);
        if(!panel) fail('CREATE_FAILED','BAZIS did not return the new panel');
        panel.Name=s.name; if(s.material) panel.MaterialName=s.material; panel.Thickness=s.thickness;
        requireFunction(prop(panel,'Build'),'panel.Build'); panel.Build(); return panel;
    }

    var handlers={};
    handlers.ping=function(){return {pong:true,version:VERSION};};
    handlers.get_model=function(){
        var m=requireModel();
        return {name:prop(m,'Name'),filename:filename,top_level_count:count(m),selection_count:prop(m,'SelectionCount'),units:'mm',
            axes:{x:'width',y:'height / up',z:'depth'},active_material:typeof ActiveMaterial!=='undefined'?{name:prop(ActiveMaterial,'Name'),thickness:prop(ActiveMaterial,'Thickness')}:null};
    };
    handlers.capabilities=function(){
        return {version:VERSION,protocol:PROTOCOL,node:process.version,architecture:process.arch,api_version:typeof system!=='undefined'?prop(system,'apiVersion'):null,
            escape_protection:escapeGuard,
            stop_key:stopKey,connection_mode:'manual',client_presence_monitor:false,
            allow_edits:config.allow_edits===true,handlers:Object.keys(handlers).sort(),
            detected:{continue_execution:typeof prop(Action,'Continue')==='function',commit:typeof prop(Action,'Commit')==='function',revert:typeof prop(Action,'Revert')==='function',
                create_panel:typeof AddFrontPanel==='function' && typeof AddHorizPanel==='function' && typeof AddVertPanel==='function',
                create_block:typeof BeginBlock==='function' && typeof EndBlock==='function',copy:typeof AddCopy==='function',delete_object:typeof DeleteObject==='function',save_model:typeof prop(Action,'SaveModel')==='function'},
            scope:'Legacy scripting API; API availability is not a successful live edit test'};
    };
    handlers.list_objects=function(p){
        var root=requireModel(), prefix=[];
        if(p.parent_id) {var located=locate(p.parent_id);root=located.obj;prefix=located.entry.indexes;}
        var all=scan(root,prefix,p.recursive===true), filtered=[], query=typeof p.name_contains==='string'?p.name_contains.toLowerCase():'';
        for(var i=0;i<all.length;i++) if(!query || String(prop(all[i].obj,'Name') || '').toLowerCase().indexOf(query)>=0) filtered.push(all[i]);
        var offset=numeric(p.offset,'offset',0,50000,0),limit=numeric(p.limit,'limit',1,500,100),items=[];
        if(offset!==Math.floor(offset) || limit!==Math.floor(limit)) fail('INVALID_ARGUMENT','offset and limit must be integers');
        for(i=offset;i<Math.min(filtered.length,offset+limit);i++) items.push(snapshot(filtered[i].obj,filtered[i].indexes,false));
        return {total:filtered.length,offset:offset,items:items,next_offset:offset+items.length<filtered.length?offset+items.length:null};
    };
    handlers.get_object=function(p){var t=locate(p.object_id);return snapshot(t.obj,t.entry.indexes,true);};
    handlers.get_panel_drilling=function(p){
        requireModel();
        if(p.model_token!==modelToken())fail('MODEL_CHANGED','Read get_model again');
        var ts=targets(p);
        requireFunction(typeof NewHoleDrilling!=='undefined'?NewHoleDrilling:null,'NewHoleDrilling');
        var drilling=NewHoleDrilling(),panels=[],total=0;
        requireFunction(prop(drilling,'AddBody'),'HoleDrilling.AddBody');
        requireFunction(prop(drilling,'AddFasteners'),'HoleDrilling.AddFasteners');
        requireFunction(prop(drilling,'DrillHoles'),'HoleDrilling.DrillHoles');
        ts.forEach(function(t){drilling.AddBody(t.obj);});
        drilling.AddFasteners(requireModel());drilling.DrillHoles();
        var bodies=prop(drilling,'Bodies');requireFunction(prop(bodies,'FindBodyInfo'),'Bodies.FindBodyInfo');
        ts.forEach(function(t){
            var info=bodies.FindBodyInfo(t.obj),holes=prop(info,'Holes'),n=prop(holes,'Count'),items=prop(holes,'Items');
            if(typeof n!=='number'||n<0||n!==Math.floor(n))fail('UNSUPPORTED','Native drilled-hole collection unavailable');
            total+=n;if(total>50000)fail('LIMIT','More than 50000 calculated holes; request fewer panels');
            var record={panel:snapshot(t.obj,t.entry.indexes,false),holes:[]};
            for(var i=0;i<n;i++){
                var hole=items?prop(items,i):prop(holes,i);if(!hole)fail('UNSUPPORTED','Native drilled hole unavailable');
                var row={index:i,body_uid:identity(prop(hole,'Body')),fastener_uid:identity(prop(hole,'Fastener')),
                    fastener_name:prop(prop(hole,'Fastener'),'Name'),properties:{},position_raw:vector(prop(hole,'Position')),direction_raw:vector(prop(hole,'Direction'))};
                ['Diameter','Radius','Depth','DrillMode'].forEach(function(k){var v=prop(hole,k);if(scalar(v)&&typeof v!=='undefined')row.properties[k]=v;});
                row.contour_element_count=prop(prop(hole,'Contour'),'Count');
                if(row.position_raw&&typeof prop(t.obj,'ToGlobal')==='function')row.position_panel_to_global_candidate=vector(t.obj.ToGlobal(prop(hole,'Position')));
                if(row.direction_raw&&typeof prop(t.obj,'NToGlobal')==='function')row.direction_panel_to_global_candidate=vector(t.obj.NToGlobal(prop(hole,'Direction')));
                record.holes.push(row);
            }
            panels.push(record);
        });
        return {source:'BAZIS NewHoleDrilling / Bodies.FindBodyInfo',panel_count:panels.length,hole_count:total,panels:panels,
            coordinate_note:'Calculated holes associated by BAZIS. Validate raw versus body-local coordinates before rendering.'};
    };
    // Read existing native tessellation only. Never Build/Triangulate the model.
    handlers.read_geometry=function(p){
        requireModel();
        if(p.model_token!==modelToken()) fail('MODEL_CHANGED','Read get_model again');
        var t=locate(p.object_id), o=t.obj, mesh=null, result={object:snapshot(o,t.entry.indexes,true),source_properties:{},components:[]};
        var names=['FileName','Filename','FilePath','SourceFile','SourceFileName','FragmentFileName'];
        names.forEach(function(k){var v=prop(o,k);if(typeof v==='string' && v)result.source_properties[k]=v;});
        var cap=numeric(p.max_triangles,'max_triangles',1,200000,20000), used=0;
        if(cap!==Math.floor(cap))fail('INVALID_ARGUMENT','max_triangles must be integer');
        var rows=[{obj:o,indexes:t.entry.indexes}];
        if(p.recursive===true)rows=rows.concat(scan(o,t.entry.indexes,true));
        if(rows.length>2000)fail('LIMIT','Read a smaller component');
        rows.forEach(function(row){
            var obj=row.obj, item={uid:identity(obj),name:prop(obj,'Name'),is_mesh:null,triangles:[],triangles_to_global:[],errors:[]};
            try{
                if(typeof prop(obj,'IsMesh')==='function')item.is_mesh=obj.IsMesh();
                mesh=item.is_mesh===true && typeof prop(obj,'AsMesh')==='function'?obj.AsMesh():obj;
                var n=prop(mesh,'TriListsCount');item.tri_lists_count=typeof n==='number'?n:null;
                if(typeof n==='number' && n>=0 && n<=10000){
                    var lists=prop(mesh,'TriLists');
                    for(var i=0;i<n;i++){
                        var list=prop(lists,i), size=prop(list,'Count'), tris=prop(list,'Triangles');
                        if(i===0)item.native_triangle_list=nativeData(list,1,[],{remaining:100});
                        if(typeof size!=='number' || size<0 || size!==Math.floor(size))fail('INVALID_GEOMETRY','Invalid triangle count');
                        if(used+size>cap)fail('LIMIT','Triangle budget exceeded; read a smaller component');
                        for(var j=0;j<size;j++){
                            var tri=prop(tris,j), vertices=[prop(tri,'Vertex1'),prop(tri,'Vertex2'),prop(tri,'Vertex3')], raw=vertices.map(vector);
                            if(raw.some(function(v){return !v;}))fail('INVALID_GEOMETRY','Invalid triangle vertices');
                            item.triangles.push(raw);used++;
                            if(typeof prop(obj,'ToGlobal')==='function')item.triangles_to_global.push(vertices.map(function(v){return vector(obj.ToGlobal(v));}));
                        }
                    }
                }
            }catch(e){if(e.code==='LIMIT')throw e;item.errors.push(message(e));}
            result.components.push(item);
        });
        result.triangle_count=used;result.complete=used>0&&result.components.every(function(c){return !c.errors.length&&c.tri_lists_count!==null;});result.solid_closed_verified=false;result.coordinate_note='Raw vertices and separately ToGlobal-transformed vertices; validate against object bounds before rendering.';
        return result;
    };
    handlers.get_selection=function(){
        var all=scan(requireModel(),[],true),items=[],total=0;
        for(var i=0;i<all.length;i++) if(prop(all[i].obj,'Selected')===true) {total++;if(items.length<500)items.push(snapshot(all[i].obj,all[i].indexes,false));}
        return {total:total,items:items,truncated:total>items.length};
    };
    handlers.select_objects=function(p){
        editGuard(p);var ts=targets(p),m=requireModel();
        if(p.replace!==false) {requireFunction(prop(m,'UnSelectAll'),'Model.UnSelectAll');m.UnSelectAll();}
        for(var i=0;i<ts.length;i++) ts[i].obj.Selected=true;
        return {selected:ts.map(function(t){return t.id;})};
    };
    handlers.set_properties=function(p){
        editGuard(p);var ts=targets(p),props={},map={name:'Name',visible:'Visible',art_pos:'ArtPos',designation:'Designation'};
        for(var key in map) if(Object.prototype.hasOwnProperty.call(map,key) && p[key]!==null && typeof p[key]!=='undefined') {
            if(key==='visible') {if(typeof p[key]!=='boolean')fail('INVALID_ARGUMENT','visible must be boolean');}
            else text(p[key],key,key!=='name'); props[map[key]]=p[key];
        }
        if(!Object.keys(props).length) fail('INVALID_ARGUMENT','No properties supplied');
        transaction('MCP: properties',function(){for(var i=0;i<ts.length;i++)for(var k in props)if(Object.prototype.hasOwnProperty.call(props,k))ts[i].obj[k]=props[k];});
        return {changed:ts.map(function(t){return snapshot(t.obj,t.entry.indexes,false);})};
    };
    handlers.move_objects=function(p){
        editGuard(p);var ts=targets(p),delta=offsets(p),v=newVector(delta);
        ts.forEach(function(t){requireFunction(prop(t.obj,'TranslateGCS'),'object.TranslateGCS');});
        transaction('MCP: move',function(){ts.forEach(function(t){t.obj.TranslateGCS(v);});});
        return {moved:ts.map(function(t){return snapshot(t.obj,t.entry.indexes,false);})};
    };
    handlers.rotate_objects=function(p){
        editGuard(p);var ts=targets(p);if(['x','y','z'].indexOf(p.axis)<0)fail('INVALID_ARGUMENT','Invalid axis');
        var angle=numeric(p.angle,'angle',-3600,3600),axis={x:0,y:0,z:0};axis[p.axis]=1;axis=newVector(axis);
        ts.forEach(function(t){requireFunction(prop(t.obj,'RotateGCS'),'object.RotateGCS');});
        transaction('MCP: rotate',function(){ts.forEach(function(t){t.obj.RotateGCS(axis,angle);});});
        return {rotated:ts.map(function(t){return snapshot(t.obj,t.entry.indexes,false);}),pivot:'global origin'};
    };
    handlers.duplicate_objects=function(p){
        editGuard(p);var ts=targets(p),delta=offsets(p),v=newVector(delta),copies=[];
        requireFunction(typeof AddCopy!=='undefined'?AddCopy:null,'AddCopy');
        transaction('MCP: duplicate',function(){ts.forEach(function(t){var copy=AddCopy(t.obj);requireFunction(prop(copy,'TranslateGCS'),'copy.TranslateGCS');copy.TranslateGCS(v);copies.push(copy);});});
        var snapshots=copies.map(function(obj){return committedSnapshot(obj,false);});
        return creationReceipt({copies:snapshots},snapshots.some(function(item){return item===null;}));
    };
    handlers.create_panel=function(p){
        editGuard(p);var spec=panelSpec(p);panelFunctions();var panel=transaction('MCP: create panel',function(){return addPanel(spec);});
        var details=committedSnapshot(panel,true);return creationReceipt({panel:details},details===null);
    };
    handlers.create_cabinet=function(p){
        editGuard(p);panelFunctions();requireFunction(typeof BeginBlock!=='undefined'?BeginBlock:null,'BeginBlock');requireFunction(typeof EndBlock!=='undefined'?EndBlock:null,'EndBlock');
        var w=numeric(p.width,'width',1,100000),h=numeric(p.height,'height',1,100000),d=numeric(p.depth,'depth',1,100000),t=numeric(p.thickness,'thickness',0.1,100,18);
        var shelves=numeric(p.shelves,'shelves',0,30,0),back=numeric(p.back_thickness,'back_thickness',0,50,4),name=text(p.name,'name');
        var origin={x:numeric(p.x,'x',-1000000,1000000,0),y:numeric(p.y,'y',-1000000,1000000,0),z:numeric(p.z,'z',-1000000,1000000,0)};
        if(shelves!==Math.floor(shelves) || w<=2*t || h<=(shelves+2)*t || d<=t)fail('INVALID_ARGUMENT','Cabinet dimensions leave no interior clearance');
        var mat=p.material===null || typeof p.material==='undefined'?null:text(p.material,'material');
        var backMat=p.back_material===null || typeof p.back_material==='undefined'?mat:text(p.back_material,'back_material');
        var specs=[];
        function spec(label,o,pw,ph,px,py,pz,thick,material){specs.push(panelSpec({name:label,orientation:o,width:pw,height:ph,x:px,y:py,z:pz,thickness:thick,material:material}));}
        spec('Left side','vertical',d,h,0,0,0,t,mat);spec('Right side','vertical',d,h,w-t,0,0,t,mat);
        spec('Bottom','horizontal',w-2*t,d,t,0,0,t,mat);spec('Top','horizontal',w-2*t,d,t,h-t,0,t,mat);
        var gap=(h-(shelves+2)*t)/(shelves+1);
        for(var i=0;i<shelves;i++)spec('Shelf '+(i+1),'horizontal',w-2*t,d,t,t+gap*(i+1)+t*i,0,t,mat);
        if(back>0)spec('Back','front',w,h,0,0,d,back,backMat);
        var block=transaction('MCP: create cabinet',function(){
            var b=BeginBlock(name);try {specs.forEach(addPanel);}finally{EndBlock();}
            if(!b)fail('CREATE_FAILED','BeginBlock did not return a block');
            if(origin.x || origin.y || origin.z){requireFunction(prop(b,'TranslateGCS'),'block.TranslateGCS');b.TranslateGCS(newVector(origin));}return b;
        });
        var details=committedSnapshot(block,true);return creationReceipt({cabinet:details,panel_count:specs.length,construction:'Applied back increases overall depth by back_thickness. No doors or fittings.'},details===null);
    };
    handlers.delete_objects=function(p){
        editGuard(p);var ts=targets(p);requireFunction(typeof DeleteObject!=='undefined'?DeleteObject:null,'DeleteObject');
        transaction('MCP: delete',function(){ts.forEach(function(t){DeleteObject(t.obj);});});
        return {deleted:ts.map(function(t){delete handles[t.id];return t.id;})};
    };
    handlers.set_view=function(p){
        var views={front:typeof p3dFront!=='undefined'?p3dFront:null,back:typeof p3dBack!=='undefined'?p3dBack:null,left:typeof p3dLeft!=='undefined'?p3dLeft:null,right:typeof p3dRight!=='undefined'?p3dRight:null,top:typeof p3dTop!=='undefined'?p3dTop:null,bottom:typeof p3dBottom!=='undefined'?p3dBottom:null,isometric:typeof p3dIsometric!=='undefined'?p3dIsometric:null};
        if(!Object.prototype.hasOwnProperty.call(views,p.view) || views[p.view]===null)fail('UNSUPPORTED','View unavailable');
        requireFunction(typeof SetCamera!=='undefined'?SetCamera:null,'SetCamera');if(p.fit_all!==false)requireFunction(typeof ViewAll!=='undefined'?ViewAll:null,'ViewAll');
        SetCamera(views[p.view]);if(p.fit_all!==false)ViewAll();return {view:p.view};
    };
    handlers.save_model_copy=function(p){
        editGuard(p);var filename=text(p.filename,'filename');
        if(!/^[^<>:"/\\|?*\x00-\x1f]+\.b3d$/i.test(filename) || /^(con|prn|aux|nul|com[0-9]|lpt[0-9])\./i.test(filename) || /[ .]$/.test(filename))fail('INVALID_ARGUMENT','Use a simple new filename ending .b3d');
        var dest=path.join(folder,'exports',filename);if(fs.existsSync(dest))fail('ALREADY_EXISTS','Refusing to overwrite an existing model');
        requireFunction(prop(Action,'SaveModel'),'Action.SaveModel');Action.SaveModel(dest);
        if(!fs.existsSync(dest) || fs.statSync(dest).size===0)fail('SAVE_FAILED','BAZIS did not create the output file');
        return {path:dest,bytes:fs.statSync(dest).size,active_filename_may_change:true};
    };
    handlers.stop_bridge=function(){return {stopping:true};};

    function installKeyboard() {
        previousKeyboard={preview:prop(Action,'KeyPreview'),down:prop(Action,'OnKeyDown'),up:prop(Action,'OnKeyUp')};
        function handle(sender,key,down) {
            // These events use Windows virtual-key codes, not Unicode code points.
            // VK_OEM_3=192 is the ` physical key on the tested target layout.
            // Do not use 96 here: that would also consume numpad zero.
            var ref=null,code,field,candidates=[key,sender];
            for(var i=0;i<candidates.length;i++) {
                var candidate=candidates[i];
                if(!candidate || (typeof candidate!=='object' && typeof candidate!=='function'))continue;
                if(typeof prop(candidate,'value')==='number'){ref=candidate;code=prop(candidate,'value');field='value';break;}
                if(typeof prop(candidate,'Value')==='number'){ref=candidate;code=prop(candidate,'Value');field='Value';break;}
            }
            if(!ref)return;
            if(code!==27 && code!==stopKey.virtual_key)return;
            // Escape is consumed only for this script's action. Other keys keep
            // their native meaning; stopping never relaunches the listener.
            try {
                ref[field]=0;
                if(prop(ref,field)!==0)return;
                if(code===27)escapeGuard.ignored_events++;
                else if(down){stopKey.events++;if(busy)stopRequested=true;else finish();}
            }catch(e){escapeGuard.error=message(e);}
        }
        try {
            Action.KeyPreview=true;
            Action.OnKeyDown=function(sender,key){handle(sender,key,true);};
            Action.OnKeyUp=function(sender,key){handle(sender,key,false);};
            escapeGuard.installed=prop(Action,'KeyPreview')===true && typeof prop(Action,'OnKeyDown')==='function';
            if(!escapeGuard.installed)escapeGuard.error='Native key preview/event binding could not be verified';
        }catch(e){escapeGuard.error=message(e);}
    }
    function restoreKeyboard() {
        if(!previousKeyboard)return;
        try{Action.OnKeyDown=previousKeyboard.down || null;}catch(_){}
        try{Action.OnKeyUp=previousKeyboard.up || null;}catch(_){}
        if(typeof previousKeyboard.preview==='boolean')try{Action.KeyPreview=previousKeyboard.preview;}catch(_){}
        previousKeyboard=null;
    }
    function showState(state) {
        // Stable text. No presence lease, no connection scan and no indicator animation.
        var hint=state==='fault'?'Codex MCP: eroare. Oprire: `.':
            state==='stopped'?'Codex MCP oprit. Pornire manuala: F5.':'Codex MCP activ. Oprire: `.';
        if(hint!==lastHint)try{Action.Hint=hint;lastHint=hint;}catch(_){}
    }
    function heartbeat(state) {
        refreshModel();
        showState(state);
        atomic(path.join(folder,'status.json'),{protocol:PROTOCOL,version:VERSION,session_id:session,state:state,
            pid:process.pid,updated_at_ms:Date.now(),model_token:modelToken(),completed_requests:completed,last_error:lastError,
            connection_mode:'manual',client_presence_monitor:false,last_client_request_at_ms:lastClientRequestMs,
            stop_key:stopKey,escape_protection:escapeGuard});
        lastHeartbeat=Date.now();
    }
    function stop() {
        if(stopped)return;stopped=true;if(timer)clearInterval(timer);
        restoreKeyboard();
        try{heartbeat('stopped');}catch(_){}
        try{if(jsonFile(lockPath).session_id===session)fs.unlinkSync(lockPath);}catch(_){}
    }
    function finish() {stop();try{Action.Finish();}catch(_){}}
    function processRequest(name) {
        var id=name.slice(0,-5),inbox=path.join(folder,'inbox',name),processing=path.join(folder,'processing',name),response=path.join(folder,'outbox',name),journal=path.join(folder,'journal',name);
        try{fs.renameSync(inbox,processing);}catch(_){return;}
        var req,reply={id:id,session_id:session,ok:false},started=false;
        try {
            if(fs.statSync(processing).size>1024*1024)fail('LIMIT','Request exceeds 1 MiB');
            req=jsonFile(processing);
            if(req.id!==id || req.protocol!==PROTOCOL)fail('PROTOCOL','Invalid request envelope');
            if(req.token!==config.token)fail('AUTH','Invalid local token');
            if(req.session_id!==session)fail('SESSION_CHANGED','Request belongs to a previous bridge session');
            lastClientRequestMs=Date.now();
            if(fs.existsSync(response)){return;}
            if(fs.existsSync(journal))fail('OUTCOME_UNKNOWN','Request was started previously; refusing to repeat it');
            if(typeof req.deadline_ms!=='number' || !isFinite(req.deadline_ms) || Date.now()>req.deadline_ms)fail('EXPIRED','Request expired before execution');
            if(fs.existsSync(path.join(folder,'cancel',name)))fail('CANCELLED','Request was cancelled before execution');
            if(typeof req.method!=='string' || !Object.prototype.hasOwnProperty.call(handlers,req.method))fail('UNKNOWN_METHOD','Unsupported command');
            if(!req.params || typeof req.params!=='object' || Array.isArray(req.params))fail('INVALID_ARGUMENT','params must be an object');
            refreshModel();
            atomic(journal,{id:id,session_id:session,state:'started',method:req.method,started_at_ms:Date.now()});started=true;
            var result=handlers[req.method](req.params);refreshModel();
            result.model_token=modelToken();result.request_id=id;result.session_id=session;
            reply.ok=true;reply.result=result;completed++;
        } catch(e) {
            reply.error={code:e.code || 'BAZIS_ERROR',message:message(e)};lastError=reply.error;
        } finally {
            // Duplicate completed requests retain their original response.
            if(!fs.existsSync(response))atomic(response,reply);
            if(started)atomic(journal,{id:id,session_id:session,state:reply.ok?'completed':'failed',method:req.method,finished_at_ms:Date.now(),error:reply.error || null});
            try{fs.unlinkSync(processing);}catch(_){}
        }
        if(reply.ok && req.method==='stop_bridge') {
            finish();
        }
    }
    function tick() {
        if(stopped || busy)return;busy=true;
        try {
            refreshModel();var names=fs.readdirSync(path.join(folder,'inbox')).filter(function(n){return /^[0-9a-f]{32}\.json$/.test(n);}).sort();
            for(var i=0;i<Math.min(names.length,4) && !stopped && !stopRequested;i++)processRequest(names[i]);
            if(!stopped && Date.now()-lastHeartbeat>=1000)heartbeat('ready');
        }catch(e){lastError={code:e.code || 'POLL_ERROR',message:message(e)};try{heartbeat('fault');}catch(_){} }
        finally{busy=false;if(stopRequested && !stopped)finish();}
    }
    try {
        config=jsonFile(configPath);
        if(typeof config.token!=='string' || config.token.length<32 || typeof config.bridge_dir!=='string')fail('CONFIG','Invalid local bridge config');
        folder=config.bridge_dir;session=crypto.randomBytes(16).toString('hex');lockPath=path.join(folder,'bridge.lock');
        ['inbox','processing','outbox','journal','cancel','exports'].forEach(function(n){var dir=path.join(folder,n);if(!fs.existsSync(dir))fs.mkdirSync(dir);});
        if(fs.existsSync(lockPath)) {
            var old=jsonFile(lockPath),alive=true;
            if(typeof old.pid==='number')try{process.kill(old.pid,0);}catch(e){if(e.code==='ESRCH')alive=false;}
            if(alive)fail('ALREADY_RUNNING','A BAZIS bridge still owns this folder. Stop it before starting another');
            fs.unlinkSync(lockPath);
        }
        fs.writeFileSync(lockPath,JSON.stringify({session_id:session,pid:process.pid}),{flag:'wx'});
        requireFunction(prop(Action,'Continue'),'Action.Continue');
        Action.OnFinish=stop;
        installKeyboard();
        Action.Continue();heartbeat('ready');
        timer=setInterval(tick,Math.max(100,Math.min(1000,config.poll_interval_ms || 250)));
    } catch(e) {
        // Only release a lock created by this invocation, never someone else's.
        if(session && lockPath)try{if(jsonFile(lockPath).session_id===session)fs.unlinkSync(lockPath);}catch(_){}
        if(typeof alert==='function')alert('BAZIS MCP: '+message(e)+'\nRuleaza install.py daca lipseste configurarea.');
        else throw e;
    }
}());

