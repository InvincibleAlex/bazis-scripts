'use strict';
const TitleBlock = (() => {
  const clone = value => JSON.parse(JSON.stringify(value));
  const defaults = () => ({schema:1,name:'Cartuș A4',page:{width:210,height:297,margins:{left:10,right:10,top:10,bottom:10}},
    block:{width:165,maxWidth:190,dynamic:true,gap:10,padding:1,stroke:.2},logo:'',
    parameters:[{name:'proiect',value:'Proiect mobilier'},{name:'client',value:'Client'},{name:'placa',value:'Placa 01'},{name:'material',value:'PAL Kronospan'},{name:'dimensiuni',value:'1327 × 430 × 18 mm'},{name:'pagina',value:'1 / 24'},{name:'data',value:new Date().toLocaleDateString('ro-RO')}],
    rows:[{height:5,cells:[{text:'Proiect: {proiect}',weight:2,font:2.2,align:'left',bold:true},{text:'Client: {client}',weight:2,font:2.2,align:'left'}]},
      {height:5,cells:[{text:'{placa}',weight:1.3,font:2.2,align:'left'},{text:'{material}',weight:2.2,font:2.2,align:'left'},{text:'{dimensiuni}',weight:1.5,font:2.2,align:'center'}]},
      {height:5,cells:[{text:'Data: {data}',weight:1,font:2.2,align:'left'},{text:'Pagina: {pagina}',weight:1,font:2.2,align:'right'}]}]});
  const escape = text => String(text).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  function validate(value){
    if(!value || value.schema!==1)throw Error('Șablon necunoscut. Alege un fișier salvat din acest editor.');
    const v=clone(value),positive=(n,label,min,max)=>{if(!Number.isFinite(n)||n<min||n>max)throw Error(label+' nu este valid.');};
    positive(v.page?.width,'Lățimea foii',50,2000);positive(v.page?.height,'Înălțimea foii',50,2000);
    for(const side of ['left','right','top','bottom'])positive(v.page.margins?.[side],'Marginea '+side,0,1000);
    if(v.page.width-v.page.margins.left-v.page.margins.right<20||v.page.height-v.page.margins.top-v.page.margins.bottom<20)throw Error('Marginile nu lasă suficient spațiu în chenar.');
    for(const key of ['width','maxWidth'])positive(v.block?.[key],'Lățimea cartușului',20,2000);
    if(v.block.dynamic&&v.block.maxWidth<v.block.width)throw Error('Lățimea maximă trebuie să fie cel puțin egală cu lățimea cartușului.');
    positive(v.block.gap,'Spațiul până la desen',0,1000);positive(v.block.padding,'Spațiul în celulă',0,20);positive(v.block.stroke,'Grosimea liniei',.05,2);
    if(!Array.isArray(v.rows)||!v.rows.length||v.rows.length>40)throw Error('Cartușul trebuie să aibă între 1 și 40 de rânduri.');
    v.rows.forEach(row=>{positive(row.height,'Înălțimea rândului',3,200);if(!Array.isArray(row.cells)||!row.cells.length||row.cells.length>20)throw Error('Un rând trebuie să aibă între 1 și 20 de celule.');row.cells.forEach(cell=>{positive(cell.weight,'Lățimea celulei',.1,1000);positive(cell.font,'Mărimea textului',1,10);if(typeof cell.text!=='string'||cell.text.length>10000||!['left','center','right'].includes(cell.align))throw Error('Celulă invalidă.');});});
    if(!Array.isArray(v.parameters)||v.parameters.length>100)throw Error('Lista de parametri nu este validă.');
    const names=new Set();for(const p of v.parameters){if(!/^[A-Za-z_][A-Za-z0-9_]*$/.test(p.name)||names.has(p.name)||typeof p.value!=='string')throw Error('Parametrii trebuie să aibă nume unice, cu litere, cifre și _.');names.add(p.name);}
    if(v.logo && (!/^data:image\/(png|jpeg);base64,[A-Za-z0-9+/=]+$/.test(v.logo)||v.logo.length>7000000))throw Error('Logo invalid sau prea mare.');
    return v;
  }
  function resolve(text,params,values){return values?text.replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g,(all,name)=>params.get(name)??all):text;}
  function wrap(text,maxWidth,measure){
    const lines=[];
    for(const paragraph of text.split('\n')){
      let line='';for(const word of paragraph.split(/\s+/)){if(!word)continue;const next=line?line+' '+word:word;if(measure(next)<=maxWidth){line=next;continue;}if(line){lines.push(line);line='';}if(measure(word)<=maxWidth){line=word;continue;}for(const ch of word){if(line&&measure(line+ch)>maxWidth){lines.push(line);line='';}line+=ch;}}
      lines.push(line);
    }return lines;
  }
  function layout(config,measure,values=true){
    const s=validate(config),p=s.page,b=s.block,m=p.margins,available=p.width-m.left-m.right,params=new Map(s.parameters.map(p=>[p.name,p.value]));
    const prepared=s.rows.map(row=>({...row,cells:row.cells.map(cell=>({...cell,resolved:resolve(cell.text,params,values)}))}));
    let desired=b.width;
    if(b.dynamic)for(const row of prepared){const total=row.cells.reduce((n,c)=>n+c.weight,0);for(const cell of row.cells){const longest=Math.max(...cell.resolved.split('\n').map(t=>measure(t,cell.font,cell.bold)));desired=Math.max(desired,(longest+2*b.padding)*total/cell.weight);}}
    const width=Math.min(available,b.dynamic?Math.max(b.width,b.maxWidth):b.width,desired),left=p.width-m.right-width;
    let height=0;const rows=prepared.map(row=>{const total=row.cells.reduce((n,c)=>n+c.weight,0);let x=left,rowHeight=row.height;const cells=row.cells.map(cell=>{const w=width*cell.weight/total,inner=w-2*b.padding;if(inner<1)throw Error('Celulă prea îngustă. Mărește lățimea sau redu spațiul interior.');const lines=cell.logo?[]:wrap(cell.resolved,inner,t=>measure(t,cell.font,cell.bold));rowHeight=Math.max(rowHeight,lines.length*cell.font*1.25+2*b.padding);const out={...cell,x,width:w,lines};x+=w;return out;});const out={height:rowHeight,cells};height+=rowHeight;return out;});
    const top=p.height-m.bottom-height;if(top-b.gap<=m.top)throw Error('Cartușul nu încape pe foaie. Redu rândurile sau marginile.');let y=top;rows.forEach(row=>{row.y=y;row.cells.forEach(c=>{c.y=y;c.height=row.height;});y+=row.height;});
    return {config:s,width,height,left,top,rows,drawing:{x:m.left,y:m.top,width:available,height:top-b.gap-m.top}};
  }
  function svg(model,selected,options={}){
    const s=model.config,p=s.page,m=p.margins,b=s.block;let out=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${p.width} ${p.height}" width="${p.width}mm" height="${p.height}mm" font-family="Arial,sans-serif"><rect width="${p.width}" height="${p.height}" fill="white"/><rect x="${m.left}" y="${m.top}" width="${p.width-m.left-m.right}" height="${p.height-m.top-m.bottom}" fill="none" stroke="black" stroke-width="${b.stroke}"/>`;
    if(options.guides){const d=model.drawing;out+=`<g class="guide"><rect x="${d.x+1}" y="${d.y+1}" width="${Math.max(0,d.width-2)}" height="${Math.max(0,d.height-2)}" fill="none" stroke="#c3d8dd" stroke-width=".15" stroke-dasharray="1.5 1.5"/><text x="${d.x+d.width/2}" y="${d.y+d.height/2}" text-anchor="middle" font-size="2.5" fill="#a4b8bf">Zona pentru desen</text></g>`;}
    model.rows.forEach((row,ri)=>row.cells.forEach((cell,ci)=>{const id=`r${ri}c${ci}`;out+=`<g data-row="${ri}" data-cell="${ci}"><rect class="cell${selected&&selected[0]===ri&&selected[1]===ci?' selected':''}" x="${cell.x}" y="${cell.y}" width="${cell.width}" height="${cell.height}" fill="white" stroke="black" stroke-width="${b.stroke}"/>`;
      if(cell.logo&&s.logo)out+=`<image href="${s.logo}" x="${cell.x+b.padding}" y="${cell.y+b.padding}" width="${cell.width-2*b.padding}" height="${cell.height-2*b.padding}" preserveAspectRatio="xMidYMid meet" pointer-events="none"/>`;
      else if(!cell.logo){const x=cell.align==='center'?cell.x+cell.width/2:cell.align==='right'?cell.x+cell.width-b.padding:cell.x+b.padding,anchor=cell.align==='center'?'middle':cell.align==='right'?'end':'start',lineHeight=cell.font*1.25,first=cell.y+(cell.height-cell.lines.length*lineHeight)/2+cell.font;
        out+=`<text pointer-events="none" x="${x}" text-anchor="${anchor}" font-size="${cell.font}" font-weight="${cell.bold?'bold':'normal'}">${cell.lines.map((line,i)=>`<tspan x="${x}" y="${first+i*lineHeight}">${escape(line)}</tspan>`).join('')}</text>`;}
      out+='</g>';}));return out+'</svg>';
  }
  return {defaults,validate,layout,svg,clone};
})();
if(typeof module!=='undefined')module.exports=TitleBlock;
if(typeof document!=='undefined'){
  const $=id=>document.getElementById(id),key='bazis-titleblock-v1';let state=TitleBlock.defaults(),selection=[0,0],lastModel;
  try{const old=localStorage.getItem(key);if(old)state=TitleBlock.validate(JSON.parse(old));}catch(e){$('status').textContent='Copia locală nu a putut fi încărcată.';}
  const context=document.createElement('canvas').getContext('2d'),measure=(text,font,bold)=>{context.font=`${bold?'bold ':''}${font}px Arial`;return context.measureText(text).width;};
  function render(){try{lastModel=TitleBlock.layout(state,measure,$('showValues').checked);$('preview').innerHTML=TitleBlock.svg(lastModel,selection,{guides:$('guides').checked});$('error').textContent='';$('size').textContent=`Cartuș: ${lastModel.width.toFixed(1)} × ${lastModel.height.toFixed(1)} mm. Zona desenului: ${lastModel.drawing.width.toFixed(1)} × ${lastModel.drawing.height.toFixed(1)} mm.`;try{localStorage.setItem(key,JSON.stringify(state));$('status').textContent='Ciornă salvată în acest browser';}catch(e){$('status').textContent='Folosește Salvează șablon pentru păstrare.';}return true;}catch(e){$('error').textContent=e.message;return false;}}
  function inspect(){const [r,c]=selection,row=state.rows[r],cell=row.cells[c];$('selectionTitle').textContent=`Rând ${r+1} · celulă ${c+1}`;for(const name of ['text','weight','font','align'])$(name).value=cell[name];$('bold').checked=!!cell.bold;$('logoCell').checked=!!cell.logo;$('rowHeight').value=row.height;}
  function params(){const container=$('parameters');container.replaceChildren();$('insertParam').replaceChildren(new Option('Alege un parametru…',''));state.parameters.forEach((param,index)=>{const div=document.createElement('div');div.className='param';const name=document.createElement('input'),value=document.createElement('input'),del=document.createElement('button');name.value=param.name;name.placeholder='nume';value.value=param.value;value.placeholder='Valoare de probă';del.textContent='×';del.title='Șterge parametrul';name.onchange=()=>{const old=param.name;param.name=name.value.trim();for(const row of state.rows)for(const cell of row.cells)cell.text=cell.text.split('{'+old+'}').join('{'+param.name+'}');inspect();render();params();};value.oninput=()=>{param.value=value.value;render();};del.onclick=()=>{state.parameters.splice(index,1);params();render();};div.append(name,value,del);container.append(div);$('insertParam').add(new Option(param.name,param.name));});}
  function populate(){for(const side of ['left','right','top','bottom'])$(side).value=state.page.margins[side];$('pageWidth').value=state.page.width;$('pageHeight').value=state.page.height;for(const name of ['width','maxWidth','gap','padding','stroke'])$(name).value=state.block[name];$('dynamic').checked=state.block.dynamic;selection=[0,0];inspect();params();render();}
  for(const side of ['left','right','top','bottom'])$(side).oninput=()=>{state.page.margins[side]=Number($(side).value);render();};
  for(const [id,name] of [['pageWidth','width'],['pageHeight','height']])$(id).oninput=()=>{state.page[name]=Number($(id).value);render();};
  for(const name of ['width','maxWidth','gap','padding','stroke'])$(name).oninput=()=>{state.block[name]=Number($(name).value);render();};$('dynamic').onchange=()=>{state.block.dynamic=$('dynamic').checked;render();};
  for(const name of ['text','weight','font','align','bold','logoCell'])$(name).oninput=()=>{const cell=state.rows[selection[0]].cells[selection[1]];cell[name==='logoCell'?'logo':name]=['bold','logoCell'].includes(name)?$(name).checked:['weight','font'].includes(name)?Number($(name).value):$(name).value;render();};
  $('rowHeight').oninput=()=>{state.rows[selection[0]].height=Number($('rowHeight').value);render();};
  $('preview').onclick=event=>{const cell=event.target.closest('[data-row]');if(cell){selection=[Number(cell.dataset.row),Number(cell.dataset.cell)];inspect();render();}};
  $('addCell').onclick=()=>{const row=state.rows[selection[0]];row.cells.splice(selection[1]+1,0,{text:'Texte',weight:1,font:2.2,align:'left'});selection[1]++;inspect();render();};
  $('removeCell').onclick=()=>{const row=state.rows[selection[0]];if(row.cells.length===1)return;row.cells.splice(selection[1],1);selection[1]=Math.min(selection[1],row.cells.length-1);inspect();render();};
  $('addRow').onclick=()=>{state.rows.splice(selection[0]+1,0,{height:5,cells:[{text:'Text',weight:1,font:2.2,align:'left'}]});selection=[selection[0]+1,0];inspect();render();};
  $('removeRow').onclick=()=>{if(state.rows.length===1)return;state.rows.splice(selection[0],1);selection=[Math.min(selection[0],state.rows.length-1),0];inspect();render();};
  for(const [id,delta] of [['moveLeft',-1],['moveRight',1]])$(id).onclick=()=>{const cells=state.rows[selection[0]].cells,i=selection[1],j=i+delta;if(j<0||j>=cells.length)return;[cells[i],cells[j]]=[cells[j],cells[i]];selection[1]=j;inspect();render();};
  for(const [id,delta] of [['moveUp',-1],['moveDown',1]])$(id).onclick=()=>{const i=selection[0],j=i+delta;if(j<0||j>=state.rows.length)return;[state.rows[i],state.rows[j]]=[state.rows[j],state.rows[i]];selection[0]=j;inspect();render();};
  $('addParam').onclick=()=>{let n=1;while(state.parameters.some(p=>p.name==='parametru_'+n))n++;state.parameters.push({name:'parametru_'+n,value:'Valoare'});params();render();};
  $('insertParam').onchange=()=>{if(!$('insertParam').value)return;state.rows[selection[0]].cells[selection[1]].text+='{'+$('insertParam').value+'}';inspect();$('insertParam').value='';render();};
  $('showValues').onchange=render;$('guides').onchange=render;
  $('save').onclick=()=>{if(!render())return;const blob=new Blob([JSON.stringify(TitleBlock.validate(state),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='cartus.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('status').textContent='Șablon exportat în cartus.json';};
  $('load').onclick=()=>$('jsonFile').click();$('jsonFile').onchange=async()=>{const file=$('jsonFile').files[0];if(!file)return;try{if(file.size>8000000)throw Error('Fișier prea mare.');const next=TitleBlock.validate(JSON.parse(await file.text()));TitleBlock.layout(next,measure);state=next;populate();}catch(e){$('error').textContent=e.message;}$('jsonFile').value='';};
  $('logo').onclick=()=>$('logoFile').click();$('logoFile').onchange=()=>{const file=$('logoFile').files[0];if(!file)return;if(!['image/png','image/jpeg'].includes(file.type)||file.size>5000000){$('error').textContent='Alege PNG sau JPG de maximum 5 MB.';return;}const reader=new FileReader();reader.onload=()=>{state.logo=reader.result;state.rows[selection[0]].cells[selection[1]].logo=true;inspect();render();};reader.readAsDataURL(file);};$('removeLogo').onclick=()=>{state.logo='';for(const row of state.rows)for(const cell of row.cells)cell.logo=false;inspect();render();};
  $('print').onclick=()=>{if(!render())return;let style=document.getElementById('printSize');if(!style){style=document.createElement('style');style.id='printSize';document.head.append(style);}style.textContent=`@media print{.paper{width:${state.page.width}mm}}@page{size:${state.page.width}mm ${state.page.height}mm;margin:0}`;window.print();};
  $('reset').onclick=()=>{if(confirm('Revii la șablonul inițial? Salvează înainte dacă vrei să păstrezi modificările.')){state=TitleBlock.defaults();populate();}};populate();
}
