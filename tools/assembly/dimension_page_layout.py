"""Physical spacing, nearest-edge dimension planning and non-paginated table flow."""
import math
from reportlab.lib.units import mm
PADDING=10*mm
DIMENSION_STEP=13
DIMENSION_START=20


def grouped_coordinates(entries):
    groups=[]
    for entry in sorted(entries,key=lambda entry:entry[0]):
        value,color=entry[:2];source=entry[2] if len(entry)>2 else 'hole'
        if groups and value-groups[-1][0][0]<=.01:groups[-1].append((value,color,source))
        else:groups.append([(value,color,source)])
    return groups


def nearest_dimension_sides(holes,outer,convert,width,height,contour_color):
    result={side:[] for side in ['bottom','top','left','right']}
    points=[(convert(h['position']),h['color'],'hole') for h in holes]
    points.extend((convert(q),contour_color,'contour') for q in outer)
    for q,color,source in points:
        if .01<q[0]<width-.01:result['top' if q[1]>height/2 else 'bottom'].append((q[0],color,source))
        if .01<q[1]<height-.01:result['right' if q[0]>width/2 else 'left'].append((q[1],color,source))
    return result


def dimension_envelope(sides,cuts,bands):
    extents={side:(DIMENSION_START+DIMENSION_STEP*(len(grouped_coordinates(entries))-1) if entries else 0) for side,entries in sides.items()}
    if cuts:
        extents['top']=max(extents['top'],23+20*(len(cuts)-1))
        extents['right']=max(extents['right'],25+20*(len(cuts)-1))
    overall={'bottom':extents['bottom']+DIMENSION_STEP+5,'left':extents['left']+DIMENSION_STEP+5}
    extents.update(overall)
    margins={side:max(value+12,45 if bands else 18) for side,value in extents.items()}
    return {'margins':margins,'overall':overall,'extents':extents}


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
