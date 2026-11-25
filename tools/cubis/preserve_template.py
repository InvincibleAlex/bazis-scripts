"""Preserve original XLSX native features; copy only artifact-authored input cells.

No workbook library rewrites the original dropdowns, names, drawings or formulas.
"""
from pathlib import Path
import copy
import json
import re
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ET.register_namespace('',NS)
template,authored,manifest,destination=map(Path,sys.argv[1:])
data=json.loads(manifest.read_text(encoding='utf-8'))
mapping=data.get('sheet_mapping',{'Formular':'xl/worksheets/sheet1.xml','Date client':'xl/worksheets/sheet2.xml'})
def col(addr):
    value=0
    for c in re.match('[A-Z]+',addr)[0]:value=value*26+ord(c)-64
    return value
with zipfile.ZipFile(template) as original,zipfile.ZipFile(authored) as source:
    strings=[]
    if 'xl/sharedStrings.xml' in source.namelist():
        strings=[''.join(x.itertext()) for x in ET.fromstring(source.read('xl/sharedStrings.xml'))]
    changes={}
    styles=original.read('xl/styles.xml').decode('utf-8')
    for sheet,addresses in data['touched'].items():
        filename=mapping[sheet]
        text=original.read(filename).decode('utf-8')
        cells={c.get('r'):c for c in ET.fromstring(source.read(filename)).iter('{'+NS+'}c')}
        for address in addresses:
            cell=copy.deepcopy(cells.get(address,ET.Element('{'+NS+'}c',{'r':address})))
            if cell.get('t')=='s':
                value=cell.find('{'+NS+'}v');value_text=strings[int(value.text)]
                cell.remove(value);cell.set('t','inlineStr')
                inline=ET.SubElement(cell,'{'+NS+'}is');ET.SubElement(inline,'{'+NS+'}t').text=value_text
            pattern=r'<c\b(?=[^>]*\br="'+address+r'")[^>]*?(?:/>|>.*?</c>)'
            old=re.search(pattern,text,re.S)
            cell.attrib.pop('s',None)
            if old:
                style=re.search(r'\bs="(\d+)"',old.group())
                if style:cell.set('s',style[1])
            replacement=ET.tostring(cell,encoding='unicode').replace(' xmlns="'+NS+'"','')
            if old:text=text[:old.start()]+replacement+text[old.end():]
            else:
                number=re.search(r'\d+',address)[0]
                row=re.search(r'(<row\b(?=[^>]*\br="'+number+r'")[^>]*>)(.*?)(</row>)',text,re.S)
                if not row:raise ValueError('Missing template row '+number)
                body=row[2];at=len(body)
                for other in re.finditer(r'<c\b[^>]*\br="([A-Z]+\d+)"',body):
                    if col(other[1])>col(address):at=other.start();break
                body=body[:at]+replacement+body[at:]
                text=text[:row.start(2)]+body+text[row.end(2):]
        sizing=data.get('size_piece_inputs',{})
        if sizing.get('sheet')==sheet and data.get('rows'):
            sys.path.insert(0,str(Path(__file__).resolve().parent))
            from size_piece_inputs import size_inputs
            first=sizing['first_row'];columns=list(sizing['columns'])
            text,styles=size_inputs(text,styles,first,first+len(data['rows'])-1,columns,sizing['material'],sizing['notes'],resize_columns=sizing.get('resize_columns',True))
        ET.fromstring(text)
        changes[filename]=text.encode('utf-8')
    if styles!=original.read('xl/styles.xml').decode('utf-8'):changes['xl/styles.xml']=styles.encode('utf-8')
    # Native Excel recalculates its original formulas and interactive dropdown helpers.
    workbook=original.read('xl/workbook.xml').decode('utf-8')
    workbook=re.sub(r'<calcPr\b[^>]*/>', '<calcPr calcId="191029" calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/>',workbook)
    changes['xl/workbook.xml']=workbook.encode('utf-8')
    if destination.exists():raise FileExistsError('Output already exists: '+str(destination))
    temporary=destination.with_name(destination.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with zipfile.ZipFile(temporary,'x',zipfile.ZIP_DEFLATED) as output:
            for info in original.infolist():output.writestr(copy.copy(info),changes.get(info.filename,original.read(info.filename)))
        with zipfile.ZipFile(temporary) as check:
            for info in original.infolist():
                if info.filename not in changes and check.read(info.filename)!=original.read(info.filename):raise ValueError('Unrelated part changed')
            for filename in mapping.values():
                before=ET.fromstring(original.read(filename));after=ET.fromstring(check.read(filename))
                def formulas(root):
                    return [(c.get('r'),dict(c.find('{'+NS+'}f').attrib),c.find('{'+NS+'}f').text)
                        for c in root.iter('{'+NS+'}c') if c.find('{'+NS+'}f') is not None]
                if formulas(before)!=formulas(after):raise ValueError('Original formulas changed')
                for tag in ['dataValidations','extLst','mergeCells','conditionalFormatting','sheetProtection']:
                    a=[ET.tostring(x) for x in before.findall('{'+NS+'}'+tag)]
                    b=[ET.tostring(x) for x in after.findall('{'+NS+'}'+tag)]
                    if a!=b:raise ValueError('Native feature changed: '+tag)
        temporary.rename(destination)
    finally:
        if temporary.exists():temporary.unlink()
print('Preserved template native features; authored input cells copied; Excel recalc requested.')
