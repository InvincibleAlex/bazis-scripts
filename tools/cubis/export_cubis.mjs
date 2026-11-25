import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile,Workbook} from '@oai/artifact-tool';
import {groupedPlateRows,isDirectExecution} from './group_rows.mjs';
const [reportPath,outputPath,python]=process.argv.slice(2);
// CUBIS_TEMPLATE permite testarea pe o copie a sablonului.
const template=process.env.CUBIS_TEMPLATE||'\\\\RG\\Bazis\\Sabloane Tabel\\Cubis.xlsx';
// Sablonul are randurile 2-1000 preformatate (999 piese) si 10 locuri PAL / 10 ABS in "Date client".
const MAX_ROWS=999,MAX_PAL=10,MAX_ABS=10;
function requireValue(ok,message){if(!ok)throw Error(message);}
export function isPalPanel(p){return /\bpal\b/i.test(String(p.material||'').split('\r')[0]);}
export function transformPanel(p){
 const name=p.diagnostic_material?.desemnare_piesa;
 requireValue(typeof name==='string'&&name.length>0,`Piesa ${p.nume}: lipseste desemnarea`);
 const material=p.material_db?.desemnare;
 requireValue(material,`Piesa ${name}: desemnare PAL indisponibila. ${p.material_db?.stare||''}`);
 let x=p.cote_cubis?.lungime_mm,y=p.cote_cubis?.latime_mm,fibre=p.fibra;
 requireValue(Number.isFinite(x)&&x>0&&Number.isFinite(y)&&y>0,`Piesa ${name}: cote de taiere neconfirmate`);
 requireValue([0,1,2].includes(fibre),`Piesa ${name}: fibra neidentificata`);
 const bounding=p.cote_cubis?.foloseste_gabarit===true;
 const notes=bounding?['Gabarit; contur nedreptunghiular; scadere cant sub-taiere pe laturile exterioare']:[];
 if(p.observatii_export)notes.push(p.observatii_export);
 const swap=y>x, local={X_min:'X_min',X_max:'X_max',Y_min:'Y_min',Y_max:'Y_max'};
 if(swap){[x,y]=[y,x];if(fibre)fibre=3-fibre;
  Object.assign(local,{X_min:'Y_max',X_max:'Y_min',Y_min:'X_min',Y_max:'X_max'});}
 const edges={},conflicts=new Set();
 for(const e of p.canturi){
  const side=local[e.latura_locala];
  if(bounding&&!side){notes.push('Cant pe contur interior/oblic: '+(e.semn||'fara cod'));continue;}
  requireValue(side&&e.semn,`Piesa ${name}: latura sau desemnarea cantului indisponibila`);
  if(bounding&&edges[side]){
   if(edges[side]!==e.semn){conflicts.add(side);notes.push('Canturi diferite pe '+side+': '+edges[side]+' / '+e.semn);}
   continue;
  }
  requireValue(!edges[side],`Piesa ${name}: mai multe canturi pe aceeasi latura`);
  edges[side]=e.semn;
 }
 // Front/back run parallel to grain, even if grain follows the second dimension.
 // Rotation is clockwise; no mirror operation is performed.
 for(const side of conflicts)delete edges[side];
 const order=fibre===2?['X_max','X_min','Y_min','Y_max']:['Y_min','Y_max','X_min','X_max'];
 return [name,material,x,y,1,fibre,...order.map(k=>edges[k]||''),[...new Set(notes)].join('; ')];
}
// Row layout: [name, material, x, y, qty, fibre, front, back, left, right, notes].
export function distinctBands(rows){return [...new Set(rows.flatMap(r=>r.slice(6,10)).filter(Boolean))];}
export function drawingName(report){
 const base=f=>f?path.basename(f,path.extname(f)):'';
 return report.nume_export||base(report.desen_bln)||base(report.context_eveniment?.model_filename)||'Placi';
}
async function main(){
 const report=JSON.parse(await fs.readFile(reportPath,'utf8'));
 requireValue(report.numar_placi>0,'Modelul nu contine placi');
 const templateBook=await SpreadsheetFile.importXlsx(await FileBlob.load(template));
 function catalog(sheet){return templateBook.worksheets.getItem(sheet).getRange('A2:A'+(sheet==='PAL'?2000:3000)).values.flat().filter(v=>typeof v==='string'&&v);}
 const pal=catalog('PAL'),abs=catalog('ABS');
 const rows=groupedPlateRows(report.placi.filter(isPalPanel),transformPanel,{byMaterial:true});
 for(const row of rows){
  requireValue(pal.filter(v=>v===row[1]).length===1,`PAL lipsa sau duplicat in Cubis: ${row[1]}`);
  for(const sign of row.slice(6,10).filter(Boolean))requireValue(abs.filter(v=>v===sign).length===1,`ABS lipsa sau duplicat in Cubis: ${sign}`);
 }
 requireValue(rows.length>0,'Modelul nu contine panouri cu PAL in numele materialului');
 // Keep each PAL together; stable sort keeps model order inside a material.
 const firstSeen=new Map();rows.forEach(r=>{if(!firstSeen.has(r[1]))firstSeen.set(r[1],firstSeen.size);});
 const materials=[...firstSeen.keys()],bands=distinctBands(rows);
 requireValue(rows.length<=MAX_ROWS,`Sablonul Cubis are ${MAX_ROWS} randuri pregatite; modelul are ${rows.length}`);
 requireValue(materials.length<=MAX_PAL,`"Date client" are ${MAX_PAL} locuri PAL; modelul are ${materials.length}: ${materials.join(', ')}`);
 requireValue(bands.length<=MAX_ABS,`"Date client" are ${MAX_ABS} locuri ABS; modelul are ${bands.length}: ${bands.join(', ')}`);
 requireValue(!(await fs.stat(outputPath).catch(()=>null)),'Fisierul exista deja: '+outputPath);
 await writeWorkbook(rows,materials,bands,outputPath,drawingName(report));
 console.log(JSON.stringify({ok:true,path:outputPath,rows:rows.length,pieces:report.numar_placi,materials,bands,first_row:rows[0]}));
}
async function writeWorkbook(rows,materials,bands,outputPath,drawing){
 // Author only the input cells. The preservation helper merges them into the
 // untouched native template; Excel recalculates its interactive dropdown formulas.
 // Recalculating CELL/INDIRECT/full-column helpers after each write is prohibitively slow.
 const wb=Workbook.create();wb.worksheets.add('Formular');wb.worksheets.add('Date client');
 const touched={Formular:[], 'Date client':[]};
 const form=wb.worksheets.getItem('Formular');
 console.error('Cubis: completare formular...');
 form.getRange(`A2:K${rows.length+1}`).values=rows;
 for(let r=2;r<=rows.length+1;r++)for(const c of 'ABCDEFGHIJK')touched.Formular.push(c+r);
 const client=wb.worksheets.getItem('Date client');
 const clientMaterials=client.getRange('E5:E26').values.map(row=>[row[0]]);
 for(let i=0;i<10;i++){
  clientMaterials[i]=[materials[i]||null];
  clientMaterials[12+i]=[bands[i]||null];
  touched['Date client'].push('E'+(5+i),'E'+(17+i));
 }
 client.getRange('E5:E26').values=clientMaterials;
 client.getRange('B10').values=[[drawing]];touched['Date client'].push('B10');
 console.error('Cubis: date completate; recalculare...');
 wb.recalculate();
 console.error('Cubis: recalculare terminata; previzualizare...');
 const work=await fs.mkdtemp(path.join(os.tmpdir(),'bazis-cubis-'));
 const preview=await wb.render({sheetName:'Formular',range:`A1:L${Math.min(rows.length+1,8)}`,scale:1,format:'png'});
 await fs.writeFile(path.join(work,'result.png'),new Uint8Array(await preview.arrayBuffer()));
 const tmp=path.join(work,'authored-'+process.pid+'.xlsx'),manifest=path.join(work,'manifest-'+process.pid+'.json');
 await (await SpreadsheetFile.exportXlsx(wb)).save(tmp);
 await fs.writeFile(manifest,JSON.stringify({touched,rows,materials,bands,size_piece_inputs:{sheet:'Formular',first_row:2,columns:'ABCDEFGHIJK',material:'B',notes:'K'}}));
 const repair=spawnSync(python,[path.join(path.dirname(fileURLToPath(import.meta.url)),'preserve_template.py'),template,tmp,manifest,outputPath],{encoding:'utf8',windowsHide:true});
 if(repair.status!==0)throw Error(repair.stderr||repair.stdout||'Pastrarea sablonului a esuat');
 await fs.unlink(tmp);await fs.unlink(manifest);
}
if(isDirectExecution(import.meta.url))main().catch(e=>{console.error(e.message);process.exitCode=1;});
