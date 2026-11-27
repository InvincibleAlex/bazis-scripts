"""Experimental native board dimension sheets. No hardware drawing or model edits."""
import sys
from time import perf_counter

_PROCESS_START = perf_counter()
from pathlib import Path

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import argparse
import json
import math
import tempfile
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor,Color
from reportlab.pdfbase.pdfmetrics import stringWidth

W,H=842,595
ORANGE=HexColor('#b15d12')
BLUE=HexColor('#1668b2')

def fmt(value):
    if value is None:return '?'
    rounded=Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    if rounded==0:return '0'
    return format(rounded,'f').rstrip('0').rstrip('.')


def xy(p):return [p['x'],p['y']] if isinstance(p,dict) else list(p[:2])

def to_local(panel,point,direction=False):
    f=panel.get('frame')
    if not f:raise ValueError('Lipsește sistemul local nativ al plăcii '+panel['id'])
    return [sum((point[j]-(0 if direction else f['origin'][j]))*axis[j] for j in range(3)) for axis in f['axes']]

def geometry(panel):
    if panel.get('dimension_properties',{}).get('Bent'):raise ValueError('Cotarea plăcilor curbate necesită desfășurata nativă: '+panel['id'])
    bounds=panel.get('local_bounds')
    contour=panel.get('native_contour')
    edges=[]
    if not bounds or not bounds.get('min') or not bounds.get('max') or not contour:
        # Compatibility for existing test reports: project actual native edges,
        # never replace a shaped contour with a fabricated rectangle.
        if panel.get('geometry_source')!='BAZIS Edges.GVertices':raise ValueError('Contur nativ indisponibil: '+panel['id'])
        edges=[[to_local(panel,a),to_local(panel,b)] for a,b in panel.get('edges',[])]
        points=[p for edge in edges for p in edge]
        bounds={'min':[min(p[i] for p in points) for i in range(2)],'max':[max(p[i] for p in points) for i in range(2)]}
    lo,hi=xy(bounds['min']),xy(bounds['max'])
    return lo,hi,contour,edges

def holes_for(panel,lo):
    rows=[]
    for hole in panel.get('holes',[]):
        if not hole.get('coordinate_space_verified') or hole.get('panel_uid')!=panel.get('uid'):raise ValueError('Gaură fără asociere/coordonate confirmate: '+panel['id'])
        p=hole.get('position_panel_local_mm') or to_local(panel,hole['position_global_mm'])
        d=hole.get('direction_panel_local') or to_local(panel,hole['direction_global'],True)
        if abs(d[2])>.999:face='Zmin' if d[2]>0 else 'Zmax'
        elif abs(d[0])>.999:face='Xmin' if d[0]>0 else 'Xmax'
        elif abs(d[1])>.999:face='Ymin' if d[1]>0 else 'Ymax'
        else:face='oblică'
        rows.append(dict(tag=f'G{len(rows)+1:02}',x=p[0]-lo[0],y=p[1]-lo[1],z=p[2],position=p,direction=d,
            diameter=hole.get('diameter_mm'),depth=hole.get('depth_mm'),face=face))
    return rows

def flatten(contour):
    for e in (contour or {}).get('elements',[]):
        if e.get('type')=='list':yield from flatten(e.get('contour'))
        else:yield e

def clipped_groove_spans(edges,a,direction,normal,offsets,floor,length):
    # Matching parallel edges on the floor confirm the actual material span.
    tolerance=.001
    rails=[]
    for offset in offsets:
        intervals=[]
        for edge in edges:
            positions=[]
            for x,y,z in edge:
                dx,dy=x-a[0],y-a[1]
                if abs(z-floor)>tolerance or abs(dx*normal[0]+dy*normal[1]-offset)>tolerance:
                    break
                positions.append(dx*direction[0]+dy*direction[1])
            if len(positions)!=2:continue
            start,end=sorted(positions)
            if start>=-tolerance and end<=length+tolerance and end-start>tolerance:
                intervals.append((max(0,start),min(length,end)))
        merged=[]
        for start,end in sorted(intervals):
            if merged and start<=merged[-1][1]+tolerance:
                merged[-1]=(merged[-1][0],max(merged[-1][1],end))
            else:
                merged.append((start,end))
        rails.append(merged)
    if len(rails[0])!=len(rails[1]):return []
    spans=[]
    for left,right in zip(*rails):
        if any(abs(x-y)>tolerance for x,y in zip(left,right)):return []
        start,end=max(left[0],right[0]),min(left[1],right[1])
        if end-start<=tolerance:return []
        spans.append((start,end))
    return spans


def milling_for(panel,lo):
    rows=[]
    for source_index,cut in enumerate(panel.get('machining',{}).get('cuts',[])):
        params=cut.get('params') or {};trajectory=list(flatten(cut.get('trajectory')));section=list(flatten(cut.get('section')))
        row={'tag':f'F{len(rows)+1:02}','name':cut.get('properties',{}).get('Name') or params.get('Name') or 'Frezare',
            'native_type':params.get('CutType'),'depth':params.get('Depth'),'width':params.get('Width'),'offset':params.get('Offset'),
            'trajectory':trajectory,'source_index':source_index,'verified_rectangle':False}
        # The section coordinates describe transverse offset and panel-local Z.
        # Restrict footprint dimensions to a straight path + rectangular profile.
        if len(trajectory)==1 and trajectory[0].get('type')=='line' and len(section)==4 and all(e.get('type')=='line' for e in section):
            a=xy(trajectory[0]['start']);b=xy(trajectory[0]['end']);dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy)
            pts=[xy(e[k]) for e in section for k in ['start','end']]
            sx=sorted(set(round(p[0],6) for p in pts));sz=sorted(set(round(p[1],6) for p in pts))
            axis_aligned=all(abs(xy(e['start'])[0]-xy(e['end'])[0])<1e-6 or abs(xy(e['start'])[1]-xy(e['end'])[1])<1e-6 for e in section)
            if length>0 and len(sx)==2 and len(sz)==2 and axis_aligned:
                direction=[dx/length,dy/length];normal=[-direction[1],direction[0]]
                low=(panel.get('z_limits') or {}).get('LowZ',0);high=(panel.get('z_limits') or {}).get('HighZ',panel['thickness'])
                face='Zmin' if abs(sz[0]-low)<1e-5 else 'Zmax' if abs(sz[1]-high)<1e-5 else 'profil interior'
                # A complete native profile swept wholly outside the contour
                # envelope cannot remove material, regardless of floor-edge evidence.
                bounds=panel.get('local_bounds') or {}
                if (cut['trajectory'].get('complete') and cut['section'].get('complete')
                        and (panel.get('native_contour') or {}).get('complete')
                        and bounds.get('min') and bounds.get('max')):
                    profile_xy=[[p[i]+normal[i]*offset for i in range(2)] for p in (a,b) for offset in sx]
                    lower=[min(p[i] for p in profile_xy) for i in range(2)]
                    upper=[max(p[i] for p in profile_xy) for i in range(2)]
                    board_min,board_max=xy(bounds['min']),xy(bounds['max'])
                    if any(upper[i]<board_min[i]-.001 or lower[i]>board_max[i]+.001 for i in range(2)):
                        row.update(no_effect=True,nominal_face=face,nominal_length=length,
                                   nominal_width=sx[1]-sx[0],nominal_depth=sz[1]-sz[0],
                                   local_footprint=dict(min=lower,max=upper))
                        rows.append(row)
                        continue
                native_edges=[[to_local(panel,v) for v in edge] for edge in panel.get('edges',[]) if len(edge)==2] if panel.get('geometry_source')=='BAZIS Edges.GVertices' else []
                def footprint(start,end):
                    return [[p[0]+normal[0]*offset,p[1]+normal[1]*offset] for p,offset in [(start,sx[0]),(end,sx[0]),(end,sx[1]),(start,sx[1])]]
                through=sz[0]<=low+.01 and sz[1]>=high-.01
                floor=sz[1] if face=='Zmin' else sz[0] if face=='Zmax' else None
                spans=clipped_groove_spans(native_edges,a,direction,normal,sx,floor,length) if floor is not None and not through else []
                if not spans:
                    full=footprint(a,b)
                    if all(any(math.dist(q,v[:2])<.001 for edge in native_edges for v in edge) for q in full):
                        spans=[(0,length)]
                if spans:
                    for start,end in spans:
                        first,last=([a[i]+direction[i]*d for i in range(2)] for d in (start,end))
                        corners=footprint(first,last)
                        rows.append(dict(row,tag=f'F{len(rows)+1:02}',verified_rectangle=True,through=through,
                            split=len(spans)>1,corners=corners,x=min(q[0] for q in corners)-lo[0],y=min(q[1] for q in corners)-lo[1],
                            start=[corners[0][i]-lo[i] for i in range(2)],end=[corners[1][i]-lo[i] for i in range(2)],
                            length=end-start,width=sx[1]-sx[0],profile_depth=sz[1]-sz[0],face=face))
                    continue
                row['verification_note']='Amprenta frezarii nu este confirmata de geometria nativa'
        rows.append(row)
    return rows

def dimension_label(c,x,y,label,secondary_colors,rail=None):
    layout=getattr(c,'annotation_layout',None)
    if layout:
        layout.draw(c,x,y,label,centered=True,secondary_colors=secondary_colors,leader=False,secondary_rail=rail)
    else:
        c.drawCentredString(x,y,label)
        half=min(3,stringWidth(label,'Body',7)*.375)
        for index,color in enumerate(secondary_colors):
            c.setStrokeColor(color);c.line(x-half,(y if rail is None else rail)-3.5-index*2.2,x+half,(y if rail is None else rail)-3.5-index*2.2)


def dimension(c,a,b,offset,label,vertical=False,color=None,secondary_colors=(),overall=False):
    c.saveState();c.setStrokeColorRGB(.28,.28,.28);c.setFillColorRGB(.15,.15,.15);c.setLineWidth(.2);c.setFont('Body',7)
    if color is not None:c.setStrokeColor(color);c.setFillColor(color)
    if overall:c.setFillAlpha(.5)
    layout=getattr(c,'annotation_layout',None)
    if layout:
        if vertical:segments=[(a,[offset-3,a[1]]),(b,[offset-3,b[1]]),([offset,a[1]],[offset,b[1]])]
        else:segments=[(a,[a[0],offset-3]),(b,[b[0],offset-3]),([a[0],offset],[b[0],offset])]
        for start,end in segments:layout.add_stroke(c,start,end)
    if vertical:
        x=offset;c.setStrokeAlpha(.5);c.line(a[0],a[1],x-3,a[1]);c.line(b[0],b[1],x-3,b[1]);c.setStrokeAlpha(.5 if overall else 1);c.line(x,a[1],x,b[1])
        for y in [a[1],b[1]]:c.line(x-2,y-2,x+2,y+2)
        c.translate(x-(3+max(0,len(secondary_colors)-1)*2.2 if secondary_colors else 1.5),(a[1]+b[1])/2);c.rotate(90)
        dimension_label(c,0,0,label,secondary_colors,rail=-(3+max(0,len(secondary_colors)-1)*2.2 if secondary_colors else 1.5))
    else:
        y=offset;c.setStrokeAlpha(.5);c.line(a[0],a[1],a[0],y-3);c.line(b[0],b[1],b[0],y-3);c.setStrokeAlpha(.5 if overall else 1);c.line(a[0],y,b[0],y)
        for x in [a[0],b[0]]:c.line(x-2,y-2,x+2,y+2)
        dimension_label(c,(a[0]+b[0])/2,y+(3+max(0,len(secondary_colors)-1)*2.2 if secondary_colors else 1.5),label,secondary_colors,rail=y)
    c.restoreState()

def curve(c,e,project):
    kind=e.get('type')
    if kind=='line':c.line(*project(xy(e['start'])),*project(xy(e['end'])))
    elif kind=='circle':
        p=xy(e['center']);a=project(p);b=project([p[0]+e['radius'],p[1]]);c.circle(*a,abs(b[0]-a[0]),stroke=1,fill=0)
    elif kind=='arc':
        center=xy(e['center']);a=xy(e['start']);b=xy(e['end']);radius=math.dist(a,center)
        start=math.atan2(a[1]-center[1],a[0]-center[0]);end=math.atan2(b[1]-center[1],b[0]-center[0])
        sweep=(end-start)%(2*math.pi) if e.get('counterclockwise') else -((start-end)%(2*math.pi))
        count=max(8,min(720,math.ceil(abs(sweep)*radius/.5)));path=c.beginPath();path.moveTo(*project(a))
        for i in range(1,count+1):path.lineTo(*project([center[0]+radius*math.cos(start+sweep*i/count),center[1]+radius*math.sin(start+sweep*i/count)]))
        c.drawPath(path)
    else:return False
    return True

def dimension_positions(values,tolerance=.01):
    groups=[]
    for value in sorted(values):
        if groups and value-groups[-1][0]<=tolerance:groups[-1].append(value)
        else:groups.append([value])
    result=[]
    for group in groups:
        value=sum(group)/len(group)
        if abs(value-round(value))<=tolerance:value=float(round(value))
        result.append(value)
    return result

def hole_labels(holes,project):
    occupied=[];result=[]
    for hole in sorted(holes,key=lambda h:(-h['y'],h['x'])):
        x,y=project(hole['position']);width=stringWidth(hole['tag'],'Body',6)
        choices=[(4,4),(4,-10),(-width-4,4),(-width-4,-10),(5,12),(5,-18),(-width-5,12),(-width-5,-18)]
        selected=None
        for dx,dy in choices:
            box=(x+dx,y+dy-1,x+dx+width,y+dy+7)
            if box[0]<35 or box[2]>605 or box[1]<100 or box[3]>505:continue
            if any(not(box[2]+1<a or c+1<box[0] or box[3]+1<b or d+1<box[1]) for a,b,c,d in occupied):continue
            selected=(box,(x+dx,y+dy));break
        if selected is None:selected=((x+4,y+4,x+4+width,y+11),(x+4,y+4))
        occupied.append(selected[0]);result.append((hole,selected[1]))
    return result


def write_dimensions(report,output,progress=None):
    from dimension_sheets import write_sheets
    return write_sheets(report,output,progress)


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--progress',action='store_true');parser.add_argument('--diagnostic',type=Path)
    parser.add_argument('--no-paic-json', action='store_true', help='Nu publica rapoartele PAIC lângă PDF.')
    parser.add_argument('--no-overwrite', action='store_true', help='Publica un PDF nou, fără a înlocui unul existent.')
    parser.add_argument('--performance',action='store_true')
    args=parser.parse_args()
    import export_performance as perf
    if args.performance:
        perf.start()
    bootstrap=perf_counter()-_PROCESS_START
    with perf.stage('citire_si_deserializare_JSON'):
        source=json.loads(Path(args.input).read_text(encoding='utf-8-sig'));report=source.get('report',source)
    native_performance=report.pop('_export_performance',None)
    if not report.get('panels'):raise ValueError('Nu există plăci pentru cotare')
    output=Path(args.output)
    diagnostic_path=args.diagnostic
    if diagnostic_path is not None and diagnostic_path.resolve() in (output.resolve(),Path(args.input).resolve()):
        raise ValueError('Calea raportului trebuie sa fie distincta de PDF si de fisierul de intrare')
    if output.suffix.lower()!='.pdf':raise ValueError('Destinația trebuie să fie PDF')
    if args.no_overwrite and output.exists():
        raise FileExistsError(f'PDF-ul există deja: {output}')
    progress=(lambda s:print(s,file=sys.stderr,flush=True)) if args.progress else None
    from export_assembly import clean_report,make_plan
    from holes import add_hole_edges
    from hierarchical import write_hierarchical
    if '_native_xml' in report:
        from native_xml import review_geometry, verify_files
        native=report['_native_xml']
        if not Path(report['model']).samefile(native['model']) or report.get('order') != native['order']:
            raise ValueError('Identitatea modelului s-a schimbat după validarea sursei.')
        if Path(args.output).resolve() != Path(native['destination']).resolve():
            raise ValueError('Destinația PDF nu corespunde rulării validate.')
        verify_files(native)
        native['geometry_review']=review_geometry(report,native)
        native.pop('geometry')
    report=clean_report(report)
    add_hole_edges(report)
    from titleblock import load_template
    template=load_template()
    if template:
        report['_titleblock']=template
        from titleblock import load_manual_settings
        report['_cartus_manual']=load_manual_settings()
    plan=make_plan(report)
    report['_paic03_findings']=[]
    report['_paic04_findings']=[]
    report['_paic05_findings']=[]
    report['_paic06_rows']=[]
    report['_paic08_findings']=[]
    report['_paic09_findings']=[]
    from bevel_sections import legend_labels
    report['_paic04_labels']=legend_labels(report)
    from pypdf import PdfReader
    with tempfile.TemporaryDirectory(prefix='.cote-',dir=output.parent) as directory:
        staged=Path(directory)/'document.pdf' if args.no_overwrite else Path(directory)/output.name
        pages=write_hierarchical(report,staged,plan,progress=progress,dimensions=True)
        from specification import insert_specification
        with perf.stage('inserare_tabele_si_reasamblare'):
            pages+=insert_specification(report,staged,plan)
        from model_views import insert_model_views
        with perf.stage('inserare_vederi_si_reasamblare'):
            pages+=insert_model_views(report,staged,plan)
        from project_legend import insert_project_legend
        with perf.stage('inserare_legenda_si_reasamblare'):
            pages+=insert_project_legend(report,staged,plan)
        if template:
            from titleblock import frame_pdf
            frame_pdf(staged,template,report,plan.get('cartus_contexts',{}),cover_without_titleblock=True)
        result={'pages':pages,'panels':len(report['panels']),'holes':sum(len(p.get('holes',[])) for p in report['panels'])}
        with staged.open('rb') as stream:
            if pages<1 or len(PdfReader(stream).pages)!=pages:
                raise ValueError('Numarul paginilor din PDF nu corespunde exportului')
        report.pop('_paic04_labels',None)
        if diagnostic_path is not None:
            with tempfile.TemporaryDirectory(prefix='.cote-report-',dir=diagnostic_path.parent) as report_dir:
                diagnostic=Path(report_dir)/diagnostic_path.name
                diagnostic.write_text(json.dumps({'report':report,'dimensions':result,'plan':plan},ensure_ascii=False),encoding='utf-8')
                diagnostic.replace(diagnostic_path)
        if '_native_xml' in report:
            verify_files(native)
        with perf.stage('publicare_PDF'):
            if args.no_overwrite:
                import os
                try:
                    if os.name=='nt':
                        staged.rename(output)
                    else:
                        os.link(staged,output)
                except FileExistsError as exc:
                    raise FileExistsError(f'PDF-ul a apărut între timp. Alegeți o altă destinație: {output}') from exc
            else:
                staged.replace(output)
    diagnostic_base=None
    if not args.no_paic_json:
        from diagnostic_reports import report_base, write_report
        try:
            diagnostic_base=report_base(output,report.get('model'))
            write_report(diagnostic_base,'.cote.json',{'report':report,'dimensions':result,'plan':plan},indent=None)
        except (OSError,ValueError,TypeError) as error:
            print('Diagnostic: raportul nu a putut fi salvat: '+str(error),file=sys.stderr)
    if diagnostic_base is not None:
        # Validation is separate from the PDF and cannot reject a production export.
        try:
            from panel_validation import validate_panels
            validation=validate_panels(report,plan)
            write_report(diagnostic_base,'.PAIC-02.json',validation)
        except Exception as error:
            print('PAIC-02: raportul tehnic nu a putut fi generat: '+str(error),file=sys.stderr)
        try:
            findings=report['_paic03_findings']
            pages_by_plate={str(c['placa']):int(n) for n,c in plan.get('cartus_contexts',{}).items() if c.get('placa')}
            for item in findings:item['page']=pages_by_plate.get(str(item.get('plate')))
            write_report(diagnostic_base,'.PAIC-03.json',{'model':report.get('model'),'panels':len(report['panels']),
                                                 'operations':findings})
        except (OSError, ValueError, TypeError) as error:
            print('PAIC-03: raportul nu a putut fi salvat: '+str(error),file=sys.stderr)
        try:
            findings=report['_paic04_findings']
            pages_by_plate={str(c['placa']):int(n) for n,c in plan.get('cartus_contexts',{}).items() if c.get('placa')}
            for item in findings:item['page']=pages_by_plate.get(str(item.get('plate')))
            write_report(diagnostic_base,'.PAIC-04.json',{'model':report.get('model'),'panels':len(report['panels']),
                                                 'operations':findings})
        except (OSError,ValueError,TypeError) as error:
            print('PAIC-04: raportul nu a putut fi salvat: '+str(error),file=sys.stderr)
        try:
            findings=report['_paic05_findings']
            pages_by_plate={str(c['placa']):int(n) for n,c in plan.get('cartus_contexts',{}).items() if c.get('placa')}
            for item in findings:item['page']=pages_by_plate.get(str(item.get('plate')))
            write_report(diagnostic_base,'.PAIC-05.json',{'model':report.get('model'),'panels':len(report['panels']),
                                                 'operations':findings})
        except (OSError,ValueError,TypeError) as error:
            print('PAIC-05: raportul nu a putut fi salvat: '+str(error),file=sys.stderr)
        try:
            from specification import processing_report
            write_report(diagnostic_base,'.PAIC-06.json',processing_report(report,plan))
        except (OSError,ValueError,TypeError) as error:
            print('PAIC-06: raportul nu a putut fi salvat: '+str(error),file=sys.stderr)
        try:
            findings=report['_paic08_findings']
            pages_by_plate={str(c['placa']):int(n) for n,c in plan.get('cartus_contexts',{}).items() if c.get('placa')}
            for item in findings:item['page']=pages_by_plate.get(str(item.get('plate')))
            write_report(diagnostic_base,'.PAIC-08.json',{'model':report.get('model'),'panels':len(report['panels']),
                                                 'views':findings})
        except (OSError,ValueError,TypeError) as error:
            print('PAIC-08: raportul nu a putut fi salvat: '+str(error),file=sys.stderr)
        try:
            findings=report['_paic09_findings']
            pages={c['_orthographic_id']:int(n) for n,c in plan.get('cartus_contexts',{}).items() if '_orthographic_id' in c}
            for item in findings:item['page']=pages.get(item['subject']['id'])
            write_report(diagnostic_base,'.PAIC-09.json',{'model':report.get('model'),'views':findings})
        except (OSError,ValueError,TypeError) as error:
            print('PAIC-09: raportul nu a putut fi salvat: '+str(error),file=sys.stderr)
    if diagnostic_base is not None:
        result['diagnostic_base']=str(diagnostic_base)
    if args.performance:
        result['performance']={'native':native_performance,'python':perf.stop(),
                               'python_bootstrap_seconds':round(bootstrap,6),
                               'renderer_seconds':round(perf_counter()-_PROCESS_START,6)}
    print(json.dumps({'ok':True,'pdf':str(output),**result},ensure_ascii=False))

if __name__=='__main__':main()
