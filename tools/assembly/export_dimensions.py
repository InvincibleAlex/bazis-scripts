"""Experimental native board dimension sheets. No hardware drawing or model edits."""
import argparse
import json
import math
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor,Color
from reportlab.pdfbase.pdfmetrics import stringWidth

W,H=842,595
ORANGE=HexColor('#b15d12')
BLUE=HexColor('#1668b2')

def fmt(value):
    return '?' if value is None else f'{float(value):.3f}'.rstrip('0').rstrip('.')

def xy(p):return [p['x'],p['y']] if isinstance(p,dict) else list(p[:2])

def to_local(panel,point,direction=False):
    f=panel.get('frame')
    if not f:raise ValueError('Lipsește sistemul local nativ al plăcii '+panel['id'])
    return [sum((point[j]-(0 if direction else f['origin'][j]))*axis[j] for j in range(3)) for axis in f['axes']]

def geometry(panel):
    if panel.get('dimension_properties',{}).get('Bent'):raise ValueError('Cotarea plăcilor curbate necesită desfășurata nativă: '+panel['id'])
    bounds=panel.get('local_bounds')
    contour=panel.get('native_contour')
    edges=[]
    if not bounds or not bounds.get('min') or not bounds.get('max') or not contour:
        # Compatibility for existing test reports: project actual native edges,
        # never replace a shaped contour with a fabricated rectangle.
        if panel.get('geometry_source')!='BAZIS Edges.GVertices':raise ValueError('Contur nativ indisponibil: '+panel['id'])
        edges=[[to_local(panel,a),to_local(panel,b)] for a,b in panel.get('edges',[])]
        points=[p for edge in edges for p in edge]
        bounds={'min':[min(p[i] for p in points) for i in range(2)],'max':[max(p[i] for p in points) for i in range(2)]}
    lo,hi=xy(bounds['min']),xy(bounds['max'])
    return lo,hi,contour,edges

def holes_for(panel,lo):
    rows=[]
    for hole in panel.get('holes',[]):
        if not hole.get('coordinate_space_verified') or hole.get('panel_uid')!=panel.get('uid'):raise ValueError('Gaură fără asociere/coordonate confirmate: '+panel['id'])
        p=hole.get('position_panel_local_mm') or to_local(panel,hole['position_global_mm'])
        d=hole.get('direction_panel_local') or to_local(panel,hole['direction_global'],True)
        if abs(d[2])>.999:face='Zmin' if d[2]>0 else 'Zmax'
        elif abs(d[0])>.999:face='Xmin' if d[0]>0 else 'Xmax'
        elif abs(d[1])>.999:face='Ymin' if d[1]>0 else 'Ymax'
        else:face='oblică'
        rows.append(dict(tag=f'G{len(rows)+1:02}',x=p[0]-lo[0],y=p[1]-lo[1],z=p[2],position=p,direction=d,
            diameter=hole.get('diameter_mm'),depth=hole.get('depth_mm'),face=face))
    return rows

def flatten(contour):
    for e in (contour or {}).get('elements',[]):
        if e.get('type')=='list':yield from flatten(e.get('contour'))
        else:yield e

def milling_for(panel,lo):
    rows=[]
    for cut in panel.get('machining',{}).get('cuts',[]):
        params=cut.get('params') or {};trajectory=list(flatten(cut.get('trajectory')));section=list(flatten(cut.get('section')))
        row={'tag':f'F{len(rows)+1:02}','name':cut.get('properties',{}).get('Name') or params.get('Name') or 'Frezare',
            'native_type':params.get('CutType'),'depth':params.get('Depth'),'width':params.get('Width'),'offset':params.get('Offset'),
            'trajectory':trajectory,'verified_rectangle':False}
        # The section coordinates describe transverse offset and panel-local Z.
        # Restrict footprint dimensions to a straight path + rectangular profile.
        if len(trajectory)==1 and trajectory[0].get('type')=='line' and len(section)==4 and all(e.get('type')=='line' for e in section):
            a=xy(trajectory[0]['start']);b=xy(trajectory[0]['end']);dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
            pts=[xy(e[k]) for e in section for k in ['start','end']]
            sx=sorted(set(round(p[0],6) for p in pts));sz=sorted(set(round(p[1],6) for p in pts))
            axis_aligned=all(abs(xy(e['start'])[0]-xy(e['end'])[0])<1e-6 or abs(xy(e['start'])[1]-xy(e['end'])[1])<1e-6 for e in section)
            if length>0 and len(sx)==2 and len(sz)==2 and axis_aligned:
                normal=[-dy/length,dx/length]
                corners=[[p[0]+normal[0]*offset,p[1]+normal[1]*offset] for p,offset in [(a,sx[0]),(b,sx[0]),(b,sx[1]),(a,sx[1])]]
                native_points=[to_local(panel,v) for edge in panel.get('edges',[]) for v in edge] if panel.get('geometry_source')=='BAZIS Edges.GVertices' else []
                if not all(any(math.dist(q,v[:2])<.001 for v in native_points) for q in corners):
                    row['verification_note']='Amprenta secțiunii nu coincide cu vârfurile geometriei native';rows.append(row);continue
                low=(panel.get('z_limits') or {}).get('LowZ',0);high=(panel.get('z_limits') or {}).get('HighZ',panel['thickness'])
                face='Zmin' if abs(sz[0]-low)<1e-5 else 'Zmax' if abs(sz[1]-high)<1e-5 else 'profil interior'
                row.update(verified_rectangle=True,corners=corners,x=min(p[0] for p in corners)-lo[0],y=min(p[1] for p in corners)-lo[1],
                    start=[a[0]+normal[0]*sx[0]-lo[0],a[1]+normal[1]*sx[0]-lo[1]],
                    end=[b[0]+normal[0]*sx[0]-lo[0],b[1]+normal[1]*sx[0]-lo[1]],length=length,width=sx[1]-sx[0],profile_depth=sz[1]-sz[0],face=face)
        rows.append(row)
    return rows

def dimension(c,a,b,offset,label,vertical=False,color=None):
    c.saveState();c.setStrokeColorRGB(.28,.28,.28);c.setFillColorRGB(.15,.15,.15);c.setLineWidth(.35);c.setFont('Body',7)
    if color is not None:c.setStrokeColor(color);c.setFillColor(color)
    if vertical:
        x=offset;c.line(a[0],a[1],x-3,a[1]);c.line(b[0],b[1],x-3,b[1]);c.line(x,a[1],x,b[1])
        for y in [a[1],b[1]]:c.line(x-2,y-2,x+2,y+2)
        c.translate(x-3,(a[1]+b[1])/2);c.rotate(90);c.drawCentredString(0,0,label)
    else:
        y=offset;c.line(a[0],a[1],a[0],y-3);c.line(b[0],b[1],b[0],y-3);c.line(a[0],y,b[0],y)
        for x in [a[0],b[0]]:c.line(x-2,y-2,x+2,y+2)
        c.drawCentredString((a[0]+b[0])/2,y+3,label)
    c.restoreState()

def curve(c,e,project):
    kind=e.get('type')
    if kind=='line':c.line(*project(xy(e['start'])),*project(xy(e['end'])))
    elif kind=='circle':
        p=xy(e['center']);a=project(p);b=project([p[0]+e['radius'],p[1]]);c.circle(*a,abs(b[0]-a[0]),stroke=1,fill=0)
    elif kind=='arc':
        center=xy(e['center']);a=xy(e['start']);b=xy(e['end']);radius=math.dist(a,center)
        start=math.atan2(a[1]-center[1],a[0]-center[0]);end=math.atan2(b[1]-center[1],b[0]-center[0])
        sweep=(end-start)%(2*math.pi) if e.get('counterclockwise') else -((start-end)%(2*math.pi))
        count=max(8,min(720,math.ceil(abs(sweep)*radius/.5)));path=c.beginPath();path.moveTo(*project(a))
        for i in range(1,count+1):path.lineTo(*project([center[0]+radius*math.cos(start+sweep*i/count),center[1]+radius*math.sin(start+sweep*i/count)]))
        c.drawPath(path)
    else:return False
    return True

def dimension_positions(values,tolerance=.01):
    groups=[]
    for value in sorted(values):
        if groups and value-groups[-1][0]<=tolerance:groups[-1].append(value)
        else:groups.append([value])
    result=[]
    for group in groups:
        value=sum(group)/len(group)
        if abs(value-round(value))<=tolerance:value=float(round(value))
        result.append(value)
    return result

def hole_labels(holes,project):
    occupied=[];result=[]
    for hole in sorted(holes,key=lambda h:(-h['y'],h['x'])):
        x,y=project(hole['position']);width=stringWidth(hole['tag'],'Body',6)
        choices=[(4,4),(4,-10),(-width-4,4),(-width-4,-10),(5,12),(5,-18),(-width-5,12),(-width-5,-18)]
        selected=None
        for dx,dy in choices:
            box=(x+dx,y+dy-1,x+dx+width,y+dy+7)
            if box[0]<35 or box[2]>605 or box[1]<100 or box[3]>505:continue
            if any(not(box[2]+1<a or c+1<box[0] or box[3]+1<b or d+1<box[1]) for a,b,c,d in occupied):continue
            selected=(box,(x+dx,y+dy));break
        if selected is None:selected=((x+4,y+4,x+4+width,y+11),(x+4,y+4))
        occupied.append(selected[0]);result.append((hole,selected[1]))
    return result


def write_dimensions(report,output,progress=None):
    pdfmetrics.registerFont(TTFont('Body','C:/Windows/Fonts/arial.ttf'))
    panels=report.get('panels',[]);prepared=[]
    for panel in panels:
        lo,hi,contour,edges=geometry(panel);holes=holes_for(panel,lo);cuts=milling_for(panel,lo)
        prepared.append((panel,lo,hi,contour,edges,holes,cuts))
    total=sum(max(1,math.ceil(len(holes)/22),math.ceil(len(cuts)/3)) for _,_,_,_,_,holes,cuts in prepared)
    c=canvas.Canvas(str(output),pagesize=(W,H));c.setTitle('Export Cote');page=0
    for number,(p,lo,hi,contour,edges,holes,cuts) in enumerate(prepared,1):
        width,height=hi[0]-lo[0],hi[1]-lo[1]
        if width<=0 or height<=0:raise ValueError('Contur cu dimensiuni invalide')
        copies=max(1,math.ceil(len(holes)/22),math.ceil(len(cuts)/3))
        for part in range(copies):
            page+=1
            number=p.get("label",number)
            if progress:progress('Desen: Cotare placa '+str(number))
            c.setFillColor(HexColor('#172b3a'));c.setFont('Body',17);c.drawString(35,554,f'Placa {number:02} | {p.get("designation") or p["id"]} | {p.get("name","")}'[:98])
            c.setFont('Body',9);c.drawString(35,535,f'{fmt(width)} × {fmt(height)} × {fmt(p["thickness"])} mm | {p.get("material","")}'[:135])
            c.setFont('Body',8);c.drawString(35,519,'Vedere dinspre +Z local. Origine cote: Xmin/Ymin. Contur și prelucrări din date BAZIS.')
            scale=min(460/width,310/height);left=130+(460-width*scale)/2;bottom=180+(310-height*scale)/2
            project=lambda q:(left+(q[0]-lo[0])*scale,bottom+(q[1]-lo[1])*scale)
            c.setStrokeColor(BLUE);c.setLineWidth(.65);unsupported=0
            if contour:
                for e in flatten(contour):unsupported+=not curve(c,e,project)
            else:
                for a,b in edges:c.line(*project(a),*project(b))
            cx,cy=project([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2])
            c.setFillColor(BLUE);c.circle(cx,cy,9,stroke=0,fill=1)
            c.setFillColorRGB(1,1,1);c.setFont('Body',8);c.drawCentredString(cx,cy-3,str(number))
            dimension(c,project(lo),project([hi[0],lo[1]]),bottom-18,fmt(width))
            dimension(c,project(lo),project([lo[0],hi[1]]),left-18,fmt(height),True)
            c.setFillColor(HexColor('#172b3a'));c.setFont('Body',7);c.drawString(left-5,bottom-10,'0')
            for hole in holes:
                a=project(hole['position']);r=(hole['diameter'] or 0)*scale/2
                c.setStrokeColorRGB(.1,.1,.1);c.setLineWidth(.45);c.setDash(2,2) if hole['face']=='Zmin' else c.setDash()
                if hole['face'].startswith('Z') and r>0:c.circle(*a,r,stroke=1,fill=0)
                c.setDash();c.line(a[0]-3,a[1],a[0]+3,a[1]);c.line(a[0],a[1]-3,a[0],a[1]+3)
            c.setFont('Body',6)
            for hole,tag_position in hole_labels(holes,project):c.drawString(*tag_position,hole['tag'])
            for cut in cuts:
                c.setStrokeColor(ORANGE);c.setLineWidth(.7)
                if cut['verified_rectangle']:
                    path=c.beginPath();path.moveTo(*project(cut['corners'][0]))
                    for q in cut['corners'][1:]:path.lineTo(*project(q))
                    path.close();c.drawPath(path)
                    q=project(cut['corners'][0]);c.setFillColor(ORANGE);c.setFont('Body',8);c.drawString(q[0]+4,q[1]+9,cut['tag'])
                    cut_min=[min(p[i] for p in cut['corners']) for i in range(2)]
                    cut_max=[max(p[i] for p in cut['corners']) for i in range(2)]
                    if abs(cut_max[1]-cut_min[1]-cut['length'])<.001:
                        dimension(c,project([cut_min[0],cut_min[1]]),project([cut_max[0],cut_min[1]]),project(hi)[1]+36,'l '+fmt(cut['width']),color=ORANGE)
                        if cut_min[1]>lo[1]+.001:dimension(c,project([hi[0],lo[1]]),project([hi[0],cut_min[1]]),project(hi)[0]+30,fmt(cut_min[1]-lo[1]),True,color=ORANGE)
                        near_right=hi[0]-cut_max[0]<cut_min[0]-lo[0]
                        edge=hi[0] if near_right else lo[0];groove=cut_max[0] if near_right else cut_min[0]
                        dimension(c,project([groove,hi[1]]),project([edge,hi[1]]),project(hi)[1]+18,fmt(abs(edge-groove)),color=ORANGE)
                        if cut['length']<height-.001:dimension(c,project([hi[0],cut_min[1]]),project([hi[0],cut_max[1]]),project(hi)[0]+18,'L '+fmt(cut['length']),True,color=ORANGE)
                    elif abs(cut_max[0]-cut_min[0]-cut['length'])<.001:
                        dimension(c,project([cut_min[0],cut_min[1]]),project([cut_min[0],cut_max[1]]),left-24,'l '+fmt(cut['width']),True,color=ORANGE)
                        if cut_min[0]>lo[0]+.001:dimension(c,project([lo[0],hi[1]]),project([cut_min[0],hi[1]]),project(hi)[1]+30,fmt(cut_min[0]-lo[0]),color=ORANGE)
                        near_top=hi[1]-cut_max[1]<cut_min[1]-lo[1]
                        edge=hi[1] if near_top else lo[1];groove=cut_max[1] if near_top else cut_min[1]
                        dimension(c,project([hi[0],groove]),project([hi[0],edge]),project(hi)[0]+18,fmt(abs(edge-groove)),True,color=ORANGE)
                        if cut['length']<width-.001:dimension(c,project([cut_min[0],hi[1]]),project([cut_max[0],hi[1]]),project(hi)[1]+18,'L '+fmt(cut['length']),color=ORANGE)
                else:
                    c.setDash(3,2)
                    for e in cut['trajectory']:curve(c,e,project)
                    c.setDash()
            xs=dimension_positions(h['x'] for h in holes if 0<h['x']<width)
            ys=dimension_positions(h['y'] for h in holes if 0<h['y']<height)
            # All coordinates are tabulated; limit dimension ladders to preserve legibility.
            for i,x in enumerate(xs[:5]):dimension(c,project(lo),project([lo[0]+x,lo[1]]),bottom-36-i*11,fmt(x))
            for i,y in enumerate(ys[:5]):dimension(c,project(lo),project([lo[0],lo[1]+y]),left-36-i*11,fmt(y),True)
            c.setFillColorRGB(.1,.1,.1);c.setFont('Body',8);c.drawString(610,486,'Găuri — coordonate și dimensiuni în mm')
            columns=[610,631,662,693,724,750,777];head=['Nr.','X','Y','Z','Ø','Ad.','Intrare']
            c.setFont('Body',6)
            for x,t in zip(columns,head):c.drawString(x,471,t)
            for i,h in enumerate(holes[part*22:(part+1)*22]):
                yy=456-i*12;values=[h['tag'],fmt(h['x']),fmt(h['y']),fmt(h['z']),fmt(h['diameter']),fmt(h['depth']),h['face']]
                for x,t in zip(columns,values):c.drawString(x,yy,t)
                c.setStrokeColorRGB(.85,.85,.85);c.setLineWidth(.2);c.line(610,yy-3,807,yy-3)
            c.setFillColor(ORANGE);c.setFont('Body',9);c.drawString(35,91,'Frezări — cote față de marginile conturului')
            c.setFont('Body',6.5)
            subset=cuts[part*3:(part+1)*3]
            if not cuts:c.drawString(35,77,'Nicio frezare în lista nativă Cuts. Golurile din contur sunt desenate separat.')
            for i,cut in enumerate(subset):
                yy=77-i*17
                if cut['verified_rectangle']:
                    text=f'{cut["tag"]}: Xmin={fmt(cut["x"])}  Ymin={fmt(cut["y"])}  L={fmt(cut["length"])}  l={fmt(cut["width"])}  ad.={fmt(cut["profile_depth"])}  intrare {cut["face"]}'
                    c.drawString(35,yy,text)
                    c.drawString(420,yy,f'Debut ({fmt(cut["start"][0])}, {fmt(cut["start"][1])}) → final ({fmt(cut["end"][0])}, {fmt(cut["end"][1])})')
                else:c.drawString(35,yy,f'{cut["tag"]}: profil de verificat; ad. nativă={fmt(cut["depth"])}; lățime={fmt(cut["width"])}; offset={fmt(cut["offset"])}. Amprenta nu este dedusă.')
            c.setFillColorRGB(.35,.35,.35);c.setFont('Body',7)
            note='Zmin: cerc întrerupt; Zmax: cerc continuu; muchie: reper la intrarea găurii.'
            if unsupported:note+=' Elemente de contur nesuportate: '+str(unsupported)
            c.drawString(35,22,note);c.drawRightString(807,22,f'{page} / {total}');c.showPage()
    c.save()
    return {'pages':page,'holes':sum(len(x[5]) for x in prepared),'panels':len(panels),'cuts':sum(len(x[6]) for x in prepared)}

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--progress',action='store_true');args=parser.parse_args()
    source=json.loads(Path(args.input).read_text(encoding='utf-8-sig'));report=source.get('report',source)
    if not report.get('panels'):raise ValueError('Nu există plăci pentru cotare')
    output=Path(args.output)
    if output.suffix.lower()!='.pdf':raise ValueError('Destinația trebuie să fie PDF')
    progress=(lambda s:print(s,file=sys.stderr,flush=True)) if args.progress else None
    from export_assembly import clean_report,make_plan
    from holes import add_hole_edges
    from hierarchical import write_hierarchical
    report=clean_report(report)
    add_hole_edges(report)
    plan=make_plan(report)
    pages=write_hierarchical(report,output,plan,progress=progress,dimensions=True)
    result={'pages':pages,'panels':len(report['panels']),'holes':sum(len(p.get('holes',[])) for p in report['panels'])}
    output.with_suffix('.cote.json').write_text(json.dumps({'report':report,'dimensions':result,'plan':plan},ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'ok':True,'pdf':str(output),**result},ensure_ascii=False))

if __name__=='__main__':main()
