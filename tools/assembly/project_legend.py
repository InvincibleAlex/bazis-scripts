"""Project-wide colour key and unique native milling cross sections."""
import tempfile
from pathlib import Path
from pypdf import PdfReader,PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from assembly_fonts import register_body_font
from export_dimensions import flatten,geometry,milling_for,fmt
from dimension_sheets import FACE,THROUGH,EDGE,MILL,INK,contour_data,sampled
from dimension_sections import cross_section,draw_detail,section_label


def profile_geometry(profile,low,high,planar):
    lines=[sampled(e) for e in profile]
    lines=[line for line in lines if len(line)>1]
    if not lines:return [],(0,0),(),None
    points=[p for line in lines for p in line]
    x0=min(p[0] for p in points);x1=max(p[0] for p in points)
    y0=min(p[1] for p in points);y1=max(p[1] for p in points)
    # Sections of the same groove from opposite faces open upwards.
    at_bottom=abs(y0-low)<.001
    at_top=abs(y1-high)<.001
    bottom_only=not planar and at_bottom and not at_top
    sections=[[(x-x0,y1-y if bottom_only else y-y0) for x,y in line] for line in lines]
    def point_key(p):return tuple(round(v,3) for v in p)
    key=tuple(sorted({tuple(sorted((point_key(a),point_key(b))))
                      for line in sections for a,b in zip(line,line[1:])}))
    if planar:placement=None
    elif at_bottom and at_top:placement=('through',)
    elif at_bottom or at_top:placement=('surface',)
    else:placement=('internal',round(y0-low,3))
    return sections,(x1-x0,y1-y0),key,placement


def project_sections(report):
    result={}
    for panel in report.get('panels',[]):
        raw=panel.get('machining',{}).get('cuts',[])
        if not raw:continue
        lo,_,_,_=geometry(panel)
        loops=contour_data(panel)
        thickness=panel['thickness']
        limits=panel.get('z_limits') or {}
        low=limits.get('LowZ',0);high=limits.get('HighZ',low+thickness)
        for cut in milling_for(panel,lo):
            source=raw[cut['source_index']]
            profile=list(flatten(source.get('section')))
            trajectory=source.get('trajectory') or {}
            depth=(source.get('properties') or {}).get('Thickness')
            planar=bool(profile and trajectory.get('complete') and not trajectory.get('elements')
                        and isinstance(depth,(int,float)) and abs(depth)>0)
            lines,size,shape,placement=profile_geometry(profile,low,high,planar)
            key=(cut['name'],round(thickness,3),planar,shape,placement,abs(depth) if planar else None)
            detail=None if planar else cross_section(panel,cut,loops)
            if key in result and (result[key]['cut']['section_detail'] or not detail):continue
            result[key]={'name':cut['name'],'profile':profile,'lines':lines,'size':size,
                         'cut':dict(cut,section_detail=detail),'thickness':thickness,
                         'planar':planar,'through':planar and abs(depth)>=thickness-.01}
    return sorted(result.values(),key=lambda entry:entry['planar'])


def section_scale(entries,width):
    limits=[]
    for entry in entries:
        if entry['planar']:continue
        detail=entry['cut']['section_detail']
        if detail:limits.extend([118/(detail['right']-detail['left']),45/detail['thickness']])
        elif entry['lines']:
            w,h=entry['size']
            if w>0:limits.append((width-42)/w)
            if h>0:limits.append(55/h)
    return min(limits,default=1)


def draw_profile(c,entry,x,top,width,scale):
    cut=entry['cut']
    if cut['section_detail']:
        detail=cut['section_detail']
        draw_detail(c,cut,x+width/2-30-(detail['right']-detail['left'])*scale/2,top,scale=scale)
        return
    lines=entry['lines']
    w,h=entry['size']
    c.setFillColor(INK);c.setFont('Body',8)
    label=cut.get('section_label')
    c.drawCentredString(x+width/2,top,label+'–'+label if label else 'Vedere în plan (scară separată)')
    if not lines:
        c.setFont('Body',7);c.drawCentredString(x+width/2,top-42,'Profil nativ indisponibil')
        return
    if entry['planar']:
        scale=min((width-42)/max(w,.001),55/max(h,.001))
    ox=x+(width-w*scale)/2;oy=top-46-h*scale/2
    c.setStrokeColor(MILL);c.setLineWidth(.5)
    for line in lines:
        for a,b in zip(line,line[1:]):c.line(ox+a[0]*scale,oy+a[1]*scale,ox+b[0]*scale,oy+b[1]*scale)
    caption='Decupaj străpuns: ' if entry['through'] else 'Contur: ' if entry['planar'] else 'Profil: '
    c.setFont('Body',7);c.drawCentredString(x+width/2,top-90,caption+fmt(w)+' × '+fmt(h)+' mm')


def write_project_legend(report,output):
    register_body_font();size=A4;bounds=(10*mm,10*mm,size[0]-10*mm,size[1]-10*mm)
    if report.get('_titleblock'):
        from titleblock import layout,bindings
        model=layout(report['_titleblock'],bindings(report));size=model['page_size'];bounds=model['bounds']
    left,bottom,right,top=bounds;left+=5*mm;right-=5*mm;top-=7*mm;bottom+=5*mm
    c=canvas.Canvas(str(output),pagesize=size);pages=1
    def heading(continuation=False):
        c.setFillColor(INK);c.setFont('Body',11);c.drawString(left,top,'Legendă și secțiuni frezări'+(' — continuare' if continuation else ''))
    heading();y=top-28
    for color,text,kind in [(FACE,'Albastru — gaură pe fața plăcii, fără străpungere','hole'),
                            (THROUGH,'Roșu — gaură străpunsă','hole'),
                            (EDGE,'Fuchsia — gaură în cantul plăcii','hole'),
                            (MILL,'Maro — frezare','line')]:
        c.saveState();c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(.6)
        if kind=='hole':
            c.circle(left+9,y,3,stroke=1,fill=0);c.line(left+4,y,left+14,y);c.line(left+9,y-5,left+9,y+5)
        c.line(left+14,y,left+35,y);c.setFont('Body',8);c.drawString(left+43,y-3,text);c.restoreState();y-=23
    c.saveState();c.setStrokeColorRGB(.55,.55,.55);c.setLineWidth(.4)
    x=left+3;side=13;lower=y-side/2
    c.rect(x,lower,side,side,stroke=1,fill=0)
    for offset in range(-12,14,3):
        a=max(0,-offset);b=min(side,side-offset)
        c.line(x+a,lower+a+offset,x+b,lower+b+offset)
    c.setFillColor(INK);c.setFont('Body',8)
    text='Decupaj străpuns în placă — realizat prin modificarea conturului'
    lines=simpleSplit(text,'Body',8,right-left-43)
    for index,line in enumerate(lines):c.drawString(left+43,y-3-index*11,line)
    c.restoreState();y-=max(23,len(lines)*11+8)
    y-=17;c.setFont('Body',9);c.drawString(left,y,'Secțiunile frezărilor din proiect');y-=22
    entries=project_sections(report);column_width=(right-left-15)/2;row_height=145
    scale=section_scale(entries,column_width)
    if not entries:c.setFont('Body',8);c.drawString(left,y,'Proiectul nu conține frezări.')
    for index,entry in enumerate(entries):
        column=index%2
        if column==0:
            row_height=max([145]+[118+len(simpleSplit(e['name'],'Body',7,column_width-8))*9 for e in entries[index:index+2]])
        if column==0 and y-row_height<bottom:
            c.showPage();pages+=1;heading(True);y=top-30
        x=left+column*(column_width+15)
        if not entry['planar']:entry['cut']['section_label']=section_label(index)
        draw_profile(c,entry,x,y,column_width,scale)
        c.setFillColor(INK);c.setFont('Body',7)
        lines=simpleSplit(entry['name'],'Body',7,column_width-8)
        for j,line in enumerate(lines):c.drawCentredString(x+column_width/2,y-108-j*9,line)
        if column==1:y-=row_height
    c.showPage();c.save();return pages


def insert_project_legend(report,output,plan):
    with tempfile.TemporaryDirectory(prefix='project-legend-',dir=output.parent) as folder:
        sheet=Path(folder)/'legend.pdf';count=write_project_legend(report,sheet)
        reader=PdfReader(output);writer=PdfWriter()
        for page in reader.pages[:2]:writer.add_page(page)
        writer.append(sheet)
        for page in reader.pages[2:]:writer.add_page(page)
        merged=Path(folder)/'merged.pdf'
        with merged.open('wb') as stream:writer.write(stream)
        merged.replace(output)
    plan['cartus_contexts']={int(n)+(count if int(n)>2 else 0):v for n,v in plan.get('cartus_contexts',{}).items()}
    plan['cartus_contexts'].update({n:{'_specification':True} for n in range(3,3+count)})
    plan['module_page_ranges']={k:[a+(count if a>2 else 0),b+(count if b>2 else 0)] for k,(a,b) in plan.get('module_page_ranges',{}).items()}
    return count
