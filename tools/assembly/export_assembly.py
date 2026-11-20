"""Read-only board assembly PDF prototype. Never claims inferred paths are validated."""
import argparse
import json
import math
import os
import re
import tempfile
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit

W,H=842,595
BLUE=HexColor('#1668b2')
HARDWARE=HexColor('#b15d12')

def repair_text(value):
    """Undo only demonstrable UTF-8-as-legacy decoding; keep valid Unicode intact."""
    if not isinstance(value,str):return value
    def damage(s):return sum(s.count(c) for c in ('Ã','Â','Ä','È','™','ƒ','Å','Ð','Ñ'))
    for _ in range(2):
        options=[value]
        for enc in ('cp1252','latin1'):
            try:options.append(value.encode(enc).decode('utf-8'))
            except (UnicodeError,LookupError):pass
        candidate=min(options,key=damage)
        if damage(candidate)>=damage(value):break
        value=candidate
    return value

def clean_report(report):
    for collection in ('nodes','panels','hardware'):
        for item in report.get(collection,[]):
            for key in ('name','material','designation','article'):
                if key in item:item[key]=repair_text(item[key])
    return report

def norm(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn')

def box_edges(p):
    lo,hi=p['bounds']['min'],p['bounds']['max']
    v=[[hi[0] if i&1 else lo[0],hi[1] if i&2 else lo[1],hi[2] if i&4 else lo[2]] for i in range(8)]
    return [[v[i],v[i^(1<<a)]] for i in range(8) for a in range(3) if not i&(1<<a)]

def center(p):
    return [(a+b)/2 for a,b in zip(p['bounds']['min'],p['bounds']['max'])]

def hardware_scope(fitting,panels):
    """Constrain heuristic matches to the closest BAZIS ancestor with boards."""
    for ancestor in reversed(fitting.get('ancestors',[])):
        scope=[p for p in panels if ancestor in p.get('ancestors',[])]
        if scope:return scope
    return panels if not fitting.get('ancestors') else []

def hardware_hosts(fitting,panels):
    links=set(fitting.get('connected_panel_uids',[]))
    exact={p['id'] for p in panels if p.get('uid') is not None and p['uid'] in links}
    if exact:return exact
    if links:return set()  # Never replace an explicit external BAZIS link with proximity.
    # Bounds contact is a preview association, not evidence of a joint type.
    def touches(p):
        return all(fitting['bounds']['min'][i]<=p['bounds']['max'][i]+.5 and fitting['bounds']['max'][i]>=p['bounds']['min'][i]-.5 for i in range(3))
    return {p['id'] for p in hardware_scope(fitting,panels) if touches(p)}

def assign_hardware(hardware,panels):
    """One owner per physical fitting; retain method for review in sidecar."""
    for f in hardware:
        f.pop('host_panel_id',None);f.pop('host_method',None)
        hosts=hardware_hosts(f,panels)
        candidates=[p for p in panels if p['id'] in hosts]
        if not candidates:continue
        def overlap(p):
            lengths=[max(0,min(f['bounds']['max'][i],p['bounds']['max'][i])-max(f['bounds']['min'][i],p['bounds']['min'][i])) for i in range(3)]
            volume=math.prod(lengths)
            distance=sum((center(f)[i]-center(p)[i])**2 for i in range(3))
            return volume,-distance
        f['host_panel_id']=max(candidates,key=overlap)['id']
        f['host_method']='BAZIS links / max overlap' if f.get('connected_panel_uids') else 'bounds overlap - unvalidated'

def role(p,nodes,reference_frame=None):
    """Geometric orientation only; object and ancestor names are not consulted."""
    basis=(reference_frame or {}).get('axes',[[1,0,0],[0,1,0],[0,0,1]])
    normal=(p.get('frame') or {}).get('axes',[])
    if len(normal)==3:
        axis=max(range(3),key=lambda i:abs(sum(normal[2][j]*basis[i][j] for j in range(3))))
    else:
        dims=[b-a for a,b in zip(p['bounds']['min'],p['bounds']['max'])]
        axis=min(range(3),key=lambda i:dims[i])
    if axis==0:return 'side'
    if axis==1:return 'horizontal'
    return 'back' if p['thickness']<=6 else 'face'

def structural_parent(parts,nodes,root,reference_frame):
    """Infer a structural group from direct boards on several planes."""
    direct={}
    for p in parts:direct.setdefault(p.get('parent'),[]).append(p)
    def score(item):
        parent,boards=item
        planes={'face' if (r:=role(p,nodes,reference_frame))=='back' else r for p in boards}
        chain=boards[0].get('ancestors',[])
        depth=chain.index(parent)-chain.index(root) if parent in chain and root in chain else len(chain)
        return (len(planes)>=2,-depth,len(boards))
    return max(direct.items(),key=score)[0] if direct else root

def mounting_stage(p,nodes,primary=None,reference_frame=None):
    r=role(p,nodes,reference_frame)
    return 1 if r=='back' else 2 if r=='face' else 0

def local_center(p,reference_frame=None):
    frame=reference_frame or {};origin=frame.get('origin',[0,0,0])
    basis=frame.get('axes',[[1,0,0],[0,1,0],[0,0,1]])
    point=center(p)
    return [sum((point[j]-origin[j])*axis[j] for j in range(3)) for axis in basis]

def designation_order(p):
    value=str(p.get('designation') or '').strip()
    if not value:return (1,())
    return (0,tuple((0,int(part)) if part.isdigit() else (1,part.casefold())
                    for part in re.split(r'(\d+)',value) if part))

def make_plan(report):
    nodes={n['id']:n for n in report['nodes']};groups={}
    for p in report['panels']:
        candidates=[a for a in p.get('ancestors',[]) if a in nodes and re.fullmatch(r'M\d+',nodes[a]['name'],re.I)]
        root=candidates[0] if candidates else next((a for a in p.get('ancestors',[])[1:] if a in nodes),p['parent'] or p['id'])
        groups.setdefault(root,[]).append(p)
    modules=[]
    for root,parts in groups.items():
        reference_frame=nodes.get(root,{}).get('frame')
        primary=structural_parent(parts,nodes,root,reference_frame)
        def key(p):
            r=role(p,nodes,reference_frame);stage=mounting_stage(p,nodes,primary,reference_frame)
            position=local_center(p,reference_frame)
            # Sweep side/horizontal boards together, regardless of subgroup depth.
            # Face boards enter from positive local Z. Seat deeper boards first,
            # before the outer face closes access. This is not collision solving.
            if r=='face':return (stage,round(position[2],4),round(position[0],4),designation_order(p),position[1])
            return (stage,round(position[0],4),{'side':0,'horizontal':1,'back':2,'face':3}[r],designation_order(p),position[1],position[2])
        ordered=sorted(parts,key=key);steps=[]
        for i,p in enumerate(ordered):
            r=role(p,nodes,reference_frame);delta=[0,0,0]
            # Schematic assembly motion, deliberately not a collision solver.
            if i:
                if r in ('side','horizontal'):delta=[180,0,0]
                elif r=='back':delta=[0,0,-160]
                elif r=='face':delta=[0,0,180]
                else:delta=[0,120,0]
            steps.append({'panel_id':p['id'],'offset_mm':delta,'role':r,'mounting_stage':mounting_stage(p,nodes,primary,reference_frame),'center_module_local_mm':local_center(p,reference_frame),'instruction':'Așază piesa de pornire.' if i==0 else 'Adu placa în poziția indicată. Verifică îmbinările înainte de fixare.'})
        modules.append({'id':root,'name':nodes.get(root,{}).get('name','Corp'),'structural_group_id':primary,'order_source':'local-X sweep of side/horizontal boards; back boards follow; face boards by increasing local Z before outer closure; numeric code breaks ties','steps':steps})
    return {'schema':1,'status':'draft_unvalidated','modules':modules}

VIEW_Y=math.radians(-20)
VIEW_X=math.radians(20)
def project(p):
    sy,cy=math.sin(VIEW_Y),math.cos(VIEW_Y);sx,cx=math.sin(VIEW_X),math.cos(VIEW_X)
    return cy*p[0]+sy*p[2],sx*sy*p[0]+cx*p[1]-sx*cy*p[2]

def choose_page(items):
    points=[project(v) for p in items for edge in p.get('edges') or box_edges(p) for v in edge]
    if not points:return (842,595)
    width=max(v[0] for v in points)-min(v[0] for v in points)+100
    height=max(v[1] for v in points)-min(v[1] for v in points)+100
    return max(((842,595),(595,842)),key=lambda size:min((size[0]-90)/width,(size[1]-150)/height))

def repetition_key(p,step,preview=False):
    # User's BAZIS designation is the authoritative identical-part key.
    if not p.get('designation') or not p.get('parent') or not any(step['offset_mm']):return None
    return json.dumps([p['parent'],p['designation'],step['role'],step['offset_mm']],sort_keys=True)

def display_steps(report,module):
    parts={p['id']:p for p in report['panels']};result=[];phase=None;within={}
    counts={}
    for p in report['panels']:
        for ancestor in p.get('ancestors',[]):counts[ancestor]=counts.get(ancestor,0)+1
    preview=report.get('geometry_source','').startswith('MCP')
    for step in module['steps']:
        p=parts[step['panel_id']]
        # Ignore per-board assembly wrappers (one board plus its fittings).
        parent=next((a for a in reversed(p.get('ancestors',[])) if counts.get(a,0)>1),p.get('parent'))
        k=repetition_key(dict(p,parent=parent),step,preview)
        current=(parent,step['role'],tuple(step['offset_mm']))
        # Same mounting stage only. Never jump across a base/side/back/door stage.
        if current!=phase or k is None:within={};phase=current
        if k is not None and k in within and len(within[k]['instances'])<12:
            within[k]['instances'].append(step)
        else:
            op={'key':k,'instances':[step]};result.append(op)
            if k is not None:within[k]=op
    return result

def draw_scene(c,parts,new_id,offset,frame,all_parts,hardware=None,mark_hardware=False,hide_hidden=False,color_hardware=False,label_all=False):
    new_ids=set(new_id if isinstance(new_id,list) else [new_id])
    x,y,w,h=frame
    extrema=[]
    for p in all_parts:
        for edge in p.get('edges') or box_edges(p):
            extrema.extend(project(v) for v in edge)
    for p in parts+(hardware or []):
        fresh=p['id'] in new_ids or (p.get('kind')=='hardware' and p.get('host_panel_id') in new_ids)
        if fresh and any(offset):
            for edge in p.get('edges') or box_edges(p):extrema.extend(project([v[i]+offset[i] for i in range(3)]) for v in edge)
    # Fit both the exploded position and its destination, with proportional margins.
    detail=all(p.get('kind')=='hardware' for p in all_parts)
    span=max(max(p[i] for p in extrema)-min(p[i] for p in extrema) for i in (0,1))
    pad=max(1,span*.10) if detail else max(20,min(240,span*.08))
    xmin=min(p[0] for p in extrema)-pad;xmax=max(p[0] for p in extrema)+pad
    ymin=min(p[1] for p in extrema)-pad;ymax=max(p[1] for p in extrema)+pad
    scale=min(w/max(1,xmax-xmin),h/max(1,ymax-ymin))
    def pt(v,d=(0,0,0)):
        a,b=project([v[i]+d[i] for i in range(3)])
        return x+w/2+(a-(xmin+xmax)/2)*scale,y+h/2+(b-(ymin+ymax)/2)*scale
    mask=None
    if hide_hidden:
        from visibility import DepthMask,board_faces
        mask=DepthMask(frame,pt,scale)
        for p in parts:
            d=offset if p['id'] in new_ids else [0,0,0]
            for face in board_faces(p,d):mask.polygon(face)
    for p in sorted(parts+(hardware or []),key=lambda p:center(p)[2]):
        fresh=p['id'] in new_ids or (p.get('kind')=='hardware' and p.get('host_panel_id') in new_ids);d=offset if fresh else [0,0,0]
        fitting=p.get('kind')=='hardware'
        c.setStrokeColor(HARDWARE if fitting and (fresh or color_hardware) else BLUE if fresh else HexColor('#737b82'));c.setLineWidth(.20 if fitting else .25)
        for a,b in p.get('edges') or box_edges(p):
            a=[a[i]+d[i] for i in range(3)];b=[b[i]+d[i] for i in range(3)]
            for aa,bb in mask.segments(a,b) if mask else [(a,b)]:c.line(*pt(aa),*pt(bb))
        if fitting and mark_hardware:
            a=pt(center(p));c.setFillColor(HARDWARE);c.setFont('Body',7);c.drawString(a[0]+3,a[1]+3,p.get('label',''))
    for p in [p for p in parts if p['id'] in new_ids]:
        a=pt(center(p),offset);b=pt(center(p))
        if any(offset):
            c.setStrokeColor(BLUE);c.setFillColor(BLUE);c.setLineWidth(.35);c.line(*a,*b)
            angle=math.atan2(b[1]-a[1],b[0]-a[0]);path=c.beginPath();path.moveTo(*b)
            for da in [-.5,.5]:path.lineTo(b[0]-10*math.cos(angle+da),b[1]-10*math.sin(angle+da))
            path.close();c.drawPath(path,fill=1,stroke=0)
    labelled=[p for p in parts if label_all or p['id'] in new_ids]
    for p in labelled:
        a=pt(center(p),offset if p['id'] in new_ids else [0,0,0])
        c.setFillColor(BLUE);c.circle(a[0],a[1]+17,9,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1);c.setFont('Body',9);c.drawCentredString(a[0],a[1]+14,str(p['label']))
    return pt

def write_pdf(report,output,plan,work_views=None,include_final=True,before_step=None,progress=None):
    W,H=842,595
    font=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'arial.ttf'
    pdfmetrics.registerFont(TTFont('Body',str(font)))
    parts={p['id']:p for p in report['panels']}
    hardware=[p for p in report.get('hardware',[]) if not p.get('hidden') and p.get('bounds',{}).get('min') and p.get('bounds',{}).get('max')]
    assign_hardware(hardware,report['panels'])
    for i,p in enumerate(hardware,1):p.update(kind='hardware',label=f'F{i:03d}')
    for i,p in enumerate(report['panels'],1):p['label']=i
    pages=0
    with tempfile.NamedTemporaryFile(suffix='.pdf',dir=output.parent,delete=False) as f:tmp=Path(f.name)
    try:
        c=canvas.Canvas(str(tmp),pagesize=(W,H));c.setTitle('Asamblare - '+Path(report.get('model','Model')).stem)
        def header(title,sub,items=None):
            nonlocal pages,W,H
            if progress:progress(title)
            W,H=choose_page(items) if items else (842,595);c.setPageSize((W,H))
            pages+=1;c.setFillColor(HexColor('#172b3a'));c.setFont('Body',20);c.drawString(35,H-43,title[:80])
            c.setFont('Body',10);c.drawString(35,H-64,sub[:130])
            if before_step is None:
                c.setFillColorRGB(.4,.4,.4);c.drawRightString(W-35,24,str(pages))
        for module in plan['modules']:
            mp=[parts[s['panel_id']] for s in module['steps']]
            mh=[p for p in hardware if module['id'] in p.get('ancestors',[]) or p.get('module_id')==module['id']]
            ids={p['id'] for p in mp}
            mh=[p for p in mh if p.get('host_panel_id') in ids or
                (not p.get('host_panel_id') and (scope:=hardware_scope(p,report['panels'])) and all(q['id'] in ids for q in scope))]
            if work_views and module['id'] in work_views:
                mp,mh=work_views[module['id']]
                view_parts={p['id']:p for p in mp}
            else:view_parts=parts
            from inventory_layout import inventory_rows,draw_inventory_rows,draw_numbered_labels
            pending=list(mp)
            while pending:
                header(module['name']+' | Inventar plăci','')
                table_x=W*.49;table_width=W-table_x-30;available=H-155;batch=[];used=0
                for row in inventory_rows(pending,table_width):
                    if batch and (used+row[2]>available or len(batch)>=32):break
                    batch.append(row);used+=row[2]
                shown=[row[0] for row in batch];pending=pending[len(batch):]
                figure=(30,65,table_x-50,H-155)
                point=draw_scene(c,mp,None,[0,0,0],(figure[0]+35,figure[1],figure[2]-70,figure[3]),mp+mh,hardware=mh,color_hardware=True)
                draw_numbered_labels(c,shown,point,figure)
                draw_inventory_rows(c,batch,table_x,H-95,table_width)
                c.showPage()
            if mh:
                by_article={}
                for fitting in mh:
                    key=(fitting['name'].split('\r')[0],fitting.get('article',''))
                    by_article.setdefault(key,[]).append(fitting)
                fitting_groups=list(by_article.values())
                for start in range(0,len(fitting_groups),8):
                    header(module['name']+' | Inventar feronerie',f'{len(mh)} articole')
                    draw_scene(c,mp,None,[0,0,0],(25,65,355,440),mp+mh,hardware=mh,color_hardware=True)
                    for j,instances in enumerate(fitting_groups[start:start+8]):
                        fitting=instances[0];yy=H-100-j*54
                        c.setFillColor(HARDWARE);c.setFont('Body',9);c.drawString(405,yy,f"{fitting['label']}   × {len(instances)}"+(f"   | {fitting['article']}" if fitting.get('article') else ''))
                        c.setFillColorRGB(.1,.1,.1);c.setFont('Body',8)
                        for k,line in enumerate(simpleSplit(fitting['name'].split('\r')[0],'Body',8,300)[:3]):c.drawString(405,yy-12-k*10,line)
                        draw_scene(c,[],None,[0,0,0],(725,yy-35,85,42),[fitting],hardware=[fitting],color_hardware=True)
                    c.showPage()
            assembled=[]
            for i,operation in enumerate(display_steps(report,module),1):
                step=operation['instances'][0];p=view_parts[step['panel_id']]
                added=[view_parts[s['panel_id']] for s in operation['instances']]
                if before_step:before_step(c,module,i,added,mp,mh,header)
                labels=', '.join(f"{q['label']:02d}" for q in added)
                header(f"{module['name']} | Pasul {i:02d}",f"{'Plăcile' if len(added)>1 else 'Placa'} {labels} - {p['designation'] or p['id']} - {p['name']}"+(f" | {len(added)} buc." if len(added)>1 else ''),mp)
                seated={p['id'] for p in assembled+added}
                installed=[f for f in mh if f.get('host_panel_id') in seated]
                draw_scene(c,assembled+added,[q['id'] for q in added],step['offset_mm'],(45,60,W-90,H-155),mp,hardware=installed,hide_hidden=True)
                assembled.extend(added)
                c.showPage()
            if mh and before_step is None:
                header(module['name']+' | Complet','',mp+mh)
                draw_scene(c,mp,None,[0,0,0],(45,55,W-90,H-150),mp+mh,hardware=mh,hide_hidden=True)
                c.showPage()
        if include_final:
            all_parts=list(parts.values())
            header('Ansamblu complet','',all_parts+hardware)
            draw_scene(c,all_parts,None,[0,0,0],(35,60,W-70,H-150),all_parts+hardware,hardware=hardware,hide_hidden=True)
            c.setFillColorRGB(.2,.2,.2);c.setFont('Body',10)
            c.drawString(35,40,' | '.join(m['name'] for m in plan['modules'])[:140])
            c.showPage()
        c.save();os.replace(tmp,output)
    finally:
        if tmp.exists():tmp.unlink()
    return pages

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--plan');ap.add_argument('--sample-module');ap.add_argument('--layout',choices=['hierarchical','steps'],default='hierarchical');ap.add_argument('--progress',action='store_true');a=ap.parse_args()
    def progress(message):
        if a.progress:print(message,file=sys.stderr,flush=True)
    progress('Citire date exportate din BAZIS...')
    report=clean_report(json.loads(Path(a.input).read_text(encoding='utf-8-sig')));out=Path(a.output).resolve()
    from holes import add_hole_edges
    add_hole_edges(report)
    if out.suffix.lower()!='.pdf':raise ValueError('Destinația trebuie să fie PDF.')
    if not report.get('panels'):raise ValueError('Nu există plăci.')
    progress('Calcul ordine de montaj si asociere feronerie...')
    plan=json.loads(Path(a.plan).read_text(encoding='utf-8')) if a.plan else make_plan(report)
    expected=[p['id'] for p in report['panels']];actual=[s['panel_id'] for m in plan['modules'] for s in m['steps']]
    if len(actual)!=len(set(actual)) or set(actual)!=set(expected):raise ValueError('Planul trebuie să includă fiecare exemplar exact o dată.')
    for m in plan['modules']:
        for s in m['steps']:
            if len(s['offset_mm'])!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in s['offset_mm']):raise ValueError('Direcție invalidă.')
    if a.layout=='hierarchical':
        from hierarchical import write_hierarchical
        pages=write_hierarchical(report,out,plan,a.sample_module,progress=progress)
    else:pages=write_pdf(report,out,plan,progress=progress)
    progress('Salvare raport de asamblare...')
    out.with_suffix('.assembly.json').write_text(json.dumps({'report':report,'plan':plan},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'panels':len(expected),'hardware':len(report.get('hardware',[])),'pages':pages,'pdf':str(out)},ensure_ascii=False))

if __name__=='__main__':main()
