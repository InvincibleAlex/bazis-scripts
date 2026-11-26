'use strict';
const TitleBlock = (() => {
  const clone = value => JSON.parse(JSON.stringify(value));
  const legacyDefaults = () => ({schema:1,name:'Cartuș A4',page:{width:210,height:297,margins:{left:10,right:10,top:10,bottom:10}},
    block:{width:165,maxWidth:190,dynamic:true,gap:10,padding:1,stroke:.2},logo:'',
    parameters:[{name:'proiect',value:'Proiect mobilier'},{name:'client',value:'Client'},{name:'placa',value:'Placa 01'},{name:'material',value:'PAL Kronospan'},{name:'dimensiuni',value:'1327 × 430 × 18 mm'},{name:'pagina',value:'1 / 24'},{name:'data',value:new Date().toLocaleDateString('ro-RO')}],
    rows:[{height:5,cells:[{text:'Proiect: {proiect}',weight:2,font:2.2,align:'left',bold:true},{text:'Client: {client}',weight:2,font:2.2,align:'left'}]},
      {height:5,cells:[{text:'{placa}',weight:1.3,font:2.2,align:'left'},{text:'{material}',weight:2.2,font:2.2,align:'left'},{text:'{dimensiuni}',weight:1.5,font:2.2,align:'center'}]},
      {height:5,cells:[{text:'Data: {data}',weight:1,font:2.2,align:'left'},{text:'Pagina: {pagina}',weight:1,font:2.2,align:'right'}]}]});

  const blank=(col,colSpan=1,rowSpan=1)=>({col,colSpan,rowSpan,text:'',font:2.2,align:'left'});
  function migrate(value){
    const v=clone(value);if(v.schema!==1)return v;
    const bounds=[0,1];
    for(const row of v.rows){let x=0,total=row.cells.reduce((n,c)=>n+c.weight,0);for(const c of row.cells){x+=c.weight/total;if(!bounds.some(b=>Math.abs(b-x)<1e-8))bounds.push(x);}}
    bounds.sort((a,b)=>a-b);v.columns=bounds.slice(1).map((x,i)=>x-bounds[i]);
    for(const row of v.rows){let x=0,total=row.cells.reduce((n,c)=>n+c.weight,0);for(const c of row.cells){const end=x+c.weight/total;c.col=bounds.findIndex(b=>Math.abs(b-x)<1e-8);c.colSpan=bounds.findIndex(b=>Math.abs(b-end)<1e-8)-c.col;c.rowSpan=1;delete c.weight;x=end;}}
    v.schema=2;return v;
  }
  const defaults=()=>migrate(legacyDefaults());
  function grid(v,fill=false){
    const occupied=v.rows.map(()=>Array(v.columns.length).fill(null));
    v.rows.forEach((row,r)=>row.cells.forEach(cell=>{
      if(!Number.isInteger(cell.col)||!Number.isInteger(cell.colSpan)||!Number.isInteger(cell.rowSpan)||cell.col<0||cell.colSpan<1||cell.rowSpan<1||cell.col+cell.colSpan>v.columns.length||r+cell.rowSpan>v.rows.length)throw Error('Celulă în afara grilei.');
      for(let y=r;y<r+cell.rowSpan;y++)for(let x=cell.col;x<cell.col+cell.colSpan;x++){if(occupied[y][x])throw Error('Două celule se suprapun.');occupied[y][x]={row:r,cell};}
    }));
    if(fill)for(let r=0;r<v.rows.length;r++)for(let c=0;c<v.columns.length;c++)if(!occupied[r][c]){const cell=blank(c);v.rows[r].cells.push(cell);occupied[r][c]={row:r,cell};}
    for(const row of v.rows)row.cells.sort((a,b)=>a.col-b.col);
    return occupied;
  }
  function merge(v,r,c,colSpan,rowSpan){
    const cell=v.rows[r].cells[c],end=cell.col+colSpan,bottom=r+rowSpan;
    if(colSpan<1||rowSpan<1||end>v.columns.length||bottom>v.rows.length)throw Error('Selectează un număr de rânduri/coloane care încape în cartuș.');
    const included=[];
    v.rows.forEach((row,y)=>row.cells.forEach(other=>{
      if(y<bottom&&y+other.rowSpan>r&&other.col<end&&other.col+other.colSpan>cell.col){
        if(y<r||y+other.rowSpan>bottom||other.col<cell.col||other.col+other.colSpan>end)throw Error('Zona taie o celulă deja unită. Separă acea celulă mai întâi.');
        included.push(other);
      }
    }));
    const texts=included.filter(x=>x!==cell&&x.text).map(x=>x.text);
    if(texts.length)cell.text=[cell.text,...texts].filter(Boolean).join('\n');
    for(const row of v.rows)row.cells=row.cells.filter(x=>x===cell||!included.includes(x));
    cell.colSpan=colSpan;cell.rowSpan=rowSpan;grid(v,true);return cell;
  }
  function unmerge(v,r,c){const cell=v.rows[r].cells[c];cell.colSpan=1;cell.rowSpan=1;grid(v,true);return cell;}
  function insertColumn(v,index){
    v.columns.splice(index,0,v.columns[Math.max(0,index-1)]||1);
    v.rows.forEach(row=>row.cells.forEach(cell=>{if(cell.col>=index)cell.col++;else if(cell.col+cell.colSpan>index)cell.colSpan++;}));grid(v,true);
  }
  function insertRow(v,index,height=5){
    v.rows.forEach((row,r)=>row.cells.forEach(cell=>{if(r<index&&r+cell.rowSpan>index)cell.rowSpan++;}));v.rows.splice(index,0,{height,cells:[]});grid(v,true);
  }
  function split(v,r,c,axis){
    const cell=v.rows[r].cells[c];
    if(axis==='vertical'){
      if(cell.colSpan===1){const at=cell.col,weight=v.columns[at]/2;v.columns.splice(at,1,weight,weight);v.rows.forEach(row=>row.cells.forEach(other=>{if(other.col>at)other.col++;else if(other.col<=at&&other.col+other.colSpan>at)other.colSpan++;}));}
      const first=Math.ceil(cell.colSpan/2),other={...clone(cell),col:cell.col+first,colSpan:cell.colSpan-first,text:'',logo:false};cell.colSpan=first;v.rows[r].cells.push(other);
    }else{
      if(cell.rowSpan===1){const h=v.rows[r].height/2;if(h<3)throw Error('Mărește înălțimea rândului la minimum 6 mm înainte de împărțire.');v.rows[r].height=h;v.rows.forEach((row,y)=>row.cells.forEach(other=>{if(y<=r&&y+other.rowSpan>r)other.rowSpan++;}));v.rows.splice(r+1,0,{height:h,cells:[]});}
      const first=Math.ceil(cell.rowSpan/2),other={...clone(cell),rowSpan:cell.rowSpan-first,text:'',logo:false};cell.rowSpan=first;v.rows[r+first].cells.push(other);
    }grid(v,true);return cell;
  }
  function removeRow(v,index){
    if(v.rows.length===1)throw Error('Păstrează cel puțin un rând.');
    const continuing=v.rows[index].cells.filter(c=>c.rowSpan>1).map(c=>({...c,rowSpan:c.rowSpan-1}));
    v.rows.forEach((row,r)=>row.cells.forEach(c=>{if(r<index&&r+c.rowSpan>index)c.rowSpan--;}));v.rows.splice(index,1);if(continuing.length)v.rows[index].cells.push(...continuing);grid(v,true);
  }
  function removeColumn(v,index){
    if(v.columns.length===1)throw Error('Păstrează cel puțin o coloană.');v.columns.splice(index,1);
    for(const row of v.rows){row.cells=row.cells.filter(c=>!(c.col===index&&c.colSpan===1));for(const c of row.cells){if(c.col>index)c.col--;else if(c.col<=index&&c.col+c.colSpan>index)c.colSpan--;}}grid(v,true);
  }
  function logoPreset(base){
    const v=clone(base);v.columns=[25,60,40,35];v.rows=[
      {height:7,cells:[{...blank(0,1,3),logo:true,text:'LOGO',align:'center'},{...blank(1,3),text:'Proiect: {proiect}',bold:true}]},
      {height:7,cells:[{...blank(1),text:'{placa}'},{...blank(2),text:'{material}'},{...blank(3),text:'{dimensiuni}'}]},
      {height:7,cells:[{...blank(1,2),text:'Client: {client}'},{...blank(3),text:'Pagina: {pagina}',align:'right'}]}];return v;
  }
  const escape = text => String(text).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  function validate(value){
    if(!value || ![1,2].includes(value.schema))throw Error('Șablon necunoscut. Alege un fișier salvat din acest editor.');
    const v=migrate(value),positive=(n,label,min,max)=>{if(!Number.isFinite(n)||n<min||n>max)throw Error(label+' nu este valid.');};
    positive(v.page?.width,'Lățimea foii',50,2000);positive(v.page?.height,'Înălțimea foii',50,2000);
    for(const side of ['left','right','top','bottom'])positive(v.page.margins?.[side],'Marginea '+side,0,1000);
    if(v.page.width-v.page.margins.left-v.page.margins.right<20||v.page.height-v.page.margins.top-v.page.margins.bottom<20)throw Error('Marginile nu lasă suficient spațiu în chenar.');
    for(const key of ['width','maxWidth'])positive(v.block?.[key],'Lățimea cartușului',20,2000);
    if(v.block.dynamic&&v.block.maxWidth<v.block.width)throw Error('Lățimea maximă trebuie să fie cel puțin egală cu lățimea cartușului.');
    positive(v.block.gap,'Spațiul până la desen',0,1000);positive(v.block.padding,'Spațiul în celulă',0,20);positive(v.block.stroke,'Grosimea liniei',.05,2);
    if(!Array.isArray(v.rows)||!v.rows.length||v.rows.length>40)throw Error('Cartușul trebuie să aibă între 1 și 40 de rânduri.');
    if(!Array.isArray(v.columns)||!v.columns.length||v.columns.length>120)throw Error('Număr de coloane invalid.');
    v.columns.forEach(n=>positive(n,'Lățimea coloanei',.000001,10000));
    v.rows.forEach(row=>{positive(row.height,'Înălțimea rândului',3,200);if(!Array.isArray(row.cells)||row.cells.length>120)throw Error('Rând invalid.');row.cells.forEach(cell=>{positive(cell.font,'Mărimea textului',1,10);if(typeof cell.text!=='string'||cell.text.length>10000||!['left','center','right'].includes(cell.align))throw Error('Celulă invalidă.');});});
    grid(v,true);
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
    const total=s.columns.reduce((n,x)=>n+x,0),fraction=cell=>s.columns.slice(cell.col,cell.col+cell.colSpan).reduce((n,x)=>n+x,0)/total;
    const prepared=s.rows.map(row=>({...row,cells:row.cells.map(cell=>({...cell,resolved:resolve(cell.text,params,values)}))}));
    let desired=b.width;
    if(b.dynamic)for(const row of prepared)for(const cell of row.cells){if(cell.logo)continue;const longest=Math.max(...cell.resolved.split('\n').map(t=>measure(t,cell.font,cell.bold)));desired=Math.max(desired,(longest+2*b.padding)/fraction(cell));}
    const width=Math.min(available,b.dynamic?b.maxWidth:b.width,desired),left=p.width-m.right-width;
    const xs=[left];for(const col of s.columns)xs.push(xs[xs.length-1]+width*col/total);
    const heights=prepared.map(row=>row.height);
    const rows=prepared.map((row,r)=>({...row,cells:row.cells.map(cell=>{const w=xs[cell.col+cell.colSpan]-xs[cell.col],inner=w-2*b.padding;if(inner<1)throw Error('Celulă prea îngustă. Mărește lățimea sau redu spațiul interior.');const lines=cell.logo?[]:wrap(cell.resolved,inner,t=>measure(t,cell.font,cell.bold));return {...cell,x:xs[cell.col],width:w,lines,needed:lines.length*cell.font*1.25+2*b.padding};})}));
    for(let r=0;r<rows.length;r++)for(const cell of rows[r].cells)if(cell.rowSpan===1)heights[r]=Math.max(heights[r],cell.needed);
    for(let r=0;r<rows.length;r++)for(const cell of rows[r].cells)if(cell.rowSpan>1){const existing=heights.slice(r,r+cell.rowSpan).reduce((n,x)=>n+x,0);if(cell.needed>existing)heights[r+cell.rowSpan-1]+=cell.needed-existing;}
    const height=heights.reduce((n,h)=>n+h,0),top=p.height-m.bottom-height;
    if(top-b.gap<=m.top)throw Error('Cartușul nu încape pe foaie. Redu rândurile sau marginile.');let y=top;
    rows.forEach((row,r)=>{row.y=y;row.height=heights[r];row.cells.forEach(cell=>{cell.y=y;cell.height=heights.slice(r,r+cell.rowSpan).reduce((n,h)=>n+h,0);});y+=row.height;});
    return {config:s,width,height,left,top,rows,drawing:{x:m.left,y:m.top,width:available,height:top-b.gap-m.top}};
  }

  function svg(model,selected,options={}){
    const s=model.config,p=s.page,m=p.margins,b=s.block;let out=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${p.width} ${p.height}" width="${p.width}mm" height="${p.height}mm" font-family="Arial,sans-serif"><rect width="${p.width}" height="${p.height}" fill="white"/><rect x="${m.left}" y="${m.top}" width="${p.width-m.left-m.right}" height="${p.height-m.top-m.bottom}" fill="none" stroke="black" stroke-width="${b.stroke}"/>`;
    if(options.guides){const d=model.drawing;out+=`<g class="guide"><rect x="${d.x+1}" y="${d.y+1}" width="${Math.max(0,d.width-2)}" height="${Math.max(0,d.height-2)}" fill="none" stroke="#c3d8dd" stroke-width=".15" stroke-dasharray="1.5 1.5"/><text x="${d.x+d.width/2}" y="${d.y+d.height/2}" text-anchor="middle" font-size="2.5" fill="#a4b8bf">Zona pentru desen</text></g>`;}
    model.rows.forEach((row,ri)=>row.cells.forEach((cell,ci)=>{const id=`r${ri}c${ci}`;out+=`<g data-row="${ri}" data-cell="${ci}"><rect class="cell${selected&&selected[0]===ri&&selected[1]===ci?' selected':''}" x="${cell.x}" y="${cell.y}" width="${cell.width}" height="${cell.height}" fill="white" stroke="black" stroke-width="${b.stroke}"/>`;
      if(cell.logo&&s.logo)out+=`<image href="${s.logo}" x="${cell.x+b.padding}" y="${cell.y+b.padding}" width="${cell.width-2*b.padding}" height="${cell.height-2*b.padding}" preserveAspectRatio="xMidYMid meet" pointer-events="none"/>`;
      else if(cell.logo)out+=`<text pointer-events="none" x="${cell.x+cell.width/2}" y="${cell.y+cell.height/2}" text-anchor="middle" font-size="2.5" fill="#84959c">LOGO</text>`;
      else {const x=cell.align==='center'?cell.x+cell.width/2:cell.align==='right'?cell.x+cell.width-b.padding:cell.x+b.padding,anchor=cell.align==='center'?'middle':cell.align==='right'?'end':'start',lineHeight=cell.font*1.25,first=cell.y+(cell.height-cell.lines.length*lineHeight)/2+cell.font;
        out+=`<text pointer-events="none" x="${x}" text-anchor="${anchor}" font-size="${cell.font}" font-weight="${cell.bold?'bold':'normal'}">${cell.lines.map((line,i)=>`<tspan x="${x}" y="${first+i*lineHeight}">${escape(line)}</tspan>`).join('')}</text>`;}
      out+='</g>';}));return out+'</svg>';
  }
  return {defaults,validate,layout,svg,clone,migrate,grid,merge,unmerge,split,insertRow,insertColumn,removeRow,removeColumn,logoPreset};
})();
if(typeof module!=='undefined')module.exports=TitleBlock;
if(typeof document!=='undefined'){
  const $=id=>document.getElementById(id),key='bazis-titleblock-v1';let state=TitleBlock.defaults(),selection=[0,0],lastModel,lastGood=null,undoStack=[],redoStack=[];
  try{const old=localStorage.getItem(key);if(old)state=TitleBlock.validate(JSON.parse(old));}catch(e){$('status').textContent='Copia locală nu a putut fi încărcată.';}
  const context=document.createElement('canvas').getContext('2d'),measure=(text,font,bold)=>{context.font=`${bold?'bold ':''}${font}px Arial`;return context.measureText(text).width;};
  function render(){try{state=TitleBlock.validate(state);lastModel=TitleBlock.layout(state,measure,$('showValues').checked);$('preview').innerHTML=TitleBlock.svg(lastModel,selection,{guides:$('guides').checked});$('error').textContent='';if($('zoom').value==='block')$('preview').querySelector('svg').setAttribute('viewBox',`${lastModel.left-3} ${lastModel.top-3} ${lastModel.width+6} ${lastModel.height+6}`);const serialized=JSON.stringify(state);if(lastGood&&lastGood!==serialized){undoStack.push(lastGood);if(undoStack.length>80)undoStack.shift();redoStack=[];}lastGood=serialized;$('undo').disabled=!undoStack.length;$('redo').disabled=!redoStack.length;$('size').textContent=`Cartuș: ${lastModel.width.toFixed(1)} × ${lastModel.height.toFixed(1)} mm. Zona desenului: ${lastModel.drawing.width.toFixed(1)} × ${lastModel.drawing.height.toFixed(1)} mm.`;try{localStorage.setItem(key,JSON.stringify(state));$('status').textContent='Ciornă salvată în acest browser';}catch(e){$('status').textContent='Folosește Salvează șablon pentru păstrare.';}return true;}catch(e){$('error').textContent=e.message;return false;}}
  function inspect(){
    selection[0]=Math.min(selection[0],state.rows.length-1);
    if(!state.rows[selection[0]].cells.length)selection=[0,0];
    selection[1]=Math.min(selection[1],state.rows[selection[0]].cells.length-1);
    const [r,c]=selection,row=state.rows[r],cell=row.cells[c];
    $('selectionTitle').textContent=`Rând ${r+1} · coloana ${cell.col+1}`;
    for(const name of ['text','font','align'])$(name).value=cell[name];
    $('weight').value=lastModel?lastModel.rows[r].cells[c].width.toFixed(2):20;
    $('colSpan').value=cell.colSpan;$('rowSpan').value=cell.rowSpan;
    $('bold').checked=!!cell.bold;$('logoCell').checked=!!cell.logo;$('rowHeight').value=row.height;
  }
  function change(action){const before=TitleBlock.clone(state);try{const next=action(state);state=TitleBlock.validate(state);if(next){const [r,col]=next;selection=[r,state.rows[r].cells.findIndex(c=>c.col===col)];if(selection[1]<0)selection=[0,0];}if(!render())throw Error($('error').textContent);inspect();}catch(e){state=before;render();inspect();$('error').textContent=e.message;}}
  function selected(){return state.rows[selection[0]].cells[selection[1]];}
  function restore(stack,other){if(!stack.length)return;other.push(JSON.stringify(state));state=JSON.parse(stack.pop());lastGood=null;selection=[0,0];populate();}
  $('undo').onclick=()=>restore(undoStack,redoStack);$('redo').onclick=()=>restore(redoStack,undoStack);
  document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)&&['z','y'].includes(event.key.toLowerCase())){event.preventDefault();(event.key.toLowerCase()==='y'||event.shiftKey?$('redo'):$('undo')).click();}});
  function params(){const container=$('parameters');container.replaceChildren();$('insertParam').replaceChildren(new Option('Alege un parametru…',''));state.parameters.forEach((param,index)=>{const div=document.createElement('div');div.className='param';const name=document.createElement('input'),value=document.createElement('input'),del=document.createElement('button');name.value=param.name;name.placeholder='nume';value.value=param.value;value.placeholder='Valoare de probă';del.textContent='×';del.title='Șterge parametrul';name.onchange=()=>{const old=param.name;param.name=name.value.trim();for(const row of state.rows)for(const cell of row.cells)cell.text=cell.text.split('{'+old+'}').join('{'+param.name+'}');inspect();render();params();};value.oninput=()=>{param.value=value.value;render();};del.onclick=()=>{state.parameters.splice(index,1);params();render();};div.append(name,value,del);container.append(div);$('insertParam').add(new Option(param.name,param.name));});}
  function populate(){for(const side of ['left','right','top','bottom'])$(side).value=state.page.margins[side];$('pageWidth').value=state.page.width;$('pageHeight').value=state.page.height;for(const name of ['width','maxWidth','gap','padding','stroke'])$(name).value=state.block[name];$('dynamic').checked=state.block.dynamic;selection=[0,0];params();render();inspect();}
  for(const side of ['left','right','top','bottom'])$(side).oninput=()=>{state.page.margins[side]=Number($(side).value);render();};
  for(const [id,name] of [['pageWidth','width'],['pageHeight','height']])$(id).oninput=()=>{state.page[name]=Number($(id).value);render();};
  for(const name of ['width','maxWidth','gap','padding','stroke'])$(name).oninput=()=>{state.block[name]=Number($(name).value);render();};$('dynamic').onchange=()=>{state.block.dynamic=$('dynamic').checked;render();};
  for(const name of ['text','font','align','bold','logoCell'])$(name).oninput=()=>{const cell=selected();cell[name==='logoCell'?'logo':name]=['bold','logoCell'].includes(name)?$(name).checked:name==='font'?Number($(name).value):$(name).value;render();};
  $('rowHeight').onchange=()=>change(v=>{v.rows[selection[0]].height=Number($('rowHeight').value);});
  $('weight').onchange=()=>change(v=>{const cell=selected(),total=v.columns.reduce((n,x)=>n+x,0),old=v.columns.slice(cell.col,cell.col+cell.colSpan).reduce((n,x)=>n+x,0),desired=Number($('weight').value),available=lastModel.width;if(desired<2||desired>=available)throw Error('Lățimea trebuie să fie între 2 mm și lățimea cartușului.');const rest=total-old;if(rest<=0)throw Error('Celula ocupă toată lățimea. Modifică lățimea cartușului.');const target=desired/available*total;v.columns=v.columns.map((x,i)=>x*(i>=cell.col&&i<cell.col+cell.colSpan?target/old:(total-target)/rest));});
  function resizeSpan(){change(v=>{const [r,c]=selection,col=selected().col,cs=Number($('colSpan').value),rs=Number($('rowSpan').value);TitleBlock.unmerge(v,r,c);const index=v.rows[r].cells.findIndex(x=>x.col===col);TitleBlock.merge(v,r,index,cs,rs);return [r,col];});}
  $('colSpan').onchange=resizeSpan;$('rowSpan').onchange=resizeSpan;
  $('preview').onclick=event=>{const cell=event.target.closest('[data-row]');if(cell){selection=[Number(cell.dataset.row),Number(cell.dataset.cell)];inspect();render();}};
  $('zoom').onchange=render;
  $('mergeRight').onclick=()=>change(v=>{const [r,c]=selection,cell=selected(),g=TitleBlock.grid(v),right=g[r][cell.col+cell.colSpan];if(!right)throw Error('Nu mai există o celulă la dreapta.');TitleBlock.merge(v,r,c,right.cell.col+right.cell.colSpan-cell.col,cell.rowSpan);return [r,cell.col];});
  $('mergeDown').onclick=()=>change(v=>{const [r,c]=selection,cell=selected(),g=TitleBlock.grid(v),below=g[r+cell.rowSpan]?.[cell.col];if(!below)throw Error('Nu mai există un rând dedesubt.');TitleBlock.merge(v,r,c,cell.colSpan,below.row+below.cell.rowSpan-r);return [r,cell.col];});
  $('unmerge').onclick=()=>change(v=>{const [r,c]=selection,col=selected().col;TitleBlock.unmerge(v,r,c);return [r,col];});
  for(const [id,axis] of [['splitV','vertical'],['splitH','horizontal']])$(id).onclick=()=>change(v=>{const [r,c]=selection,col=selected().col;TitleBlock.split(v,r,c,axis);return [r,col];});
  $('clearCell').onclick=()=>change(()=>{selected().text='';selected().logo=false;});
  $('addRow').onclick=()=>change(v=>{const index=selection[0]+selected().rowSpan;TitleBlock.insertRow(v,index);return [index,0];});
  $('removeRow').onclick=()=>change(v=>{TitleBlock.removeRow(v,selection[0]);return [0,0];});
  $('addColumn').onclick=()=>change(v=>{const index=selected().col+selected().colSpan;TitleBlock.insertColumn(v,index);return [selection[0],index];});
  $('removeColumn').onclick=()=>change(v=>{TitleBlock.removeColumn(v,selected().col);return [0,0];});
  $('presetLogo').onclick=()=>{if(confirm('Înlocuiești compartimentarea cu modelul pentru logo pe 3 rânduri? Poți reveni cu Înapoi.')){state=TitleBlock.logoPreset(state);selection=[0,0];populate();$('zoom').value='block';render();}};
  $('addParam').onclick=()=>{let n=1;while(state.parameters.some(p=>p.name==='parametru_'+n))n++;state.parameters.push({name:'parametru_'+n,value:'Valoare'});params();render();};
  $('insertParam').onchange=()=>{if(!$('insertParam').value)return;state.rows[selection[0]].cells[selection[1]].text+='{'+$('insertParam').value+'}';inspect();$('insertParam').value='';render();};
  $('showValues').onchange=()=>{render();inspect();};$('guides').onchange=render;
  $('save').onclick=()=>{if(!render())return;const blob=new Blob([JSON.stringify(TitleBlock.validate(state),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='cartus.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('status').textContent='Șablon exportat în cartus.json';};
  $('load').onclick=()=>$('jsonFile').click();$('jsonFile').onchange=async()=>{const file=$('jsonFile').files[0];if(!file)return;try{if(file.size>8000000)throw Error('Fișier prea mare.');const next=TitleBlock.validate(JSON.parse(await file.text()));TitleBlock.layout(next,measure);state=next;populate();}catch(e){$('error').textContent=e.message;}$('jsonFile').value='';};
  $('logo').onclick=()=>$('logoFile').click();$('logoFile').onchange=()=>{const file=$('logoFile').files[0];if(!file)return;if(!['image/png','image/jpeg'].includes(file.type)||file.size>5000000){$('error').textContent='Alege PNG sau JPG de maximum 5 MB.';return;}const reader=new FileReader();reader.onload=()=>{state.logo=reader.result;state.rows[selection[0]].cells[selection[1]].logo=true;inspect();render();};reader.readAsDataURL(file);};$('removeLogo').onclick=()=>{state.logo='';for(const row of state.rows)for(const cell of row.cells)cell.logo=false;inspect();render();};
  $('print').onclick=()=>{if(!render())return;const zoom=$('zoom').value;$('zoom').value='page';render();let style=document.getElementById('printSize');if(!style){style=document.createElement('style');style.id='printSize';document.head.append(style);}style.textContent=`@media print{.paper{width:${state.page.width}mm}}@page{size:${state.page.width}mm ${state.page.height}mm;margin:0}`;window.print();$('zoom').value=zoom;render();};
  $('reset').onclick=()=>{if(confirm('Revii la șablonul inițial? Salvează înainte dacă vrei să păstrezi modificările.')){state=TitleBlock.defaults();populate();}};populate();
}
