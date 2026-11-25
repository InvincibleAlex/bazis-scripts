"""Read-only VRML export inventory. Does not load texture URLs or execute scripts."""
import argparse, collections, gzip, json, re
from pathlib import Path
TOKEN=re.compile(r'\#[^\r\n]*|"(?:\\.|[^"\\])*"|[A-Za-z_][A-Za-z_0-9.:-]*|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?|[{}\[\],]')

def inspect(path):
    path=Path(path);raw=path.read_bytes()
    if len(raw)>128*1024*1024:raise ValueError('Export exceeds 128 MiB inspection limit')
    if raw[:2]==b'\x1f\x8b':
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:raw=f.read(128*1024*1024+1)
        if len(raw)>128*1024*1024:raise ValueError('Decompressed export too large')
    text=raw.decode('utf-8-sig',errors='replace')
    if '#VRML V2.0' not in text[:100]:raise ValueError('Expected VRML V2.0; other formats are not silently interpreted')
    tokens=[m.group() for m in TOKEN.finditer(text) if not m.group().startswith('#')]
    counts=collections.Counter();defs=[];urls=[];coordinates=[];face_sets=[];stack=[];nodes=[]
    for i,token in enumerate(tokens):
        if token=='{':
            kind=tokens[i-1] if i else '?';counts[kind]+=1;stack.append((kind,i))
        elif token=='}':
            if not stack:raise ValueError('Unbalanced node braces')
            kind,start=stack.pop();nodes.append((kind,start,i))
        elif token=='DEF' and i+1<len(tokens):defs.append(tokens[i+1])
    if stack:raise ValueError('Unbalanced node braces')
    def field_array(start,end,name):
        for i in range(start+1,end):
            if tokens[i]==name and i+1<end and tokens[i+1]=='[':
                j=i+2
                while j<end and tokens[j]!=']':j+=1
                if j==end:raise ValueError('Unclosed array '+name)
                return [x for x in tokens[i+2:j] if x!=',']
        return None
    for kind,start,end in nodes:
        if kind=='Coordinate':
            values=field_array(start,end,'point')
            if values is not None:
                if len(values)%3:raise ValueError('Coordinate point array is not XYZ triples')
                coordinates.append(len(values)//3)
        elif kind=='IndexedFaceSet':
            values=field_array(start,end,'coordIndex')
            if values is not None:
                indices=[int(x) for x in values];sizes=[];size=0
                for index in indices:
                    if index==-1:
                        if size:sizes.append(size)
                        size=0
                    elif index>=0:size+=1
                    else:raise ValueError('Invalid negative coordinate index')
                if size:sizes.append(size)
                face_sets.append({'faces':len(sizes),'triangles':sum(n==3 for n in sizes),'polygon_faces':sum(n>3 for n in sizes),'degenerate_faces':sum(n<3 for n in sizes)})
        elif kind=='ImageTexture':
            values=field_array(start,end,'url')
            if values is None:
                values=[tokens[i+1] for i in range(start+1,end-1) if tokens[i]=='url' and tokens[i+1].startswith('"')]
            urls.extend(v[1:-1] for v in values if v.startswith('"'))
    return {'path':str(path),'bytes':len(raw),'node_counts':dict(counts),'coordinate_points':sum(coordinates),'face_sets':face_sets,
        'total_faces':sum(x['faces'] for x in face_sets),'def_names':defs[:200],'texture_urls':list(dict.fromkeys(urls)),
        'note':'Structural inventory only. DEF/USE, transforms, units, material assignments and hardware identity require separate verification. No URL is opened.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('path');args=parser.parse_args();print(json.dumps(inspect(args.path),ensure_ascii=True))
