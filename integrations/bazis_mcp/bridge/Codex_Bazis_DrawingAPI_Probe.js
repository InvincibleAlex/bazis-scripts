// Read-only native API discovery, compatible with BAZIS embedded Node 8.
// Run once in the BAZIS Script Editor. Does not generate, edit or export drawings.
(function () {
    'use strict';
    var fs=require('fs'),path=require('path'),os=require('os');
    var LIMIT=400,DEPTH=4;
    var relevant=/draw|draft|sheet|document|page|view|text|font|size|dim|extension|leader|hole|cut|groov|render|print|export|setting|style|scale|layout/i;
    var report={probe_version:'1.0',scope:'Native metadata discovery; not proof of a callable 2D rendering API',
        model_modified:false,drawings_modified:false,configuration_modified:false,
        arbitrary_methods_invoked:false,created_factory_wrappers:[],roots:[],errors:[]};

    function error(e){return String(e && e.message || e);}
    function describe(value,label) {
        var entry={name:label,type:typeof value,available:value!==null && typeof value!=='undefined',levels:[],relevant_members:[]};
        if(!entry.available || (typeof value!=='object' && typeof value!=='function'))return entry;
        var current=value,seen=[],hits={};
        for(var depth=0;current && depth<DEPTH;depth++) {
            if(seen.indexOf(current)>=0)break;
            seen.push(current);
            var level={depth:depth,members:[]},names;
            try{names=Object.getOwnPropertyNames(current).sort();}
            catch(e){level.error=error(e);entry.levels.push(level);break;}
            if(names.length>LIMIT){level.truncated=true;names=names.slice(0,LIMIT);}
            for(var i=0;i<names.length;i++) {
                var name=names[i],item={name:name};
                try {
                    var descriptor=Object.getOwnPropertyDescriptor(current,name);
                    if(!descriptor){item.kind='descriptor unavailable';}
                    else if(descriptor.get || descriptor.set) {
                        item.kind='accessor; not read';item.getter=!!descriptor.get;item.setter=!!descriptor.set;
                    } else {
                        item.kind=typeof descriptor.value;
                        if(item.kind==='function') {
                            var length=Object.getOwnPropertyDescriptor(descriptor.value,'length');
                            if(length && typeof length.value==='number')item.declared_parameter_count=length.value;
                        }
                    }
                }catch(e){item.error=error(e);}
                level.members.push(item);
                if(relevant.test(name) && !hits[name]){entry.relevant_members.push(item);hits[name]=true;}
            }
            entry.levels.push(level);
            try{current=Object.getPrototypeOf(current);}catch(e){entry.prototype_error=error(e);break;}
        }
        // Constructor prototypes may contain native interfaces even when static
        // constructor metadata contains only JavaScript's name/length fields.
        if(typeof value==='function')try {
            var prototype=Object.getOwnPropertyDescriptor(value,'prototype');
            if(prototype && prototype.value && prototype.value!==value)
                entry.instance_prototype=describe(prototype.value,label+'.prototype');
        }catch(e){entry.instance_prototype_error=error(e);}
        return entry;
    }
    function add(label,getter) {
        try{report.roots.push(describe(getter(),label));}
        catch(e){report.roots.push({name:label,error:error(e)});}
    }

    add('Action',function(){return typeof Action!=='undefined'?Action:undefined;});
    add('Control',function(){return typeof Control!=='undefined'?Control:undefined;});
    add('Owner',function(){return typeof Owner!=='undefined'?Owner:undefined;});
    add('system',function(){return typeof system!=='undefined'?system:undefined;});
    add('IDrawingManager',function(){return typeof IDrawingManager!=='undefined'?IDrawingManager:undefined;});
    add('TUserSettings',function(){return typeof TUserSettings!=='undefined'?TUserSettings:undefined;});
    add('TScriptImportExport',function(){return typeof TScriptImportExport!=='undefined'?TScriptImportExport:undefined;});
    add('TScriptImportExport3D',function(){return typeof TScriptImportExport3D!=='undefined'?TScriptImportExport3D:undefined;});
    add('TScriptSystemNamespace',function(){return typeof TScriptSystemNamespace!=='undefined'?TScriptSystemNamespace:undefined;});
    add('TDrawingBufferData',function(){return typeof TDrawingBufferData!=='undefined'?TDrawingBufferData:undefined;});
    add('TScaledGraphicDrawer',function(){return typeof TScaledGraphicDrawer!=='undefined'?TScaledGraphicDrawer:undefined;});

    // This documented factory creates an import/export wrapper, not model
    // geometry. Never call its Load/Save methods or unknown native constructors.
    if(typeof NewImportExport==='function')try {
        var wrapper=NewImportExport();report.created_factory_wrappers.push('NewImportExport');
        report.roots.push(describe(wrapper,'NewImportExport()'));
    }catch(e){report.errors.push({operation:'NewImportExport wrapper construction',message:error(e)});}

    var folder=path.join(os.homedir(),'Documents','Bazis','Scripts');
    var target=path.join(folder,'Codex_Bazis_DrawingAPI.report.json');
    if(!fs.existsSync(folder))fs.mkdirSync(folder);
    fs.writeFileSync(target,JSON.stringify(report,null,2),'utf8');
    if(typeof alert==='function')alert('Diagnostic API desene terminat.\nRaport: Codex_Bazis_DrawingAPI.report.json\nModelul, desenele si setarile nu au fost modificate.');
}());
