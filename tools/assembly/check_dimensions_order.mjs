import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../../bridge/Export Cote.js',import.meta.url),'utf8');
const block=source.slice(source.indexOf('  // Native order metadata,'),source.indexOf('  var report={schema:1,model:filename,order:order'));
assert(block.length>0);
for(const extra of [{Article:{OrderName:'ClientDemo',OrderCode:'C01'}},{currentFileData:{article:{OrderName:'ClientExample',OrderCode:'C02'}}},{}]){
 const context={get:(obj,key)=>obj?.[key],text:value=>value==null?'':String(value),...extra};
 vm.createContext(context);vm.runInContext(block,context);
 assert.equal(context.order.name,extra.Article?.OrderName??extra.currentFileData?.article.OrderName??'');
 assert.equal(context.order.code,extra.Article?.OrderCode??extra.currentFileData?.article.OrderCode??'');
}
console.log('PASS: native order name read in legacy and current BAZIS APIs; missing order stays empty');
