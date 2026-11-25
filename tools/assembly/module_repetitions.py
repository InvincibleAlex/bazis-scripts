"""Conservative assembly equivalence, independent of instance IDs and world placement."""
import collections
import hashlib
import json
import math


def canonical(value):
    if isinstance(value,float):
        if not math.isfinite(value):raise ValueError('Nonfinite comparison value')
        value=round(value,6)
        return int(value) if value.is_integer() else value
    if isinstance(value,dict):return {k:canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,(list,tuple)):return [canonical(v) for v in value]
    return value


def packed(value):return json.dumps(canonical(value),sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(value):return hashlib.sha256(packed(value).encode()).hexdigest()
def unordered(values):return sorted(values,key=packed)


def describe_module(report,module,items=None):
    """No missing machining/material/geometry evidence is treated as an empty feature."""
    from hierarchical import module_items
    nodes={n['id']:n for n in report['nodes']}
    frame=nodes.get(module['id'],{}).get('frame')
    if not frame or frame.get('source')!='BAZIS ToGlobal':raise ValueError('Lipsește reperul nativ al corpului')
    axes=frame['axes'];origin=frame['origin']
    det=sum(axes[0][i]*(axes[1][(i+1)%3]*axes[2][(i+2)%3]-axes[1][(i+2)%3]*axes[2][(i+1)%3]) for i in range(3))
    if abs(det-1)>1e-5:raise ValueError('Reper reflectat sau neortonormal')
    for a in range(3):
        for b in range(3):
            if abs(sum(axes[a][i]*axes[b][i] for i in range(3))-(a==b))>1e-5:raise ValueError('Reper neortonormal')
    panels,hardware=items if items is not None else module_items(report,module)
    def local(p):return [sum((p[i]-origin[i])*axis[i] for i in range(3)) for axis in axes]
    all_points=[local(v) for p in panels for e in p.get('edges',[]) for v in e]
    if not all_points:raise ValueError('Lipsește geometria plăcilor')
    anchor=[min(p[i] for p in all_points) for i in range(3)]
    def point(p):return [x-anchor[i] for i,x in enumerate(local(p))]
    def direction(v):return [sum(v[i]*axis[i] for i in range(3)) for axis in axes]
    def edges(p):return unordered([unordered([point(a),point(b)]) for a,b in p['edges']])
    board_rows=[];by_uid={};by_id={}
    for p in panels:
        snapshot=p.get('module_comparison')
        if not snapshot or not snapshot.get('complete'):raise ValueError('Lipsesc datele complete de cant/fibră/straturi')
        if p.get('geometry_source') not in ('BAZIS Edges.GVertices','BAZIS contour extrusion') or not p.get('edges') or p.get('warnings'):raise ValueError('Geometrie de placă neconfirmată')
        if not p.get('machining',{}).get('complete') or 'holes' not in p or p.get('drilling_source')!='BAZIS NewHoleDrilling':raise ValueError('Prelucrări incomplete')
        if any(not cut.get('trajectory',{}).get('complete') or not cut.get('section',{}).get('complete') for cut in p['machining'].get('cuts',[])):raise ValueError('Contur de frezare incomplet')
        if not p.get('frame'):raise ValueError('Reperul plăcii lipsește')
        holes=[]
        for h in p['holes']:
            if not h.get('coordinate_space_verified'):raise ValueError('Coordonate de găurire neverificate')
            holes.append({k:h.get(k) for k in ('diameter_mm','radius_mm','depth_mm','drill_mode','contour_element_count')})
            holes[-1].update(position=point(h['position_global_mm']),direction=direction(h['direction_global']))
        data=dict(material=p['material'],dimensions=[p['width'],p['height'],p['thickness']],
            frame_origin=point(p['frame']['origin']),frame_axes=[direction(a) for a in p['frame']['axes']],
            edges=edges(p),features=snapshot,machining=p['machining'],holes=unordered(holes))
        key=digest(data);board_rows.append((key,p));by_id[p['id']]=key
        if p.get('uid') is not None:by_uid[p['uid']]=key
    # Do not suppress pages when an accessory with potential module scope was omitted.
    included_hardware={h['id'] for h in hardware}
    for h in report.get('hardware',[]):
        if not h.get('hidden') and module['id'] in h.get('ancestors',[]) and h['id'] not in included_hardware:raise ValueError('Accesoriu cu asociere incompletă')
    fittings=[]
    for h in hardware:
        if h.get('approximate_components',1)!=0 or not h.get('edges'):raise ValueError('Geometrie de feronerie aproximată')
        links=h.get('connected_panel_uids',[])
        if any(uid not in by_uid for uid in links):raise ValueError('Legături către plăci din alt corp')
        fittings.append(dict(article=h.get('article') or h.get('name'),edges=edges(h),
            linked_boards=sorted(by_uid[uid] for uid in links),host=by_id.get(h.get('host_panel_id')),
            insertion_axis=direction(h['insertion_axis']) if h.get('insertion_axis') else None))
    return digest({'boards':sorted(k for k,_ in board_rows),'hardware':unordered(fittings)}),board_rows


def find_repetitions(report,modules,views=None):
    seen={};result={}
    raw={p['id']:p for collection in ('panels','hardware') for p in report.get(collection,[])}
    for module in modules:
        try:
            items=tuple([raw[p['id']] for p in group] for group in views[module['id']]) if views else None
            key,rows=describe_module(report,module,items)
        except (ValueError,KeyError,TypeError,IndexError) as error:
            module['repetition_check']={'status':'separate','reason':str(error)};continue
        if key not in seen:
            seen[key]=(module,rows);module['repetition_check']={'status':'original','signature':key};continue
        reference,reference_rows=seen[key];buckets=collections.defaultdict(list)
        for board_key,p in reference_rows:buckets[board_key].append(p)
        mapping=[]
        for board_key,p in rows:
            source=buckets[board_key].pop(0)
            mapping.append({'panel_id':p['id'],'reference_panel_id':source['id'],'label':p.get('label'),'reference_label':source.get('label'),'designation':p.get('designation','')})
        result[module['id']]={'reference_module_id':reference['id'],'reference_name':reference['name'],'panel_mapping':mapping,'signature':key}
        module['repetition_check']={'status':'duplicate',**result[module['id']]}
    return result
