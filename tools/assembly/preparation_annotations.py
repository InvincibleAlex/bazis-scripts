"""Preparation-only dashed insertion axes, short arrows and article numbers."""
import math
from reportlab.lib.colors import HexColor
from export_assembly import center
from inventory_layout import draw_numbered_labels

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

def projected_arrow(start,end):
    length=math.dist(start,end)
    if length<3:return None
    dx=(end[0]-start[0])/length;dy=(end[1]-start[1])/length
    gap=min(6,length*.08)
    axis_start=(start[0]+dx*gap,start[1]+dy*gap)
    axis_end=(end[0]-dx*gap,end[1]-dy*gap)
    tip=(start[0]+dx*length*.60,start[1]+dy*length*.60)
    stem=min(18,length*.28)
    tail=(tip[0]-dx*stem,tip[1]-dy*stem)
    return dict(axis_start=axis_start,axis_end=axis_end,tail=tail,tip=tip,direction=(dx,dy),head=min(4,stem*.35))


def draw_preparation_annotations(c,plate,original,moved,point,frame):
    color=HexColor('#b15d12')
    c.saveState();c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(.45)
    for arrow in insertion_arrows(original,moved):
        drawing=projected_arrow(point(arrow['start']),point(arrow['end']))
        if not drawing:continue
        c.setDash(3,3);c.line(*drawing['axis_start'],*drawing['axis_end'])
        c.setDash();c.line(*drawing['tail'],*drawing['tip'])
        dx,dy=drawing['direction'];x,y=drawing['tip'];size=drawing['head']
        path=c.beginPath();path.moveTo(x,y)
        path.lineTo(x-dx*size-dy*size*.45,y-dy*size+dx*size*.45)
        path.lineTo(x-dx*size+dy*size*.45,y-dy*size-dx*size*.45)
        path.close();c.drawPath(path,fill=1,stroke=0)
    c.restoreState()
    return draw_numbered_labels(c,moved,point,frame,color=color)
