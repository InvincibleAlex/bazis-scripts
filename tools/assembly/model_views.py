"""Aligned first-angle orthographic projections of native model edges (X/Y/Z)."""
import tempfile
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black
from reportlab.lib.units import mm
from assembly_fonts import register_body_font
from export_dimensions import dimension, fmt


def view_layout(bounds, region,four=False):
    lo,hi=bounds
    width,height,depth=[hi[i]-lo[i] for i in range(3)]
    left,bottom,right,top=region
    gap=24*mm; padding=15*mm
    scale=min((right-left-2*padding-gap*(2 if four else 1))/max(width+depth*(2 if four else 1),.001),
              (top-bottom-2*padding-gap-15)/max(height+depth,.001))
    if scale<=0: raise ValueError('Spațiu insuficient pentru proiecțiile modelului.')
    x=left+(right-left-(width+depth*(2 if four else 1))*scale-gap*(2 if four else 1))/2
    y=bottom+(top-bottom-(height+depth)*scale-gap)/2
    # First angle: right view to the left of front; top view below front.
    views=[(2,1,x,y+depth*scale+gap,'Vedere din dreapta'),
                  (0,1,x+depth*scale+gap,y+depth*scale+gap,'Vedere din față'),
                  (0,2,x+depth*scale+gap,y,'Vedere de sus')]
    if four:views.append((2,1,x+(depth+width)*scale+2*gap,y+depth*scale+gap,'Vedere din stânga'))
    return scale,views


def opaque_faces(panel):
    """Use native extruded outlines, keeping internal contour openings transparent."""
    from visibility import board_faces
    if panel.get('faces'):
        return [(face,[]) for face in panel['faces']]
    if not panel.get('native_contour') or not panel.get('frame'):
        return [(face,[]) for face in board_faces(panel,[0,0,0])]
    from dimension_sheets import contour_data
    loops=contour_data(panel);frame=panel['frame'];origin=frame['origin'];axes=frame['axes']
    z=panel.get('z_limits') or {};low=z.get('LowZ',0);high=z.get('HighZ',low+panel['thickness'])
    def world(p,z):return [origin[j]+p[0]*axes[0][j]+p[1]*axes[1][j]+z*axes[2][j] for j in range(3)]
    faces=[];holes=[loop for loop in loops if loop['interior']]
    for loop in loops:
        points=loop['points']
        if not loop['interior']:
            for level in (low,high):faces.append(([world(p,level) for p in points],[[world(p,level) for p in h['points']] for h in holes]))
        for a,b in zip(points,points[1:]):faces.append(([world(a,low),world(b,low),world(b,high),world(a,high)],[]))
    return faces


def detail_coordinates(panels,axis,lo,hi):
    """Contour/component boundaries form a straight manufacturing chain, not origin stairs."""
    values=[lo,hi]
    for p in panels:
        # Broad faces carry the outline, not the drill-mouth tessellation.
        for face,_ in opaque_faces(p):
            for point in face:
                value=point[axis]
                if lo-.01<=value<=hi+.01:values.append(value)
    from export_dimensions import dimension_positions
    return dimension_positions(values)


def write_model_views(report, output,module_name=None):
    register_body_font()
    items=[p for p in report.get('panels',[])+report.get('hardware',[])
           if not p.get('hidden') and p.get('bounds',{}).get('min') and p.get('bounds',{}).get('max')]
    if not items: raise ValueError('Modelul nu conține geometrie pentru proiecții.')
    lo=[min(p['bounds']['min'][i] for p in items) for i in range(3)]
    hi=[max(p['bounds']['max'][i] for p in items) for i in range(3)]
    size=A4;region=(10*mm,10*mm,size[0]-10*mm,size[1]-10*mm)
    if report.get('_titleblock'):
        from titleblock import bindings,layout
        model=layout(report['_titleblock'],bindings(report));size=model['page_size'];region=model['bounds']
    left,bottom,right,top=region
    c=canvas.Canvas(str(output),pagesize=size)
    c.setFont('Body',11);c.drawString(left+4*mm,top-6*mm,('Vederi — '+module_name) if module_name else 'Secțiuni model')
    region=(left,bottom,right,top-12*mm)
    scale,views=view_layout((lo,hi),region,four=True)
    rw,rh=right-left,top-12*mm-bottom
    rotated_scale,rotated_views=view_layout((lo,hi),(0,0,rh,rw),four=True)
    if rotated_scale>scale:
        c.translate(right,bottom);c.rotate(90)
        region=(0,0,rh,rw);scale,views=rotated_scale,rotated_views
    edges=[edge for p in items for edge in p.get('edges',[])]
    if not edges: raise ValueError('Lipsesc muchiile native ale modelului pentru proiecții.')
    from visibility import DepthMask
    faces=[face for p in report.get('panels',[]) if not p.get('hidden') for face in opaque_faces(p)]
    dimensioned=set()
    for horizontal,vertical,x,y,title in views:
        w=(hi[horizontal]-lo[horizontal])*scale;h=(hi[vertical]-lo[vertical])*scale
        def point(p):
            u=p[horizontal]-lo[horizontal]
            v=p[vertical]-lo[vertical]
            # Looking from +X: positive Z goes to the left; looking down:
            # positive Z (front) goes towards the bottom of the top view.
            if horizontal==2 and title!='Vedere din stânga':u=hi[2]-p[2]
            if vertical==2:v=hi[2]-p[2]
            return x+u*scale,y+v*scale
        c.setStrokeColor(black);c.setLineWidth(.25)
        axis=({0,1,2}-{horizontal,vertical}).pop()
        sign=-1 if title=='Vedere din stânga' else 1
        mask=DepthMask((x-2,y-2,w+4,h+4),point,scale,depth_function=lambda p:p[axis]*sign)
        for vertices,holes in faces:mask.polygon(vertices,holes)
        seen=set()
        for a,b in edges:
            for aa,bb in mask.segments(a,b):
                aa,bb=point(aa),point(bb)
                key=tuple(sorted((tuple(round(v,3) for v in aa),tuple(round(v,3) for v in bb))))
                if key in seen or key[0]==key[1]:continue
                seen.add(key);c.line(*aa,*bb)
        c.setFillColor(black);c.setFont('Body',7)
        c.drawCentredString(x+w/2,y+h+9,title)
        for axis,is_vertical in ((horizontal,False),(vertical,True)):
            if module_name and axis in dimensioned:continue
            dimensioned.add(axis)
            points=detail_coordinates(report['panels'],axis,lo[axis],hi[axis]) if module_name else [lo[axis],hi[axis]]
            # Keep fine detail only when its number fits; full native board machining
            # remains on the individual plate sheets.
            chain=len(points)>2
            for a,b in zip(points,points[1:]) if chain else []:
                if (b-a)*scale<12:continue
                first=[lo[0],lo[1],lo[2]];second=list(first);first[axis]=a;second[axis]=b
                dimension(c,point(first),point(second),x-16 if is_vertical else y-16,fmt(b-a),vertical=is_vertical,color=black)
            dimension(c,[x,y],[x,y+h] if is_vertical else [x+w,y],x-(34 if chain else 16) if is_vertical else y-(34 if chain else 16),fmt(hi[axis]-lo[axis]),color=black,vertical=is_vertical,overall=True)
    c.showPage();c.save()


def insert_model_views(report,output,plan):
    with tempfile.TemporaryDirectory(prefix='model-views-',dir=output.parent) as folder:
        sheet=Path(folder)/'views.pdf';write_model_views(report,sheet)
        original=PdfReader(output);writer=PdfWriter();writer.add_page(original.pages[0]);writer.append(sheet)
        for page in original.pages[1:]:writer.add_page(page)
        merged=Path(folder)/'merged.pdf'
        with merged.open('wb') as stream:writer.write(stream)
        merged.replace(output)
    plan['cartus_contexts']={int(n)+(1 if int(n)>1 else 0):v for n,v in plan.get('cartus_contexts',{}).items()}
    plan['cartus_contexts'][2]={'_specification':True}
    plan['module_page_ranges']={k:[a+(a>1),b+(b>1)] for k,(a,b) in plan.get('module_page_ranges',{}).items()}
    return 1
