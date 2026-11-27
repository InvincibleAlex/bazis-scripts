"""Render the editor's version-2 grid in physical mm, with native BAZIS bindings."""
from export_performance import measured, stage
import base64
from collections import Counter
from datetime import datetime
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import unicodedata
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth,registerFont,getRegisteredFontNames
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from pypdf import PdfReader,PdfWriter,Transformation
from assembly_fonts import register_body_font


def load_template(explicit=None):
    choices=[Path(explicit)] if explicit else [Path(os.environ.get('BAZIS_COTE_TEMPLATE',r'\\RG\Bazis\Scripts\Editor Cartus\Cartus_A4_Portret_cote.json')),
        Path(__file__).with_name('cartus_cote.json')]
    for path in choices:
        if path.is_file():
            template=json.loads(path.read_text(encoding='utf-8-sig'))
            if template.get('schema')!=2:raise ValueError('Cartușul trebuie salvat din editorul cu celule unite.')
            for row in template['rows']:
                for cell in row['cells']:
                    if '{nume}' in cell['text']:
                        field='proiectant' if cell['text'].strip().lower().startswith('proiectant') else 'verificator' if cell['text'].strip().lower().startswith('verificator') else 'nume'
                        cell['text']=cell['text'].replace('{nume}','{'+field+'}')
            reference=template.get('logo_file') or load_manual_settings(path).get('logo_file')
            if reference:
                logo=Path(reference)
                if not logo.is_absolute():logo=path.parent/logo
                if logo.suffix.lower() not in ('.png','.jpg','.jpeg'):raise ValueError('Logo-ul extern trebuie să fie PNG sau JPG.')
                if not logo.is_file():raise FileNotFoundError('Logo-ul cartușului nu există: '+str(logo))
                mime='png' if logo.suffix.lower()=='.png' else 'jpeg'
                template['logo']='data:image/'+mime+';base64,'+base64.b64encode(logo.read_bytes()).decode('ascii')
            return template
    if explicit:raise FileNotFoundError('Șablonul cartușului nu există: '+str(explicit))
    return None


def bindings(report,panel=None,*,represented_panels=None):
    manual=report.get('_cartus_manual',{})
    values={str(k):str(v or '') for k,v in manual.items()}
    # Older saved reports can retain an explicitly supplied client. New exports
    # always carry the native order field, including an intentionally empty one.
    client=str((report.get('order') or {}).get('name') or '').strip() if 'order' in report else values.get('client','')
    values.update(proiect=values.get('proiect') or Path(str(report.get('model','')).replace('\\','/')).stem,
        client=client,proiectant=values.get('proiectant',''),verificator=values.get('verificator',''),
        data=datetime.now().strftime('%d.%m.%Y'),pagina='',placa='',nume_placa='',cod='',material='',dimensiuni='',corp=report.get('_cartus_corp',''),bucati='')
    if panel:
        from export_dimensions import geometry,fmt
        lo,hi,_,_=geometry(panel)
        code=panel.get('designation') or ''
        # Count physical model records assigned to this sheet, independently of designation.
        instances=(panel,) if represented_panels is None else represented_panels
        quantity=len({instance['id'] for instance in instances})
        values.update(placa=str(panel.get('label','')),nume_placa=str(panel.get('name') or ''),cod=str(code),material=str(panel.get('material','')).split('\r')[0],
            dimensiuni=' × '.join(fmt(x) for x in [hi[0]-lo[0],hi[1]-lo[1],panel['thickness']])+' mm',
            bucati=str(quantity))
    return values


def load_manual_settings(template_path=None):
    template=Path(template_path) if template_path else Path(os.environ.get('BAZIS_COTE_TEMPLATE',r'\\RG\Bazis\Scripts\Editor Cartus\Cartus_A4_Portret_cote.json'))
    settings=Path(os.environ.get('BAZIS_COTE_PARAMETERS',str(template.with_name('Parametri_cote.json'))))
    if not settings.is_file():settings=Path(__file__).with_name('cartus_parametri.json')
    if not settings.is_file():return {}
    result=json.loads(settings.read_text(encoding='utf-8-sig'))
    if not isinstance(result,dict):raise ValueError('Parametri_cote.json trebuie să conțină un obiect cu nume și valori.')
    return result


def wrap(text,width,font,size):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if stringWidth(candidate,font,size)<=width:line=candidate;continue
            if line:lines.append(line);line=''
            for char in word:
                if line and stringWidth(line+char,font,size)>width:lines.append(line);line=''
                line+=char
        lines.append(line)
    return lines


def substitute_parameters(text,values):
    """Accept Romanian diacritics while preserving exact custom parameter keys."""
    def replace(match):
        key=match[1]
        canonical=''.join(c for c in unicodedata.normalize('NFD',key) if not unicodedata.combining(c))
        return str(values.get(key,values.get(canonical,'')))
    return re.sub(r'\{\s*([^\W\d]\w*)\s*:?\s*\}',replace,text)


@measured('layout_cartus')
def layout(template,values):
    register_body_font()
    if 'BodyBold' not in getRegisteredFontNames():
        import reportlab
        bold=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts/arialbd.ttf'
        if not bold.is_file():bold=Path(reportlab.__file__).parent/'fonts/VeraBd.ttf'
        registerFont(TTFont('BodyBold',str(bold)))
    p=template['page'];b=template['block'];m=p['margins'];columns=template['columns'];total=sum(columns)
    if not columns or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in columns) or not template['rows']:raise ValueError('Grilă de cartuș invalidă.')
    if p['width']<=m['left']+m['right'] or p['height']<=m['top']+m['bottom']:raise ValueError('Marginile cartușului depășesc foaia.')
    occupied=set()
    def fraction(cell):return sum(columns[cell['col']:cell['col']+cell['colSpan']])/total
    prepared=[];desired=b['width']
    for r,row in enumerate(template['rows']):
        cells=[]
        for original in row['cells']:
            cell=dict(original);cell['text']=substitute_parameters(cell['text'],values)
            if cell['col']<0 or cell['colSpan']<1 or cell['rowSpan']<1 or cell['col']+cell['colSpan']>len(columns) or r+cell['rowSpan']>len(template['rows']):raise ValueError('Celulă în afara grilei cartușului.')
            for y in range(r,r+cell['rowSpan']):
                for x in range(cell['col'],cell['col']+cell['colSpan']):
                    if (x,y) in occupied:raise ValueError('Celule suprapuse în cartuș.')
                    occupied.add((x,y))
            cell['font_name']='BodyBold' if cell.get('bold') else 'Body'
            if b['dynamic'] and not cell.get('logo'):
                desired=max(desired,(max(stringWidth(line,cell['font_name'],cell['font']*mm)/mm for line in cell['text'].split('\n'))+2*b['padding'])/fraction(cell))
            cells.append(cell)
        prepared.append(cells)
    width=min(p['width']-m['left']-m['right'],b['maxWidth'] if b['dynamic'] else b['width'],desired)
    left=p['width']-m['right']-width;xs=[left]
    for col in columns:xs.append(xs[-1]+width*col/total)
    heights=[row['height'] for row in template['rows']]
    for r,cells in enumerate(prepared):
        for cell in cells:
            cell['x']=xs[cell['col']];cell['width']=xs[cell['col']+cell['colSpan']]-cell['x'];inner=(cell['width']-2*b['padding'])*mm
            if inner<=0:raise ValueError('Celulă prea îngustă în cartuș.')
            cell['lines']=wrap(cell['text'],inner,cell['font_name'],cell['font']*mm) if cell['text'].strip() else []
            caption=len(cell['lines'])*cell['font']*1.25+2*b['padding']
            cell['needed']=(caption+cell['font']*2 if cell['lines'] else 0) if cell.get('logo') else caption
            if cell['rowSpan']==1:heights[r]=max(heights[r],cell['needed'])
    for r,cells in enumerate(prepared):
        for cell in cells:
            end=r+cell['rowSpan'];missing=cell['needed']-sum(heights[r:end])
            if missing>0:heights[end-1]+=missing
    height=sum(heights);top=p['height']-m['bottom']-height;y=top
    for r,cells in enumerate(prepared):
        for cell in cells:cell.update(y=y,height=sum(heights[r:r+cell['rowSpan']]))
        y+=heights[r]
    bottom=(m['bottom']+height+b['gap'])*mm
    bounds=(m['left']*mm,bottom,(p['width']-m['right'])*mm,(p['height']-m['top'])*mm)
    if bounds[3]<=bottom:raise ValueError('Cartușul ocupă întreaga foaie.')
    return {'rows':prepared,'bounds':bounds,'page_size':(p['width']*mm,p['height']*mm),'height':height}


@measured('desenare_cartus')
def draw(c,template,model):
    p=template['page'];b=template['block'];m=p['margins'];ph=p['height']*mm
    c.saveState();c.setStrokeColorRGB(0,0,0);c.setFillColorRGB(0,0,0);c.setLineWidth(b['stroke']*mm)
    c.rect(m['left']*mm,m['bottom']*mm,(p['width']-m['left']-m['right'])*mm,(p['height']-m['top']-m['bottom'])*mm,stroke=1,fill=0)
    for row in model['rows']:
        for cell in row:
            x=cell['x']*mm;y=ph-(cell['y']+cell['height'])*mm;w=cell['width']*mm;h=cell['height']*mm
            c.rect(x,y,w,h,stroke=1,fill=0);size=cell['font']*mm;line_height=size*1.25;lines=cell['lines'];caption=(len(lines)*line_height+2*b['padding']*mm) if lines else 0
            if cell.get('logo') and template.get('logo'):
                with stage('logo_cartus_decodare_si_desenare'):
                    raw=base64.b64decode(template['logo'].split(',',1)[1]);c.drawImage(ImageReader(BytesIO(raw)),x,y+caption,width=w,height=h-caption,preserveAspectRatio=True,anchor='c',mask='auto')
            c.setFont(cell['font_name'],size)
            first=y+b['padding']*mm+len(lines)*line_height-size if cell.get('logo') else y+(h+len(lines)*line_height)/2-size
            for index,line in enumerate(lines):
                yy=first-index*line_height
                if cell['align']=='center':c.drawCentredString(x+w/2,yy,line)
                elif cell['align']=='right':c.drawRightString(x+w-b['padding']*mm,yy,line)
                else:c.drawString(x+b['padding']*mm,yy,line)
    c.restoreState()


def content_transform(width,height,bounds):
    """Fit the unchanged composition; landscape content turns 90° CCW."""
    left,bottom,right,top=bounds
    rotated=width>height
    placed_width,placed_height=(height,width) if rotated else (width,height)
    scale=min((right-left)/placed_width,(top-bottom)/placed_height)
    x=left+(right-left-placed_width*scale)/2
    y=bottom+(top-bottom-placed_height*scale)/2
    if rotated:return Transformation().rotate(90).scale(scale).translate(x+height*scale,y)
    return Transformation().scale(scale).translate(x,y)


@measured('aplicare_cartuse')
def frame_pdf(path,template,report,contexts,*,cover_without_titleblock=False):
    reader=PdfReader(path);writer=PdfWriter();count=len(reader.pages)
    for number,page in enumerate(reader.pages,1):
        values=bindings(report);values.update(contexts.get(number,{}));values['pagina']=f'{number} / {count}'
        model=layout(template,values)
        if number==1 and cover_without_titleblock:
            result=writer.add_blank_page(*model['page_size'])
        else:
            buf=BytesIO();c=canvas.Canvas(buf,pagesize=model['page_size']);draw(c,template,model);c.save();buf.seek(0)
            result=writer.add_page(PdfReader(buf).pages[0])
        # Treat the existing sheet as one immutable composition. Only the
        # whole landscape sheet turns; the portrait cartouche stays upright.
        width,height=float(page.mediabox.width),float(page.mediabox.height)
        footer=BytesIO();mask=canvas.Canvas(footer,pagesize=(width,height))
        mask.setFillColorRGB(1,1,1);mask.rect(width-90,14,75,25,stroke=0,fill=1);mask.save();footer.seek(0)
        page.merge_page(PdfReader(footer).pages[0])
        transform=Transformation() if contexts.get(number,{}).get('_specification') else content_transform(width,height,model['bounds'])
        result.merge_transformed_page(page,transform,over=False)
    temporary=path.with_suffix('.cartus.tmp.pdf')
    with temporary.open('wb') as stream:writer.write(stream)
    temporary.replace(path)
