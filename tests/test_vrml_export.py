from pathlib import Path
import sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from inspect_vrml_export import inspect
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'export.wrl';s='''#VRML V2.0 utf8
# Box { is just a comment
DEF Dowel Shape { geometry Cylinder { radius 4 height 30 } }
Shape { geometry IndexedFaceSet { coord Coordinate { point [ 0 0 0, 1 0 0, 0 1 0 ] } coordIndex [0,1,2,-1] } appearance Appearance { texture ImageTexture {url ["Kronospan/test.jpg"]} } }
''';p.write_text(s);r=inspect(p)
 assert r['node_counts']['Cylinder']==1 and 'Box' not in r['node_counts']
 assert r['coordinate_points']==3 and r['total_faces']==1
 assert r['texture_urls']==['Kronospan/test.jpg'];assert p.read_text()==s
print('PASS: primitive and surface inventory, texture references retained, source unchanged')
