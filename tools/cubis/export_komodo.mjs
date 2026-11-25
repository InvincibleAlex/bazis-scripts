import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {FileBlob,SpreadsheetFile,Workbook} from '@oai/artifact-tool';
import {isPalPanel,transformPanel} from './export_cubis.mjs';
import {groupedPlateRows,isDirectExecution} from './group_rows.mjs';
export function transformKomodo(p){
 const material=String(p.material||'').split('\r')[0];
 const original={...p,material_db:{desemnare:material},cote_cubis:{...p.cote_cubis,
  lungime_mm:Math.round(p.contur_x_mm*1000)/1000,latime_mm:Math.round(p.contur_y_mm*1000)/1000}};
 const row=transformPanel(original);
 row[10]=row[10].replace('scadere cant sub-taiere pe laturile exterioare','dimensiuni originale, fara scadere cant');
 return row;
}
async function main(){
 const [reportPath,out,python]=process.argv.slice(2),report=JSON.parse(await fs.readFile(reportPath,'utf8'));
 const rows=groupedPlateRows(report.placi.filter(isPalPanel),transformKomodo);
 if(!rows.length)throw Error('Nu exista panouri PAL pentru Komodo');
 const template='\\\\RG\\Bazis\\Sabloane Tabel\\Komodo.xlsx';
 const work=await fs.mkdtemp(path.join(os.tmpdir(),'bazis-komodo-'));
 const original=await SpreadsheetFile.importXlsx(await FileBlob.load(template));
 const before=await original.render({sheetName:'Sheet2',range:'A19:K24',scale:1,format:'png'});
 await fs.writeFile(path.join(work,'before.png'),new Uint8Array(await before.arrayBuffer()));
 const wb=Workbook.create(),sheet=wb.worksheets.add('Sheet2');
 sheet.getRange(`A20:K${19+rows.length}`).values=rows;
 wb.recalculate();
 const authored=path.join(work,`authored-${process.pid}.xlsx`),manifest=path.join(work,`manifest-${process.pid}.json`);
 await(await SpreadsheetFile.exportXlsx(wb)).save(authored);
 const touched=[];for(let r=20;r<20+rows.length;r++)for(const c of 'ABCDEFGHIJK')touched.push(c+r);
 await fs.writeFile(manifest,JSON.stringify({rows,touched:{Sheet2:touched},sheet_mapping:{Sheet2:'xl/worksheets/sheet1.xml'},size_piece_inputs:{sheet:'Sheet2',first_row:20,columns:'ABCDEFGHIJK',material:'B',notes:'K',resize_columns:true,wrap_material:false}}));
 const merged=spawnSync(python,[path.join(path.dirname(fileURLToPath(import.meta.url)),'preserve_komodo.py'),template,authored,manifest,out],{encoding:'utf8',windowsHide:true});
 if(merged.status!==0)throw Error(merged.stderr||merged.stdout||'Salvare Komodo esuata');
 const final=await SpreadsheetFile.importXlsx(await FileBlob.load(out));
 const preview=await final.render({sheetName:'Sheet2',range:`A19:K${Math.min(19+rows.length,25)}`,scale:1,format:'png'});
 await fs.writeFile(path.join(work,'result.png'),new Uint8Array(await preview.arrayBuffer()));
 await fs.unlink(authored);await fs.unlink(manifest);
 console.log(JSON.stringify({ok:true,path:out,rows:rows.length,pieces:report.placi.filter(isPalPanel).length,first_row:rows[0]}));
}
if(isDirectExecution(import.meta.url))main().catch(e=>{console.error(e.message);process.exitCode=1;});
