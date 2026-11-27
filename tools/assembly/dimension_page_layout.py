"""Physical spacing, nearest-edge dimension planning and non-paginated table flow."""
import math
from decimal import Decimal,ROUND_HALF_UP
from reportlab.lib.units import mm
PADDING=10*mm
DIMENSION_STEP=13
DIMENSION_START=20


def grouped_coordinates(entries):
    groups=[]
    for entry in sorted(entries,key=lambda entry:entry[0]):
        value,color=entry[:2];source=entry[2] if len(entry)>2 else 'hole'
        if groups and not source.startswith('step:') and not groups[-1][0][2].startswith('step:') and value-groups[-1][0][0]<=.01:groups[-1].append((value,color,source))
        else:groups.append([(value,color,source)])
    return groups


def merge_opposite_coordinates(sides):
    """A datum coordinate is shared across opposite rails, regardless of color.

    Local chain segments are deliberately excluded: equal lengths can describe
    different pieces of the contour and must remain visible.
    """
    for primary,opposite in [('bottom','top'),('left','right')]:
        coordinates={}
        for side in [primary,opposite]:
            for entry in sides[side]:
                if entry[2].startswith('step:'):continue
                key=Decimal(str(entry[0])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                coordinates.setdefault(key,{primary:[],opposite:[]})[side].append(entry)
        replacements={primary:[],opposite:[]}
        for group in coordinates.values():
            def score(side):
                entries=group[side]
                return (len(set(color for _,color,_ in entries)),any(source=='contour' for _,_,source in entries),len(entries))
            chosen=opposite if score(opposite)>score(primary) else primary
            for side in [chosen,opposite if chosen==primary else primary]:
                for entry in group[side]:
                    if entry not in replacements[chosen]:replacements[chosen].append(entry)
        for side in [primary,opposite]:
            sides[side]=[entry for entry in sides[side] if entry[2].startswith('step:')]+replacements[side]
    return sides


def contour_recesses(paths,convert,width,height):
    """Find excursions that leave and return to the same outer bounding side."""
    result=[]
    tolerance=.01
    for path in paths:
        points=[convert(p) for p in path[:-1]]
        for side,axis,edge in [('bottom',0,0),('top',0,height),('left',1,0),('right',1,width)]:
            normal=1-axis
            extent=(width,height)[axis]
            normal_extent=(width,height)[normal]
            contacts=[i for i,q in enumerate(points) if abs(q[normal]-edge)<=tolerance]
            if len(contacts)<2:continue
            for first,last in zip(contacts,contacts[1:]+[contacts[0]+len(points)]):
                if last-first<2:continue
                excursion=[points[i%len(points)] for i in range(first,last+1)]
                start,end=sorted((excursion[0][axis],excursion[-1][axis]))
                if end-start<=tolerance:continue
                inner=excursion[1:-1]
                if any(q[axis]<=tolerance or q[axis]>=extent-tolerance
                       or abs(q[normal]-(normal_extent-edge))<=tolerance for q in inner):continue
                deepest=max(inner,key=lambda q:abs(q[normal]-edge))
                result.append(dict(side=side,axis=axis,edge=edge,start=start,end=end,deepest=deepest,points=excursion))
    return result


def nearest_dimension_sides(holes,outer,convert,width,height,contour_color,recesses=()):
    result={side:[] for side in ['bottom','top','left','right']}
    contour_points=[convert(q) for q in outer]
    points=[(convert(h['position']),h['color'],'hole') for h in holes]
    points.extend((q,contour_color,'contour') for q in contour_points)
    for q,color,source in points:
        if .01<q[0]<width-.01:result['top' if q[1]>height/2 else 'bottom'].append((q[0],color,source))
        if .01<q[1]<height-.01:result['right' if q[0]>width/2 else 'left'].append((q[1],color,source))
    # Contour coordinates form a single straight chain. Keep an origin-based
    # contour coordinate only when it is also needed by a hardware hole.
    for side,entries in result.items():
        hole_values=[value for value,_,source in entries if source=='hole']
        result[side]=[entry for entry in entries if entry[2]!='contour' or any(abs(entry[0]-value)<=.01 for value in hole_values)]
    def remaining_on_axis(axis):
        recess_points=[q for recess in recesses if recess['axis']==axis for q in recess['points']]
        return [q for q in contour_points if not any(math.dist(q,r)<=.01 for r in recess_points)]

    chains={}

    for side in result:
        openings=[r for r in recesses if r['side']==side]
        if not openings:continue
        extent=(width,height)[openings[0]['axis']]
        values=[0,extent]+[value for r in openings for value in (r['start'],r['end'])]
        chains[side]=values
    for axis,extent,side in [(0,width,'bottom'),(1,height,'left')]:
        remaining=remaining_on_axis(axis)
        values=[]
        for value in sorted(q[axis] for q in remaining):
            if not values or value-values[-1]>.01:values.append(value)
        if len(values)<3:continue  # A rectangle needs only its overall size.
        normal_extent=height if axis==0 else width
        feature=[q[axis^1] for q in remaining if .01<q[axis]<extent-.01]
        if feature and min(abs(normal_extent-v) for v in feature)<min(abs(v) for v in feature):
            side='top' if axis==0 else 'right'
        chains.setdefault(side,[]).extend(values)
    for side,values in chains.items():
        stations=[]
        for value in sorted(values):
            if not stations or value-stations[-1]>.01:stations.append(value)
        for start,end in zip(stations,stations[1:]):
            result[side].append((end,contour_color,'step:'+str(start)))
    return merge_opposite_coordinates(result)


def dimension_envelope(sides,cuts,bands,overall_reference=None):
    extents={}
    for side,entries in sides.items():
        rails=len(grouped_coordinates([entry for entry in entries if len(entry)<3 or not entry[2].startswith('step:')]))+int(any(len(entry)>2 and entry[2].startswith('step:') for entry in entries))
        extents[side]=DIMENSION_START+DIMENSION_STEP*(rails-1) if rails else 0
    if cuts:
        extents['top']=max(extents['top'],23+20*(len(cuts)-1))
        extents['right']=max(extents['right'],25+20*(len(cuts)-1))
    split_count=sum(bool(cut.get('split')) for cut in cuts)
    split_rails={side:extents[side] for side in ('top','right')}
    for side in split_rails:
        extents[side]+=36*split_count
    overall={'bottom':extents['bottom']+DIMENSION_STEP+5,'left':extents['left']+DIMENSION_STEP+5}
    reference=sides if overall_reference is None else overall_reference
    overall_sides={'x':'top' if any(len(e)>2 and e[2].startswith('step:') for e in reference['top']) else 'bottom',
                   'y':'right' if any(len(e)>2 and e[2].startswith('step:') for e in reference['right']) else 'left'}
    for side in overall_sides.values():overall[side]=extents[side]+DIMENSION_STEP+5
    extents.update(overall)
    margins={side:max(value+18,45 if bands else 18) for side,value in extents.items()}
    return {'margins':margins,'overall':overall,'extents':extents,'overall_sides':overall_sides,'split_rails':split_rails}


def flow_coordinate_tables(groups,top,bottom,measure,row_height=10):
    """Keep font/row height fixed; continue data in neighboring columns, never repeat boards."""
    available=top-bottom
    capacity=max(1,math.floor((available-30)/row_height)-1)
    chunks=[]
    for group in groups:
        rows=group['rows'];colors=group['colors']
        for offset in range(0,max(1,len(rows)),capacity):
            chunk=dict(group,rows=rows[offset:offset+capacity],colors=colors[offset:offset+capacity])
            chunk['width']=measure(chunk['rows'],chunk['title'])
            chunk['height']=30+row_height*(len(chunk['rows'])+1)
            chunks.append(chunk)
    columns=[]
    for chunk in chunks:
        if not columns or columns[-1]['used']+PADDING+chunk['height']>available:
            columns.append({'chunks':[],'used':0,'width':0})
        column=columns[-1]
        chunk['top']=top-column['used']-(PADDING if column['chunks'] else 0)
        column['used']=top-chunk['top']+chunk['height'];column['width']=max(column['width'],chunk['width']);column['chunks'].append(chunk)
    return columns


def fit_view_regions(region,views):
    """Maximal common scale, allocating each face the space its own dimensions require."""
    left,bottom,right,top=region
    margins=[view['envelope']['margins'] for view in views]
    annotation_height=sum(m['top']+m['bottom'] for m in margins)
    available=top-bottom-PADDING*max(0,len(views)-1)-annotation_height
    max_left=max(m['left'] for m in margins);max_right=max(m['right'] for m in margins)
    scale=min([available/sum(view['height'] for view in views)]+
              [(right-left-max_left-max_right)/view['width'] for view in views])
    if scale<=0:raise ValueError('Spațiu insuficient pentru desen și cote la spațierea cerută')
    heights=[m['top']+view['height']*scale+m['bottom'] for view,m in zip(views,margins)]
    free=top-bottom-sum(heights)-PADDING*max(0,len(views)-1)
    slot_top=top
    result=[]
    for view,m,height in zip(views,margins,heights):
        slot_height=height+free/len(views);slot_bottom=slot_top-slot_height
        total_w=max_left+view['width']*scale+max_right
        result.append({'scale':scale,'left':left+(right-left-total_w)/2+max_left,
                       'bottom':slot_bottom+free/len(views)/2+m['bottom'],'bounds':(left,slot_bottom,right,slot_top)})
        slot_top=slot_bottom-PADDING
    return result
