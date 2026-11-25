from pathlib import Path
import struct,sys,zlib,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from inspect_furniture_source import parse_nodes,inspect
keys=['Document','FurnList','F123','TriData']
dictionary=struct.pack('<I',len(keys))+b''.join(struct.pack('<I',len(k))+k.encode() for k in keys)
def node(k,children=(),blob=None):
 return struct.pack('<IIB',k,len(children),7 if blob is not None else 0)+(struct.pack('<I',len(blob))+blob if blob is not None else b'')+b''.join(children)
data=dictionary+node(0,[node(1,[node(2,[node(3,blob=b'native-mesh-data')])])])
tree,count=parse_nodes(data);assert count==4
assert tree['children'][0]['children'][0]['children'][0]['value']['blob_bytes']==16
for bad in [data[:-1],data+b'extra']:
 try:parse_nodes(bad)
 except (ValueError,struct.error):pass
 else:raise AssertionError('Partial parsing must not be accepted')
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/'fixture.f3d';original=b'BZ85-test'+zlib.compress(data);p.write_bytes(original)
 r=inspect(p);assert len(r['streams'])==1;assert r['streams'][0]['fully_parsed'];assert p.read_bytes()==original
print('PASS: complete native node parsing, blob metadata, truncation rejection, source unchanged')
