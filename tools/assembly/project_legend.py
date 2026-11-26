"""Project-wide colour key and unique native milling cross sections."""
import json
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


def project_sections(report):
    result=[];seen=set()
    for panel in report.get('panels',[]):
        lo,_,_,_=geometry(panel)
        raw=panel.get('machining',{}).get('cuts',[])
        for source,cut in zip(raw,milling_for(panel,lo)):
            profile=list(flatten(source.get('section')))
            key=json.dumps([cut['name'],panel['thickness'],profile],sort_keys=True,ensure_ascii=False)
            if key in seen:continue
            seen.add(key)
            detail=cross_section(panel,cut,contour_data(panel))
            result.append({'name':cut['name'],'profile':profile,'cut':dict(cut,section_detail=detail),
                           'thickness':panel['thickness']})
    return result


def draw_profile(c,entry,x,top,width):
    cut=entry['cut']
    if cut['section_detail']:
        draw_detail(c,cut,x+(width-174)/2,top)
        return
    segments=[sampled(e) for e in entry['profile']]
    points=[p for line in segments for p in line]
    c.setFillColor(INK);c.setFont('Body',8)
    c.drawCentredString(x+width/2,top,cut['section_label']+'–'+cut['section_label'])
    if not points:
        c.setFont('Body',7);c.drawCentredString(x+width/2,top-42,'Profil nativ indisponibil')
        return
    lo=[min(p[i] for p in points) for i in range(2)];hi=[max(p[i] for p in points) for i in range(2)]
    scale=min((width-42)/max(hi[0]-lo[0],.001),55/max(hi[1]-lo[1],.001))
    ox=x+(width-(hi[0]-lo[0])*scale)/2;oy=top-75
    c.setStrokeColor(MILL);c.setLineWidth(.5)
    for line in segments:
        for a,b in zip(line,line[1:]):c.line(ox+(a[0]-lo[0])*scale,oy+(a[1]-lo[1])*scale,ox+(b[0]-lo[0])*scale,oy+(b[1]-lo[1])*scale)
    c.setFont('Body',7);c.drawCentredString(x+width/2,top-90,'Profil: '+fmt(hi[0]-lo[0])+' × '+fmt(hi[1]-lo[1])+' mm')


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
                            (MILL,'Maro — frezare','line'),
                            (INK,'Gri punctat — prelucrare pe fața opusă','hidden')]:
        c.saveState();c.setStrokeColor(color);c.setFillColor(INK);c.setLineWidth(.6)
        if kind=='hole':
            c.circle(left+9,y,3,stroke=1,fill=0);c.line(left+4,y,left+14,y);c.line(left+9,y-5,left+9,y+5)
        if kind=='hidden':c.setStrokeColorRGB(.6,.6,.6);c.setDash(2,2)
        c.line(left+14,y,left+35,y);c.setFont('Body',8);c.drawString(left+43,y-3,text);c.restoreState();y-=23
    y-=17;c.setFont('Body',9);c.drawString(left,y,'Secțiunile frezărilor din proiect');y-=22
    entries=project_sections(report);column_width=(right-left-15)/2;row_height=145
    if not entries:c.setFont('Body',8);c.drawString(left,y,'Proiectul nu conține frezări.')
    for index,entry in enumerate(entries):
        column=index%2
        if column==0:
            row_height=max([145]+[118+len(simpleSplit(e['name'],'Body',7,column_width-8))*9 for e in entries[index:index+2]])
        if column==0 and y-row_height<bottom:
            c.showPage();pages+=1;heading(True);y=top-30
        x=left+column*(column_width+15)
        entry['cut']['section_label']=section_label(index)
        draw_profile(c,entry,x,y,column_width)
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
