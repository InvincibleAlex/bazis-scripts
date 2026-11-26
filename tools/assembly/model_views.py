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


def view_layout(bounds, region):
    lo,hi=bounds
    width,height,depth=[hi[i]-lo[i] for i in range(3)]
    left,bottom,right,top=region
    gap=24*mm; padding=15*mm
    scale=min((right-left-2*padding-gap)/max(width+depth,.001),
              (top-bottom-2*padding-gap-15)/max(height+depth,.001))
    if scale<=0: raise ValueError('Spațiu insuficient pentru proiecțiile modelului.')
    x=left+(right-left-(width+depth)*scale-gap)/2
    y=bottom+(top-bottom-(height+depth)*scale-gap)/2
    # First angle: right view to the left of front; top view below front.
    return scale,[(2,1,x,y+depth*scale+gap,'Vedere din dreapta'),
                  (0,1,x+depth*scale+gap,y+depth*scale+gap,'Vedere din față'),
                  (0,2,x+depth*scale+gap,y,'Vedere de sus')]


def write_model_views(report, output):
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
    c.setFont('Body',11);c.drawString(left+4*mm,top-6*mm,'Secțiuni model')
    scale,views=view_layout((lo,hi),(left,bottom,right,top-12*mm))
    edges=[edge for p in items for edge in p.get('edges',[])]
    if not edges: raise ValueError('Lipsesc muchiile native ale modelului pentru proiecții.')
    for horizontal,vertical,x,y,title in views:
        w=(hi[horizontal]-lo[horizontal])*scale;h=(hi[vertical]-lo[vertical])*scale
        def point(p):
            u=p[horizontal]-lo[horizontal]
            v=p[vertical]-lo[vertical]
            # Looking from +X: positive Z goes to the left; looking down:
            # positive Z (front) goes towards the bottom of the top view.
            if horizontal==2:u=hi[2]-p[2]
            if vertical==2:v=hi[2]-p[2]
            return x+u*scale,y+v*scale
        c.setStrokeColor(black);c.setLineWidth(.25)
        seen=set()
        for a,b in edges:
            a,b=point(a),point(b)
            key=tuple(sorted((tuple(round(v,3) for v in a),tuple(round(v,3) for v in b))))
            if key in seen or key[0]==key[1]:continue
            seen.add(key);c.line(*a,*b)
        c.setFillColor(black);c.setFont('Body',7)
        c.drawCentredString(x+w/2,y+h+9,title)
        dimension(c,[x,y],[x+w,y],y-13,fmt(hi[horizontal]-lo[horizontal]),color=black,overall=True)
        dimension(c,[x,y],[x,y+h],x-13,fmt(hi[vertical]-lo[vertical]),color=black,vertical=True,overall=True)
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
