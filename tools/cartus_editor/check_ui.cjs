// Exercise event wiring against the actual HTML controls without a browser dependency.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(require('path').join(__dirname,'Editor cartus.html'),'utf8');
class Element{
 constructor(){this.value='';this.checked=false;this.disabled=false;this.children=[];this.tagName='DIV';}
 append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}add(item){this.children.push(item);}
 querySelector(){return {setAttribute(){}};}click(){this.onclick?.();}
 getContext(){return {font:'',measureText(text){return {width:text.length*1.1};}};}
}
const elements=new Map([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new Element()]));
elements.get('showValues').checked=true;elements.get('guides').checked=true;elements.get('zoom').value='page';
const storage=new Map(),document={activeElement:{tagName:'BODY'},head:new Element(),addEventListener(){},
 getElementById(id){if(id==='printSize')return null;assert(elements.has(id),'Missing HTML control '+id);return elements.get(id);},createElement(){return new Element();}};
const ctx={document,localStorage:{getItem:key=>storage.get(key),setItem:(key,v)=>storage.set(key,v)},Option:class{constructor(text,value){this.text=text;this.value=value;}},confirm:()=>true,console,Date,Blob,URL,setTimeout,window:{print(){}}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(require('path').join(__dirname,'editor.js'),'utf8'),ctx);
const state=()=>JSON.parse(storage.get('bazis-titleblock-v1'));
assert.equal(state().schema,2);
elements.get('presetLogo').click();assert.equal(state().rows[0].cells[0].rowSpan,3);assert.equal(elements.get('zoom').value,'block');
elements.get('splitV').click();assert.equal(state().columns.length,5);
elements.get('undo').click();assert.equal(state().columns.length,4);assert.equal(state().rows[0].cells[0].rowSpan,3);
elements.get('redo').click();assert.equal(state().columns.length,5);
elements.get('unmerge').click();assert.equal(state().rows[0].cells[0].rowSpan,1);
elements.get('rowSpan').value=3;elements.get('rowSpan').onchange();assert.equal(state().rows[0].cells[0].rowSpan,3);
elements.get('preview').onclick({target:{closest:()=>({dataset:{row:'1',cell:'0'}})}});
assert(elements.get('selectionTitle').textContent.includes('Rând 2'));
elements.get('text').value='Număr: {pagina}';elements.get('text').oninput();assert.equal(state().rows[1].cells[0].text,'Număr: {pagina}');
elements.get('addRow').click();assert.equal(state().rows.length,4);
elements.get('removeRow').click();assert.equal(state().rows.length,3);
assert.equal(elements.get('error').textContent,'');
console.log('PASS: HTML controls, preset, split, span editor, selection, undo/redo and row commands');
