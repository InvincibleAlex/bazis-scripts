// Aggregate a plate together with its native face layers. A layer stays directly
// below its own parent even when its material differs from the base material.
export function groupedPlateRows(panels,transform,{byMaterial=false}={}){
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
 if(byMaterial){
  const order=new Map();for(const rows of bundles)if(!order.has(rows[0][1]))order.set(rows[0][1],order.size);
  bundles.sort((a,b)=>order.get(a[0][1])-order.get(b[0][1]));
 }
 return bundles.flat();
}
