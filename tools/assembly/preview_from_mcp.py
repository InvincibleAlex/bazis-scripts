"""Build a clearly tagged bounds-only preview from an MCP read snapshot."""
import json
import re
import sys
from pathlib import Path
from export_assembly import norm, box_edges, clean_report

def convert(raw):
    items=raw['items'];by={p['object_id']:p for p in items}
    children={}
    for p in items:children.setdefault(p.get('parent_id'),[]).append(p)
    def ancestors(p):
        out=[]
        while p.get('parent_id'):
            p=by[p['parent_id']];out.insert(0,p['object_id'])
        return out
    # Export every cabinet even while BAZIS temporarily isolates the active one.
    def visible(p):return True
    def bounds(p):
        b=p.get('bounds_global_mm',{})
        return {k:[b[k][a] for a in ('x','y','z')] for k in ('min','max')} if b.get('min') and b.get('max') else None
    def board(p):return all(p.get(k,0)>0 for k in ('contour_width_mm','contour_height_mm','thickness_mm')) and re.search(r'\b(pal|mdf|hdf|pfl|placaj|plywood)\b',p.get('material',''),re.I)
    def skip(p):return re.match(r'gaur|hole\b|linie de|caseta de',norm(p.get('name','')))
    chosen=[];covered=set()
    for p in items:
        if not visible(p) or skip(p) or board(p) or any(a in covered for a in ancestors(p)):continue
        name=p.get('name','')
        if '\r' in name or (not p.get('child_count') and re.search(r'surub|diblu|balama|glisier|picior|clem|maner|suport|talpici',norm(name))):
            chosen.append(p);covered.add(p['object_id'])
    hardware=[]
    for p in chosen:
        b=bounds(p)
        if not b:continue
        edges=[];stack=[p]
        while stack:
            obj=stack.pop()
            if not visible(obj) or skip(obj):continue
            kids=children.get(obj['object_id'],[])
            if kids:stack.extend(kids)
            else:
                bb=bounds(obj)
                if bb:edges.extend(box_edges({'bounds':bb}))
        hardware.append(dict(id=p['object_id'],uid=p.get('uid'),parent=p.get('parent_id'),ancestors=ancestors(p),name=p['name'],article=p['name'].split('\r',1)[1] if '\r' in p['name'] else '',bounds=b,edges=edges,kind='hardware',approximate_components=True,geometry_source='MCP component bounds'))
    panels=[]
    for p in items:
        if not visible(p) or not board(p) or any(a in covered for a in ancestors(p)):continue
        b=bounds(p)
        if not b:continue
        panels.append(dict(id=p['object_id'],uid=p.get('uid'),parent=p.get('parent_id'),ancestors=ancestors(p),name=p['name'],designation=p.get('designation',''),material=p.get('material','').split('\r')[0],width=p['contour_width_mm'],height=p['contour_height_mm'],thickness=p['thickness_mm'],bounds=b,edges=[],warnings=['MCP bounds preview']))
    return clean_report(dict(schema=2,model=raw['model'],model_token=raw['model_token'],nodes=[dict(id=p['object_id'],parent=p.get('parent_id'),name=p['name'],designation=p.get('designation','')) for p in items],panels=panels,hardware=hardware,geometry_source='MCP bounds preview: hardware and boards; no exact mesh'))

if __name__=='__main__':
    raw=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    report=convert(raw)
    Path(sys.argv[2]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'panels':len(report['panels']),'hardware':len(report['hardware'])}))
