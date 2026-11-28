"""Read native Cubis catalog labels without evaluating volatile Excel helpers."""
from pathlib import PurePosixPath
import json
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


def read_catalogs(filename):
    with zipfile.ZipFile(filename) as book:
        shared = []
        if 'xl/sharedStrings.xml' in book.namelist():
            shared = [''.join(node.itertext()) for node in ET.fromstring(
                book.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        relationships = {node.attrib['Id']: node.attrib['Target'] for node in
                         ET.fromstring(book.read('xl/_rels/workbook.xml.rels'))}
        sheets = ET.fromstring(book.read('xl/workbook.xml')).find('s:sheets', NS)
        result = {}
        for sheet in sheets:
            name = sheet.attrib['name']
            if name not in ('PAL', 'ABS'):
                continue
            target = relationships[sheet.attrib[REL]].replace('\\', '/')
            member = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
            if '..' in PurePosixPath(member).parts or not member.startswith('xl/'):
                raise ValueError('Invalid catalog worksheet relationship')
            labels = []
            seen = set()
            for cell in ET.fromstring(book.read(member)).findall('.//s:sheetData/s:row/s:c', NS):
                address = cell.get('r', '')
                if not re.fullmatch(r'A[0-9]+', address) or address == 'A1':
                    continue
                value = cell.find('s:v', NS)
                if cell.get('t') == 's' and value is not None:
                    text = shared[int(value.text)]
                elif cell.get('t') == 'inlineStr':
                    text = ''.join(cell.find('s:is', NS).itertext())
                else:
                    text = value.text if value is not None else None
                if text and text not in seen:
                    labels.append(text)
                    seen.add(text)
            result[name] = labels
        if set(result) != {'PAL', 'ABS'}:
            raise ValueError('Cubis PAL/ABS catalogs are missing')
        return result


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(read_catalogs(sys.argv[1]), ensure_ascii=False))
