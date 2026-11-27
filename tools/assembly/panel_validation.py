"""Read-only comparison of physical panel instances sharing a BAZIS designation."""
from collections import Counter, defaultdict
from itertools import combinations
from math import cos, sin, isfinite, dist

from export_dimensions import flatten, to_local, xy
from module_repetitions import canonical, packed, unordered

# Reuse the existing module comparison precision (canonical, six decimals).
# The four rotations keep the two finished faces. The remaining transforms
# are physical half-turns with an accompanying Z flip, checked as possibilities.
ORIENTATIONS = ((0,1,1),(1,-1,1),(0,-1,-1),(1,1,-1),
                (0,-1,1),(0,1,-1),(1,1,1),(1,-1,-1))
LABELS = ('0°','90°','180°','270°','Întoarcere X','Întoarcere Y','Întoarcere diagonală','Întoarcere antidiagonală')


def shape(c, point, flip=False, directed=False):
    if not c or c.get('complete') is not True:
        raise ValueError('contur incomplet')
    def element(e):
        kind=e['type']
        if kind=='circle':
            return [kind,point(xy(e['center'])),e['radius']]
        if kind not in ('line','arc'):
            raise ValueError('element de contur nesuportat: '+kind)
        a,b=point(xy(e['start'])),point(xy(e['end']))
        direction=e.get('counterclockwise')
        if kind=='arc' and not isinstance(direction,bool):
            raise ValueError('sensul arcului lipsește')
        if not directed and packed(a)>packed(b):
            a,b=b,a
            if kind=='arc':direction=not direction
        return [kind,a,b,point(xy(e['center'])),direction!=flip] if kind=='arc' else [kind,a,b]
    rows=[element(e) for e in flatten(c)]
    return rows if directed else unordered(rows)


def signature(panel, orientation):
    axis,sx,sy=ORIENTATIONS[orientation]
    swap_faces=orientation>=4
    bounds=panel.get('local_bounds') or {}
    z=panel.get('z_limits') or {}
    lo=xy(bounds['min']);hi=xy(bounds['max'])
    width,height=(hi[i]-lo[i] for i in range(2))
    low=z.get('LowZ',0);high=z.get('HighZ',low+panel['thickness'])
    size=(width,height)
    def point(p):
        i,j=axis,1-axis
        return [(p[i]-lo[i]) if sx>0 else (hi[i]-p[i]),
                (p[j]-lo[j]) if sy>0 else (hi[j]-p[j])]
    def vector(v):
        return [sx*v[axis],sy*v[1-axis]]+([-v[2] if swap_faces else v[2]] if len(v)==3 else [])
    def grain_axis(v):
        q=vector(v)
        return min((canonical(q),canonical([-x for x in q])),key=packed)
    missing=[]
    if not {'LowZ','HighZ'}<=z.keys():missing.append('Limitele native Z lipsesc')
    features={'gabarit':(size[axis],size[1-axis],panel['thickness']),'grosime':panel['thickness']}
    material=panel.get('technical_material')
    if material and '\r' in material and material.partition('\r')[2].strip():
        features['material']=material
    else:
        missing.append('Codul/identificatorul materialului lipsește')
        if material:features['denumire material']=material.split('\r')[0]
    native=panel.get('native_contour')
    snapshot=panel.get('module_comparison') or {}
    if not snapshot.get('complete'):missing.append('Inventarul nativ de canturi/finisaje este incomplet')
    texture=snapshot.get('texture') or {}
    appearance=panel.get('appearance') or {}
    try:
        if panel.get('dimension_properties',{}).get('Bent') is not False:
            raise ValueError('placă curbată sau stare neverificată')
        perimeter=shape(native,point,swap_faces)
        if not perimeter:raise ValueError('contur gol')
        tree=panel.get('contour_tree')
        if not tree:raise ValueError('arborele contururilor lipsește')
        def branch(node):
            if type(node.get('child_count')) is not int or node['child_count']!=len(node['children']):
                raise ValueError('copii de contur lipsă')
            return [shape(node['geometry'],point,swap_faces),unordered(branch(child) for child in node['children'])]
        features['contur']=[perimeter,branch(tree)]
    except (ValueError,KeyError,TypeError) as e:missing.append('Contur: '+str(e))
    name=appearance.get('orientation_name')
    angle=texture.get('TextureAngle')
    if name=='None':
        features['fibră']=None
    elif name in ('Horizontal','Vertical') and isinstance(angle,(float,int)) and isfinite(angle):
        features['fibră']=[grain_axis([1,0] if name=='Horizontal' else [0,1]),grain_axis([cos(angle),sin(angle)])]
    else:missing.append('Direcția nativă a fibrei lipsește sau este personalizată')
    layers=snapshot.get('layers')
    if not isinstance(layers,list) or 'FrontFace' not in texture:
        missing.append('Datele despre fețe și finisaje lipsesc')
    elif swap_faces:
        if not panel.get('faces_interchangeable') or layers:
            missing.append('Echivalența fețelor la întoarcere nu este confirmată')
    elif layers and orientation!=0:
        missing.append('Transformarea fibrei straturilor nu este confirmată')
    elif any(not {'Material','Thickness','Side','TextureOrientation','MaterialWidth'}<=row.keys() for row in layers):
        missing.append('Proprietăți de strat incomplete')
    else:
        features['fețe']=[texture['FrontFace'],unordered(layers)]
    try:
        bands=snapshot['bands']
        if not isinstance(bands,list):raise ValueError('listă indisponibilă')
        contour=native['elements']
        rows=[]
        for band in bands:
            if not {'ElemIndex','Material','Thickness','Width','ClipPanel','Allowance','Sign'}<=band.keys():
                raise ValueError('proprietăți incomplete')
            i=band['ElemIndex']
            if type(i) is not int or not 0<=i<len(contour):raise ValueError('index nativ invalid')
            rows.append([shape({'complete':True,'elements':[contour[i]]},point,swap_faces),
                         {k:v for k,v in band.items() if k!='ElemIndex'}])
        features['canturi']=unordered(rows)
    except (KeyError,ValueError,TypeError,IndexError) as e:missing.append('Canturi: '+str(e))
    try:
        if panel.get('drilling_source')!='BAZIS NewHoleDrilling':raise ValueError('calcul nativ indisponibil')
        rows=[];unverified_profiles=False
        features['număr operațiuni de găurire']=len(panel['holes'])
        for h in panel['holes']:
            if not h.get('coordinate_space_verified') or h['panel_uid']!=panel.get('uid'):
                raise ValueError('asociere sau coordonate neconfirmate')
            d=vector(h.get('direction_panel_local') or to_local(panel,h['direction_global'],True))
            p=h.get('position_panel_local_mm') or to_local(panel,h['position_global_mm'])
            zz=high-p[2] if swap_faces else p[2]-low
            diameter,depth,mode=(h.get(k) for k in ('diameter_mm','depth_mm','drill_mode'))
            if diameter is None or depth is None or mode is None:
                raise ValueError('parametri de găurire incompleți')
            if h.get('contour_element_count') not in (0,1):
                unverified_profiles=True
            access=next((('XYZ'[i]+('min' if v>0 else 'max')) for i,v in enumerate(d) if abs(v)>.999),'oblică')
            end=zz+d[2]*depth
            through=access.startswith('Z') and min(zz,end)<=.01 and max(zz,end)>=high-low-.01
            rows.append([point(p)+[zz],d,diameter,depth,mode,access,through])
        features['găuriri']=unordered(rows)
        if unverified_profiles:missing.append('Profilul conturului de găurire nu este disponibil')
    except (KeyError,ValueError,TypeError) as e:missing.append('Găuriri: '+str(e))
    try:
        machining=panel['machining']
        if not machining.get('complete'):raise ValueError('listă incompletă')
        features['număr frezări']=len(machining['cuts'])
        # A straight-edged profile's diameter is invariant even if a face swap
        # prevents comparison of the full machining toolpath.
        profile_diameters=[]
        for cut in machining['cuts']:
            profile=cut.get('section') or {}
            edges=list(flatten(profile))
            if not profile.get('complete') or not 2<=len(edges)<=4 or any(e['type']!='line' for e in edges):break
            vertices=[xy(e[k]) for e in edges for k in ('start','end')]
            profile_diameters.append(max(dist(a,b) for a,b in combinations(vertices,2)))
        else:
            features['diametre profile frezări']=sorted(profile_diameters)
        rows=[]
        for cut in machining['cuts']:
            if swap_faces:raise ValueError('profilul la întoarcere nu este confirmat')
            props=cut.get('properties') or {};params=cut.get('params')
            if 'CutType' not in props or 'Thickness' not in props or 'FrontSide' not in props or params is None or params.get('Fragment'):
                raise ValueError('parametri nativi incompleți sau prelucrare personalizată')
            path=shape(cut['trajectory'],point,directed=True)
            section=shape(cut['section'],(lambda p:list(p)) if path else point)
            if not section:raise ValueError('profil nativ gol')
            rows.append([path,section,{k:v for k,v in props.items() if k not in ('Name','Sign')},
                         {k:v for k,v in params.items() if k not in ('Name','Sign','SignFormula')}])
        features['frezări']=unordered(rows)
    except (KeyError,ValueError,TypeError) as e:missing.append('Frezări: '+str(e))
    return canonical(features),missing


def orthogonal_datum(p):
    try:
        bounds=p['local_bounds'];lo=xy(bounds['min']);hi=xy(bounds['max'])
        edges=[(canonical(xy(e['start'])),canonical(xy(e['end']))) for e in flatten(p['native_contour']) if e['type']=='line']
        return all(any(a[i]==b[i]==canonical(edge) and a[1-i]!=b[1-i] for a,b in edges)
                   for i in range(2) for edge in (lo[i],hi[i]))
    except (KeyError,ValueError,TypeError,IndexError):
        return False


def compare(a,b,faces_interchangeable=False,orthogonal=True):
    left,missing_a=a[0]
    hypotheses=[]
    for index,(right,missing_b) in enumerate(b):
        differences=sorted(k for k in left.keys() & right.keys() if left[k]!=right[k])
        hypotheses.append(dict(transform=LABELS[index],differences=differences,
                               missing=sorted(set(missing_a+missing_b))))
        if not differences and not missing_a and not missing_b and (index<4 or faces_interchangeable):
            return dict(category='A' if index==0 else 'B',transform=LABELS[index],hypotheses=hypotheses)
    possible=[h for h in hypotheses if not h['differences']]
    invariants={'grosime','material','denumire material','număr operațiuni de găurire','număr frezări','diametre profile frezări'}
    limited=not orthogonal and not all(invariants.intersection(h['differences']) for h in hypotheses)
    result=dict(category='D' if possible or limited else 'C',hypotheses=hypotheses)
    if limited:result['limitation']='O reorientare neortogonală nu poate fi exclusă din contururile disponibile'
    if result['category']=='C':
        best=min(hypotheses,key=lambda h:len(h['differences']))
        result['evidence']={'closest_transform':best['transform'],
                            'differences':best['differences'],
                            'original_frame':sorted(k for k in left.keys() & b[0][0].keys() if left[k]!=b[0][0][k]),
                            'values':{k:{'first':left[k],'second':b[LABELS.index(best['transform'])][0][k]}
                                      for k in best['differences']}}
        result['recommendation']='Verificați diferențele la modelare și atribuiți manual coduri distincte dacă piesele rămân tehnologic diferite.'
    return result


def validate_panels(report,plan):
    panels=report.get('panels',[])
    grouped=defaultdict(list)
    for p in panels:
        if p.get('designation'):grouped[p['designation']].append(p)
    pages={str(c['placa']):(int(n),c.get('corp')) for n,c in plan.get('cartus_contexts',{}).items() if c.get('placa')}
    modules={step['panel_id']:m['name'] for m in plan.get('modules',[]) for step in m['steps']}
    def location(p):
        page,corp=pages.get(str(p.get('label')),(None,None))
        return dict(uid=p.get('uid'),id=p['id'],plate=p.get('label'),page=page,module=corp or modules.get(p['id']))
    groups=[]
    for code,instances in grouped.items():
        if len(instances)<2:continue
        signatures={}
        for p in instances:
            try:signatures[p['id']]=[signature(p,i) for i in range(8)]
            except (KeyError,ValueError,TypeError,IndexError) as exc:
                signatures[p['id']]=[({},['Date geometrice insuficiente: '+str(exc)])]*8
        axes={p['id']:orthogonal_datum(p) for p in instances}
        pairs=[]
        for a,b in combinations(instances,2):
            row=compare(signatures[a['id']],signatures[b['id']],bool(a.get('faces_interchangeable') and b.get('faces_interchangeable')),axes[a['id']] and axes[b['id']])
            row.update(first=location(a),second=location(b))
            pairs.append(row)
        categories={p['category'] for p in pairs}
        category=next(k for k in 'CDBA' if k in categories)
        proven={frozenset((pair['first']['id'],pair['second']['id'])) for pair in pairs if pair['category'] in ('A','B')}
        subgroups=[]
        for p in instances:
            subgroup=next((cluster for cluster in subgroups if all(frozenset((p['id'],q['id'])) in proven for q in cluster)),None)
            if subgroup is None:subgroups.append([p])
            else:subgroup.append(p)
        groups.append(dict(code=code,category=category,instances=[location(p) for p in instances],pairs=pairs,
                           equivalent_subgroups=[[location(p) for p in cluster] for cluster in subgroups if len(cluster)>1]))
    counts=Counter(g['category'] for g in groups)
    return dict(schema=1,intervention='PAIC-02 / ERR-002',model=report.get('model'),native_verdict=None,
                precision='Existing module comparison canonicalization (6 decimals); no new tolerance',
                source='BAZIS native contours, sheet material, edges, face layers, cuts and calculated drilling',
                face_swap='Requires positive evidence that both panel faces may be interchanged',

                panels=len(panels),distinct_codes=len(grouped),repeated_codes=len(groups),
                categories={k:counts[k] for k in 'ABCD'},groups=groups)
