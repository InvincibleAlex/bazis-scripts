"""Render only circular bores calculated and assigned to a panel by BAZIS."""
import math


def finite_vector(value):
    return isinstance(value,list) and len(value)==3 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in value)


def bore_edges(hole,segments=32):
    if hole.get('source')!='BAZIS NewHoleDrilling':return []
    p=hole.get('position_global_mm');axis=hole.get('direction_global')
    diameter=hole.get('diameter_mm');depth=hole.get('depth_mm')
    if not finite_vector(p) or not finite_vector(axis):return []
    if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in [diameter,depth]):return []
    length=math.sqrt(sum(v*v for v in axis))
    if length<1e-9:return []
    axis=[v/length for v in axis]
    ref=min(([1,0,0],[0,1,0],[0,0,1]),key=lambda v:abs(sum(a*b for a,b in zip(v,axis))))
    u=[axis[1]*ref[2]-axis[2]*ref[1],axis[2]*ref[0]-axis[0]*ref[2],axis[0]*ref[1]-axis[1]*ref[0]]
    norm=math.sqrt(sum(v*v for v in u));u=[v/norm for v in u]
    v=[axis[1]*u[2]-axis[2]*u[1],axis[2]*u[0]-axis[0]*u[2],axis[0]*u[1]-axis[1]*u[0]]
    rings=[]
    for distance in [0,depth]:
        ring=[[p[k]+axis[k]*distance+diameter/2*(u[k]*math.cos(i*2*math.pi/segments)+v[k]*math.sin(i*2*math.pi/segments)) for k in range(3)] for i in range(segments)]
        rings.extend([[ring[i],ring[(i+1)%segments]] for i in range(segments)])
    return rings


def add_hole_edges(report):
    from export_assembly import box_edges
    for panel in report.get('panels',[]):
        if panel.get('native_hole_edges_added'):continue
        outlines=[];drawn=0
        for hole in panel.get('holes',[]):
            # Explicit native association required; never infer a receiving panel
            # just because the fastener or its bounding box touches that panel.
            if hole.get('panel_uid')!=panel.get('uid') or hole.get('coordinate_space_verified') is not True:continue
            edges=bore_edges(hole)
            if edges:outlines.extend(edges);drawn+=1
        if outlines:
            panel['edges']=(panel.get('edges') or box_edges(panel))+outlines
            panel['native_hole_edges_added']=True
        panel['holes_drawn']=drawn
    return report
