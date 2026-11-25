import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {SpreadsheetFile,Workbook} from '@oai/artifact-tool';
import {isPalPanel,distinctBands,drawingName} from './export_cubis.mjs';
import {transformKomodo} from './export_komodo.mjs';
import {groupedPlateRows,isDirectExecution} from './group_rows.mjs';
// HOLVER_TEMPLATE permite testarea pe o copie a sablonului.
const template=process.env.HOLVER_TEMPLATE||'\\\\RG\\Bazis\\Sabloane Tabel\\Holver.xlsx';
// Foaia "general": randuri piese 18-1016 (999); legenda "Tip de cant" are 8 locuri (F10:F13 = 1-4, I10:I13 = 5-8).
// Peste 8 tipuri de cant: codul se scrie direct in celula (formula din foaia Export il preia neschimbat).
const FIRST=18,MAX_ROWS=999,LEGEND=['F10','F11','F12','F13','I10','I11','I12','I13'];
// Same rules as Komodo (original contour, BAZIS material name, edge codes), plus thickness.
export function holverRow(p){return [...transformKomodo(p),p.grosime_mm];}
// Holver: Lungime = directia fibrei (fata/spate paralele cu fibra). Fibra pe a doua cota => cotele se inverseaza;
// ordinea canturilor din Komodo are deja fata/spate paralele cu fibra.
// Coloana Fibra: necompletat = fara rotire, orice valoare = rotire permisa (piesa fara fibra).
export function holverCells(row,band){
 const [name,material,x,y,qty,fibre,front,back,left,right,notes,thickness]=row;
 const [length,width]=fibre===2?[y,x]:[x,y];
 return {F:material,G:thickness,H:name,I:qty,J:length,K:width,L:fibre===0?1:null,
  M:band(front),N:band(back),O:band(left),P:band(right),Q:notes||null};
}
async function writeWorkbook(rows,bands,drawing,outputPath,python){
 const wb=Workbook.create(),sheet=wb.worksheets.add('general'),touched=[];
 function put(address,value){
  if(value===null||value===undefined||value==='')return;
  sheet.getRange(address).values=[[value]];touched.push(address);
 }
 const band=code=>{if(!code)return null;const i=bands.indexOf(code);return i<LEGEND.length?i+1:code;};
 rows.forEach((row,i)=>{for(const [col,value] of Object.entries(holverCells(row,band)))put(col+(FIRST+i),value);});
 bands.slice(0,LEGEND.length).forEach((code,i)=>put(LEGEND[i],code));
 put('I8',drawing);
 const work=await fs.mkdtemp(path.join(os.tmpdir(),'bazis-holver-'));
 const authored=path.join(work,`authored-${process.pid}.xlsx`),manifest=path.join(work,`manifest-${process.pid}.json`);
 await(await SpreadsheetFile.exportXlsx(wb)).save(authored);
 await fs.writeFile(manifest,JSON.stringify({rows,touched:{general:touched},sheet_mapping:{general:'xl/worksheets/sheet1.xml'},size_piece_inputs:{sheet:'general',first_row:18,columns:'FGHIJKLMNOPQ',material:'F',notes:'Q',resize_columns:false}}));
 const merged=spawnSync(python,[path.join(path.dirname(fileURLToPath(import.meta.url)),'preserve_template.py'),template,authored,manifest,outputPath],{encoding:'utf8',windowsHide:true});
 if(merged.status!==0)throw Error(merged.stderr||merged.stdout||'Salvare Holver esuata');
 await fs.unlink(authored);await fs.unlink(manifest);
}
async function main(){
 const [reportPath,out,python]=process.argv.slice(2),report=JSON.parse(await fs.readFile(reportPath,'utf8'));
 const rows=groupedPlateRows(report.placi.filter(isPalPanel),holverRow);
 if(!rows.length)throw Error('Nu exista panouri PAL pentru Holver');
 if(rows.length>MAX_ROWS)throw Error(`Sablonul Holver are ${MAX_ROWS} randuri pregatite; modelul are ${rows.length}`);
 if(await fs.stat(out).catch(()=>null))throw Error('Fisierul exista deja: '+out);
 await writeWorkbook(rows,distinctBands(rows),drawingName(report),out,python);
 console.log(JSON.stringify({ok:true,path:out,rows:rows.length,pieces:report.placi.filter(isPalPanel).length,first_row:rows[0]}));
}
if(isDirectExecution(import.meta.url))main().catch(e=>{console.error(e.message);process.exitCode=1;});
