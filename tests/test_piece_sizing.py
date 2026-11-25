import sys
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/cubis'))
from size_piece_inputs import size_inputs,NS
ET.register_namespace('',NS)
styles=f'<styleSheet xmlns="{NS}"><cellXfs count="1"><xf fontId="0"><alignment wrapText="1"/></xf></cellXfs></styleSheet>'
sheet=f'<worksheet xmlns="{NS}"><cols><col min="1" max="12" width="10"/></cols><sheetData><row r="1" ht="27"><c r="A1" t="inlineStr"><is><t>Antet</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>cod</t></is></c><c r="B2" t="inlineStr"><is><t>PAL</t></is></c><c r="K2" t="inlineStr"><is><t>{"Observatie lunga "*30}</t></is></c><c r="L2"><f>A2</f><v>1</v></c></row></sheetData></worksheet>'
result,formatted=size_inputs(sheet,styles,2,2,list('ABCDEFGHIJK'),'B','K')
r=ET.fromstring(result);xfs=ET.fromstring(formatted).find('{'+NS+'}cellXfs')
row=r.find('{'+NS+'}sheetData/{'+NS+'}row[@r="2"]')
assert row.get('ht')=='15','long observations must not grow the row'
notes=row.find('{'+NS+'}c[@r="K2"]');alignment=xfs[int(notes.get('s'))].find('{'+NS+'}alignment')
assert alignment.get('wrapText')=='0'
assert r.find('{'+NS+'}sheetData/{'+NS+'}row[@r="1"]').get('ht')=='27'
assert row.find('{'+NS+'}c[@r="L2"]/{'+NS+'}f').text=='A2'
assert xfs[0].find('{'+NS+'}alignment').get('wrapText')=='1','original style must remain unchanged'
print('PASS: piece rows sized, observations stay one line, header and formulas retained')
