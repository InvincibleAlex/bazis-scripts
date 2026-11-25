"""Dimensioned local A-A sections from verified native straight groove footprints."""
import math
from reportlab.lib.colors import HexColor
from export_dimensions import dimension,fmt
from dimension_annotations import AnnotationLayout

INK=HexColor('#172b3a');MILL=HexColor('#b15d12')
DETAIL_WIDTH=174;DETAIL_HEIGHT=100;DETAIL_GAP=12;SECTIONS_PER_PAGE=3

def section_label(index):
    result=''
    while True:
        result=chr(65+index%26)+result;index=index//26-1
        if index<0:return result

def cross_section(panel,cut,loops):
    if not cut.get('verified_rectangle') or cut.get('through') or cut.get('face') not in ('Zmin','Zmax'):return None
    width=cut['width'];depth=cut['profile_depth'];thickness=panel['thickness']
    if width<=0 or depth<=0 or depth>thickness:return None
    corners=cut['corners'];origin=[sum(q[i] for q in corners)/4 for i in range(2)]
    normal=[(corners[3][i]-corners[0][i])/width for i in range(2)]
    intersections=[]
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    for loop in loops:
        for a,b in zip(loop['points'],loop['points'][1:]):
            v=[b[i]-a[i] for i in range(2)];delta=[a[i]-origin[i] for i in range(2)];den=cross(normal,v)
            if abs(den)<1e-9:continue
            t=cross(delta,v)/den;along=cross(delta,normal)/den
            if -.000001<=along<=1.000001:intersections.append(t)
    values=[]
    for t in sorted(intersections):
        if not values or t-values[-1]>.00001:values.append(t)
    # Native closed contour crossings delimit actual material intervals.
    interval=next(((a,b) for a,b in zip(values[::2],values[1::2]) if a<=-width/2+.001 and b>=width/2-.001),None)
    if interval is None:return None
    margin=max(8,width*.8)
    left=max(interval[0],-width/2-margin);right=min(interval[1],width/2+margin)
    return {'origin':origin,'normal':normal,'width':width,'depth':depth,'thickness':thickness,'face':cut['face'],
            'left':left,'right':right,'cropped_left':left>interval[0]+.001,'cropped_right':right<interval[1]-.001}

def draw_section_mark(c,cut,convert,project):
    section=cut.get('section_detail')
    if not section or cut.get('section_label') not in getattr(c,'section_labels_on_page',{cut.get('section_label')}):return
    origin=section['origin'];normal=section['normal'];half=section['width']/2
    a=project(convert([origin[i]-normal[i]*half for i in range(2)]));b=project(convert([origin[i]+normal[i]*half for i in range(2)]))
    length=math.dist(a,b)
    if length<.0001:return
    u=[(b[i]-a[i])/length for i in range(2)];d=[-u[1],u[0]]
    ends=[[a[i]-u[i]*10 for i in range(2)],[b[i]+u[i]*10 for i in range(2)]]
    c.saveState();c.setStrokeColor(INK);c.setFillColor(INK);c.setLineWidth(.25);c.setDash([4,2,1,2]);c.line(*ends[0],*ends[1]);c.setDash();c.setFont('Body',7)
    for q in ends:
        tail=[q[i]-d[i]*15 for i in range(2)];c.line(*tail,*q)
        c.line(*q,q[0]-d[0]*4+u[0]*1.5,q[1]-d[1]*4+u[1]*1.5)
        c.line(*q,q[0]-d[0]*4-u[0]*1.5,q[1]-d[1]*4-u[1]*1.5)
        c.annotation_layout.draw(c,tail[0]+3,tail[1]-4,cut['section_label'],target=tail)
    c.restoreState()

def draw_detail(c,cut,x,top):
    data=cut['section_detail'];label=cut['section_label'];width=data['width'];depth=data['depth'];thickness=data['thickness']
    left,right=data['left'],data['right'];half=width/2
    scale=min(118/(right-left),45/thickness)
    ox=x+30-left*scale;oy=top-76
    p=lambda q:(ox+q[0]*scale,oy+q[1]*scale)
    # Normalize the local detail so the machined face and opening always face upward.
    # Native face classification still controls which plan view receives A-A.
    poly=[[left,0],[right,0],[right,thickness],[half,thickness],[half,thickness-depth],[-half,thickness-depth],[-half,thickness],[left,thickness]]
    c.saveState();c.setStrokeColor(INK);c.setLineWidth(.25);c.setFillColor(INK);c.setFont('Body',7)
    c.drawString(x+30,top,label+'–'+label)
    path=c.beginPath();path.moveTo(*p(poly[0]))
    for q in poly[1:]:path.lineTo(*p(q))
    path.close();c.saveState();c.clipPath(path,stroke=0);c.setStrokeColor(HexColor('#888888'));c.setLineWidth(.15)
    start=p([left,0]);end=p([right,thickness])
    for offset in range(-60,200,6):c.line(start[0]+offset,start[1]-2,start[0]+offset+60,end[1]+2)
    c.restoreState();c.drawPath(path,stroke=1,fill=0)
    # Break marks distinguish the cropped local material from an entire board width.
    for side,cropped in [(left,data['cropped_left']),(right,data['cropped_right'])]:
        if cropped:
            xx,yy=p([side,thickness/2]);c.setFillColorRGB(1,1,1);c.rect(xx-2,yy-5,4,10,stroke=0,fill=1)
            c.line(xx,yy-6,xx-2,yy-2);c.line(xx-2,yy-2,xx+2,yy+2);c.line(xx+2,yy+2,xx,yy+6)
    previous=getattr(c,'annotation_layout',None);c.annotation_layout=AnnotationLayout((x,top-DETAIL_HEIGHT,x+DETAIL_WIDTH,top+8))
    surface=thickness;floor=thickness-depth
    dimension(c,p([-half,surface]),p([half,surface]),p([0,thickness])[1]+12,fmt(width),color=MILL)
    dimension(c,p([half,surface]),p([half,floor]),p([right,0])[0]+10,fmt(depth),True,color=MILL)
    dimension(c,p([left,0]),p([left,thickness]),p([left,0])[0]-12,fmt(thickness),True,color=INK)
    c.annotation_layout=previous;c.restoreState()
