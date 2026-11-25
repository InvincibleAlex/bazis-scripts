"""Experimental read-only inspection of BAZIS BZ85 compressed node streams.

Undocumented format: accept only streams parsed completely; never edit source files
or interpret object type codes as geometry classes without native confirmation.
"""
import argparse, hashlib, json, math, struct, zlib
from pathlib import Path

LIMIT=64*1024*1024

def parse_nodes(data):
    pos=0; nodes=0
    def take(size):
        nonlocal pos
        if size<0 or pos+size>len(data):raise ValueError('Truncated stream')
        value=data[pos:pos+size];pos+=size;return value
    def number(fmt):return struct.unpack(fmt,take(struct.calcsize(fmt)))[0]
    count=number('<I')
    if not 1<=count<=10000:raise ValueError('Invalid dictionary count')
    keys=[]
    for _ in range(count):
        size=number('<I')
        if size>2000:raise ValueError('Invalid dictionary string')
        keys.append(take(size).decode('utf8'))
    def node(depth=0):
        nonlocal nodes
        nodes+=1
        if nodes>200000 or depth>64:raise ValueError('Node budget exceeded')
        key=number('<I');children=number('<I');tag=number('<B');value=None
        if key!=0xffffffff and key>=len(keys):raise ValueError('Unknown dictionary key')
        if children>200000:raise ValueError('Invalid child count')
        if tag in (1,2):value={'native_boolean_tag':tag}
        elif tag==3:value=number('<B')
        elif tag==4:value=number('<i')
        elif tag==9:value={'native_datetime_float':number('<d')}
        elif tag==5:
            value=number('<d')
            if not math.isfinite(value):raise ValueError('Nonfinite value')
        elif tag in (6,7):
            size=number('<I');blob=take(size*(2 if tag==6 else 1))
            value=blob.decode('utf-16le',errors='surrogatepass') if tag==6 else {'blob_bytes':size,'sha256':hashlib.sha256(blob).hexdigest(),'head_hex':blob[:32].hex()}
        elif tag!=0:raise ValueError('Unsupported value tag '+str(tag)+' at '+str(pos-1)+' key '+(keys[key] if key<len(keys) else str(key)))
        return {'key':keys[key] if key!=0xffffffff else '(unnamed)','value':value,'children':[node(depth+1) for _ in range(children)]}
    tree=node()
    if pos!=len(data):raise ValueError('Unparsed trailing bytes')
    return tree,nodes

def inspect(path):
    path=Path(path)
    if path.stat().st_size>LIMIT:raise ValueError('File too large')
    raw=path.read_bytes()
    if raw[:4]!=b'BZ85':raise ValueError('Unsupported file signature')
    results=[];diagnostics=[]
    for offset in range(len(raw)-2):
        if raw[offset]!=0x78 or (raw[offset]*256+raw[offset+1])%31:continue
        try:
            decoder=zlib.decompressobj();data=decoder.decompress(raw[offset:],LIMIT+1)
            if len(data)>LIMIT or not decoder.eof:continue
            tree,nodes=parse_nodes(data)
        except (ValueError,UnicodeError,struct.error,zlib.error) as error:
            if 'Unsupported value tag' in str(error):diagnostics.append({'offset':offset,'error':str(error)})
            continue
        objects=[];blobs=[]
        def walk(item,trail=''):
            trail+='/'+item['key']
            if item['key']=='Obj':
                values={x['key']:x['value'] for x in item['children'] if x['value'] is not None}
                objects.append({'path':trail,'properties':values})
            if isinstance(item['value'],dict) and 'blob_bytes' in item['value']:blobs.append({'path':trail,**item['value']})
            for child in item['children']:walk(child,trail)
        walk(tree)
        results.append({'offset':offset,'uncompressed_bytes':len(data),'fully_parsed':True,'node_count':nodes,'objects':objects,'blobs':blobs})
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'file_bytes':len(raw),'streams':results,'diagnostics':diagnostics,'format_status':'experimental; raw values only; not a solid decoder'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('paths',nargs='+');args=parser.parse_args()
    for path in args.paths:print(json.dumps(inspect(path),ensure_ascii=True))
