import path from 'node:path';
import {fileURLToPath} from 'node:url';
export function isDirectExecution(url){
 if(!process.argv[1])return false;
 let a=path.resolve(process.argv[1]),b=fileURLToPath(url);
 if(process.platform==='win32'){a=a.toLowerCase();b=b.toLowerCase();}
 return a===b;
}
// Aggregate a plate together with its native face layers. A layer stays directly
// below its own parent even when its material differs from the base material.
const codeOrder=new Intl.Collator('ro',{numeric:true,sensitivity:'base'});
export function comparePlateCodes(a,b){return codeOrder.compare(String(a??''),String(b??''));}
export function groupedPlateRows(panels,transform){
 const parents=[],byNumber=new Map(),groups=new Map(),bundles=[];
 for(const p of panels){
  if(p.tip==='dublura')continue;
  const entry={panel:p,layers:[]};parents.push(entry);
  if(p.nr!==undefined){if(byNumber.has(p.nr))throw Error('Numar placa duplicat: '+p.nr);byNumber.set(p.nr,entry);}
 }
 for(const p of panels)if(p.tip==='dublura'){
  const parent=byNumber.get(p.dublura_pentru_nr);
  if(!parent)throw Error('Dublura fara placa de baza: '+p.dublura_pentru_cod);
  parent.layers.push(p);
 }
 for(const {panel,layers} of parents){
  const rows=[transform(panel),...layers.map(transform)],key=JSON.stringify(rows);
  if(groups.has(key)){for(const row of groups.get(key))row[4]++;}
  else{groups.set(key,rows);bundles.push(rows);}
 }
 // Sort complete bundles, never individual layer rows. All suppliers use the
 // same natural ascending piece-code order, independent of material and size.
 bundles.sort((a,b)=>comparePlateCodes(a[0][0],b[0][0]));
 return bundles.flat();
}
