const fs=require('fs'),os=require('os'),path=require('path'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../bridge/Export Cubis.js'),'utf8');new vm.Script(source);
const workflow=source.slice(source.indexOf("        var cubisMessage=''"),source.indexOf("        var folderOpenError = ''"));
for(const scenario of ['success','Cubis','Komodo','Holver','missing-file','locked-csv']){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'bazis-cleanup-test-')),base=path.join(dir,'Model');
 try{
  const originals=new Map([['.json',Buffer.from('{"original":"ă"}')],['.csv',Buffer.from('sep=;\r\nDate;1')]]);
  for(const [ext,bytes] of originals)fs.writeFileSync(base+ext,bytes);
  fs.writeFileSync(path.join(dir,'Older.json'),'keep');
  const mockFs=Object.assign({},fs,{unlinkSync(file){if(scenario==='locked-csv'&&file.endsWith('.csv'))throw Error('Locked');return fs.unlinkSync(file);}});
  const context={fs:mockFs,path,base,exportStatus:()=>{},readerConfig:{node:'node',python:'python',cubis_script:path.join(dir,'export_cubis.mjs')},require:()=>({execFileSync(exe,args){
   const kind=path.basename(args[0]).match(/export_(\w+)/i)[1].replace(/\.mjs$/,'');
   if(kind.toLowerCase()===scenario.toLowerCase())throw Error('Test export failed');
   if(!(scenario==='missing-file'&&kind==='holver'))fs.writeFileSync(args[2],'xlsx bytes');
   return JSON.stringify({ok:true,rows:10});
  }})};
  vm.createContext(context);vm.runInContext(workflow,context);
  if(scenario==='success'){
   assert(context.cubisSucceeded);assert.equal(context.diagnosticMessage,'');
   assert(!fs.existsSync(base+'.json'));assert(!fs.existsSync(base+'.csv'));
  }else{
   for(const [ext,bytes] of originals)assert.deepEqual(fs.readFileSync(base+ext),bytes);
   assert(context.diagnosticMessage.length>0);
   assert.equal(context.cubisSucceeded,scenario==='locked-csv');
  }
  assert.equal(fs.readFileSync(path.join(dir,'Older.json'),'utf8'),'keep');
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
}
const names=source.slice(source.indexOf('        function exportBaseExists('),source.indexOf('        // Citeste numai valori proprii simple;'));
const existing=new Set(['C:/exports/Model Cubis.xlsx']);
const context={fs:{existsSync:p=>existing.has(p)},path:path.posix,base:'C:/exports/Model',folder:'C:/exports',exportName:'Model',stamp:'stamp',process:{pid:12}};
vm.createContext(context);vm.runInContext(names,context);assert.equal(context.base,'C:/exports/Model_stamp_12');
console.log('PASS: diagnostics removed only after all verified exports; errors and locks preserve debug data; Excel-only previous exports retain unique names');
