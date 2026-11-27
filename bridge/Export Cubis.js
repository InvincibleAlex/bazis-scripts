// Test read-only pentru BAZIS 2022 / Node 8. Nu necesita MCP.
// Contur local + cote Cubis: minus adaosul Cubis (2 -> 1.5 mm, 0.8 -> 0.3 mm, restul neschimbat) pe fiecare latura cantuita, pentru dreptunghiuri.
(function () {
    'use strict';
    var exportLog=null,exportState=null;
    function exportStatus(message){if(exportLog)fs.appendFileSync(exportLog,new Date().toLocaleTimeString()+' | '+message+'\n','utf8');}
    try {
        var fs = require('fs'), path = require('path'), os = require('os');
        var commonRoot=path.join('\\\\RG\\Bazis\\Scripts','Export Tabele');
        if(typeof __dirname==='string'&&fs.existsSync(path.join(__dirname,'Export Tabele','runtime.json')))
            commonRoot=path.join(__dirname,'Export Tabele');
        var consoleScript=path.join(commonRoot,'progress_console.ps1');
        if(!fs.existsSync(consoleScript))throw Error('Lipseste consola comuna: '+consoleScript);
        exportLog=path.join(os.tmpdir(),'bazis-tabele-'+process.pid+'-'+Date.now()+'.log');exportState=exportLog+'.state';
        fs.writeFileSync(exportLog,'Pornire export tabele...\n','utf8');
        function psText(value){return "[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+Buffer.from(value,'utf8').toString('base64')+"'))";}
        var terminal="& ("+psText(consoleScript)+") -LogPath ("+psText(exportLog)+") -StatePath ("+psText(exportState)+")";
        var encoded=Buffer.from(terminal,'utf16le').toString('base64');
        var launcher="$ErrorActionPreference='Stop'; Start-Process -FilePath 'powershell.exe' -WindowStyle Normal -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand','"+encoded+"'); $ack="+psText(exportState+'.opened')+"; $until=[DateTime]::UtcNow.AddSeconds(12); while(!(Test-Path -LiteralPath $ack) -and [DateTime]::UtcNow -lt $until){Start-Sleep -Milliseconds 100}; if(!(Test-Path -LiteralPath $ack)){throw 'Terminalul de progres nu a pornit.'}";
        require('child_process').execFileSync('powershell.exe',['-NoProfile','-EncodedCommand',Buffer.from(launcher,'utf16le').toString('base64')],{stdio:'ignore',windowsHide:true,timeout:15000});
        exportStatus('Citire placi si dubluri din modelul BAZIS...');
        if (typeof Model === 'undefined' || !Model) throw new Error('Model nu este disponibil in acest context/eveniment.');
        function get(o, k) { try { return o[k]; } catch (_) { return undefined; } }
        function num(v) { return typeof v === 'number' && isFinite(v) && v > 0; }
        // Use the same contour dimensions for all three tables. Snap only tiny
        // differences from whole millimetres; retain other fractional dimensions.
        // Raw native values remain in contur_bazis_brut for audit.
        function exportDimension(v) {
            var whole=Math.round(v);
            return whole>0 && Math.abs(v-whole)<0.01 ? whole : v;
        }
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
        function nativeLayers(panel) {
            var list=get(panel,'Plastics'),n=get(list,'Count'),out=[];
            if(list===undefined||list===null)return out;
            if(typeof n!=='number'||n<0||n>100||n!==Math.floor(n))throw Error('Lista nativa de straturi invalida');
            var items=get(list,'Plastics')||get(list,'Items')||list;
            for(var i=0;i<n;i++){
                var layer=get(items,i);if(!layer)throw Error('Strat BAZIS indisponibil: '+i);
                out.push({index:i,material:str(get(layer,'Material')),grosime_mm:get(layer,'Thickness'),
                    fata:get(layer,'Side'),orientare_fibra:get(layer,'TextureOrientation'),sursa:'BAZIS panel.Plastics'});
            }
            return out;
        }
        // Cubis cutting allowance differs from the physical edging thickness.
        // Keep native thicknesses intact for material matching and other suppliers.
        function cubisEdgeDeduction(thickness) {
            if(Math.abs(thickness-2)<0.000001)return 1.5;
            if(Math.abs(thickness-0.8)<0.000001)return 0.3;
            return thickness;
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
                        else deduction[side]=Math.max(deduction[side]||0,cubisEdgeDeduction(e.grosime_mm));
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
                else used[side]=e.sub_taiere ? cubisEdgeDeduction(e.grosime_mm) : 0;
            });
            var dx=(used.X_min||0)+(used.X_max||0);
            var dy=(used.Y_min||0)+(used.Y_max||0);
            if(w-dx<=0||h-dy<=0)issues.push('cota rezultata nepozitiva');
            return {lungime_mm:issues.length?null:Math.round((w-dx)*1000)/1000,
                latime_mm:issues.length?null:Math.round((h-dy)*1000)/1000,
                scadere_x_mm:dx,scadere_y_mm:dy,stare:issues.length?issues.join('; '):'OK - scadere cant conform regulii Cubis'};
        }
        var rows = [], seen = new WeakSet(), stack = [{o:Model, parent:''}], visited = 0;
        while (stack.length) {
            var item = stack.pop(), o = item.o;
            if (!o || (typeof o !== 'object' && typeof o !== 'function') || seen.has(o)) continue;
            seen.add(o);
            if (++visited > 100000) throw new Error('Limita de 100000 obiecte depasita; exportul a fost oprit.');
            if(visited%100===0&&typeof exportStatus==='function')exportStatus('Citite '+visited+' obiecte; '+rows.length+' placi si dubluri');
            var w = get(o, 'ContourWidth'), h = get(o, 'ContourHeight'), t = get(o, 'Thickness');
            var name = str(get(o, 'Name'));
            if (num(w) && num(h) && num(t) && /\b(?:pal|blat)\b/i.test(str(get(o, 'MaterialName')).split('\r')[0])) {
                var rawW=w, rawH=h;
                w=exportDimension(w); h=exportDimension(h);
                var edges=edgeData(o), fibre=fibreData(o), cubis=cubisDimensions(o,w,h,edges);
                var baseRow={
                nr:rows.length + 1, nume:name, grup:item.parent,
                pozitie:str(get(o, 'ArtPos')), material:str(get(o, 'MaterialName')),
                contur_x_mm:w, contur_y_mm:h, grosime_mm:t, canturi:edges, fibra:fibre.cod,
                contur_bazis_brut:{x_mm:rawW,y_mm:rawH},
                normalizare_cote:{toleranta_mm:0.01,spre_mm_intreg:true,modificat:w!==rawW||h!==rawH},
                detalii_fibra:fibre, cote_cubis:cubis, diagnostic_material:materialProbe(o), material_db:null,
                straturi_native:nativeLayers(o)
                };
                rows.push(baseRow);
                baseRow.straturi_native.forEach(function(layer){
                    // Native face layers follow the panel contour. Bands belong
                    // to the assembled panel and must not be ordered twice.
                    if(!/\b(?:pal|blat)\b/i.test(layer.material.split('\r')[0]))return;
                    if(!num(layer.grosime_mm))throw Error('Grosime dublura indisponibila pentru '+baseRow.diagnostic_material.desemnare_piesa);
                    var code=baseRow.diagnostic_material.desemnare_piesa,label='Dublur\u0103 pentru '+code;
                    var lf=fibreData({TextureOrientation:layer.orientare_fibra});
                    rows.push({nr:rows.length+1,nume:label,grup:baseRow.grup,pozitie:baseRow.pozitie,
                        material:layer.material,grosime_mm:layer.grosime_mm,contur_x_mm:w,contur_y_mm:h,
                        contur_bazis_brut:{x_mm:rawW,y_mm:rawH},canturi:[],fibra:lf.cod,detalii_fibra:lf,
                        cote_cubis:{lungime_mm:cubis.lungime_mm,latime_mm:cubis.latime_mm,
                            scadere_x_mm:cubis.scadere_x_mm,scadere_y_mm:cubis.scadere_y_mm,
                            foloseste_gabarit:cubis.foloseste_gabarit,stare:cubis.stare},
                        diagnostic_material:{desemnare_piesa:label,nume_material:layer.material},material_db:null,
                        tip:'dublura',dublura_pentru_nr:baseRow.nr,dublura_pentru_cod:code,
                        strat_index:layer.index,fata:layer.fata,sursa:'BAZIS panel.Plastics',
                        observatii_export:'Lipire pe '+code+'; canturile sunt ale ansamblului, trecute numai la placa de baza.'});
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
        exportStatus('Citire model terminata: '+rows.length+' placi si dubluri. Verific materialele in baza de date...');
        try {
            var commonRoot=path.join('\\\\RG\\Bazis\\Scripts','Export Tabele');
            if(typeof __dirname==='string'&&fs.existsSync(path.join(__dirname,'Export Tabele','runtime.json')))
                commonRoot=path.join(__dirname,'Export Tabele');
            var packageConfig=JSON.parse(fs.readFileSync(path.join(commonRoot,'runtime.json'),'utf8'));
            var readerConfig={python:path.resolve(commonRoot,packageConfig.python),node:path.resolve(commonRoot,packageConfig.node),
                script:path.resolve(commonRoot,packageConfig.material_reader),cubis_script:path.resolve(commonRoot,packageConfig.cubis_script)};
            ['python','node','script','cubis_script'].forEach(function(k){if(!fs.existsSync(readerConfig[k]))throw Error('Lipseste componenta comuna: '+readerConfig[k]);});
            var dbOutput=require('child_process').execFileSync(readerConfig.python,[readerConfig.script],{
                input:JSON.stringify(rows.map(function(r){return {material:r.material,thickness_mm:r.grosime_mm};})),
                encoding:'utf8',windowsHide:true,timeout:45000,maxBuffer:8*1024*1024,stdio:['pipe','pipe','pipe']});
            var dbResult=JSON.parse(dbOutput);
            if(!dbResult.ok)throw Error(dbResult.error||'Citirea bazei a esuat');
            if(!Array.isArray(dbResult.materials) || dbResult.materials.length!==rows.length)throw Error('Raspuns Firebird invalid');
            rows.forEach(function(r,i){r.material_db=dbResult.materials[i];});
            exportStatus('Citire baza de date reusita.');
        } catch(dbError) {
            var dbFailure=String(dbError.message||dbError);
            try{if(dbError.stdout)dbFailure=JSON.parse(String(dbError.stdout)).error||dbFailure;}catch(ignore){}
            rows.forEach(function(r){r.material_db={desemnare:null,sursa:'Firebird direct',
                stare:dbFailure.slice(0,500)};});
            exportStatus('PROBLEMA baza de date: '+dbFailure.slice(0,500));
        }
        exportStatus('Identific folderul si numele fisierelor de export...');
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
        // Successful runs remove diagnostics, so check the Excel outputs too.
        function exportBaseExists(candidate) {
            if (fs.existsSync(candidate+'.csv') || fs.existsSync(candidate+'.json')) return true;
            return ['Cubis','Komodo','Holver'].some(function(kind){return fs.existsSync(candidate+' '+kind+'.xlsx');});
        }
        if (exportBaseExists(base)) {
            base = path.join(folder, exportName + '_' + stamp + '_' + process.pid);
            var suffix=1, uniqueBase=base;
            while(exportBaseExists(base))base=uniqueBase+'_'+suffix++;
        }
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
        var report = {versiune:7, data:new Date().toISOString(), model:str(get(Model, 'Name')), context_eveniment:context,
            desen_bln: drawingName, nume_export: exportName, sursa_nume: drawingName ? 'BLN recent' : 'numele modelului (BLN neidentificat)',
            folder_export:folder, sursa_folder:folderSource, diagnostic_folder:folderError,
            sursa_dimensiuni:'Contur X/Y BAZIS, normalizat la mm intreg numai pentru abateri sub 0.01 mm; valori native pastrate in contur_bazis_brut. Cote Cubis = contur normalizat minus adaosul Cubis (2 -> 1.5 mm, 0.8 -> 0.3 mm, restul neschimbat) al fiecarui cant aplicat, numai cand ClipPanel=true. Komodo/Holver = contur normalizat fara scadere cant. Fara compensare suplimentara de prefrezare. Prima cota=X, a doua=Y; fara rotire.',
            numar_placi:rows.length,numar_placi_baza:rows.filter(function(r){return r.tip!=='dublura';}).length,
            numar_dubluri:rows.filter(function(r){return r.tip==='dublura';}).length, placi:rows};
        fs.writeFileSync(base + '.json', JSON.stringify(report, null, 2), {encoding:'utf8', flag:'wx'});
        exportStatus('Raport JSON salvat: '+base+'.json');
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
        exportStatus('CSV salvat. Incep generarea tabelelor Excel.');
        var cubisMessage='', cubisSucceeded=true;
        ['Cubis','Komodo','Holver'].forEach(function(kind){
            exportStatus(kind+': generare Excel...');
            try {
                if(!readerConfig || !readerConfig.node || !readerConfig.cubis_script)
                    throw Error('Lipseste pachetul comun Export Tabele de langa script.');
                var helper=kind==='Cubis'?readerConfig.cubis_script:
                    path.join(path.dirname(readerConfig.cubis_script),'export_'+kind.toLowerCase()+'.mjs');
                var destination=base+' '+kind+'.xlsx';
                var raw=require('child_process').execFileSync(readerConfig.node,
                    [helper,base+'.json',destination,readerConfig.python],
                    {encoding:'utf8',windowsHide:true,timeout:180000,maxBuffer:1024*1024,stdio:['ignore','pipe','pipe']});
                var outputLines=raw.trim().split(/\r?\n/),result=JSON.parse(outputLines[outputLines.length-1]);
                if(!result.ok) throw Error('Exportul Excel nu a confirmat reusita.');
                var written=Array.isArray(result.paths)&&result.paths.length?result.paths:[destination];
                written.forEach(function(file){
                    if(!fs.statSync(file).isFile()||fs.statSync(file).size===0)
                        throw Error('Fisierul Excel nu poate fi verificat pe disc: '+file);
                });
                cubisMessage+=kind+' REUSIT: '+written.join('\n')+'\nRanduri grupate: '+result.rows+'\n\n';
                exportStatus(kind+' REUSIT: '+result.rows+' randuri | '+written.join(' | '));
            } catch(error) {
                cubisSucceeded=false;
                var detail=error.stderr?String(error.stderr):String(error.message||error);
                cubisMessage+=kind+' CU PROBLEME: '+detail.slice(0,900)+'\n\n';
                exportStatus(kind+' EROARE: '+detail.slice(0,900));
            }
        });
        // Only this run's diagnostics are removed, after all three verified exports.
        var diagnosticMessage='CSV si raport JSON pastrate pentru depanare:\n'+base;
        if(cubisSucceeded) {
            var diagnosticFiles=[base+'.json',base+'.csv'], diagnosticCopies=[];
            try {
                diagnosticCopies=diagnosticFiles.map(function(file){return fs.readFileSync(file);});
                diagnosticFiles.forEach(function(file){fs.unlinkSync(file);});
                diagnosticMessage='';
                exportStatus('Toate tabelele sunt verificate. JSON si CSV eliminate.');
            } catch(cleanupError) {
                // Restore an already removed file if the other file was locked.
                diagnosticFiles.forEach(function(file,index){
                    if(diagnosticCopies[index] && !fs.existsSync(file)) {
                        try{fs.writeFileSync(file,diagnosticCopies[index],{flag:'wx'});}catch(restoreError){exportStatus('Restaurare diagnostic nereusita: '+file);}
                    }
                });
                diagnosticMessage='Tabelele au reusit, dar curatarea JSON/CSV nu s-a incheiat. Verificati fisierele:\n'+base;
                exportStatus('Curatare diagnostic nereusita: '+String(cleanupError.message||cleanupError));
            }
        }
        var folderOpenError = '';
        try {
            var explorer = path.join(process.env.SystemRoot || 'C:\\Windows', 'explorer.exe');
            var folderProcess = require('child_process').spawn(explorer, [folder],
                {detached:true,windowsHide:true,stdio:'ignore'});
            folderProcess.on('error', function () { /* Export already saved; folder path is shown below. */ });
            folderProcess.unref();
        } catch (_) { folderOpenError = '\nFolderul nu a putut fi deschis automat.'; }
        exportStatus('Folder rezultate: '+folder);
        fs.writeFileSync(exportState,cubisSucceeded?'done':'error','utf8');
        alert((cubisSucceeded ? 'EXPORT CUBIS + KOMODO + HOLVER REUSIT\n\n' : 'EXPORT CU PROBLEME\n\n')+
            cubisMessage+(diagnosticMessage?'\n\n'+diagnosticMessage:'')+
            (rows.length ? '' : '\nNu s-au gasit placi cu dimensiuni accesibile in acest context.')+folderOpenError);
    } catch (e) {
        try{exportStatus('EXPORT OPRIT: '+String(e&&e.message||e));if(exportState)fs.writeFileSync(exportState,'error','utf8');}catch(ignore){}
        alert('EXPORT OPRIT\n' + String(e && e.message || e));
    }
})();
