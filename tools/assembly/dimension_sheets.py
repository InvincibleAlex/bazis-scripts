"""Two-sided native board sheets; all view transforms are presentation only."""
import math
from reportlab.lib.units import mm
from dimension_sections import cross_section,section_label,draw_detail,draw_section_mark,DETAIL_WIDTH,DETAIL_HEIGHT,DETAIL_GAP,SECTIONS_PER_PAGE
from dimension_annotations import AnnotationLayout
from dimension_page_layout import PADDING,DIMENSION_STEP,DIMENSION_START,grouped_coordinates,nearest_dimension_sides,contour_recesses,dimension_envelope,flow_coordinate_tables,fit_view_regions
from pathlib import Path
from assembly_fonts import register_body_font
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from export_dimensions import geometry,holes_for,milling_for,flatten,xy,curve,dimension,dimension_positions,fmt

FACE=HexColor('#0000ff');THROUGH=HexColor('#ff0000');EDGE=HexColor('#ff00ff')
CONTOUR=HexColor('#000000')
MILL=HexColor('#b15d12');INK=HexColor('#172b3a');BUBBLE=HexColor('#1668b2')
PAGE_W,PAGE_H=1191,842
PAGE_FRAME_INSET=0
TABLE_RIGHT_PADDING=10*mm


def board_fmt(value):
    return fmt(value)


def selected_faces(holes,cuts):
    front=any(h['face']=='Zmax' and not h['through'] for h in holes)
    back=any(h['face']=='Zmin' and not h['through'] for h in holes)
    for cut in cuts:
        if cut.get('through'):continue
        if cut.get('face')=='Zmax':front=True
        elif cut.get('face')=='Zmin':back=True
        else:return [False,True]  # An unclassified native machining face must not be hidden.
    if front and back:return [False,True]
    if back:return [True]
    return [False]


def view_transform(lo,hi,back=False,long_horizontal=False):
    width,height=hi[0]-lo[0],hi[1]-lo[1]
    flip='y' if width>=height else 'x'
    rotate=long_horizontal and height>width
    def convert(point):
        x,y=point[0]-lo[0],point[1]-lo[1]
        if back:
            if flip=='x':x=width-x
            else:y=height-y
        return [y,width-x] if rotate else [x,y]
    def direction(d):
        x=-d[0] if back and flip=='x' else d[0]
        y=-d[1] if back and flip=='y' else d[1]
        z=-d[2] if back else d[2]
        return [y,-x,z] if rotate else [x,y,z]
    return convert,direction,'y' if rotate else flip


def classified_holes(panel,lo):
    holes=holes_for(panel,lo)
    z=panel.get('z_limits') or {};low=z.get('LowZ',0);high=z.get('HighZ',low+panel['thickness'])
    for h in holes:
        end=h['z']+h['direction'][2]*(h['depth'] or 0)
        h['through']=h['face'].startswith('Z') and min(h['z'],end)<=low+.01 and max(h['z'],end)>=high-.01
        h['color']=THROUGH if h['through'] else FACE if h['face'].startswith('Z') else EDGE
    return holes


def face_holes(holes,back):
    face='Zmin' if back else 'Zmax'
    return [h for h in holes if h['through'] or h['face']==face or not h['face'].startswith('Z')]


def sampled(e):
    if e['type']=='line':return [xy(e['start']),xy(e['end'])]
    if e['type']=='circle':
        c=xy(e['center']);r=e['radius']
        return [[c[0]+r*math.cos(i*math.pi/32),c[1]+r*math.sin(i*math.pi/32)] for i in range(65)]
    if e['type']=='arc':
        c=xy(e['center']);a=xy(e['start']);b=xy(e['end']);r=math.dist(a,c)
        start=math.atan2(a[1]-c[1],a[0]-c[0]);end=math.atan2(b[1]-c[1],b[0]-c[0])
        sweep=(end-start)%(2*math.pi) if e.get('counterclockwise') else -((start-end)%(2*math.pi))
        n=max(8,math.ceil(abs(sweep)*16))
        return [[c[0]+r*math.cos(start+sweep*i/n),c[1]+r*math.sin(start+sweep*i/n)] for i in range(n+1)]
    return []


def closed_loops(contours):
    loops=[];seen=set()
    for contour in contours:
        remaining=list(flatten(contour))
        while remaining:
            first=remaining.pop(0);points=sampled(first);elements=[first]
            if not points:continue
            while math.dist(points[0],points[-1])>.001:
                found=False
                for i,e in enumerate(remaining):
                    q=sampled(e)
                    if not q:continue
                    if math.dist(points[-1],q[0])<.001:pass
                    elif math.dist(points[-1],q[-1])<.001:q=list(reversed(q))
                    else:continue
                    points.extend(q[1:]);elements.append(remaining.pop(i));found=True;break
                if not found:break
            if len(points)<4 or math.dist(points[0],points[-1])>.001:continue
            key=tuple(sorted(set((round(x,4),round(y,4)) for x,y in points)))
            if key in seen:continue
            seen.add(key);loops.append({'points':points,'elements':elements})
    return loops


def contains(poly,q):
    inside=False;x,y=q
    for a,b in zip(poly,poly[1:]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside


def contour_data(panel):
    contours=[panel.get('native_contour')];tree=panel.get('contour_tree')
    def walk(node):
        if not node:return
        contours.append(node.get('geometry'))
        for child in node.get('children',[]):walk(child)
    walk(tree)
    loops=closed_loops(contours)
    for loop in loops:
        point=loop['points'][0]
        loop['interior']=sum(contains(other['points'],point) for other in loops if other is not loop)%2==1
    return loops


def native_bands(panel):
    bands=(panel.get('module_comparison') or {}).get('bands')
    if bands is None:bands=(panel.get('duplicate_signature') or {}).get('bands',[])
    rows=[];types={}
    for b in bands:
        key=(str(b.get('Material',b.get('material',''))).strip(),str(b.get('Sign',b.get('sign',''))).strip(),b.get('Thickness',b.get('thickness')),b.get('Width',b.get('width')))
        if key not in types:types[key]=str(len(types)+1)
        rows.append({'tag':types[key],'element':b.get('ElemIndex',b.get('element')),
                     'name':str(b.get('Material',b.get('material',''))).split('\r')[0],'sign':str(b.get('Sign',b.get('sign',''))),
                     'thickness':b.get('Thickness',b.get('thickness'))})
    return rows


def grain_vector(panel):
    appearance=panel.get('appearance',{});props=appearance.get('properties',{})
    name=appearance.get('orientation_name');raw=props.get('TextureOrientation')
    if not name:
        for key,value in appearance.get('orientation_enum',{}).items():
            if value==raw:name=key
    if name=='Horizontal':return [1,0,0]
    if name=='Vertical':return [0,1,0]
    return None


def content_column_widths(headers,rows,font,max_width):
    measured=[max(pdfmetrics.stringWidth(str(row[i]),'Body',font) for row in [headers]+rows)+8 for i in range(len(headers))]
    total=sum(measured)
    return measured if total<=max_width else [value*max_width/total for value in measured]


def section_detail_positions(page_width,page_height,count):
    right=page_width-PAGE_FRAME_INSET-PADDING;columns=min(2,max(1,count))
    start=right-columns*DETAIL_WIDTH-max(0,columns-1)*PADDING
    return [(start+(i%columns)*(DETAIL_WIDTH+PADDING),page_height-PADDING-7-(i//columns)*(DETAIL_HEIGHT+PADDING)) for i in range(count)]


def coordinate_table_position(page_width,headers,rows,font=6.5,frame_inset=PAGE_FRAME_INSET):
    right=page_width-frame_inset-TABLE_RIGHT_PADDING
    max_width=240 if page_width<1000 else 300
    width=sum(content_column_widths(headers,rows,font,max_width))
    return right-width,width


def cell_lines(value,font,width):
    lines=[]
    for paragraph in str(value).replace('\r','\n').split('\n'):
        for line in simpleSplit(paragraph,'Body',font,max(1,width)+.01) or ['']:
            part=''
            for char in line:
                if part and pdfmetrics.stringWidth(part+char,'Body',font)>width+.01:lines.append(part);part=char
                else:part+=char
            lines.append(part)
    return lines or ['']


def table_metrics(headers,rows,font,row_height,width):
    widths=content_column_widths(headers,rows,font,width)
    lines=[[cell_lines(value,font,w-8) for value,w in zip(row,widths)] for row in [headers]+rows]
    heights=[max(row_height,max(len(cell) for cell in row)*(font+2)+1.5) for row in lines]
    return widths,lines,heights


def table(c,x,top,width,headers,rows,widths=None,colors=None,font=6.5,row_height=10,title=None):
    measured,lines,heights=table_metrics(headers,rows,font,row_height,width);width=sum(measured)
    c.saveState();cols=[x]
    for value in measured:cols.append(cols[-1]+value)
    c.setStrokeColor(HexColor('#6b7780'));c.setLineWidth(.2)
    if title:
        title_height=20
        c.setFillColor(HexColor('#f4f6f7'));c.rect(x,top-title_height,width,title_height,stroke=1,fill=1)
        c.setFillColor(INK);c.setFont('Body',8);c.drawCentredString(x+width/2,top-title_height/2-3,title)
        top-=title_height
    c.setFillColor(HexColor('#f4f6f7'));c.rect(x,top-heights[0],width,heights[0],stroke=0,fill=1)
    total_height=sum(heights)
    for cx in cols:c.line(cx,top,cx,top-total_height)
    y=top;c.line(x,y,x+width,y);c.setFont('Body',font)
    for index,(cells,height) in enumerate(zip(lines,heights)):
        c.setFillColor(colors[index-1] if index and colors else INK)
        for i,cell in enumerate(cells):
            for j,text in enumerate(cell):c.drawString(cols[i]+4,y-font-2-j*(font+2),text)
        y-=height;c.line(x,y,x+width,y)
    c.restoreState();return y


def draw_axes(c,left,bottom):
    c.saveState();c.setStrokeColor(INK);c.setFillColor(INK);c.setLineWidth(.25);c.setFont('Body',5)
    c.circle(left,bottom,2,stroke=1,fill=0)
    c.line(left,bottom,left+12,bottom);c.line(left,bottom,left,bottom+12)
    c.line(left+12,bottom,left+9,bottom+1);c.line(left+12,bottom,left+9,bottom-1)
    c.line(left,bottom+12,left-1,bottom+9);c.line(left,bottom+12,left+1,bottom+9)
    c.drawString(left+14,bottom-1.5,'X');c.drawString(left-1.5,bottom+14,'Y');c.restoreState()


def polygon_side_dimensions(c,loop,convert,project):
    polygon=[project(convert(p)) for p in loop['points']]
    for element in loop['elements']:
        if element.get('type')!='line':continue
        na,nb=xy(element['start']),xy(element['end']);a=project(convert(na));b=project(convert(nb))
        length=math.dist(a,b)
        if length<.0001:continue
        dx,dy=b[0]-a[0],b[1]-a[1];normal=[-dy/length,dx/length];mid=[(a[i]+b[i])/2 for i in range(2)]
        sign=1 if contains(polygon,[mid[i]+normal[i]*.5 for i in range(2)]) else -1
        label=fmt(math.dist(na,nb));offset=-sign*14
        angle=math.degrees(math.atan2(dy,dx))
        if angle>90:angle-=180
        if angle<-90:angle+=180
        # Try several inset distances before moving a side's dimension outside.
        if length>=pdfmetrics.stringWidth(label,'Body',7)+10:
            for inset in [12,18,24,30,36,42]:
                candidate=sign*inset
                c.saveState();c.setFont('Body',7);c.translate(mid[0]+normal[0]*candidate,mid[1]+normal[1]*candidate);c.rotate(angle)
                box=c.annotation_layout.text_box(c,0,3,label,centered=True);c.restoreState()
                corners=[(box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])]
                if c.annotation_layout.fits(box) and all(contains(polygon,q) for q in corners):offset=candidate;break
        aligned_dimension(c,a,b,offset,label,THROUGH)



def annotate_loop(c,loop,convert,project,width,height,index):
    pts=[convert(p) for p in loop.get('extrema',loop['points'])];mn=[min(p[i] for p in pts) for i in range(2)];mx=[max(p[i] for p in pts) for i in range(2)]
    center=[(mn[i]+mx[i])/2 for i in range(2)];cx,cy=project(center)
    c.setFillColor(THROUGH);c.setFont('Body',7)
    start,end=project(mn),project(mx);span_x=end[0]-start[0];span_y=end[1]-start[1]
    label_x=fmt(mx[0]-mn[0]);label_y=fmt(mx[1]-mn[1])
    fits=span_x>=pdfmetrics.stringWidth(label_x,'Body',7)+12 and span_y>=pdfmetrics.stringWidth(label_y,'Body',7)+18
    tag_y=end[1]+6 if fits else end[1]+29
    tag_anchor=min((project(convert(q)) for q in loop['points']),key=lambda q:math.dist(q,(start[0]+4,tag_y)))
    c.annotation_layout.draw(c,start[0]+4,tag_y,'D'+str(index),marker='decupaj',marker_anchor=tag_anchor)
    if len(loop['elements'])==1 and loop['elements'][0]['type']=='circle':
        radius=loop['elements'][0]['radius'];label='Ø '+fmt(radius*2)
        inside=span_x>=pdfmetrics.stringWidth(label,'Body',7)+12 and span_y>=20
        dimension(c,project([mn[0],center[1]]),project([mx[0],center[1]]),cy if inside else end[1]+14,label,color=THROUGH)
    elif len(loop['elements'])>4 or any(e.get('type')=='line' and abs(xy(e['start'])[0]-xy(e['end'])[0])>.000001 and abs(xy(e['start'])[1]-xy(e['end'])[1])>.000001 for e in loop['elements']):
        polygon_side_dimensions(c,loop,convert,project)
    else:
        dimension(c,project([mn[0],center[1]]),project([mx[0],center[1]]),cy-span_y*.25 if fits else end[1]+14,label_x,color=THROUGH)
        dimension(c,project([center[0],mn[1]]),project([center[0],mx[1]]),cx+span_x*.25 if fits else end[0]+16,label_y,True,color=THROUGH)
    if loop.get('technological') and len(loop['elements'])==1 and loop['elements'][0]['type']=='circle':
        # A technology circle is located by its native center on both axes.
        edge_x=0 if center[0]<width-center[0] else width
        edge_y=0 if center[1]<height-center[1] else height
        dimension(c,project([edge_x,center[1]]),project(center),cy-13,fmt(abs(edge_x-center[0])),color=THROUGH)
        dimension(c,project([center[0],edge_y]),project(center),cx+13,fmt(abs(edge_y-center[1])),True,color=THROUGH)
        return
    # Preserve the established boundary dimensions on original contour cutouts.
    edge_x=0 if mn[0]<width-mx[0] else width;value_x=mn[0] if edge_x==0 else mx[0]
    edge_y=0 if mn[1]<height-mx[1] else height;value_y=mn[1] if edge_y==0 else mx[1]
    dimension(c,project([edge_x,center[1]]),project([value_x,center[1]]),cy-13,fmt(abs(edge_x-value_x)),color=THROUGH)
    dimension(c,project([center[0],edge_y]),project([center[0],value_y]),cx+13,fmt(abs(edge_y-value_y)),True,color=THROUGH)



def annotate_round_contours(c,contour,loops,native):
    layout=c.annotation_layout
    sources=[(list(flatten(contour)),False)]
    sources.extend((loop['elements'],loop['interior']) for loop in loops)
    marks={}
    for elements,interior in sources:
        for element in elements:
            kind=element.get('type')
            if kind not in ('arc','circle'):continue
            center=xy(element['center'])
            points=sampled(element)
            middle=points[len(points)//2]
            radius=element['radius'] if kind=='circle' else math.dist(center,xy(element['start']))
            if radius<=0 or not math.isfinite(radius):continue
            def key_point(p):return tuple(round(v,4) for v in p)
            identity=(kind,key_point(center),round(radius,4))
            if kind=='arc':
                ends=sorted([key_point(points[0]),key_point(points[-1])])
                n=len(points)
                mid=(points[n//2] if n%2 else [(points[n//2-1][i]+points[n//2][i])/2 for i in range(2)])
                identity+=(*ends,key_point(mid))
            if identity not in marks or interior:
                marks[identity]=(kind,center,middle,radius,interior)
    if not marks:return
    for elements,_ in sources:
        for element in elements:
            points=sampled(element)
            for start,end in zip(points,points[1:]):
                layout.add_stroke(c,native(start),native(end))
    c.saveState();c.setFont('Body',7)
    for kind,center,middle,radius,interior in marks.values():
        color=THROUGH if interior else INK
        c.setStrokeColor(color);c.setFillColor(color)
        target=native(middle);origin=native(center)
        dx,dy=(target[i]-origin[i] for i in range(2))
        length=math.hypot(dx,dy)
        if length<1e-8:continue
        label=('D '+fmt(2*radius)) if kind=='circle' else ('R '+fmt(radius))
        layout.draw(c,target[0]+18*dx/length,target[1]+18*dy/length,label,
                    centered=True,target=target,avoid_strokes=True)
    c.restoreState()


def aligned_dimension(c,a,b,offset,label,color):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    if length<.0001:return
    normal=[-dy/length,dx/length];a2=[a[i]+normal[i]*offset for i in range(2)];b2=[b[i]+normal[i]*offset for i in range(2)]
    c.saveState();c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(.2);c.setFont('Body',7)
    c.setStrokeAlpha(.5);c.line(*a,*a2);c.line(*b,*b2);c.setStrokeAlpha(1);c.line(*a2,*b2)
    if getattr(c,'annotation_layout',None):
        for start,end in [(a,a2),(b,b2),(a2,b2)]:c.annotation_layout.add_stroke(c,start,end)
    for q in [a2,b2]:c.line(q[0]-2,q[1]-2,q[0]+2,q[1]+2)
    angle=math.degrees(math.atan2(dy,dx))
    if angle>90:angle-=180
    if angle<-90:angle+=180
    c.translate((a2[0]+b2[0])/2,(a2[1]+b2[1])/2);c.rotate(angle)
    if getattr(c,'annotation_layout',None):c.annotation_layout.draw(c,0,1.5,label,centered=True,leader=False)
    else:c.drawCentredString(0,1.5,label)
    c.restoreState()


def hatch_closed_opening(c,loop,convert,project):
    points=loop.get('points',[])
    if not loop.get('interior') or len(points)<4 or math.dist(points[0],points[-1])>.001:return
    points=[project(convert(point)) for point in points]
    xmin=min(p[0] for p in points);xmax=max(p[0] for p in points)
    ymin=min(p[1] for p in points);ymax=max(p[1] for p in points)
    path=c.beginPath();path.moveTo(*points[0])
    for point in points[1:]:path.lineTo(*point)
    path.close();c.saveState();c.clipPath(path,stroke=0,fill=0)
    c.setStrokeColor(HexColor('#aaaaaa'));c.setLineWidth(.15);c.setStrokeAlpha(1)
    spacing=4
    for index in range(math.floor((ymin-xmax)/spacing),math.ceil((ymax-xmin)/spacing)+1):
        intercept=index*spacing;c.line(xmin,xmin+intercept,xmax,xmax+intercept)
    c.restoreState()


def draw_hidden_machining(c,holes,cuts,back,convert,project):
    """Opposite-face operations are context only: no labels or coordinates."""
    opposite='Zmax' if back else 'Zmin'
    c.saveState();c.setStrokeColor(HexColor('#aaaaaa'));c.setLineWidth(.2);c.setDash(2,2)
    for hole in holes:
        if hole['face']!=opposite or hole['through']:continue
        center=project(convert(hole['position']))
        # Infer the view scale from two local points, also for rotated views.
        a=project(convert([0,0]));b=project(convert([1,0]));scale=math.dist(a,b)
        c.circle(*center,max((hole['diameter'] or 0)*scale/2,.65),stroke=1,fill=0)
    for cut in cuts:
        if cut.get('face')!=opposite or cut.get('through'):continue
        if cut.get('verified_rectangle'):
            points=[project(convert(q)) for q in cut['corners']]
            path=c.beginPath();path.moveTo(*points[0])
            for point in points[1:]:path.lineTo(*point)
            path.close();c.drawPath(path)
        else:
            for element in cut['trajectory']:curve(c,element,lambda point:project(convert(point)))
    c.restoreState()


def draw_milling(c,cuts,back,convert,project,width,height,left,bottom,top,right,split_rails=None):
    from bevel_sections import draw_bevel_path
    visible=[cut for cut in cuts if not cut.get('no_effect') and not cut.get('duplicate_bevel') and (cut.get('bevel') or cut.get('through') or cut.get('face')==('Zmin' if back else 'Zmax') or cut.get('face') not in ('Zmin','Zmax'))]
    split_index=0
    for index,cut in enumerate(visible):
        c.setStrokeColor(MILL);c.setFillColor(MILL);c.setLineWidth(.25);c.setFont('Body',7)
        if cut.get('bevel'):
            draw_bevel_path(c,cut['bevel'],back,convert,project,MILL)
            continue
        if not cut['verified_rectangle']:
            c.setDash(3,2)
            for e in cut['trajectory']:curve(c,e,lambda p:project(convert(p)))
            c.setDash();continue
        pts=[convert(q) for q in cut['corners']];path=c.beginPath();path.moveTo(*project(pts[0]))
        for q in pts[1:]:path.lineTo(*project(q))
        path.close();c.drawPath(path)
        mn=[min(p[i] for p in pts) for i in range(2)];mx=[max(p[i] for p in pts) for i in range(2)]
        cx,cy=project([(mn[0]+mx[0])/2,(mn[1]+mx[1])/2])
        vertical=abs(mx[1]-mn[1]-cut['length'])<.001
        horizontal=abs(mx[0]-mn[0]-cut['length'])<.001
        top_rail,right_rail=top,right
        if cut.get('split') and split_rails:
            top_rail+=split_rails['top']+36*split_index
            right_rail+=split_rails['right']+36*split_index
            index=0
            split_index+=1
        if not vertical and not horizontal:
            aligned_dimension(c,project(pts[0]),project(pts[1]),14,'L '+fmt(cut['length']),MILL)
            if not cut.get('section_detail'):aligned_dimension(c,project(pts[1]),project(pts[2]),12,'l '+fmt(cut['width']),MILL)
            corner=min(pts,key=lambda p:min(p[0],width-p[0],p[1],height-p[1]))
            distance,axis,edge=min([(corner[0],0,0),(width-corner[0],0,width),(corner[1],1,0),(height-corner[1],1,height)])
            q=list(corner);q[axis]=edge
            aligned_dimension(c,project(q),project(corner),12,fmt(distance),MILL)
        elif vertical:
            edge=0 if mn[0]<width-mx[0] else width;boundary=mn[0] if edge==0 else mx[0]
            dimension(c,project([edge,height]),project([boundary,height]),top_rail+12+index*20,fmt(abs(edge-boundary)),color=MILL)
            if not cut.get('section_detail'):dimension(c,project([mn[0],height]),project([mx[0],height]),top_rail+23+index*20,'l '+fmt(cut['width']),color=MILL)
            if mn[1]>.001:dimension(c,project([width,0]),project([width,mn[1]]),right_rail+12,fmt(mn[1]),True,color=MILL)
            if cut['length']<height-.001:dimension(c,project([width,mn[1]]),project([width,mx[1]]),right_rail+25,'L '+fmt(cut['length']),True,color=MILL)
        else:
            edge=0 if mn[1]<height-mx[1] else height;boundary=mn[1] if edge==0 else mx[1]
            dimension(c,project([width,edge]),project([width,boundary]),right_rail+12+index*20,fmt(abs(edge-boundary)),True,color=MILL)
            if not cut.get('section_detail'):dimension(c,project([width,mn[1]]),project([width,mx[1]]),right_rail+23+index*20,'l '+fmt(cut['width']),True,color=MILL)
            if mn[0]>.001:dimension(c,project([0,height]),project([mn[0],height]),top_rail+12,fmt(mn[0]),color=MILL)
            if cut['length']<width-.001:dimension(c,project([mn[0],height]),project([mx[0],height]),top_rail+25,'L '+fmt(cut['length']),color=MILL)
    return visible


def baseline_dimensions(c,project,entries,axis,left,bottom,side=None,width=0,height=0):
    groups=grouped_coordinates(entries);side=side or ('bottom' if axis==0 else 'left')
    sign=1 if side in ('top','right') else -1
    datum=[0,height if side=='top' else 0] if axis==0 else [width if side=='right' else 0,0]
    origin=project(datum)
    base=project([width,height])[axis^1] if side in ('top','right') else (bottom if axis==0 else left)
    ordinary=[group for group in groups if not any(source.startswith('step:') for _,_,source in group)]
    chain=[group for group in groups if any(source.startswith('step:') for _,_,source in group)]
    for index,group in enumerate(ordinary+chain):
        value=sum(v for v,_,_ in group)/len(group);colors=[]
        step=next((float(source.split(':',1)[1]) for _,_,source in group if source.startswith('step:')),None)
        label=board_fmt(value-step) if step is not None else board_fmt(value) if any(source=='contour' for _,_,source in group) else fmt(value)
        group=sorted(group,key=lambda entry:(0 if entry[2]=='contour' or entry[2].startswith('step:') else 1,0 if entry[1]==THROUGH else 1))
        for _,color,_ in group:
            if color not in colors:colors.append(color)
        point=[value,datum[1]] if axis==0 else [datum[0],value]
        endpoint=project(point);rail=len(ordinary) if step is not None else index
        offset=base+sign*(DIMENSION_START+rail*DIMENSION_STEP)
        start=project([step,datum[1]] if axis==0 else [datum[0],step]) if step is not None else origin
        dimension(c,start,endpoint,offset,label,axis==1,color=colors[0],secondary_colors=colors[1:])


def draw_band_marker(c,label,center,target):
    c.saveState();c.setStrokeColor(INK);c.setFillColor(INK);c.setLineWidth(.25)
    dx,dy=target[0]-center[0],target[1]-center[1];length=math.hypot(dx,dy)
    radius=max(7,pdfmetrics.stringWidth(str(label),'Body',7)/2+3)
    if length>radius+4:
        ux,uy=dx/length,dy/length
        c.line(center[0]+ux*radius,center[1]+uy*radius,*target)
        # Open arrowhead terminates exactly on the native contour edge.
        c.line(*target,target[0]-ux*5-uy*1.7,target[1]-uy*5+ux*1.7)
        c.line(*target,target[0]-ux*5+uy*1.7,target[1]-uy*5-ux*1.7)
    c.setFillColorRGB(1,1,1);c.circle(*center,radius,stroke=1,fill=1)
    c.setFillColor(INK);c.setFont('Body',7);c.drawCentredString(center[0],center[1]-2.4,str(label));c.restoreState()


def draw_view(c,p,lo,hi,contour,edges,holes,cuts,loops,bands,back,base,portrait=False,single=False,has_sections=False,placement=None,side_entries=None,envelope=None,recesses=None,cleanup_report=None,output_scale=1):
    width,height=hi[0]-lo[0],hi[1]-lo[1];convert,vector,flip=view_transform(lo,hi,back,long_horizontal=not single)
    if not single and height>width:width,height=height,width
    if placement is None:
        placement={'scale':min(650/width,205/height),'left':120,'bottom':base,'bounds':(20,base-110,850,base+245)}
    scale,left,bottom=placement['scale'],placement['left'],placement['bottom']
    top=bottom+height*scale;right=left+width*scale
    project=lambda p:(left+p[0]*scale,bottom+p[1]*scale)
    native=lambda p:project(convert(p))
    c.annotation_layout=AnnotationLayout(placement['bounds'])
    if cleanup_report is not None:c.annotation_layout.start_cleanup()
    if contour:
        c.setStrokeColor(INK);c.setLineWidth(.25)
        for e in flatten(contour):curve(c,e,native)
    else:
        c.setStrokeColor(INK);c.setLineWidth(.25)
        for a,b in edges:c.line(*native(a),*native(b))
    for loop in loops:
        hatch_closed_opening(c,loop,convert,project)
        c.setStrokeColor(THROUGH if loop['interior'] else INK)
        for e in loop['elements']:curve(c,e,native)
    # Contour vertices are located from the view origin, with common coordinates stacked once.
    outer=[xy(e[key]) for loop in loops if not loop['interior'] for e in loop['elements'] for key in ['start','end'] if key in e]
    draw_hidden_machining(c,holes,cuts,back,convert,project)
    visible=face_holes(holes,back);positions=[];round_mark_obstacles=[]
    for h in visible:
        q=convert(h['position']);a=project(q);d=vector(h['direction']);color=h['color'];r=(h['diameter'] or 0)*scale/2
        c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(.25)
        if h['face'].startswith('Z'):
            circle_radius=max(r,.65)
            c.circle(*a,circle_radius,stroke=1,fill=0)
            ring=[(a[0]+circle_radius*math.cos(i*math.tau/16),a[1]+circle_radius*math.sin(i*math.tau/16)) for i in range(16)]
            round_mark_obstacles.extend(zip(ring,ring[1:]+ring[:1]))
        else:
            # Native drill axis and diameter define the plan-view slot into the edge.
            length=h['depth'] or 0;norm=math.hypot(d[0],d[1]);n=[-d[1]/norm,d[0]/norm] if norm else [0,1]
            radius=(h['diameter'] or 0)/2
            pts=[[q[0]+n[0]*radius,q[1]+n[1]*radius],[q[0]+d[0]*length+n[0]*radius,q[1]+d[1]*length+n[1]*radius],
                 [q[0]+d[0]*length-n[0]*radius,q[1]+d[1]*length-n[1]*radius],[q[0]-n[0]*radius,q[1]-n[1]*radius]]
            path=c.beginPath();path.moveTo(*project(pts[0]))
            for pt in pts[1:]:path.lineTo(*project(pt))
            path.close();c.setDash(2,1);c.drawPath(path);c.setDash()
            tip=project([q[0]+d[0]*length,q[1]+d[1]*length])
            c.line(*a,*tip)
            slot=[project(pt) for pt in pts]
            round_mark_obstacles.extend(zip(slot,slot[1:]+slot[:1]))
            round_mark_obstacles.append((a,tip))
        cross=[((a[0]-2,a[1]),(a[0]+2,a[1])),((a[0],a[1]-2),(a[0],a[1]+2))]
        for start,end in cross:c.line(*start,*end)
        round_mark_obstacles.extend(cross)
        positions.append((h,q,a))
    for h,q,a in sorted(positions,key=lambda item:(-item[1][1],item[1][0])):
        c.setFont('Body',6);c.setFillColor(h['color']);c.setStrokeColor(h['color'])
        c.annotation_layout.draw(c,a[0]+5,a[1]+5,h['tag'],target=a,marker='gaură')
    if recesses is None:
        recesses=contour_recesses([loop['points'] for loop in loops if not loop['interior']],convert,width,height)
    side_entries=side_entries or nearest_dimension_sides(visible,outer,convert,width,height,CONTOUR,recesses)
    if envelope is None:
        reference=nearest_dimension_sides(visible,outer,convert,width,height,CONTOUR) if recesses else None
        envelope=dimension_envelope(side_entries,cuts,bands,reference)
    for side,entries in side_entries.items():
        baseline_dimensions(c,project,entries,0 if side in ('top','bottom') else 1,left,bottom,side,width,height)
    for i,loop in enumerate([loop for loop in loops if loop['interior']],1):annotate_loop(c,loop,convert,project,width,height,i)
    draw_milling(c,cuts,back,convert,project,width,height,left,bottom,top,right,envelope.get('split_rails'))
    x_side=envelope.get('overall_sides',{}).get('x','bottom')
    y_side=envelope.get('overall_sides',{}).get('y','left')
    x_datum=height if x_side=='top' else 0
    y_datum=width if y_side=='right' else 0
    dimension(c,project([0,x_datum]),project([width,x_datum]),(top+envelope['overall']['top'] if x_side=='top' else bottom-envelope['overall']['bottom']),board_fmt(width),color=CONTOUR,overall=True)
    dimension(c,project([y_datum,0]),project([y_datum,height]),(right+envelope['overall']['right'] if y_side=='right' else left-envelope['overall']['left']),board_fmt(height),True,color=CONTOUR,overall=True)
    grain=grain_vector(p)
    if grain:
        d=vector(grain);length=min(45,max(14,min(width,height)*scale*.3));nx,ny=-d[1],d[0]
        c.setStrokeColor(HexColor('#777777'));c.setLineWidth(.2)
        gx,gy=project([width*.5,height*.5])
        def grain_lines(x,y):
            return [((x-d[0]*length/2+nx*offset,y-d[1]*length/2+ny*offset),
                     (x+d[0]*length/2+nx*offset,y+d[1]*length/2+ny*offset)) for offset in (-3,3)]
        drawn_grain=grain_lines(gx,gy)
        technological=[loop for loop in loops if loop.get('technological')]
        if technological:
            from technological_openings import intersects
            def projected(loop):return [native(p) for p in loop['points']]
            def hits(poly,lines):
                edges=list(zip(poly,poly[1:]))
                return any(contains(poly,a) or contains(poly,b) or any(intersects(a,b,u,v) for u,v in edges)
                           for a,b in lines)
            if any(hits(projected(loop),drawn_grain) for loop in technological):
                openings=[projected(loop) for loop in loops if loop['interior']]
                outer=[projected(loop) for loop in loops if not loop['interior']]
                for q in range(1,10):
                    proposals=(grain_lines(*project((x*width,y*height)))
                               for x,y in ((.5+q/20,.5),(.5-q/20,.5),(.5,.5+q/20),(.5,.5-q/20)))
                    replacement=next((lines for lines in proposals
                                      if any(all(contains(poly,p) for edge in lines for p in edge) for poly in outer)
                                      and not any(hits(poly,lines) for poly in openings)),None)
                    if replacement:
                        drawn_grain=replacement
                        break
        for start,end in drawn_grain:
            c.line(*start,*end)
            round_mark_obstacles.append((start,end))
    contour_elements=(contour or {}).get('elements',[])
    band_markers=[]
    for band in bands:
        index=band['element']
        if not isinstance(index,int) or index<0 or index>=len(contour_elements):continue
        pts=sampled(contour_elements[index])
        if not pts:continue
        mid=pts[len(pts)//2] if len(pts)>2 else [(pts[0][i]+pts[-1][i])/2 for i in range(2)]
        xx,yy=native(mid)
        # A short external leader keeps the actual banded edge unobstructed.
        _,nx,ny=min([(abs(xx-left),-1,0),(abs(right-xx),1,0),(abs(yy-bottom),0,-1),(abs(top-yy),0,1)])
        marker=[xx+nx*29,yy+ny*29]
        for shift in [24,-24,44,-44,64,-64,84,-84,104,-104,0]:
            candidate=[marker[0]-ny*shift,marker[1]+nx*shift]
            if all(math.dist(candidate,other)>19 for other in band_markers) and c.annotation_layout.fits((candidate[0]-8,candidate[1]-8,candidate[0]+8,candidate[1]+8)):marker=candidate;break
        if not c.annotation_layout.fits((marker[0]-8,marker[1]-8,marker[0]+8,marker[1]+8)):
            for step in range(12,130,6):
                candidate=[xx+nx*step,yy+ny*step]
                if c.annotation_layout.fits((candidate[0]-8,candidate[1]-8,candidate[0]+8,candidate[1]+8)):marker=candidate;break
        if not c.annotation_layout.fits((marker[0]-8,marker[1]-8,marker[0]+8,marker[1]+8)):
            candidates=[]
            bounds=c.annotation_layout.bounds
            for yy2 in range(math.ceil(bounds[1]+9),math.floor(bounds[3]-9),16):
                for xx2 in range(math.ceil(bounds[0]+9),math.floor(bounds[2]-9),16):
                    if left-9<xx2<right+9 and bottom-9<yy2<top+9:continue
                    if c.annotation_layout.fits((xx2-8,yy2-8,xx2+8,yy2+8)):candidates.append([xx2,yy2])
            if not candidates:raise ValueError('Nu există spațiu pentru reperul de cant '+band['tag'])
            marker=min(candidates,key=lambda candidate:math.dist(candidate,[xx,yy]))
        c.annotation_layout.reserve((marker[0]-8,marker[1]-8,marker[0]+8,marker[1]+8))
        if cleanup_report is not None:
            c.annotation_layout.fixed_shapes.append(('marcaj cant',(marker[0]-8,marker[1]-8,marker[0]+8,marker[1]+8)))
        band_markers.append(marker)
        draw_band_marker(c,band['tag'],marker,[xx,yy])
        c.annotation_layout.add_stroke(c,marker,[xx,yy])
    for cut in cuts:
        if cut.get('bevel'):
            if cut['bevel']['face']==('Zmin' if back else 'Zmax') or single:
                draw_section_mark(c,cut,convert,project)
        elif cut.get('face')==('Zmin' if back else 'Zmax'):
            draw_section_mark(c,cut,convert,project,p,[loop for loop in loops if not loop.get('technological')])
    for start,end in round_mark_obstacles:c.annotation_layout.add_stroke(c,start,end)
    annotate_round_contours(c,contour,loops,native)
    if cleanup_report is not None:
        layout=c.annotation_layout
        for loop in loops:
            points=[native(q) for q in loop['points']]
            for a,b in zip(points,points[1:]):layout.add_stroke(c,a,b)
        if not loops:
            for a,b in edges:layout.add_stroke(c,native(a),native(b))
        for cut in cuts:
            if cut.get('no_effect') or cut.get('duplicate_bevel'):continue
            if cut.get('bevel'):
                for a,b,z in cut['bevel']['rails']:layout.add_stroke(c,native(a),native(b))
            elif cut.get('verified_rectangle'):
                points=[native(q) for q in cut['corners']]
                for a,b in zip(points,points[1:]+points[:1]):layout.add_stroke(c,a,b)
            else:
                for e in cut.get('trajectory',[]):
                    points=[native(q) for q in sampled(e)]
                    for a,b in zip(points,points[1:]):layout.add_stroke(c,a,b)
        item=layout.cleanup(c,output_scale)
        cleanup_report.append(dict(item,uid=p.get('uid'),code=p.get('designation'),plate=p['label'],
                                   view='Spate' if back else 'Față'))
    c.annotation_layout=None
    return visible,convert


def write_sheets(report,output,progress=None):
    from technological_openings import review_openings
    from bevel_sections import prepare_bevels
    register_body_font()
    panels=report.get('panels',[]);c=canvas.Canvas(str(output),pagesize=(PAGE_W,PAGE_H));c.setTitle('Export Cote')
    framed=bool(report.get('_titleblock'))
    total_holes=total_cuts=0
    headers=['Nr.','X','Y','Z local','Ø','Adâncime','Tip']
    for page,original in enumerate(panels,1):
        p=dict(original,label=original.get('label',page));lo,hi,contour,edges=geometry(p)
        holes=classified_holes(p,lo);cuts=milling_for(p,lo);loops=contour_data(p);bands=native_bands(p)
        total_holes+=len(holes);total_cuts+=len(cuts)
        for cut in cuts:
            cut['section_detail']=cross_section(p,cut,loops)
            if cut.get('no_effect'):
                status='no_effect'
                reason='Amprenta profilului este complet în afara conturului nativ al plăcii'
            elif cut.get('native_type')==2 and not cut['section_detail']:
                status='unresolved'
                reason='Geometria sau secțiunea frezării convenționale nu este confirmată complet'
            else:
                continue
            source=p['machining']['cuts'][cut['source_index']]
            finding=dict(uid=p.get('uid'),code=p.get('designation'),module=report.get('_cartus_corp'),
                         plate=p['label'],operation=source.get('index',cut['source_index']),
                         name=cut['name'],status=status,reason=reason)
            if cut.get('no_effect'):
                finding.update({key:cut[key] for key in ('nominal_face','nominal_length','nominal_width',
                                                        'nominal_depth','local_footprint')})
                finding['effective_length']=0
            if '_paic05_findings' in report:report['_paic05_findings'].append(finding)
            if progress:progress('PAIC-05 | UID '+str(p.get('uid'))+' | '+reason)
        if p.get('machining',{}).get('cuts'):
            try:
                added,findings=review_openings(p,loops)
            except (KeyError,TypeError,ValueError,ArithmeticError) as error:
                added=[];findings=[dict(uid=p.get('uid'),id=p['id'],code=p.get('designation'),
                                        status='unresolved',reason=str(error))]
            for item in findings:
                item.update(plate=p['label'],module=report.get('_cartus_corp'))
                if progress and item['status']=='unresolved':
                    progress('PAIC-03 | UID '+str(p.get('uid'))+' | '+str(item['reason']))
            if '_paic03_findings' in report:report['_paic03_findings'].extend(findings)
            loops=loops+added
        prepare_bevels(p,cuts,loops,report)
        details=[cut for cut in cuts if cut['section_detail']]
        conventional=[cut for cut in details if not cut.get('bevel')]
        for index,cut in enumerate(conventional):
            cut['section_label']=section_label(index)
        used={cut['section_label'] for cut in conventional}
        for cut in details:
            if not cut.get('bevel'):
                continue
            detail=cut['bevel']
            key=(cut['name'],*(round(detail[k],3) for k in ('thickness','width','depth')))
            matches=report.get('_paic04_labels',{}).get(key,[])
            label=matches[0] if len(matches)==1 and matches[0] not in used else None
            if label is None:
                label=next(section_label(i) for i in range(len(used)+1) if section_label(i) not in used)
            used.add(label)
            cut['section_label']=label
            cut['bevel_finding'].update(section_label=label,legend_labels=matches)
        faces=selected_faces(holes,cuts);single=len(faces)==1
        portrait=single and hi[1]-lo[1]>hi[0]-lo[0]
        page_width,page_height=(842,1191) if portrait else (PAGE_W,PAGE_H)
        unique_bands={band['tag']:band for band in bands}
        band_headers=['Reper','Nume căntuire','Denumire','Grosime']
        band_rows=[[b['tag'],b['name'],b['sign'],fmt(b['thickness'])] for b in unique_bands.values()]
        views=[]
        outer=[xy(e[key]) for loop in loops if not loop['interior'] for e in loop['elements'] for key in ['start','end'] if key in e]
        for back in faces:
            convert,_,_=view_transform(lo,hi,back,long_horizontal=not single)
            width,height=hi[0]-lo[0],hi[1]-lo[1]
            if not single and height>width:width,height=height,width
            visible=face_holes(holes,back)
            recesses=contour_recesses([loop['points'] for loop in loops if not loop['interior']],convert,width,height)
            side_entries=nearest_dimension_sides(visible,outer,convert,width,height,CONTOUR,recesses)
            visible_cuts=[cut for cut in cuts if cut.get('face')==('Zmin' if back else 'Zmax') or cut.get('face') not in ('Zmin','Zmax')]
            reference=nearest_dimension_sides(visible,outer,convert,width,height,CONTOUR) if recesses else None
            envelope=dimension_envelope(side_entries,visible_cuts,bands,reference)
            rows=[];colors=[]
            for hole in visible:
                q=convert(hole['position']);rows.append([hole['tag'],fmt(q[0]),fmt(q[1]),fmt(hole['z']),fmt(hole['diameter']),fmt(hole['depth']),'Străp.' if hole['through'] else 'Față' if hole['face'].startswith('Z') else 'Cant'])
                colors.append(hole['color'])
            views.append({'back':back,'width':width,'height':height,'sides':side_entries,'envelope':envelope,'recesses':recesses,'rows':rows,'colors':colors,
                          'title':'Găuri - '+('Spate' if back else 'Față')+' [mm]'})
        # Fit whole tables at their original font size; only the sheet/column flow can grow.
        for attempt in range(30):
            detail_positions=section_detail_positions(page_width,page_height,len(details))
            tables_top=min((top-DETAIL_HEIGHT-PADDING for _,top in detail_positions),default=page_height-PADDING)
            if tables_top<PADDING+180:page_height+=200;continue
            measure=lambda rows,title:max(sum(content_column_widths(headers,rows,6.5,1e9)),pdfmetrics.stringWidth(title,'Body',8))
            columns=flow_coordinate_tables([view for view in views if view['rows']],tables_top,PADDING,measure)
            coordinate_width=sum(column['width'] for column in columns)+PADDING*max(0,len(columns)-1)
            detail_width=min(2,len(details))*DETAIL_WIDTH+PADDING*max(0,min(2,len(details))-1)
            sidebar_width=max(coordinate_width,detail_width)
            sidebar_left=page_width-PADDING-sidebar_width
            drawing_right=sidebar_left-PADDING if sidebar_width else page_width-PADDING
            minimum_width=max(view['envelope']['margins']['left']+view['envelope']['margins']['right']+65 for view in views)
            if drawing_right-PADDING<minimum_width:page_width+=100;continue
            band_metrics=table_metrics(band_headers,band_rows,6,9,max(100,drawing_right-PADDING)) if band_rows else None
            band_top=PADDING+(sum(band_metrics[2]) if band_metrics else 0)
            drawing_bottom=band_top+20+PADDING if band_rows else PADDING
            drawing_top=page_height-PADDING if framed else page_height-PADDING-20-PADDING
            region=(PADDING,drawing_bottom,drawing_right,drawing_top)
            minimum_height=sum(view['envelope']['margins']['top']+view['envelope']['margins']['bottom']+60 for view in views)+PADDING*(len(views)-1)
            if region[3]-region[1]<minimum_height:page_height+=100;continue
            placements=fit_view_regions(region,views);break
        else:raise ValueError('Nu se poate așeza integral foaia de cote fără micșorarea textului')
        c.setPageSize((page_width,page_height));c.section_labels_on_page={cut['section_label'] for cut in details}
        if progress:progress('Desen: Cotare placa '+str(p['label']))
        if not framed:
            c.setFillColor(INK);c.setFont('Body',6);c.drawString(PADDING,page_height-PADDING-6,f"Placa {p['label']:02} | {p.get('designation') or p['id']} | {p.get('name','')}"[:120])
            c.setFont('Body',5);c.drawString(PADDING,page_height-PADDING-16,f"{board_fmt(hi[0]-lo[0])} × {board_fmt(hi[1]-lo[1])} × {fmt(p['thickness'])} mm | {p.get('material','')}"[:165])
        item=(p,lo,hi,contour,edges,holes,cuts,loops,bands)
        cleanup=report.get('_paic08_findings')
        output_scale=1
        if cleanup is not None and framed:
            from titleblock import bindings,content_transform,layout
            transform=content_transform(page_width,page_height,layout(report['_titleblock'],bindings(report,p))['bounds'])
            output_scale=math.hypot(*transform.ctm[:2])
        if cleanup is not None: start_cleanup=len(cleanup)
        for view,placement in zip(views,placements):
            draw_view(c,*item,view['back'],0,portrait,single,bool(details),placement,view['sides'],view['envelope'],view['recesses'],cleanup,output_scale)
        if cleanup is not None:
            for record in cleanup[start_cleanup:]: record['module']=report.get('_cartus_corp')
        right=page_width-PADDING
        x=right-coordinate_width
        for column in columns:
            column_right=x+column['width']
            for block in column['chunks']:
                grid_width=sum(content_column_widths(headers,block['rows'],6.5,1e9));grid_x=column_right-grid_width
                end=table(c,grid_x,block['top'],grid_width,headers,block['rows'],colors=block['colors'],title=block['title'])
                draw_axes(c,grid_x-2,end-2)
            x=column_right+PADDING
        for cut,(x,top) in zip(details,detail_positions):draw_detail(c,cut,x,top)
        if band_rows:
            table(c,PADDING,band_top+20,max(100,drawing_right-PADDING),band_headers,band_rows,font=6,row_height=9,title='Canturi')
        c.setFillColor(INK);c.setFont('Body',7);c.drawRightString(page_width-PADDING,14,f'{page} / {len(panels)}');c.showPage()
    c.save()
    return {'pages':len(panels),'holes':total_holes,'panels':len(panels),'cuts':total_cuts}
