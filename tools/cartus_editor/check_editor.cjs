const assert=require('node:assert/strict'),T=require('./editor.js');
const measure=(text,font)=>text.length*font*.55;
const original=T.defaults(),model=T.layout(original,measure);
assert.equal(model.left+model.width,200);assert.equal(model.top+model.height,287);
assert.equal(model.drawing.y,10);assert.equal(model.drawing.height+model.drawing.y+10,model.top);
const long=T.clone(original);long.parameters[0].value='Proiect mobilier '+ 'foarte lung '.repeat(30);
const expanded=T.layout(long,measure);assert.equal(expanded.width,190);assert(expanded.height>model.height);
for(const row of expanded.rows){assert(Math.abs(row.cells.reduce((n,c)=>n+c.width,0)-expanded.width)<1e-8);for(const cell of row.cells)for(const line of cell.lines)assert(measure(line,cell.font)<=cell.width-2*long.block.padding+1e-8);}
assert.equal(original.parameters[0].value,'Proiect mobilier');
const margins=T.clone(original);margins.page.margins={left:20,right:15,top:12,bottom:18};const moved=T.layout(margins,measure);assert.equal(moved.left+moved.width,195);assert.equal(moved.top+moved.height,279);
const unsafe=T.clone(original);unsafe.rows[0].cells[0].text='<script>alert("x")</script>';const svg=T.svg(T.layout(unsafe,measure),null);assert(!svg.includes('<script>'));assert(svg.includes('&lt;script&gt;'));
const invalid=T.clone(original);invalid.page.margins.left=205;assert.throws(()=>T.layout(invalid,measure));
const duplicate=T.clone(original);duplicate.parameters.push(duplicate.parameters[0]);assert.throws(()=>T.validate(duplicate));
const roundtrip=T.validate(JSON.parse(JSON.stringify(long)));assert.deepEqual(roundtrip,long);
console.log('PASS: margins in mm, anchored dynamic width, readable wrapping, schema round-trip and invalid-template guards');
