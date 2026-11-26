import assert from 'node:assert/strict';
import {groupedPlateRows,comparePlateCodes} from '../tools/cubis/group_rows.mjs';
const panel=(nr,code,material)=>({nr,material,diagnostic_material:{desemnare_piesa:code}});
const inputs=[panel(1,'00.01.02.00.003','A'),panel(2,'00.01.01.01.005','Z'),panel(3,'00.01.02.00.001','B'),panel(4,'00.01.02.00.002','A'),panel(5,'P10','A'),panel(6,'P2','B'),panel(7,'00.01.02.00.001','B')];
inputs.splice(0,0,{...panel(8,'Dublură pentru 00.01.02.00.001','Other material'),tip:'dublura',dublura_pentru_nr:3});
inputs.push({...panel(9,'Dublură pentru 00.01.02.00.001','Other material'),tip:'dublura',dublura_pentru_nr:7});
const snapshot=JSON.stringify(inputs);
const transform=p=>[p.diagnostic_material.desemnare_piesa,p.material,100,50,1,0,'','','','',''];
const expected=['00.01.01.01.005','00.01.02.00.001','Dublură pentru 00.01.02.00.001','00.01.02.00.002','00.01.02.00.003','P2','P10'];
for(const options of [undefined,{byMaterial:true},{byMaterial:false}]){
 const rows=groupedPlateRows(inputs,transform,options);
 assert.deepEqual(rows.map(r=>r[0]),expected);
 assert.equal(rows[1][4],2);assert.equal(rows[2][4],2);
 assert.equal(rows.reduce((n,r)=>n+r[4],0),inputs.length);
}
assert.equal(JSON.stringify(inputs),snapshot);
assert(comparePlateCodes('00.2','00.10')<0);
assert(comparePlateCodes('P9','P10')<0);
// The supplier material/size mapping cannot affect the shared code ordering.
assert.deepEqual(groupedPlateRows(inputs,p=>{const r=transform(p);r[1]='supplier '+p.material;r[2]=97;return r;}).map(r=>r[0]),expected);
console.log('PASS: natural ascending codes across suppliers and materials; layers adjacent, quantities and original input preserved');
