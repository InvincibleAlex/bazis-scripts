"""Hierarchical assembly presentation; display transforms never alter the model."""
import copy
import math
import tempfile
from io import BytesIO
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from pypdf import PdfReader,PdfWriter
from export_assembly import W,H,box_edges,center,draw_scene,assign_hardware,hardware_scope,norm,write_pdf,choose_page

def union(items):
    return {'min':[min(p['bounds']['min'][i] for p in items) for i in range(3)],'max':[max(p['bounds']['max'][i] for p in items) for i in range(3)]}

def transform(items,fn):
    result=[]
    for p in items:
        q=copy.deepcopy(p)
        q['edges']=[[fn(a),fn(b)] for a,b in p.get('edges') or box_edges(p)]
        points=[v for edge in q['edges'] for v in edge]
        q['bounds']={'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
        if p.get('frame'):
            origin=fn(p['frame']['origin']);q['frame']=copy.deepcopy(p['frame']);q['frame']['origin']=origin
            q['frame']['axes']=[[v-origin[i] for i,v in enumerate(fn([p['frame']['origin'][j]+axis[j] for j in range(3)]))] for axis in p['frame']['axes']]
        if p.get('insertion_axis'):
            zero=fn([0,0,0]);q['insertion_axis']=[v-zero[i] for i,v in enumerate(fn(p['insertion_axis']))]
        result.append(q)
    return result

def translated(items,offset):return transform(items,lambda p:[p[i]+offset[i] for i in range(3)])

def insertion_axis(fitting):
    axis=fitting.get('insertion_axis')
    if axis and math.sqrt(sum(v*v for v in axis))>1e-8:
        length=math.sqrt(sum(v*v for v in axis));return [v/length for v in axis]
    if not any(word in norm(fitting['name']) for word in ('surub','diblu')):return None
    edges=fitting.get('edges') or box_edges(fitting)
    vectors=[[b[i]-a[i] for i in range(3)] for a,b in edges]
    lengths=[math.sqrt(sum(v*v for v in d)) for d in vectors];longest=max(lengths,default=0)
    if longest<=0:return None
    axes=[[v/length for v in d] for d,length in zip(vectors,lengths) if length>=longest*.99]
    reference=axes[0]
    if not all(abs(sum(a*b for a,b in zip(reference,d)))>.995 for d in axes):return None
    return reference

def axial_explode(plate,fittings,distance=180):
    result=[];pc=center(plate)
    for fitting in fittings:
        axis=insertion_axis(fitting)
        if axis is None:
            q=copy.deepcopy(fitting);q['explosion_status']='axis unavailable; not displaced';result.append(q);continue
        outward=sum((center(fitting)[i]-pc[i])*axis[i] for i in range(3))
        delta=[v*distance*(1 if outward>=0 else -1) for v in axis]
        q=translated([fitting],delta)[0];q['explosion_offset']=delta;q['insertion_axis']=axis;q['explosion_status']='axial'
        result.append(q)
    return result

def preparation_batches(panels):
    batches={}
    for p in panels:batches.setdefault(p.get('designation') or ('instance',p['id']),[]).append(p)
    return list(batches.values())

def frame_for(module,panels,nodes):
    frame=nodes.get(module['id'],{}).get('frame')
    if frame and len(frame.get('axes',[]))==3:return frame
    # MCP has no basis vectors: for this orthogonal preview infer from door plane.
    door=next((p for p in panels if norm(p['name']).startswith(('usa','front'))),None)
    b=door['bounds'] if door else union(panels)
    sizes=[b['max'][i]-b['min'][i] for i in range(3)]
    across_x=sizes[0]<sizes[2]
    axes=[[0,0,-1],[0,1,0],[1,0,0]] if across_x else [[1,0,0],[0,1,0],[0,0,1]]
    return {'origin':center({'bounds':union(panels)}),'axes':axes,'source':'inferred orthogonal door bounds'}

def in_frame(items,frame):
    axes=frame['axes'];origin=frame['origin']
    return transform(items,lambda p:[sum((p[j]-origin[j])*axis[j] for j in range(3)) for axis in axes])

def module_items(report,module):
    ids={s['panel_id'] for s in module['steps']}
    panels=[p for p in report['panels'] if p['id'] in ids]
    all_fittings=[h for h in report.get('hardware',[]) if not h.get('hidden') and h.get('bounds',{}).get('min')]
    # Resolve against the whole model, never against a parent's few loose boards.
    assign_hardware(all_fittings,report['panels'])
    fittings=[]
    for h in all_fittings:
        if module['id'] not in h.get('ancestors',[]):continue
        if h.get('host_panel_id') in ids:fittings.append(h)
        elif not h.get('host_panel_id'):
            scope=hardware_scope(h,report['panels'])
            if scope and all(p['id'] in ids for p in scope):fittings.append(h)
    return panels,fittings

def pack(groups,gap=500):
    """Display-only exploded lineup; preserve each group's internal geometry."""
    result=[];offset=0
    for name,items in groups:
        b=union(items);moved=translated(items,[offset-b['min'][0],-b['min'][1],-b['min'][2]])
        result.append((name,moved));offset+=b['max'][0]-b['min'][0]+gap
    return result

def prepare(report,plan):
    nodes={p['id']:p for p in report['nodes']};views={};groups={}
    for i,p in enumerate(report['panels'],1):p['label']=i
    for i,p in enumerate(report.get('hardware',[]),1):p.update(kind='hardware',label=f'F{i:03d}')
    for module in plan['modules']:
        panels,fittings=module_items(report,module);frame=frame_for(module,panels,nodes)
        views[module['id']]=(in_frame(panels,frame),in_frame(fittings,frame))
        module['view_frame']=frame
        # Prefer actual parent assembly when one exists above the module.
        parent=nodes.get(module['id'],{}).get('parent');parent_name=nodes.get(parent,{}).get('name','')
        if parent and norm(parent_name) not in ('model',''):
            key=('parent',parent);name=parent_name;source='BAZIS parent group'
        elif not module['name'].lower().startswith('m'):
            key=('extras',);name='Completări';source='loose components'
        else:
            direction=tuple(round(v,3) for v in frame['axes'][2]);key=('orientation',direction);name=None;source='inferred orientation group'
        if key not in groups:groups[key]={'name':name or f'Tronson {1+sum(k[0]!="extras" for k in groups)}','source':source,'modules':[]}
        groups[key]['modules'].append(module)
    plan['presentation_groups']=list(groups.values())
    return views,list(groups.values())

def exploded_groups(module,panels,fittings,nodes):
    buckets={};branches={}
    for p in panels:
        chain=p.get('ancestors',[])
        branch=chain[chain.index(module['id'])+1] if module['id'] in chain and chain.index(module['id'])+1<len(chain) else p['id']
        name=nodes.get(branch,{}).get('name',p['name'].split('\r')[0]);key=(branch,name);branches[p['id']]=key;buckets.setdefault(key,[]).append(p)
    for p in fittings:
        key=branches.get(p.get('host_panel_id'))
        if key is None:
            chain=p.get('ancestors',[]);branch=chain[chain.index(module['id'])+1] if module['id'] in chain and chain.index(module['id'])+1<len(chain) else p['id']
            key=(branch,nodes.get(branch,{}).get('name',p['name'].split('\r')[0]))
        buckets.setdefault(key,[]).append(p)
    result=[];size=union(panels);width=size['max'][0]-size['min'][0]
    for (branch,name),items in buckets.items():
        n=norm(name)
        if 'carcas' in n:delta=[0,0,0]
        elif 'raft' in n or 'compartiment' in n:delta=[-width-350,0,0]
        elif 'usa' in n or 'usi' in n:delta=[width+350,0,0]
        elif 'picior' in n or 'soclu' in n:delta=[0,-550,0]
        else:delta=[width+350,0,0]
        moved=translated(items,delta);boards=[p for p in moved if p.get('kind')!='hardware'];by={p['id']:p for p in boards};display=list(boards)
        for fitting in [p for p in moved if p.get('kind')=='hardware']:
            host=by.get(fitting.get('host_panel_id'))
            if host:display.extend(axial_explode(host,[fitting]))
            else:
                # A standalone fitting has no validated group translation.
                original=next(p for p in items if p['id']==fitting['id'])
                display.extend(axial_explode({'bounds':size},[original]))
        result.append((name,display))
    return result

def exploded_boards(panels,fittings=None):
    b=union(panels);cx=(b['min'][0]+b['max'][0])/2;cy=(b['min'][1]+b['max'][1])/2
    groups=[]
    for p in panels:
        sizes=[p['bounds']['max'][i]-p['bounds']['min'][i] for i in range(3)];axis=min(range(3),key=lambda i:sizes[i]);delta=[0,0,0]
        if axis==0:delta[0]=-220 if center(p)[0]<cx else 220
        elif axis==1:delta[1]=-280 if center(p)[1]<cy else 280
        else:delta[2]=-350
        plate=translated([p],delta)[0]
        attached=translated([h for h in fittings or [] if h.get('host_panel_id')==p['id']],delta)
        groups.append((str(p['label']),[plate]+axial_explode(plate,attached)))
    return groups

def plate_view(p,fittings):
    frame=p.get('frame')
    if frame:normal=in_frame([p]+fittings,frame)
    else:
        b=p['bounds'];sizes=[b['max'][i]-b['min'][i] for i in range(3)]
        thin=min(range(3),key=lambda i:sizes[i]);plane=[i for i in range(3) if i!=thin]
        # Put the longer face dimension along the horizontal display axis.
        plane.sort(key=lambda i:sizes[i],reverse=True)
        normal=transform([p]+fittings,lambda v:[v[plane[0]]-b['min'][plane[0]],v[plane[1]]-b['min'][plane[1]],v[thin]-b['min'][thin]])
    return transform(normal,lambda v:[v[0],v[2],-v[1]])

def write_hierarchical(report,output,plan,sample_module=None):
    pdfmetrics.registerFont(TTFont('Body','C:/Windows/Fonts/arial.ttf'))
    views,groups=prepare(report,plan);nodes={p['id']:p for p in report['nodes']}
    selected=[m for m in plan['modules'] if sample_module is None or m['name']==sample_module]
    if not selected:raise ValueError('Corpul cerut nu există în model.')
    with tempfile.TemporaryDirectory(prefix='assembly-layout-',dir=output.parent) as temp:
        intro=Path(temp)/'intro.pdf';c=canvas.Canvas(str(intro),pagesize=(W,H));page_count=0;fragments=[];seen_preparation={};cw,ch=W,H
        def header(title,subtitle='',items=None):
            nonlocal page_count,cw,ch
            cw,ch=choose_page(items) if items else (W,H);c.setPageSize((cw,ch))
            page_count+=1;c.setFillColor(HexColor('#172b3a'));c.setFont('Body',18);c.drawString(35,ch-43,title[:80]);c.setFont('Body',9);c.drawString(35,ch-65,subtitle[:130])
        def picture(title,group_items,subtitle=''):
            items=[p for _,objects in group_items for p in objects];header(title,subtitle,items)
            panels=[p for p in items if p.get('kind')!='hardware'];fittings=[p for p in items if p.get('kind')=='hardware']
            point=draw_scene(c,panels,None,[0,0,0],(35,60,cw-70,ch-150),items,hardware=fittings,hide_hidden=True)
            from callouts import draw_callouts
            draw_callouts(c,[(name[:50],[p for p in objects if p.get('kind')!='hardware'] or objects) for name,objects in group_items if name],items,point,(35,60,cw-70,ch-150))
            c.showPage()
        picture('Ansamblu | Vedere izometrică',[('',report['panels']+report.get('hardware',[]))],f'Detaliere montaj: {sample_module}' if sample_module else '')
        packed=[]
        for group in groups:
            members=group['modules'];raw=[p for m in members for pair in [module_items(report,m)] for collection in pair for p in collection]
            frame=members[0]['view_frame'];packed.append((group['name'],in_frame(raw,frame)))
        picture('Ansamblu | Explozie pe tronsoane',pack(packed,900))
        for group in groups:
            packed=[(m['name'],views[m['id']][0]+views[m['id']][1]) for m in group['modules']]
            picture(group['name']+' | Explozie pe corpuri',pack(packed,350))
        c.save();fragments.append(intro)
        for module in selected:
            preparation_file=Path(temp)/f"prep-{module['id']}.pdf";c=canvas.Canvas(str(preparation_file),pagesize=(W,H))
            panels,fittings=views[module['id']]
            picture(module['name']+' | Explozie pe subansambluri',exploded_groups(module,panels,fittings,nodes))
            carcass=[p for p in panels if any('carcas' in norm(nodes.get(a,{}).get('name','')) for a in p.get('ancestors',[]))]
            if carcass:picture(module['name']+' | Carcasă - explozie plăci',exploded_boards(carcass,fittings))
            c.save();fragments.append(preparation_file)
            body=Path(temp)/f"body-{module['id']}.pdf"
            def prepare_step(target,active_module,step_number,added,all_panels,all_fittings,page_header):
                for instances in preparation_batches(added):
                    p=instances[0];code=p.get('designation') or ('instance',p['id'])
                    if code in seen_preparation:continue
                    seen_preparation[code]=active_module['name']
                    matching=[q for q in all_panels if (q.get('designation') or ('instance',q['id']))==code]
                    for q in matching:q['preparation_in']=active_module['name']
                    attached=[h for h in all_fittings if h.get('host_panel_id')==p['id']]
                    view=plate_view(p,attached);plate=view[0];exploded=axial_explode(plate,view[1:])
                    refs=', '.join(str(q['label']) for q in matching)
                    page_header(f"{active_module['name']} | Pregătire placă — pasul {step_number:02d}",f"Placa {refs} - {p['designation']} - {p['name']}"+(f" | {len(matching)} buc." if len(matching)>1 else ''),[plate]+exploded)
                    pw,ph=target._pagesize
                    draw_scene(target,[plate],[plate['id']],[0,0,0],(35,60,pw-70,ph-150),[plate]+exploded,hardware=exploded,hide_hidden=True)
                    target.showPage()
            write_pdf(report,body,dict(plan,modules=[module]),work_views=views,include_final=False,before_step=prepare_step)
            fragments.append(body)
        final_file=Path(temp)/'final.pdf';c=canvas.Canvas(str(final_file),pagesize=(W,H))
        picture('Ansamblu complet',[('',report['panels']+report.get('hardware',[]))]);c.save();fragments.append(final_file)
        plan['preparation_codes']={str(k):v for k,v in seen_preparation.items()}
        writer=PdfWriter()
        for p in fragments:
            reader=PdfReader(p)
            for page in reader.pages:writer.add_page(page)
        # Consistent page numbers across sections; cover the old body-local number.
        total=len(writer.pages)
        for i,page in enumerate(writer.pages,1):
            pw,ph=float(page.mediabox.width),float(page.mediabox.height)
            buf=BytesIO();overlay=canvas.Canvas(buf,pagesize=(pw,ph));overlay.setFillColorRGB(1,1,1);overlay.rect(pw-90,14,75,25,fill=1,stroke=0)
            overlay.setFillColorRGB(.4,.4,.4);overlay.setFont('Body',9);overlay.drawRightString(pw-35,24,f'{i} / {total}');overlay.save();buf.seek(0)
            page.merge_page(PdfReader(buf).pages[0])
        with output.open('wb') as stream:writer.write(stream)
        plan['sample_module']=sample_module
        return len(writer.pages)
