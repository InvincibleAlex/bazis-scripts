"""Paginated, readable model specifications preceding the unchanged drawings."""
import json
import re
import tempfile
from collections import Counter
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Flowable
from reportlab.pdfbase.pdfmetrics import stringWidth

from assembly_fonts import register_body_font
from export_dimensions import fmt, geometry, xy
from hardware_labels import article_key


def natural(value):
    return [(1, int(s)) if s.isdigit() else (0, s.casefold()) for s in re.split(r'(\d+)', str(value))]


class SingleLine(Flowable):
    """Fit full text proportionally inside its cell, without wrapping or clipping."""
    def __init__(self, text, width, font_size=5.5):
        super().__init__()
        self.text=' '.join(str(text).split())
        self.width=width
        measured=stringWidth(self.text,'Body',font_size)
        self.font_size=font_size*min(1,width/measured) if measured else font_size
        self.height=max(6.5,font_size+1)

    def draw(self):
        self.canv.setFillColor(colors.black)
        self.canv.setFont('Body',self.font_size)
        self.canv.drawString(0,1,self.text)


def specification_rows(report):
    types = {}; boards = Counter()
    for panel in sorted(report['panels'], key=lambda p: natural(p.get('designation', ''))):
        sides = {s: set() for s in ('Sus', 'Jos', 'Stânga', 'Dreapta', 'Contur')}
        bands = (panel.get('module_comparison') or {}).get('bands')
        if bands is None: bands = (panel.get('duplicate_signature') or {}).get('bands', [])
        lo, hi, contour, _ = geometry(panel)
        elements = (contour or {}).get('elements', [])
        for band in bands:
            def get(upper, lower): return band.get(upper, band.get(lower))
            key = (str(get('Material', 'material') or '').split('\r')[0],
                   str(get('Sign', 'sign') or ''), get('Thickness', 'thickness'), get('Width', 'width'))
            if key not in types: types[key] = len(types) + 1
            index = get('ElemIndex', 'element'); side = 'Contur'
            if isinstance(index, int) and 0 <= index < len(elements):
                edge = elements[index]
                if edge.get('type') == 'line':
                    a, b = xy(edge['start']), xy(edge['end'])
                    for axis, value, name in ((1, hi[1], 'Sus'), (1, lo[1], 'Jos'), (0, lo[0], 'Stânga'), (0, hi[0], 'Dreapta')):
                        if abs(a[axis]-value) < .01 and abs(b[axis]-value) < .01:
                            side = name; break
            sides[side].add(types[key])
        abbreviations={'Sus':'S','Jos':'J','Stânga':'St','Dreapta':'Dr.','Contur':'Contur'}
        edging = ', '.join(abbreviations[side] for side, numbers in sides.items() if numbers)
        cuts = (panel.get('machining') or {}).get('cuts', [])
        machining = '; '.join(dict.fromkeys(str(c.get('name') or c.get('Name') or (c.get('properties') or {}).get('Name') or (c.get('params') or {}).get('Name') or 'Frezare') for c in cuts))
        rectangular = ''
        if elements:
            rectangular = 'Da' if len(elements) == 4 and all(e.get('type') == 'line' and
                (abs(xy(e['start'])[0]-xy(e['end'])[0]) < .01 or abs(xy(e['start'])[1]-xy(e['end'])[1]) < .01)
                for e in elements) else 'Nu'
        row = (str(panel.get('designation') or ''), str(panel.get('name') or '').split('\r')[0],
               fmt(hi[0]-lo[0]), fmt(hi[1]-lo[1]), fmt(panel.get('thickness')), edging,
               str(panel.get('material') or '').split('\r')[0], machining, rectangular)
        # Group only matching native manufacturing data, never code alone.
        signature = json.dumps({k: panel.get(k) for k in ('native_contour', 'machining', 'module_comparison', 'holes')}, sort_keys=True, ensure_ascii=False)
        boards[(row, signature)] += 1
    rows = [list(row[:2])+[str(count)]+list(row[2:]) for (row, _), count in boards.items()]
    edging = [[str(number), key[0], key[1], fmt(key[2]) if key[2] is not None else ''] for key, number in types.items()]
    hardware = Counter(article_key(h) for h in report.get('hardware', []) if not h.get('hidden'))
    fittings = [[str(i), str(article or ''), name, str(count)] for i, ((name, article), count) in enumerate(sorted(hardware.items(), key=lambda item: natural(item[0][0])), 1)]
    return rows, edging, fittings


def write_specification(report, output):
    register_body_font()
    size = A4; left = bottom = 10*mm; right = size[0]-10*mm; top = size[1]-10*mm
    if report.get('_titleblock'):
        from titleblock import layout, bindings
        model = layout(report['_titleblock'], bindings(report)); size = model['page_size']
        left, bottom, right, top = model['bounds']
        left += 3*mm; right -= 3*mm; bottom += 3*mm; top -= 3*mm
    width = right-left; story = []
    definitions = [
        ('Lista plăcilor', ['Cod', 'Nume', 'Buc.', 'Lungime', 'Lățime', 'Grosime', 'Canturi', 'Material', 'Prelucrări', 'Drept.'], [24, 22, 6, 10, 10, 10, 15, 60, 27, 9]),
        ('Canturi', ['Nr.', 'Nume', 'Desemnare', 'Grosime'], [10, 70, 65, 18]),
        ('Feronerie', ['Nr.', 'Articol', 'Nume', 'Bucăți'], [10, 30, 105, 18]),
    ]
    for (heading, headers, weights), rows in zip(definitions, specification_rows(report)):
        if not rows: continue
        widths=[width*w/sum(weights) for w in weights]
        data = [[SingleLine(cell,widths[i]-4) for i,cell in enumerate(row)] for row in [headers]+rows]
        data.insert(0,[SingleLine(heading,width-4,font_size=8)]+['']*(len(headers)-1))
        table = Table(data, colWidths=widths, repeatRows=2, hAlign='LEFT', splitInRow=0)
        table.setStyle(TableStyle([
            ('SPAN',(0,0),(-1,0)),
            ('GRID', (0, 0), (-1, -1), .3, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#eeeeee')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.extend([table, Spacer(1, 5*mm)])
    doc = SimpleDocTemplate(str(output), pagesize=size, leftMargin=left, rightMargin=size[0]-right,
                           bottomMargin=bottom, topMargin=size[1]-top, allowSplitting=1)
    doc.build(story)
    return len(PdfReader(output).pages)


def insert_specification(report, output, plan):
    with tempfile.TemporaryDirectory(prefix='cote-spec-', dir=output.parent) as folder:
        spec = Path(folder)/'spec.pdf'; count = write_specification(report, spec)
        original = PdfReader(output)
        writer = PdfWriter(); writer.add_page(original.pages[0]); writer.append(spec)
        for page in original.pages[1:]: writer.add_page(page)
        merged = Path(folder)/'merged.pdf'
        with merged.open('wb') as stream: writer.write(stream)
        merged.replace(output)
    contexts = {int(number)+(count if int(number)>1 else 0): value for number, value in plan.get('cartus_contexts', {}).items()}
    contexts.update({number: {'_specification': True} for number in range(2, count+2)})
    plan['cartus_contexts'] = contexts
    plan['module_page_ranges'] = {key: [start+(count if start>1 else 0), end+(count if end>1 else 0)] for key, (start, end) in plan.get('module_page_ranges', {}).items()}
    return count
