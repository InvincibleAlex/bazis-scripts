"""Paginated, readable model specifications preceding the unchanged drawings."""
from export_performance import measured
import json
import math
import re
import tempfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from io import BytesIO

from pypdf import PdfReader, PdfWriter, Transformation
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


def wrap_cell(text, width, measure):
    """Wrap at natural separators, with character breaks for oversized tokens."""
    text = ' '.join(str(text).split())
    if measure(text) <= width:
        return (text,)
    lines = []
    line = ''
    for token in re.findall(r'[^ /;|,–—-]+[/;|,–—-]?|.', text):
        if measure(line + token) <= width:
            line += token
            continue
        if line.strip():
            lines.append(line.rstrip())
        line = token.lstrip()
        while measure(line) > width:
            lo, hi = 0, len(line)
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if measure(line[:mid]) <= width:
                    lo = mid
                else:
                    hi = mid
            if not lo:
                raise ValueError('O celulă este prea îngustă pentru un caracter la fontul nominal.')
            lines.append(line[:lo])
            line = line[lo:]
    if line.strip():
        lines.append(line.rstrip())
    return tuple(lines)


class SpecificationCell(Flowable):
    def __init__(self, lines, width, font_size):
        super().__init__()
        self.lines = lines
        self.width = width
        self.font_size = font_size
        self.leading = max(6.5, font_size + 1)
        self.height = len(lines) * self.leading

    def draw(self):
        self.canv.setFillColor(colors.black)
        self.canv.setFont('Body', self.font_size)
        for index, line in enumerate(reversed(self.lines)):
            self.canv.drawString(0, 1 + index * self.leading, line)


def operation_name(cut):
    return str(cut.get('name') or cut.get('Name') or (cut.get('properties') or {}).get('Name')
               or (cut.get('params') or {}).get('Name') or 'Frezare')


def contour_description(loop):
    from technological_openings import exact_extrema
    elements = loop['elements']
    if len(elements)==1 and elements[0]['type']=='circle':
        return 'Decupaj circular Ø'+fmt(2*elements[0]['radius'])+' mm'
    if len(elements)==4 and all(e['type']=='line' for e in elements):
        vectors = [[b-a for a,b in zip(xy(e['start']),xy(e['end']))] for e in elements]
        lengths = [math.hypot(*v) for v in vectors]
        if min(lengths)>.001 and all(abs(sum(a*b for a,b in zip(v,w))) <= .001*min(l,k)
              for i,(v,l) in enumerate(zip(vectors,lengths)) for w,k in [(vectors[(i+1)%4],lengths[(i+1)%4])]):
            long,short=sorted(lengths[:2],reverse=True)
            shape='pătrat' if abs(long-short)<.001 else 'dreptunghiular'
            return 'Decupaj '+shape+' '+fmt(long)+' × '+fmt(short)+' mm'
    arcs=[e for e in elements if e['type']=='arc']
    lines=[e for e in elements if e['type']=='line']
    if len(arcs)==len(lines)==4 and all(elements[i]['type']!=elements[(i+1)%8]['type'] for i in range(8)):
        radii=[math.dist(xy(e['center']),xy(e['start'])) for e in arcs]
        if max(radii)-min(radii)<.001 and all(any(abs(a-b)<.001 for a,b in zip(xy(e['start']),xy(e['end']))) for e in lines):
            extrema=exact_extrema(elements)
            sides=sorted([max(p[i] for p in extrema)-min(p[i] for p in extrema) for i in range(2)],reverse=True)
            return 'Decupaj '+fmt(sides[0])+' × '+fmt(sides[1])+' mm, R'+fmt(radii[0])
    if len(arcs)==len(lines)==2:
        centers=[xy(e['center']) for e in arcs]
        radii=[math.dist(c,xy(e['start'])) for c,e in zip(centers,arcs)]
        if abs(radii[0]-radii[1])<.001 and all(
                math.dist([(a+b)/2 for a,b in zip(xy(e['start']),xy(e['end']))],c)<.001 for e,c in zip(arcs,centers)):
            return 'Decupaj oval '+fmt(math.dist(*centers)+2*radii[0])+' × '+fmt(2*radii[0])+' mm'
    return 'Decupaj poligonal' if len(lines)==len(elements) else 'Decupaj neregulat'


def exterior_descriptions(loops, lo, hi):
    from dimension_page_layout import contour_recesses
    from dimension_sheets import sampled
    def side(p):
        return {(i,edge) for i in range(2) for edge in (lo[i],hi[i]) if abs(p[i]-edge)<.01}

    for loop in (v for v in loops if not v['interior']):
        points=loop['points']
        recesses=contour_recesses([points],lambda q:[p-a for p,a in zip(q,lo)],hi[0]-lo[0],hi[1]-lo[1])
        covered=set()
        for r in recesses:
            inner=r['points'][1:-1]
            key={tuple(round(q[i]+lo[i],4) for i in range(2)) for q in inner}
            if covered.intersection(key):
                continue
            covered.update(key)
            width=r['end']-r['start']; depth=abs(r['deepest'][1-r['axis']]-r['edge'])
            axis_aligned=all(any(abs(a-b)<.001 for a,b in zip(p,q)) for p,q in zip(r['points'],r['points'][1:]))
            yield 'Crestătură '+fmt(width)+' × '+fmt(depth)+' mm' if axis_aligned else 'Decupaj deschis'
        irregular=False
        for e in loop['elements']:
            q=sampled(e)
            if not q or side(q[0]).intersection(side(q[-1])) and e['type']=='line':
                continue
            if any(tuple(round(v,4) for v in point) in covered for point in q):
                continue
            a,b=side(q[0]),side(q[-1])
            corner=len(a)==len(b)==1 and next(iter(a))[0]!=next(iter(b))[0]
            if corner and e['type']=='line':
                yield 'Colț retezat'
            elif corner and e['type']=='arc':
                radius=math.dist(xy(e['center']),q[0])
                yield 'Colț rotunjit R'+fmt(radius)
            else:
                irregular=True
        if irregular:
            yield 'Contur neregulat'


def processing_index(report):
    index={}
    for number in (3,4,5):
        for item in report.get(f'_paic0{number}_findings',[]):
            uid=item.get('uid')
            if uid is not None and 'operation' in item:
                index.setdefault(uid,{})[item['operation']]=(number,item)
    return index


def processing_for(panel, lo, hi, findings):
    from dimension_sheets import closed_loops, contour_data
    from export_dimensions import milling_for
    from technological_openings import same_opening
    entries=[]
    raw=(panel.get('machining') or {}).get('cuts',[])
    rows={}
    for row in milling_for(panel,lo) if raw else ():
        rows.setdefault(row['source_index'],[]).append(row)
    loops=contour_data(panel)
    covered=set()
    footprints=set()
    openings=[]
    for i,cut in enumerate(raw):
        name=operation_name(cut); operation=cut.get('index',i)
        previous, finding=findings.get(operation,(None,{}))
        status=finding.get('status')
        reason=finding.get('reason')
        verified=rows.get(i,[])
        if any(r.get('no_effect') for r in verified) or (previous==5 and status=='no_effect'):
            result='excluded'
            reason=reason or 'PAIC-05: amprenta este în afara materialului'
        elif previous==4 and status=='already_drawn':
            result='deduplicated'
            reason='PAIC-04: aceeași geometrie fizică a frezării'
        elif previous==3 and status in ('added','already_drawn'):
            result='kept'
            for candidate in closed_loops([cut.get('section')]):
                if any(same_opening(candidate,opening) for opening in openings):
                    result='deduplicated'
                    reason='PAIC-03: aceeași geometrie fizică a decupajului'
                    continue
                openings.append(candidate)
                for k,loop in enumerate(loops):
                    if loop['interior'] and same_opening(candidate,loop):
                        covered.add(k)
                        entries.append(dict(name=contour_description(loop),status='deduplicated',operation=operation,
                                            reason='Conturul interior coincide cu operațiunea PAIC-03',source='contur nativ'))
        elif previous==4 and status in ('added','partial'):
            result='kept'
        elif any(r.get('verified_rectangle') for r in verified):
            result='kept'
            keys={('groove',r['face'],round(r['profile_depth'],6),tuple(sorted(tuple(round(x,6) for x in p) for p in r['corners'])))
                  for r in verified if r.get('verified_rectangle')}
            if keys and keys<=footprints:
                result='deduplicated'
                reason='Aceeași amprentă, față și adâncime confirmate'
            footprints.update(keys)
        else:
            result='undetermined'
            reason=reason or 'Efect geometric neconfirmat de validările disponibile'
        entries.append(dict(name=name,status=result,operation=operation,reason=reason,source='BAZIS panel.Cuts'))
    entries.extend(dict(name=contour_description(loop),status='added',source='contur interior BAZIS')
                   for k,loop in enumerate(loops) if loop['interior'] and k not in covered)
    entries.extend(dict(name=name,status='added',source='contur exterior BAZIS')
                   for name in exterior_descriptions(loops,lo,hi))
    shown=Counter(e['name'] for e in entries if e['status'] in ('kept','added','undetermined'))
    text='; '.join(name if count==1 else f'{count} × {name}' for name,count in shown.items())
    return text, entries


def specification_rows(report):
    types = {}; boards = {}
    validation=processing_index(report)
    audit=report.get('_paic06_rows')
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
        machining = '; '.join(dict.fromkeys(operation_name(c) for c in cuts))
        current,operations=processing_for(panel,lo,hi,validation.get(panel.get('uid'),{}))
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
        item=dict(uid=panel.get('uid'),id=panel.get('id'),code=row[0],before=machining,after=current,operations=operations)
        boards.setdefault((row,signature),[]).append(item)
    rows=[]
    for (row,_),items in boards.items():
        descriptions={item['after'] for item in items}
        current=items[0]['after'] if len(descriptions)==1 else row[7]
        for item in items:
            if len(descriptions)>1:
                item.update(proposed=item['after'],after=current,group_conflict=True)
            item['row']=len(rows)+1
        if audit is not None:audit.extend(items)
        rows.append([*row[:2],str(len(items)),*row[2:7],current,row[8]])
    edging = [[str(number), key[0], key[1], fmt(key[2]) if key[2] is not None else ''] for key, number in types.items()]
    hardware = Counter() if '_native_xml' in report else Counter(
        article_key(h) for h in report.get('hardware', []) if not h.get('hidden'))
    fittings = [[str(i), str(article or ''), name, str(count)] for i, ((name, article), count) in enumerate(sorted(hardware.items(), key=lambda item: natural(item[0][0])), 1)]
    return rows, edging, fittings


@measured('tabele_generale')
def write_specification(report, output):
    register_body_font()
    size = A4; left = bottom = 10*mm; right = size[0]-10*mm; top = size[1]-10*mm
    framed=bool(report.get('_titleblock'))
    if framed:
        from titleblock import layout, bindings
        model = layout(report['_titleblock'], bindings(report)); size = model['page_size']
        left, bottom, right, top = model['bounds']
        left += 3*mm; right -= 3*mm; bottom += 3*mm; top -= 3*mm
    width = right-left; story = []
    page_extents = {}

    @lru_cache(maxsize=4096)
    def measure(text, size):
        return stringWidth(text, 'Body', size)

    @lru_cache(maxsize=2048)
    def cell_lines(text, width, size):
        return wrap_cell(text, width, lambda value: measure(value, size))

    def make_cell(value, width, size=5.5):
        return SpecificationCell(cell_lines(str(value), width, size), width, size)

    class CenteredTable(Table):
        def drawOn(self, canvas, x, y, _sW=0):
            page_extents.setdefault(canvas.getPageNumber(), []).append((y, y+self._height))
            super().drawOn(canvas, left+(width-self._width)/2, y)

    table_type = CenteredTable if framed else Table
    definitions = [
        ('Lista plăcilor', ['Cod', 'Nume', 'Buc.', 'Lungime', 'Lățime', 'Grosime', 'Canturi', 'Material', 'Prelucrări', 'Drept.'], [24, 22, 6, 10, 10, 10, 15, 60, 27, 9]),
        ('Canturi', ['Nr.', 'Nume', 'Desemnare', 'Grosime'], [10, 70, 65, 18]),
        ('Feronerie', ['Nr.', 'Articol', 'Nume', 'Bucăți'], [10, 30, 105, 18]),
    ]
    tables = specification_rows(report)
    if '_native_xml' in report:
        native = report['_native_xml']
        definitions[-1] = ('Feronerie', ['Nr.', 'Articol', 'Nume', 'Cantitate'], [10, 30, 105, 18])
        definitions.append(('Profile', ['Nr.', 'Articol', 'Nume', 'Lungime (mm)', 'Bucăți'], [10, 30, 79, 26, 18]))
        tables = (*tables[:2], native['hardware'], native['profiles'])
    for (heading, headers, weights), rows in zip(definitions, tables):
        if not rows: continue
        widths=[width*w/sum(weights) for w in weights]
        data = [[make_cell(cell, widths[i]-4) for i, cell in enumerate(row)]
                for row in [headers] + rows]
        if heading == 'Lista plăcilor':
            for item in report.get('_paic06_rows', ()):
                if len(data[item['row']][8].lines) > 1:
                    item['text_fit'] = 'Celula se distribuie pe mai multe linii la fontul nominal.'
        title = make_cell(heading, width-4, size=8)
        header_height = title.height + 4 + max(cell.height for cell in data[0]) + 4
        # The standard ReportLab frame reserves 6 pt at both vertical edges.
        max_row_height = top - bottom - 12 - header_height
        for number, row in enumerate(data[1:], 1):
            if max(cell.height for cell in row) + 4 > max_row_height + 1e-6:
                raise ValueError(f'{heading}, rândul {number}: textul depășește o pagină la fontul nominal.')
        data.insert(0, [title] + ['']*(len(headers)-1))
        table = table_type(data, colWidths=widths, repeatRows=2, hAlign='LEFT', splitInRow=0)
        table.setStyle(TableStyle([
            ('SPAN',(0,0),(-1,0)),
            ('GRID', (0, 0), (-1, -1), .3, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#eeeeee')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.extend([table, Spacer(1, 5*mm)])
    buffer = BytesIO() if framed else str(output)
    doc = SimpleDocTemplate(buffer, pagesize=size, leftMargin=left, rightMargin=size[0]-right,
                           bottomMargin=bottom, topMargin=size[1]-top, allowSplitting=1)
    doc.build(story)
    if not framed:
        return len(PdfReader(output).pages)

    writer = PdfWriter()
    for number, source_page in enumerate(PdfReader(buffer).pages, 1):
        page = writer.add_page(source_page)
        extents = page_extents.get(number)
        if extents:
            lower = min(y for y, _ in extents)
            upper = max(y for _, y in extents)
            page.add_transformation(Transformation().translate(ty=(bottom+top-lower-upper)/2))
    with Path(output).open('wb') as stream:
        writer.write(stream)
    return len(writer.pages)


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


def processing_report(report, plan):
    locations={}
    for i,context in plan.get('cartus_contexts',{}).items():
        if context.get('placa'):
            locations[str(context['placa'])]=(int(i),context.get('corp'))
    labels={p.get('uid'):p.get('label') for p in report['panels'] if p.get('uid') is not None}
    rows=report.get('_paic06_rows',[])
    for row in rows:
        label=labels.get(row['uid'])
        page,module=locations.get(str(label),(None,None))
        row.update(plate=label,page=page,module=module)
    return {'model':report.get('model'),'panels':len(report['panels']),'rows':rows,
            'changed_rows':len({r['row'] for r in rows if r['before']!=r['after']})}
