"""Resolve a constructive body view using native panel frames and joint evidence."""
from math import sqrt, isfinite
import re
import unicodedata

ALIGN = .999
PERPENDICULAR = .045


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def unit(v):
    if not isinstance(v, (tuple, list)) or len(v) != 3 or not all(isinstance(x,(int,float)) and isfinite(x) for x in v):
        return None
    length=sqrt(dot(v,v))
    return [x/length for x in v] if length>1e-8 else None


def label(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))


def panel_normal(panel):
    axes=(panel.get('frame') or {}).get('axes',[])
    return unit(axes[2]) if len(axes)==3 else None


def span(panel, axis):
    points=[dot(v,axis) for edge in panel.get('edges',[]) for v in edge]
    return (min(points),max(points)) if points else None


def face_against_support(front, support, up):
    normal=panel_normal(front)
    support_normal=panel_normal(support)
    if normal is None or support_normal is None or abs(dot(normal,up))>PERPENDICULAR:
        return None
    if abs(dot(normal,support_normal))>PERPENDICULAR:
        return None
    f,s=span(front,normal),span(support,normal)
    if not f or not s or s[1]-s[0]<max(30,3*(f[1]-f[0])):
        return None
    # A front must be at one end of the attached carcass member.
    mid=sum(f)/2
    w=s[1]-s[0]
    tolerance=max(w*.13, f[1]-f[0])
    if abs(mid-s[0])<=tolerance:
        return [-x for x in normal]
    if abs(mid-s[1])<=tolerance:
        return normal
    return None


def drawer_direction(front, rear, up):
    normal=panel_normal(front)
    back=panel_normal(rear)
    if normal is None or back is None or abs(dot(normal,up))>PERPENDICULAR or abs(dot(normal,back))<ALIGN:
        return None
    lateral=unit(cross(up,normal))
    for direction in (up,lateral):
        fa,ba=span(front,direction),span(rear,direction)
        if not fa or not ba or min(fa[1],ba[1])-max(fa[0],ba[0])<=0:
            return None
    f,b=span(front,normal),span(rear,normal)
    if not f or not b:
        return None
    if f[0]-b[1]>30:
        return normal
    if b[0]-f[1]>30:
        return [-x for x in normal]
    return None


def resolve(frame, panels, fittings, explicit=None):
    """Return a drawing frame or the unchanged frame and a diagnostic."""
    native=[unit(v) for v in frame.get('axes',[])]
    if len(native)!=3 or any(v is None for v in native) or any(abs(dot(native[i],native[j]))>1e-4 for i,j in ((0,1),(0,2),(1,2))):
        return frame,dict(status='nedeterminat',reason='Cadru nativ neortonormal',evidence=[])
    right, up, forward=native
    det=dot(cross(right,up),forward)
    info=dict(native=frame, determinant=det, evidence=[])
    if dot(up,[0,1,0])<ALIGN:
        return frame,dict(info,status='nedeterminat',reason='Verticala blocului necesită un reper confirmat')
    by_uid={p.get('uid'):p for p in panels if p.get('uid') is not None}
    votes={}
    if explicit is not None:
        direct=unit(explicit)
        if direct is None or abs(dot(direct,up))>PERPENDICULAR:
            return frame,dict(info,status='nedeterminat',reason='Reper frontal explicit invalid')
        votes['explicit']=dict(source='reper explicit validat',direction=direct)
    else:
        for fit in fittings:
            # The name narrows the fitting type; BAZIS native joint links and
            # relationship to a perpendicular support determine the signed axis.
            if not re.search(r'\b(balama|hinge|петля)',label(fit.get('name',''))):
                continue
            linked=[by_uid[k] for k in dict.fromkeys(fit.get('connected_panel_uids',[])) if k in by_uid]
            for front in linked:
                if not re.match(r'^(usa|usi|door)\b',label(front.get('name',''))):
                    continue
                for support in linked:
                    direction=face_against_support(front,support,up) if support is not front else None
                    if direction is not None:
                        key=('hinge',front['uid'],support['uid'],tuple(round(x,4) for x in direction))
                        votes[key]=dict(source='balama cu legături native și montant',front=front['uid'],
                                        support=support['uid'],direction=direction)
        for front in panels:
            if not re.match(r'^front\s+sertar\b',label(front.get('name',''))):
                continue
            ancestry=front.get('ancestors',[])
            rear=[p for p in panels if (p.get('ancestors',[])==ancestry[:-1] or p.get('ancestors',[])[:-1]==ancestry[:-1])
                  and len(ancestry)>2 and re.match(r'^spate\s+sertar\b',label(p.get('name','')))]
            if len(rear)==1 and (direction:=drawer_direction(front,rear[0],up)) is not None:
                votes[('drawer',front.get('uid'))]=dict(source='pereche front/spate sertar în același subansamblu',
                    front=front.get('uid'),support=rear[0].get('uid'),direction=direction)
    info['evidence']=list(votes.values())
    if not votes:
        return frame,dict(info,status='nedeterminat',reason='Lipsesc legături sau perechi geometrice concludente')
    axes=[]
    for item in votes.values():
        axis=item['direction']
        # Quantize only to a native axis supported by the evidence, preserving
        # the exact native transform. Oblique fronts require an explicit datum.
        if explicit is None:
            candidates=[axis0 for basis in (right,forward) for axis0 in (basis,[-x for x in basis])]
            top=max(candidates,key=lambda basis:dot(axis,basis))
            if dot(axis,top)<ALIGN:
                return frame,dict(info,status='nedeterminat',reason='Front oblic, reper explicit necesar')
            axis=top
        axes.append(axis)
    if any(dot(axes[0],v)<ALIGN for v in axes[1:]):
        return frame,dict(info,status='nedeterminat',reason='Direcții de acces contradictorii sau multiple')
    # An uncorroborated door on another plane can indicate multiple accesses.
    if explicit is None:
        for p in panels:
            if not re.match(r'^(usa|usi|door)\b',label(p.get('name',''))) or re.search(r'\bfals\b',label(p.get('name',''))):
                continue
            normal=panel_normal(p)
            if normal and abs(dot(normal,axes[0]))<ALIGN:
                return frame,dict(info,status='nedeterminat',reason='Front necoroborat pe alt plan')
    if det>0 and dot(axes[0],forward)>1-1e-10:
        return frame,dict(info,status='păstrat',front=forward)
    x=unit(cross(up,axes[0]))
    if x is None:
        return frame,dict(info,status='nedeterminat',reason='Reper frontal paralel cu verticala')
    result=dict(origin=frame['origin'],axes=[x,up,cross(x,up)],source='cadru constructiv PAIC-09.2')
    return result,dict(info,status='corectat',front=result['axes'][2],constructive=result)
