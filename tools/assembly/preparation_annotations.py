"""Preparation-only insertion arrows and native fitting names."""
import math
from reportlab.lib.colors import HexColor
from export_assembly import center
from callouts import draw_callouts

def insertion_arrows(original,moved):
    by_id={h['id']:h for h in original};arrows=[]
    for fitting in moved:
        seated=by_id.get(fitting['id'])
        delta=fitting.get('explosion_offset')
        if not seated or not delta or not any(delta):continue
        targets=seated.get('assembly_entry_points') or [center(seated)]
        unique=[]
        for target in targets:
            if any(math.dist(target,q)<.01 for q in unique):continue
            unique.append(target)
            arrows.append({'id':fitting['id'],'start':[target[i]+delta[i] for i in range(3)],'end':target,
                'source':'BAZIS receiving-panel hole' if seated.get('assembly_entry_points') else 'native fitting installed position'})
    return arrows

def draw_preparation_annotations(c,plate,original,moved,point,frame):
    c.saveState();c.setStrokeColor(HexColor('#b86411'));c.setFillColor(HexColor('#b86411'));c.setLineWidth(.35)
    for arrow in insertion_arrows(original,moved):
        start=point(arrow['start']);end=point(arrow['end']);length=math.dist(start,end)
        if length<3:continue
        dx=(end[0]-start[0])/length;dy=(end[1]-start[1])/length
        # Leave a little space after the displaced fitting; point at the bore mouth.
        gap=min(10,length*.15);a=(start[0]+dx*gap,start[1]+dy*gap)
        c.line(*a,*end);size=min(6,length*.2)
        path=c.beginPath();path.moveTo(*end)
        path.lineTo(end[0]-dx*size-dy*size*.4,end[1]-dy*size+dx*size*.4)
        path.lineTo(end[0]-dx*size+dy*size*.4,end[1]-dy*size-dx*size*.4)
        path.close();c.drawPath(path,fill=1,stroke=0)
    c.restoreState()
    entries=[(h.get('name','Feronerie').split('\r')[0].strip()[:85],[h]) for h in moved]
    return draw_callouts(c,entries,[plate]+moved,point,frame,color='#b86411')
