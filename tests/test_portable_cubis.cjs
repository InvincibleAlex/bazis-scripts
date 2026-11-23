const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../bridge/Export Cubis.js'),'utf8');
const shared=String.raw`\\RG\Bazis\Scripts\Export Tabele`;
const calls=[];
const manifest={python:'runtime/python/python.exe',node:'runtime/node/node.exe',material_reader:'tools/read_material_designations.py',cubis_script:'tools/cubis/export_cubis.mjs'};
const ctx={__dirname:'C:\\OtherUser\\Scripts',path,rows:[{material:'PAL test',grosime_mm:18}],str:String,
 fs:{existsSync:p=>!p.startsWith('C:'),readFileSync:p=>{assert.equal(p,path.join(shared,'runtime.json'));return JSON.stringify(manifest);}},
 require:()=>({execFileSync:(exe,args,options)=>{calls.push(exe);assert.equal(exe,path.resolve(shared,manifest.python));assert.equal(args[0],path.resolve(shared,manifest.material_reader));return JSON.stringify({ok:true,materials:[{desemnare:'PAL_TEST',stare:'Citit direct din baza'}]});}})};
vm.createContext(ctx);vm.runInContext(source.slice(source.indexOf('        // Query all panel materials'),source.indexOf('        var folder = null')),ctx);
assert.equal(calls.length,1);assert.equal(ctx.rows[0].material_db.desemnare,'PAL_TEST');assert(ctx.readerConfig.node.startsWith(shared));
assert(!source.includes('material-db-reader.json'),'shared export must not require the old per-user runtime configuration');
new vm.Script(source);
console.log('PASS: a different Windows profile loads all export components from the shared package');
