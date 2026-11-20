// Test read-only pentru BAZIS 2022 / Node 8. Nu necesita MCP.
// Contur local + cote Cubis: minus grosimea BAZIS a cantului pe fiecare latura cantuita, pentru dreptunghiuri.
(function () {
    'use strict';
    try {
        var fs = require('fs'), path = require('path'), os = require('os');
        if (typeof Model === 'undefined' || !Model) throw new Error('Model nu este disponibil in acest context/eveniment.');
        function get(o, k) { try { return o[k]; } catch (_) { return undefined; } }
        function num(v) { return typeof v === 'number' && isFinite(v) && v > 0; }
        function str(v) { return v === undefined || v === null ? '' : String(v); }
        function materialProbe(panel) {
            var material=get(panel,'Material'), out={
                nume_material:str(get(panel,'MaterialName')),
                desemnare_piesa:str(get(panel,'Designation')),
                campuri_candidate:{}, proprietati_material:[]};
            // Diagnostic only: candidate fields are not yet confirmed to be the database designation.
            ['MaterialSign','MaterialDesignation'].forEach(function(k){
                var v=get(panel,k); if(typeof v==='string'||typeof v==='number')out.campuri_candidate['panel.'+k]=v;
            });
            ['Sign','Designation','Name','MaterialName'].forEach(function(k){
                var v=get(material,k); if(typeof v==='string'||typeof v==='number')out.campuri_candidate['Material.'+k]=v;
            });
            try {
                if (material)out.proprietati_material=Object.getOwnPropertyNames(material).slice(0,100);
            } catch (_) {}
            out.stare='Diagnostic: nicio valoare nu este folosita automat drept desemnare a materialului.';
            return out;
        }
        function edgeData(panel) {
            var result=[], butts=get(panel,'Butts'), contour=get(panel,'Contour');
            var count=get(butts,'Count'), elements=get(contour,'Objects');
            function point(p) {
                var x=get(p,'x'), y=get(p,'y');
                return typeof x==='number' && isFinite(x) && typeof y==='number' && isFinite(y) ? {x:x,y:y} : null;
            }
            var lo=point(get(contour,'Min')), hi=point(get(contour,'Max'));
            function near(a,b) { return Math.abs(a-b)<0.01; }
            if(typeof count!=='number' || count<0 || count>10000) return result;
            for(var j=0;j<count;j++) {
                var b=get(butts,j), index=get(b,'ElemIndex'), elem=get(elements || contour,index);
                var row={elem_index:index, material:str(get(b,'Material')), semn:str(get(b,'Sign')),
                    grosime_mm:get(b,'Thickness'), latime_mm:get(b,'Width'), sub_taiere:get(b,'ClipPanel'),
                    prefrezare_mm:get(b,'Allowance'), latura_locala:'neidentificata'};
                try {
                    if(elem && typeof elem.IsLine==='function' && elem.IsLine()) {
                        var line=elem.AsLine(), p=point(get(line,'Pos1')), q=point(get(line,'Pos2'));
                        row.inceput=p; row.sfarsit=q;
                        if(p && q && lo && hi) {
                            if(near(p.x,lo.x)&&near(q.x,lo.x)) row.latura_locala='X_min';
                            else if(near(p.x,hi.x)&&near(q.x,hi.x)) row.latura_locala='X_max';
                            else if(near(p.y,lo.y)&&near(q.y,lo.y)) row.latura_locala='Y_min';
                            else if(near(p.y,hi.y)&&near(q.y,hi.y)) row.latura_locala='Y_max';
                            row.lungime_segment_mm=Math.sqrt(Math.pow(p.x-q.x,2)+Math.pow(p.y-q.y,2));
                        }
                    }
                } catch(e) { row.eroare=String(e.message || e); }
                result.push(row);
            }
            return result;
        }
        function cell(v) {
            var s = str(v);
            // Numele din model sunt text, nu formule Excel.
            if (/^[\s]*[=+@-]/.test(s)) s = "'" + s;
            return '"' + s.replace(/"/g, '""') + '"';
        }
        function fibreData(panel) {
            var raw=get(panel,'TextureOrientation'), code=null, label='NEIDENTIFICATA';
            var types=typeof TextureOrientation!=='undefined' ? TextureOrientation : null;
            var fields=['None','Horizontal','Vertical'];
            for(var i=0;i<fields.length;i++) {
                var value=get(types,fields[i]);
                if(value!==undefined && raw===value) { code=i; break; }
            }
            if(code!==null) label=['fara fibra','fibra prima cota (X)','fibra a doua cota (Y)'][code];
            return {cod:code, descriere:label, bazis_orientation:typeof raw==='number'||typeof raw==='string'?raw:null,
                bazis_angle:get(panel,'TextureAngle')};
        }
        function cubisDimensions(panel,w,h,edges) {
            var issues=[], used={}, c=get(panel,'Contour'), elements=get(c,'Objects');
            var lo=get(c,'Min'), hi=get(c,'Max'), sides={};
            function close(a,b){return typeof a==='number' && typeof b==='number' && Math.abs(a-b)<0.01;}
            if(get(c,'Count')!==4) issues.push('contur nedreptunghiular');
            else try {
                for(var i=0;i<4;i++) {
                    var e=get(elements||c,i);
                    if(!e.IsLine()) throw Error('segment neliniar');
                    var line=e.AsLine(),p=line.Pos1,q=line.Pos2,side=null;
                    if(close(p.x,lo.x)&&close(q.x,lo.x)&&close(Math.abs(p.y-q.y),h))side='X_min';
                    if(close(p.x,hi.x)&&close(q.x,hi.x)&&close(Math.abs(p.y-q.y),h))side='X_max';
                    if(close(p.y,lo.y)&&close(q.y,lo.y)&&close(Math.abs(p.x-q.x),w))side='Y_min';
                    if(close(p.y,hi.y)&&close(q.y,hi.y)&&close(Math.abs(p.x-q.x),w))side='Y_max';
                    if(!side||sides[side]) throw Error('contur nedreptunghiular');
                    sides[side]=true;
                }
            } catch(_) {issues.push('contur dreptunghiular neconfirmat');}
            if(issues.length) {
                var deduction={}, warnings=[];
                edges.forEach(function(e){
                    var side=e.latura_locala;
                    if(['X_min','X_max','Y_min','Y_max'].indexOf(side)<0)return;
                    if(e.sub_taiere===true) {
                        if(typeof e.grosime_mm!=='number'||!isFinite(e.grosime_mm)||e.grosime_mm<0)
                            warnings.push('grosime cant indisponibila');
                        else deduction[side]=Math.max(deduction[side]||0,e.grosime_mm);
                    } else if(e.sub_taiere!==false)warnings.push('sub-taiere necunoscuta');
                });
                var bx=(deduction.X_min||0)+(deduction.X_max||0),
                    by=(deduction.Y_min||0)+(deduction.Y_max||0);
                if(w-bx<=0||h-by<=0)warnings.push('cota rezultata nepozitiva');
                return {lungime_mm:warnings.length?null:Math.round((w-bx)*1000)/1000,
                    latime_mm:warnings.length?null:Math.round((h-by)*1000)/1000,
                    scadere_x_mm:bx,scadere_y_mm:by,foloseste_gabarit:true,
                    stare:warnings.length?warnings.join('; '):'GABARIT - minus cant sub-taiere, o singura data pe latura'};
            }
            edges.forEach(function(e){
                var side=e.latura_locala, expected=side==='X_min'||side==='X_max'?h:w;
                if(!sides[side] || !close(e.lungime_segment_mm,expected))issues.push('cant pe segment partial sau neidentificat');
                else if(used[side]!==undefined) issues.push('mai multe canturi pe aceeasi latura');
                else if(typeof e.grosime_mm!=='number'||!isFinite(e.grosime_mm)||e.grosime_mm<0) issues.push('grosime cant indisponibila');
                else if(e.sub_taiere!==true && e.sub_taiere!==false)issues.push('sub-taiere necunoscuta');
                else used[side]=e.sub_taiere ? e.grosime_mm : 0;
            });
            var dx=(used.X_min||0)+(used.X_max||0);
            var dy=(used.Y_min||0)+(used.Y_max||0);
            if(w-dx<=0||h-dy<=0)issues.push('cota rezultata nepozitiva');
            return {lungime_mm:issues.length?null:Math.round((w-dx)*1000)/1000,
                latime_mm:issues.length?null:Math.round((h-dy)*1000)/1000,
                scadere_x_mm:dx,scadere_y_mm:dy,stare:issues.length?issues.join('; '):'OK - scadere grosimi cant din BAZIS'};
        }
        var rows = [], seen = new WeakSet(), stack = [{o:Model, parent:''}], visited = 0;
        while (stack.length) {
            var item = stack.pop(), o = item.o;
            if (!o || (typeof o !== 'object' && typeof o !== 'function') || seen.has(o)) continue;
            seen.add(o);
            if (++visited > 100000) throw new Error('Limita de 100000 obiecte depasita; exportul a fost oprit.');
            var w = get(o, 'ContourWidth'), h = get(o, 'ContourHeight'), t = get(o, 'Thickness');
            var name = str(get(o, 'Name'));
            if (num(w) && num(h) && num(t) && /\bpal\b/i.test(str(get(o, 'MaterialName')).split('\r')[0])) {
                var edges=edgeData(o), fibre=fibreData(o), cubis=cubisDimensions(o,w,h,edges);
                rows.push({
                nr:rows.length + 1, nume:name, grup:item.parent,
                pozitie:str(get(o, 'ArtPos')), material:str(get(o, 'MaterialName')),
                contur_x_mm:w, contur_y_mm:h, grosime_mm:t, canturi:edges, fibra:fibre.cod,
                detalii_fibra:fibre, cote_cubis:cubis, diagnostic_material:materialProbe(o), material_db:null
                });
            }
            var n = get(o, 'Count');
            if (typeof n === 'number' && n >= 0 && n <= 100000) {
                var children = get(o, 'Objects');
                for (var i = Math.floor(n)-1; i >= 0; i--) {
                    stack.push({o:get(children || o, i), parent:item.parent ? item.parent + ' / ' + name : name});
                }
            }
        }
        // Query all panel materials through one verified read-only Firebird connection.
        try {
            var readerConfig=JSON.parse(fs.readFileSync(path.join(os.homedir(),'.bazis-mcp','material-db-reader.json'),'utf8'));
            var dbOutput=require('child_process').execFileSync(readerConfig.python,[readerConfig.script],{
                input:JSON.stringify(rows.map(function(r){return {material:r.material,thickness_mm:r.grosime_mm};})),
                encoding:'utf8',windowsHide:true,timeout:45000,maxBuffer:8*1024*1024,stdio:['pipe','pipe','pipe']});
            var dbResult=JSON.parse(dbOutput);
            if(!dbResult.ok || !Array.isArray(dbResult.materials) || dbResult.materials.length!==rows.length)
                throw Error('Raspuns Firebird invalid');
            rows.forEach(function(r,i){r.material_db=dbResult.materials[i];});
        } catch(_) {
            rows.forEach(function(r){r.material_db={desemnare:null,sursa:'Firebird direct',
                stare:'Citire directa indisponibila; verificati configurarea/conexiunea locala'};});
        }
        var folder = null, folderSource = '', folderError = null, drawingName = null;
        var modelFile = typeof ModelFilename === 'string' ? ModelFilename : '';
        function recentDrawing(dir, maxAge) {
            var now = Date.now(), files = [];
            fs.readdirSync(dir).forEach(function (name) {
                if (!/\.bln$/i.test(name)) return; // Exclude backups .$$$bln.
                try {
                    var st = fs.statSync(path.join(dir, name)), age = now - st.mtime.getTime();
                    if (st.isFile() && age >= -5000 && age <= maxAge)
                        files.push({name:name, time:st.mtime.getTime()});
                } catch (_) {}
            });
            files.sort(function (a,b) { return b.time-a.time; });
            // Multiple simultaneous drawings do not identify a unique export name.
            if (!files.length || (files.length > 1 && files[0].time-files[1].time < 2000)) return null;
            return files[0].name;
        }
        try {
            var psSource = "$ProgressPreference = 'SilentlyContinue'\n# Read-only: returns the last Windows Save dialog directory for Bazis.exe.\n$ErrorActionPreference = 'Stop'\nAdd-Type -TypeDefinition @'\nusing System;\nusing System.Text;\nusing System.Runtime.InteropServices;\npublic static class BazisPidlPath {\n [DllImport(\"shell32.dll\", CharSet = CharSet.Unicode)]\n public static extern bool SHGetPathFromIDListW(IntPtr pidl, StringBuilder path);\n}\n'@\n$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ComDlg32\\LastVisitedPidlMRU')\ntry {\n $order = $key.GetValue('MRUListEx')\n for ($j=0; $j -lt $order.Length; $j+=4) {\n  $index = [BitConverter]::ToUInt32($order,$j)\n  if ($index -eq [uint32]::MaxValue) { break }\n  $bytes = $key.GetValue([string]$index)\n  if ($bytes -isnot [byte[]]) { continue }\n  $end=0\n  while ($end+1 -lt $bytes.Length -and ($bytes[$end] -ne 0 -or $bytes[$end+1] -ne 0)) { $end+=2 }\n  $exe=[Text.Encoding]::Unicode.GetString($bytes,0,$end)\n  if ($exe -ine 'Bazis.exe') { continue }\n  $offset=$end+2\n  $ptr=[Runtime.InteropServices.Marshal]::AllocHGlobal($bytes.Length-$offset)\n  try {\n   [Runtime.InteropServices.Marshal]::Copy($bytes,$offset,$ptr,$bytes.Length-$offset)\n   $path=New-Object Text.StringBuilder 32768\n   if ([BazisPidlPath]::SHGetPathFromIDListW($ptr,$path)) {\n    # Base64 avoids console codepage corruption for Romanian paths.\n    [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($path.ToString()))\n   }\n  } finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($ptr) }\n  break\n }\n} finally { if ($key) { $key.Dispose() } }\n";
            var ps = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
            var encoded = Buffer.from(psSource, 'utf16le').toString('base64');
            var raw = require('child_process').execFileSync(ps, ['-NoProfile','-NonInteractive','-EncodedCommand',encoded],
                {encoding:'utf8',windowsHide:true,timeout:10000,maxBuffer:65536,stdio:['ignore','pipe','pipe']}).trim();
            var candidate = Buffer.from(raw, 'base64').toString('utf8');
            if (candidate) {
                drawingName = recentDrawing(candidate, 90000);
                if (drawingName) {
                    folder = candidate; folderSource = 'Windows BAZIS Save dialog + cel mai recent BLN salvat in ultimele 90 secunde';
                }
            }
        } catch (folderException) { folderError = String(folderException.message || folderException); }
        if (!folder) {
            folder = system.askFolder('Folderul schitelor pentru tabelul placilor', '');
            if (!folder) return;
            folderSource = 'selectat explicit de utilizator';
            drawingName = recentDrawing(folder, 600000);
        }
        if (!fs.statSync(folder).isDirectory()) throw new Error('Destinatia nu este un folder existent.');
        var stamp = new Date().toISOString().replace(/[:.]/g, '-');
        var exportName = drawingName ? path.basename(drawingName, path.extname(drawingName)) :
            (modelFile ? path.basename(modelFile, path.extname(modelFile)) : 'Placi');
        // Inlocuieste numai caracterele interzise in numele de fisier Windows.
        exportName = exportName.replace(/[<>:"\/\\|?*\x00-\x1f]/g, '_').replace(/[. ]+$/, '') || 'Placi';
        var base = path.join(folder, exportName);
        // Preserve previous exports. First export has exactly the BLN basename.
        if (fs.existsSync(base + '.csv') || fs.existsSync(base + '.json'))
            base = path.join(folder, exportName + '_' + stamp + '_' + process.pid);
        // Citeste numai valori proprii simple; nu apeleaza getteri sau metode native necunoscute.
        var context = {cwd:process.cwd(), campuri:{}};
        function inspectContext(label, target) {
            if (!target) return;
            try {
                Object.getOwnPropertyNames(target).forEach(function (key) {
                    if (!/path|folder|file|directory|export|drawing|sketch|event/i.test(key)) return;
                    if (/token|secret|password|config/i.test(key)) return;
                    var d = Object.getOwnPropertyDescriptor(target, key);
                    if (d && typeof d.value === 'string' && d.value.length <= 2000)
                        context.campuri[label + '.' + key] = d.value;
                });
            } catch (_) {}
        }
        if (typeof global !== 'undefined') inspectContext('global', global);
        if (typeof Action !== 'undefined') inspectContext('Action', Action);
        if (typeof ModelFilename === 'string') context.model_filename = ModelFilename;
        var report = {versiune:6, data:new Date().toISOString(), model:str(get(Model, 'Name')), context_eveniment:context,
            desen_bln: drawingName, nume_export: exportName, sursa_nume: drawingName ? 'BLN recent' : 'numele modelului (BLN neidentificat)',
            folder_export:folder, sursa_folder:folderSource, diagnostic_folder:folderError,
            sursa_dimensiuni:'Contur X/Y original; cote Cubis = contur minus grosimea BAZIS a fiecarui cant aplicat, numai cand ClipPanel=true. Fara compensare suplimentara de prefrezare. Prima cota=X, a doua=Y; fara rotire.',
            numar_placi:rows.length, placi:rows};
        fs.writeFileSync(base + '.json', JSON.stringify(report, null, 2), {encoding:'utf8', flag:'wx'});
        var sides = ['Y_max','Y_min','X_min','X_max'];
        function edgeText(edges) {
            return edges.map(function (e) {
                return e.material + ' | grosime=' + str(e.grosime_mm) + ' mm | sub-taiere=' +
                    (e.sub_taiere === true ? 'DA' : e.sub_taiere === false ? 'NU' : 'necunoscut') +
                    ' | prefrezare=' + str(e.prefrezare_mm) + ' mm';
            }).join(' / ');
        }
        var lines = ['sep=;', ['Nr','Nume','Grup','Pozitie','Material','Contur X (mm)','Contur Y (mm)','Grosime (mm)',
            'Cant sus (Y_max local)','Cant jos (Y_min local)','Cant stanga (X_min local)','Cant dreapta (X_max local)',
            'Canturi pe alte segmente','Lungime Cubis (mm)','Latime Cubis (mm)','fibra','Directie fibra',
            'Verificare cote Cubis','Desemnare piesa (NU material)','Diagnostic desemnare material',
            'Desemnare material PAL (baza)','Stare citire material','Sursa desemnare material'].map(cell).join(';')];
        rows.forEach(function (r) {
            lines.push([r.nr,r.nume,r.grup,r.pozitie,r.material,
                String(r.contur_x_mm).replace('.', ','),String(r.contur_y_mm).replace('.', ','),
                String(r.grosime_mm).replace('.', ',')].concat(sides.map(function (side) {
                return edgeText(r.canturi.filter(function(e) { return e.latura_locala === side; }));
            })).concat([edgeText(r.canturi.filter(function(e) { return sides.indexOf(e.latura_locala)<0; })),
                r.cote_cubis.lungime_mm===null?'':String(r.cote_cubis.lungime_mm).replace('.',','),
                r.cote_cubis.latime_mm===null?'':String(r.cote_cubis.latime_mm).replace('.',','),
                r.fibra,r.detalii_fibra.descriere,r.cote_cubis.stare,
                r.diagnostic_material.desemnare_piesa,JSON.stringify(r.diagnostic_material.campuri_candidate),
                r.material_db.desemnare,r.material_db.stare,r.material_db.sursa]).map(cell).join(';'));
        });
        fs.writeFileSync(base + '.csv', '\uFEFF' + lines.join('\r\n') + '\r\n', {encoding:'utf8', flag:'wx'});
        var cubisMessage='', cubisSucceeded=true;
        ['Cubis','Komodo','Holver'].forEach(function(kind){
            try {
                if(!readerConfig || !readerConfig.node || !readerConfig.cubis_script)
                    throw Error('Lipseste configurarea locala pentru export.');
                var helper=kind==='Cubis'?readerConfig.cubis_script:
                    path.join(path.dirname(readerConfig.cubis_script),'export_'+kind.toLowerCase()+'.mjs');
                var destination=base+' '+kind+'.xlsx';
                var raw=require('child_process').execFileSync(readerConfig.node,
                    [helper,base+'.json',destination,readerConfig.python],
                    {encoding:'utf8',windowsHide:true,timeout:60000,maxBuffer:1024*1024,stdio:['ignore','pipe','pipe']});
                var outputLines=raw.trim().split(/\r?\n/),result=JSON.parse(outputLines[outputLines.length-1]);
                if(!result.ok) throw Error('Exportul Excel nu a confirmat reusita.');
                var written=Array.isArray(result.paths)&&result.paths.length?result.paths:[destination];
                written.forEach(function(file){
                    if(!fs.statSync(file).isFile()||fs.statSync(file).size===0)
                        throw Error('Fisierul Excel nu poate fi verificat pe disc: '+file);
                });
                cubisMessage+=kind+' REUSIT: '+written.join('\n')+'\nRanduri grupate: '+result.rows+'\n\n';
            } catch(error) {
                cubisSucceeded=false;
                var detail=error.stderr?String(error.stderr):String(error.message||error);
                cubisMessage+=kind+' CU PROBLEME: '+detail.slice(0,900)+'\n\n';
            }
        });
        var folderOpenError = '';
        try {
            var explorer = path.join(process.env.SystemRoot || 'C:\\Windows', 'explorer.exe');
            var folderProcess = require('child_process').spawn(explorer, [folder],
                {detached:true,windowsHide:true,stdio:'ignore'});
            folderProcess.on('error', function () { /* Export already saved; folder path is shown below. */ });
            folderProcess.unref();
        } catch (_) { folderOpenError = '\nFolderul nu a putut fi deschis automat.'; }
        alert((cubisSucceeded ? 'EXPORT CUBIS + KOMODO + HOLVER REUSIT\n\n' : 'EXPORT CU PROBLEME\n\n')+
            cubisMessage+'\n\nCSV si raport JSON salvate:\n'+base+
            (rows.length ? '' : '\nNu s-au gasit placi cu dimensiuni accesibile in acest context.')+folderOpenError);
    } catch (e) {
        alert('EXPORT OPRIT\n' + String(e && e.message || e));
    }
})();