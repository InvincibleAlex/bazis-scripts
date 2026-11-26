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

function invariant(state){
 const v=T.validate(state),g=T.grid(v);assert(g.every(row=>row.every(Boolean)));
 const m=T.layout(v,measure),cells=m.rows.flatMap(row=>row.cells);
 for(let i=0;i<cells.length;i++)for(let j=i+1;j<cells.length;j++){
  const a=cells[i],b=cells[j];assert(a.x+a.width<=b.x+1e-7||b.x+b.width<=a.x+1e-7||a.y+a.height<=b.y+1e-7||b.y+b.height<=a.y+1e-7,'Cells overlap');
 }
 for(const cell of cells)assert(cell.height+1e-8>=cell.needed);
 return m;
}
let spans=T.logoPreset(T.defaults());const logoModel=invariant(spans);
assert.equal(logoModel.rows[0].cells[0].height,logoModel.rows.reduce((n,r)=>n+r.height,0));
assert.equal(logoModel.rows[1].cells[0].x,logoModel.rows[0].cells[0].x+logoModel.rows[0].cells[0].width);
assert.equal(T.grid(spans)[2][0].row,0);
T.unmerge(spans,0,0);invariant(spans);assert.equal(spans.rows[1].cells[0].col,0);
T.merge(spans,0,0,1,3);invariant(spans);assert.equal(T.grid(spans)[2][0].cell.rowSpan,3);
T.split(spans,0,0,'vertical');invariant(spans);
T.split(spans,0,0,'horizontal');invariant(spans);
T.insertRow(spans,1);invariant(spans);T.removeRow(spans,1);invariant(spans);
T.insertColumn(spans,1);invariant(spans);T.removeColumn(spans,1);invariant(spans);
let single=T.logoPreset(T.defaults());T.removeRow(single,0);invariant(single);assert.equal(single.rows[0].cells[0].rowSpan,2);
let partial=T.logoPreset(T.defaults());assert.throws(()=>T.merge(partial,0,0,2,3),/taie/);
let longSpan=T.logoPreset(T.defaults());longSpan.rows[0].cells[0].logo=false;longSpan.rows[0].cells[0].text='Text foarte lung '.repeat(60);invariant(longSpan);
const legacy=JSON.parse(require('fs').readFileSync(require('path').join(__dirname,'cartus-initial.json'),'utf8'));
const migrated=T.validate(legacy);assert.equal(migrated.schema,2);invariant(migrated);
assert.deepEqual(T.validate(JSON.parse(JSON.stringify(spans))),spans);
const overlap=T.logoPreset(T.defaults());overlap.rows[1].cells.push({col:0,colSpan:1,rowSpan:1,text:'',font:2,align:'left'});assert.throws(()=>T.validate(overlap),/suprapun/);
console.log('PASS: 3-row logo, grid migration, merging, splitting, row/column insertion and removal, long-text height and no overlaps');

const imageOnly=T.logoPreset(T.defaults());
imageOnly.logo='data:image/png;base64,iVBORw0KGgo=';
let imageModel=T.layout(imageOnly,measure),imageCell=imageModel.rows[0].cells[0];
assert.deepEqual(T.mediaBox(imageCell,imageOnly.block.padding),{x:imageCell.x,y:imageCell.y,width:imageCell.width,height:imageCell.height});
assert(T.svg(imageModel,null).includes('preserveAspectRatio="xMidYMid meet"'));
imageOnly.rows[0].cells[0].text='Firma mea\n{client}';
imageModel=invariant(imageOnly);imageCell=imageModel.rows[0].cells[0];
const media=T.mediaBox(imageCell,imageOnly.block.padding);
assert.equal(media.width,imageCell.width);assert(media.height>0);assert(media.height<imageCell.height);
assert(media.y+media.height<=imageCell.y+imageCell.height-imageCell.lines.length*imageCell.font*1.25);
const combinedSvg=T.svg(imageModel,null);assert(combinedSvg.includes('<image'));assert(combinedSvg.includes('Firma mea'));assert(combinedSvg.includes('Client'));
console.log('PASS: logo uses full cell with proportional fit; optional caption has separate non-overlapping space');
