"""Experimental native board dimension sheets. No hardware drawing or model edits."""
import argparse
import json
import math
from decimal import Decimal,ROUND_HALF_UP
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
    if value is None:return '?'
    rounded=Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    if rounded==0:return '0'
    return format(rounded,'f').rstrip('0').rstrip('.')


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
                row.update(verified_rectangle=True,through=sz[0]<=low+.01 and sz[1]>=high-.01,corners=corners,x=min(p[0] for p in corners)-lo[0],y=min(p[1] for p in corners)-lo[1],
                    start=[a[0]+normal[0]*sx[0]-lo[0],a[1]+normal[1]*sx[0]-lo[1]],
                    end=[b[0]+normal[0]*sx[0]-lo[0],b[1]+normal[1]*sx[0]-lo[1]],length=length,width=sx[1]-sx[0],profile_depth=sz[1]-sz[0],face=face)
        rows.append(row)
    return rows

def dimension_label(c,x,y,label,secondary_colors):
    layout=getattr(c,'annotation_layout',None)
    if layout:
        layout.draw(c,x,y,label,centered=True,secondary_colors=secondary_colors,leader=False)
    else:
        c.drawCentredString(x,y,label)
        half=min(3,stringWidth(label,'Body',7)*.375)
        for index,color in enumerate(secondary_colors):
            c.setStrokeColor(color);c.line(x-half,y-3.5-index*2.2,x+half,y-3.5-index*2.2)


def dimension(c,a,b,offset,label,vertical=False,color=None,secondary_colors=()):
    c.saveState();c.setStrokeColorRGB(.28,.28,.28);c.setFillColorRGB(.15,.15,.15);c.setLineWidth(.2);c.setFont('Body',7)
    if color is not None:c.setStrokeColor(color);c.setFillColor(color)
    layout=getattr(c,'annotation_layout',None)
    if layout:
        if vertical:segments=[(a,[offset-3,a[1]]),(b,[offset-3,b[1]]),([offset,a[1]],[offset,b[1]])]
        else:segments=[(a,[a[0],offset-3]),(b,[b[0],offset-3]),([a[0],offset],[b[0],offset])]
        for start,end in segments:layout.add_stroke(c,start,end)
    if vertical:
        x=offset;c.line(a[0],a[1],x-3,a[1]);c.line(b[0],b[1],x-3,b[1]);c.line(x,a[1],x,b[1])
        for y in [a[1],b[1]]:c.line(x-2,y-2,x+2,y+2)
        c.translate(x-(6+max(0,len(secondary_colors)-1)*2.2 if secondary_colors else 3),(a[1]+b[1])/2);c.rotate(90)
        dimension_label(c,0,0,label,secondary_colors)
    else:
        y=offset;c.line(a[0],a[1],a[0],y-3);c.line(b[0],b[1],b[0],y-3);c.line(a[0],y,b[0],y)
        for x in [a[0],b[0]]:c.line(x-2,y-2,x+2,y+2)
        dimension_label(c,(a[0]+b[0])/2,y+(6+max(0,len(secondary_colors)-1)*2.2 if secondary_colors else 3),label,secondary_colors)
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
    from dimension_sheets import write_sheets
    return write_sheets(report,output,progress)


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
