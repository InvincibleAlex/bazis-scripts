"""Verify native straight edge bevels against the resulting BAZIS solid."""
import math

from export_dimensions import flatten, fmt, to_local, xy

EPS = .001


def coverage(edges, a, b, z=None):
    """Intervals along the reference line covered by collinear native edges."""
    length = math.dist(a, b)
    u = [(q-p)/length for p,q in zip(a,b)]
    spans = []
    for edge in edges:
        if z is not None and any(abs(p[2]-z)>EPS for p in edge):
            continue
        offsets = [sum((p[i]-a[i])*u[i] for i in range(2)) for p in edge]
        if any(math.dist(p[:2], [a[i]+t*u[i] for i in range(2)])>EPS for p,t in zip(edge, offsets)):
            continue
        spans.append(sorted(offsets))
    merged = []
    for start,end in sorted(spans):
        if merged and start<=merged[-1][1]+EPS:
            merged[-1][1] = max(merged[-1][1],end)
        else:
            merged.append([start,end])
    return merged


def verify(panel, source, loops):
    params = source.get('params') or {}
    trajectory = source.get('trajectory') or {}
    section = source.get('section') or {}
    path = list(flatten(trajectory))
    outline = list(flatten(section))
    if not trajectory.get('complete') or not section.get('complete') or len(path)!=1 or path[0]['type']!='line':
        raise ValueError('Traiectorie sau profil nativ incomplet; se acceptă un traseu drept continuu')
    if len(outline)!=3 or any(e['type']!='line' for e in outline):
        raise ValueError('Profilul nativ nu este un triunghi verificabil')
    points = [(xy(e['start']),xy(e['end'])) for e in outline]
    if any(math.dist(edge[1],points[(i+1)%3][0])>EPS for i,edge in enumerate(points)):
        raise ValueError('Profilul nativ nu este închis')
    slope = [(a,b) for a,b in points if all(abs(a[i]-b[i])>EPS for i in range(2))]
    if len(slope)!=1:
        raise ValueError('Profilul nu are o singură față oblică')
    q,r = slope[0]
    corner = next((a for a,_ in points if all(math.dist(a,v)>EPS for v in (q,r))),None)
    if corner is None or not any(abs(corner[0]-a[0])<=EPS and abs(corner[1]-b[1])<=EPS
                                for a,b in ((q,r),(r,q))):
        raise ValueError('Laturile profilului nu definesc secțiunea nativă perpendiculară')
    width,depth = [abs(r[i]-q[i]) for i in range(2)]
    angle = math.degrees(math.atan2(depth,width))
    if abs(angle-45)>EPS or (params.get('Angle') is not None and abs(abs(params['Angle'])-angle)>EPS):
        raise ValueError('Unghiul profilului nu confirmă 45°')
    if abs(min(q[0],r[0]))>EPS or abs(min(q[1],r[1]))>EPS:
        raise ValueError('Originea profilului nu coincide cu reperul nativ al cantului')
    a,b = [xy(path[0][key]) for key in ('start','end')]
    length = math.dist(a,b)
    if length<=EPS:
        raise ValueError('Traiectorie fără lungime')
    normal = [-(b[1]-a[1])/length,(b[0]-a[0])/length]
    exterior = [(s,t) for loop in loops if not loop['interior'] for s,t in zip(loop['points'],loop['points'][1:])]
    span = next(((s,t) for s,t in coverage(exterior,a,b) if s<=EPS and t>=length-EPS),None)
    if span is None:
        raise ValueError('Traiectoria nu corespunde unui cant exterior drept')
    low,high = [panel['z_limits'][k] for k in ('LowZ','HighZ')]
    if depth>high-low+EPS or panel.get('geometry_source')!='BAZIS Edges.GVertices':
        raise ValueError('Grosimea sau muchiile rezultate nu confirmă profilul')
    native = [[to_local(panel,p) for p in edge] for edge in panel['edges'] if len(edge)==2]
    matches = []
    for sign in (1,-1):
        inward = [sign*n for n in normal]
        def offset(p,d):
            return [p[i]+d*inward[i] for i in range(2)]
        for direction,datum in ((1,low),(-1,high)):
            profile = sorted([(p[0],datum+direction*p[1]) for p in (q,r)])
            rails = [(offset(a,d),offset(b,d),z) for d,z in profile]
            if not all(any(start<=EPS and end>=length-EPS for start,end in coverage(native,s,t,z))
                       for s,t,z in rails):
                continue
            end_pairs = [([*rails[0][i],rails[0][2]],[*rails[1][i],rails[1][2]]) for i in (0,1)]
            if not all(any(min(max(math.dist(p,a),math.dist(q,b)),max(math.dist(p,b),math.dist(q,a)))<=EPS
                               for a,b in native) for p,q in end_pairs):
                continue
            matches.append((inward,profile,rails))
    if len(matches)!=1:
        raise ValueError('Poziția sau sensul profilului nu este confirmat univoc de muchiile rezultate')
    inward,profile,rails = matches[0]
    (_,edge_z),(_,inner_z) = profile
    face = 'Zmax' if inner_z>edge_z else 'Zmin'
    if abs(inner_z-(high if face=='Zmax' else low))>EPS:
        raise ValueError('Limita interioară nu coincide cu fața de acces')
    reference = [a[i]+span[0]*(b[i]-a[i])/length for i in range(2)]
    end_reference = [b[i]+(span[1]-length)*(b[i]-a[i])/length for i in range(2)]
    corners = [a,b,rails[1][1],rails[1][0]]
    return dict(start=a,end=b,length=length,width=width,depth=depth,angle=angle,normal=inward,
                thickness=high-low,profile=[(x,z-low) for x,z in profile],residual=high-low-depth,rails=rails,face=face,
                corners=corners,low=low,high=high,reference=reference,end_reference=end_reference,
                start_offset=max(0,-span[0]),end_offset=max(0,span[1]-length))


def prepare_bevels(panel,cuts,loops,report):
    seen = set()
    for cut in cuts:
        source = panel['machining']['cuts'][cut['source_index']]
        props = source.get('properties') or {}
        params = source.get('params') or {}
        if params.get('CutType')!=4 and params.get('Angle') not in (45,-45) and '45°' not in str(props.get('Name','')):
            continue
        if cut.get('verified_rectangle'):
            continue
        item = dict(uid=panel.get('uid'),code=panel.get('designation'),plate=panel['label'],
                    module=report.get('_cartus_corp'),operation=source.get('index',cut['source_index']))
        report.get('_paic04_findings',[]).append(item)
        try:
            detail = verify(panel,source,loops)
        except (ValueError,KeyError,TypeError,ArithmeticError) as error:
            item.update(status='unresolved',reason=str(error))
            continue
        key = tuple(sorted(tuple(round(v,6) for v in p+[z])
                           for a,b,z in detail['rails'] for p in (a,b)))
        if key in seen:
            cut['duplicate_bevel'] = True
            item['status'] = 'already_drawn'
            continue
        seen.add(key)
        cut.update(bevel=detail,section_detail=detail,corners=detail['corners'],bevel_finding=item)
        item.update(status='added',**detail)


def draw_bevel_path(c,detail,back,convert,project,color):
    from dimension_sheets import aligned_dimension
    face = 'Zmin' if back else 'Zmax'
    on_cut_face = face==detail['face']
    for a,b,z in detail['rails']:
        if not on_cut_face and abs(z-(detail['low'] if back else detail['high']))>EPS:
            continue
        c.line(*project(convert(a)),*project(convert(b)))
    if not on_cut_face:
        return
    outer,inner = detail['rails']
    if detail['start_offset']>EPS:
        c.line(*project(convert(outer[0])),*project(convert(inner[0])))
    if detail['end_offset']>EPS:
        c.line(*project(convert(outer[1])),*project(convert(inner[1])))
    for a,b,value in [(detail['reference'],detail['start'],detail['start_offset']),
                      (detail['start'],detail['end'],detail['length'] if max(detail['start_offset'],detail['end_offset'])>EPS else 0),
                      (detail['end'],detail['end_reference'],detail['end_offset'])]:
        if value>EPS:
            aligned_dimension(c,project(convert(a)),project(convert(b)),14,fmt(value),color)


def legend_labels(report):
    from dimension_sections import section_label
    from project_legend import project_sections
    labels = {}
    for index,entry in enumerate(project_sections(report)):
        if not entry['planar']:
            key = (entry['name'],round(entry['thickness'],3),*(round(v,3) for v in entry['size']))
            labels.setdefault(key,[]).append(section_label(index))
    return labels
