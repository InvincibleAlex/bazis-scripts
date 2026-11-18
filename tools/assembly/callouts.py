"""Place short 45-degree/straight leaders outside projected geometry."""
import math
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor


def hull(points):
    pts=sorted(set(tuple(p) for p in points))
    if len(pts)<3:return pts
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lo=[];hi=[]
    for seq,out in [(pts,lo),(reversed(pts),hi)]:
        for p in seq:
            while len(out)>1 and cross(out[-2],out[-1],p)<=0:out.pop()
            out.append(p)
    return lo[:-1]+hi[:-1]


def intersects(rect,poly):
    if len(poly)<3:return False
    x,y,w,h=rect;box=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    axes=[(1,0),(0,1)]+[(b[1]-a[1],a[0]-b[0]) for a,b in zip(poly,poly[1:]+poly[:1])]
    for ax,ay in axes:
        aa=[p[0]*ax+p[1]*ay for p in box];bb=[p[0]*ax+p[1]*ay for p in poly]
        if max(aa)<=min(bb) or max(bb)<=min(aa):return False
    return True


def closest(poly,p):
    best=None;distance=math.inf
    for a,b in zip(poly,poly[1:]+poly[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
        q=(a[0]+t*dx,a[1]+t*dy);d=math.dist(q,p)
        if d<distance:best=q;distance=d
    return best or p


def crossing(a,b,c,d):
    def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    return cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0


def layout(entries,obstacles,frame,anchors=None):
    """Return deterministic placements; caller can audit collision scores."""
    fx,fy,fw,fh=frame;placed=[];leaders=[]
    for index,(label,poly) in enumerate(entries):
        if not poly:continue
        x0=min(p[0] for p in poly);x1=max(p[0] for p in poly);y0=min(p[1] for p in poly);y1=max(p[1] for p in poly)
        width=stringWidth(str(label),'Body',9);best=None
        anchor=anchors[index] if anchors else ((x0+x1)/2,(y0+y1)/2)
        for sign in [-1,1]:
            for vertical in [-1,1]:
                runs={14,25,40,65,100}
                runs.update(abs(edge-anchor[0])+gap for edge in [x0,x1] for gap in [12,25,45])
                runs.update(abs(edge-anchor[1])+gap for edge in [y0,y1] for gap in [12,25,45])
                for run in sorted(runs):
                    elbow=(anchor[0]+sign*run,anchor[1]+vertical*run)
                    yy=elbow[1];endx=elbow[0]+sign*14
                    textx=endx+4 if sign==1 else endx-width-4
                    rect=(textx-2,yy-6,width+4,13)
                    if rect[0]<fx or rect[1]<fy or rect[0]+rect[2]>fx+fw or rect[1]+rect[3]>fy+fh:continue
                    end=(endx,yy)
                    collisions=sum(intersects(rect,p) for p in obstacles)
                    collisions+=sum(not (rect[0]+rect[2]<=r[0] or r[0]+r[2]<=rect[0] or rect[1]+rect[3]<=r[1] or r[1]+r[3]<=rect[1]) for r in [v['rect'] for v in placed])
                    crosses=sum(crossing(a,b,c,d) for a,b in [(anchor,elbow),(elbow,end)] for c,d in leaders)
                    geometry_crossings=sum(any(crossing(a,b,u,v) for u,v in zip(p,p[1:]+p[:1])) for a,b in [(anchor,elbow),(elbow,end)] for p in obstacles)
                    # Text clearance dominates compactness and leader length.
                    score=collisions*100000+crosses*2000+geometry_crossings*1000+math.dist(anchor,elbow)+math.dist(elbow,end)
                    candidate=dict(label=str(label),rect=rect,text=(textx,yy-3),path=[anchor,elbow,end],score=score,collisions=collisions)
                    if best is None or score<best['score']:best=candidate
        if best:
            placed.append(best);leaders.extend(zip(best['path'],best['path'][1:]))
    return placed


def draw_callouts(c,entries,objects,point,frame,color='#172b3a'):
    from export_assembly import box_edges
    def polygon(items):return hull([point(v) for p in items for e in p.get('edges') or box_edges(p) for v in e])
    obstacles=[polygon([p]) for p in objects]
    specs=[(label,polygon(items)) for label,items in entries]
    anchors=[]
    for _,items in entries:
        anchors.append(point([(min(p['bounds']['min'][i] for p in items)+max(p['bounds']['max'][i] for p in items))/2 for i in range(3)]))
    placements=layout(specs,obstacles,frame,anchors)
    c.saveState();c.setStrokeColor(HexColor(color));c.setFillColor(HexColor(color));c.setLineWidth(.20);c.setFont('Body',9)
    for item in placements:
        a,b,d=item['path'];c.line(*a,*b);c.line(*b,*d);c.drawString(*item['text'],item['label'])
    c.restoreState()
    return placements
