"""Expose native planar through cuts on individual board sheets only."""
from math import atan2, cos, hypot, isfinite, sin, tau
from export_dimensions import flatten, to_local, xy

# Same continuity threshold as closed_loops; used for matching native edges,
# never to derive manufacturing dimensions.
EPS=.001


def covered(intervals, length, tolerance):
    reach=0
    for a,b in sorted(intervals):
        if a>reach+tolerance:return False
        reach=max(reach,b)
        if reach>=length-tolerance:return True
    return False


def arc_measure(element):
    center=xy(element['center'])
    if element['type']=='circle':
        return center,element['radius'],0,tau,1
    a,b=(xy(element[k]) for k in ('start','end'))
    radius=hypot(a[0]-center[0],a[1]-center[1])
    start=atan2(a[1]-center[1],a[0]-center[0])
    sign=1 if element['counterclockwise'] else -1
    end=atan2(b[1]-center[1],b[0]-center[0])
    return center,radius,start,(sign*(end-start))%tau,sign


def exact_extrema(elements):
    result=[]
    for e in elements:
        if e['type']!='circle':result.extend(xy(e[k]) for k in ('start','end'))
        if e['type']=='line':continue
        center,radius,start,length,sign=arc_measure(e)
        for i in range(4):
            angle=i*tau/4
            if (sign*(angle-start))%tau<=length:
                result.append([center[0]+radius*cos(angle),center[1]+radius*sin(angle)])
    return result


def element_on_rim(element, rim):
    kind=element['type']
    if kind=='line':
        a,b=(xy(element[k]) for k in ('start','end'))
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=hypot(dx,dy)
        if length<=EPS:return False
        intervals=[]
        for segment in rim:
            points=[(x-a[0],y-a[1]) for x,y in segment]
            if any(abs(x*dy-y*dx)>EPS*length for x,y in points):continue
            u,v=sorted((x*dx+y*dy)/length for x,y in points)
            if v>=0 and u<=length:intervals.append((max(0,u),min(length,v)))
        return covered(intervals,length,EPS)
    center,radius,start,length,sign=arc_measure(element)
    if not isfinite(radius) or radius<=EPS or length<=0:return False
    angular_tol=EPS/radius
    intervals=[];samples=set()
    for segment in rim:
        points=[(x-center[0],y-center[1]) for x,y in segment]
        if any(abs(hypot(x,y)-radius)>EPS for x,y in points):continue
        u,v=sorted((sign*(atan2(y,x)-start))%tau for x,y in points)
        if v-u>tau/2:u,v=v,u+tau
        for shift in (0,-tau):
            if v+shift>=0 and u+shift<=length:
                a,b=max(0,u+shift),min(length,v+shift)
                if b-a>angular_tol:
                    intervals.append((a,b))
                    samples.update((round(a/angular_tol),round(b/angular_tol)))
    return len(samples)>=(4 if kind=='circle' else 3) and covered(intervals,length,angular_tol)


def rim_for(points):
    return list(zip(points,points[1:]))


def intersects(a,b,c,d):
    if any(max(min(a[i],b[i]),min(c[i],d[i]))>min(max(a[i],b[i]),max(c[i],d[i])) for i in range(2)):
        return False
    def area(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(r[0]-p[0])*(q[1]-p[1])
    return area(a,b,c)*area(a,b,d)<=0 and area(c,d,a)*area(c,d,b)<=0


def same_opening(loop, other):
    # Keep the native primitives for both comparisons. A sampled match in one
    # direction alone does not establish equality of two closed openings.
    return (all(element_on_rim(e,rim_for(other['points'])) for e in loop['elements'])
            and all(element_on_rim(e,rim_for(loop['points'])) for e in other['elements']))


def review_openings(panel, loops):
    from dimension_sheets import closed_loops, contains
    added=[];findings=[]
    limits=panel.get('z_limits') or {}
    low,high=limits.get('LowZ'),limits.get('HighZ')
    rims=None
    for ordinal,cut in enumerate(panel.get('machining',{}).get('cuts',[])):
        trajectory=cut.get('trajectory') or {}
        if trajectory.get('elements'):continue  # Swept milling is outside this path.
        props=cut.get('properties') or {}
        depth=props.get('Thickness')
        if isinstance(depth,(float,int)) and isfinite(depth) and abs(depth)<panel['thickness']:
            continue  # Blind pocket, or a swept operation without a valid path.
        row=dict(uid=panel.get('uid'),id=panel['id'],code=panel.get('designation'),
                 operation=cut.get('index',ordinal),native_type=props.get('CutType'),
                 name=props.get('Name'),signed_depth_mm=depth,status='unresolved')
        findings.append(row)
        if not trajectory.get('complete') or not isinstance(depth,(float,int)) or not isfinite(depth):
            row['reason']='Traiectoria sau adâncimea nativă nu este confirmată'
            continue
        if not all(isinstance(v,(float,int)) and isfinite(v) for v in (low,high)) or high<=low or abs(depth)<high-low-EPS:
            row['reason']='Limitele Z sau străpungerea nu sunt confirmate'
            continue
        section=cut.get('section') or {}
        elements=list(flatten(section))
        if (not section.get('complete') or not elements
                or any(e.get('type') not in ('line','circle','arc') for e in elements)
                or any(e['type']=='arc' and not isinstance(e.get('counterclockwise'),bool) for e in elements)):
            row['reason']='Contur nativ incomplet sau tip de curbă indisponibil în desen'
            continue
        try:
            candidate=closed_loops([section])
        except (KeyError,TypeError,ValueError,ZeroDivisionError):
            candidate=[]
        if len(candidate)!=1 or len(candidate[0]['elements'])!=len(elements):
            row['reason']='Operațiunea nu oferă un contur interior continuu și unic'
            continue
        loop=candidate[0]
        if any(same_opening(loop,other) for other in loops+added if other['interior']):
            row['status']='already_drawn'
            continue
        boundaries=[other for other in loops if not other['interior']]
        if not any(all(contains(other['points'],p) for p in loop['points']) for other in boundaries):
            row['reason']='Conturul atinge exteriorul sau nu este integral în material'
            continue
        segments=rim_for(loop['points'])
        if any(intersects(a,b,c,d) for i,(a,b) in enumerate(segments)
               for j,(c,d) in enumerate(segments) if i+1<j and (i!=0 or j!=len(segments)-1)):
            row['reason']='Conturul operațiunii se autointersectează'
            continue
        if any(intersects(a,b,c,d) for other in loops+added for a,b in segments
               for c,d in rim_for(other['points'])) or any(
               contains(loop['points'],other['points'][0]) or contains(other['points'],loop['points'][0])
               for other in loops+added if other['interior']):
            row['reason']='Decupajul intersectează un contur existent; lipsesc limitele rezultatului final'
            continue
        if rims is None:
            rims=[[],[]]
            if panel.get('geometry_source')=='BAZIS Edges.GVertices' and panel.get('frame'):
                for edge in panel.get('edges',[]):
                    local=[to_local(panel,p) for p in edge]
                    for face,level in enumerate((low,high)):
                        if all(abs(p[2]-level)<=EPS for p in local):
                            rims[face].append([p[:2] for p in local])
        if not all(all(element_on_rim(e,rim) for e in loop['elements']) for rim in rims):
            row['reason']='Conturul nu coincide cu muchiile rezultate pe ambele fețe'
            continue
        extrema=exact_extrema(loop['elements'])
        loop.update(interior=True,technological=True,extrema=extrema)
        added.append(loop)
        row.update(status='added',source='BAZIS panel.Cuts.Contour + Edges.GVertices pe ambele fețe',
                   local_bounds_mm=dict(min=[min(p[i] for p in extrema) for i in range(2)],
                                        max=[max(p[i] for p in extrema) for i in range(2)]),
                   types=sorted({e['type'] for e in loop['elements']}))
        lines=[e for e in loop['elements'] if e['type']=='line']
        axis_rectangle=len(lines)==len(loop['elements'])==4 and all(
            any(abs(xy(e['start'])[i]-xy(e['end'])[i])<=EPS for i in range(2)) for e in lines)
        if not axis_rectangle and not (len(elements)==1 and elements[0]['type']=='circle'):
            row['limitation']='Contur nativ desenat; cotarea existentă poate să nu definească toate unghiurile sau centrele'
    return added,findings
