"""Build a relocatable Windows x64 Export Cote package from an existing CPython runtime."""
import argparse,ast,hashlib,importlib.metadata as metadata,json,platform,shutil,subprocess,sys
from pathlib import Path
from packaging.requirements import Requirement

def copy_dependencies(destination):
    pending=['reportlab','pypdf','numpy'];seen=set();versions={}
    while pending:
        name=pending.pop()
        distribution=metadata.distribution(name);key=distribution.metadata['Name'].lower()
        if key in seen:continue
        seen.add(key);versions[key]=distribution.version
        for entry in distribution.files or []:
            if '..' in entry.parts or '__pycache__' in entry.parts or entry.suffix=='.pyc':continue
            source=Path(distribution.locate_file(entry))
            if not source.is_file():continue
            target=destination/entry;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        for dependency in distribution.requires or []:
            requirement=Requirement(dependency)
            if requirement.marker is None or requirement.marker.evaluate({'extra':''}):pending.append(requirement.name)
    return versions

def helper_files(source):
    pending=['export_dimensions','dimensions_console','assembly_console'];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        path=source/(name+'.py')
        if not path.is_file():continue
        seen.add(name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.ImportFrom) and node.module and '.' not in node.module:pending.append(node.module)
            elif isinstance(node,ast.Import):pending.extend(alias.name for alias in node.names if '.' not in alias.name)
    return sorted(source/(name+'.py') for name in seen)

def build(destination,runtime):
    probe=json.loads(subprocess.check_output([str(runtime/'python.exe'),'-I','-c','import json,sys,struct; print(json.dumps([list(sys.version_info[:2]),struct.calcsize("P")*8]))'],text=True))
    if probe!=[list(sys.version_info[:2]),64] or sys.platform!='win32':raise RuntimeError('Build with matching Windows x64 Python major/minor version')
    target=destination/'runtime'/'python';target.mkdir(parents=True,exist_ok=True)
    for source in runtime.iterdir():
        if source.is_file():shutil.copy2(source,target/source.name)
    for folder in ['DLLs','Lib']:
        if (runtime/folder).is_dir():shutil.copytree(runtime/folder,target/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('site-packages','__pycache__','*.pyc','test','tests'))
    # Explicitly isolate the interpreter from another PC's installed Python/PYTHONPATH.
    tag='python'+str(sys.version_info.major)+str(sys.version_info.minor)
    (target/(tag+'._pth')).write_text(tag+'.zip\n.\nDLLs\nLib\nLib/site-packages\n../../tools/assembly\nimport site\n',encoding='utf-8')
    versions=copy_dependencies(target/'Lib'/'site-packages')
    source=Path(__file__).resolve().parents[1]/'assembly';helpers=destination/'tools'/'assembly';helpers.mkdir(parents=True,exist_ok=True)
    files=helper_files(source)
    for file in files:shutil.copy2(file,helpers/file.name)
    manifest={'schema':1,'python':'runtime/python/python.exe','console':'tools/assembly/dimensions_console.py','renderer':'tools/assembly/export_dimensions.py','dependencies':versions,
              'helpers':{file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in files}}
    (destination/'runtime.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (destination/'CITESTE.txt').write_text('Export Cote — Windows x64\nPastrati acest folder langa Export Cote.js. Poate fi copiat pe alt PC sau rulat de pe partajare.\nPython si bibliotecile sunt incluse. Nu necesita instalare Python, pip, MCP sau configurare per utilizator.\nNu stergeti runtime sau tools.\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True,type=Path);parser.add_argument('--python-runtime',required=True,type=Path);args=parser.parse_args()
    result=build(args.destination,args.python_runtime);print(json.dumps({'ok':True,'destination':str(args.destination),'dependencies':result['dependencies'],'helper_count':len(result['helpers'])}))
