"""Read-only BLN inventory and conservative LDW UTF-8 text recovery.

This does not decode drawing geometry or infer machining from isolated numbers.
LDW text candidates must have a valid little-endian byte length and trailing NUL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET
import olefile


def texts(data: bytes) -> list[dict]:
    found = []
    for offset in range(len(data) - 5):
        length = struct.unpack_from('<I', data, offset)[0]
        if not 1 <= length <= 2048 or offset + 4 + length >= len(data):
            continue
        end = offset + 4 + length
        if data[end] != 0:
            continue
        try:
            value = data[offset + 4:end].decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not value.strip() or not all(c.isprintable() or c in '\r\n\t' for c in value):
            continue
        found.append({'offset': offset + 4, 'text': value})
    return found


def hole_table(candidates: list[dict]) -> dict | None:
    """Accept only a complete column-major table with matching row counts."""
    values = [x['text'] for x in candidates if not re.search(r'Bahnschrift|Arial|Times New Roman', x['text'])]
    headers = list(re.finditer(r'^(\d+) găuri (.+)$', '\n'.join(values), re.M))
    if not headers:
        return None
    groups = [{'count': int(m[1]), 'description': m[2]} for m in headers]
    size = sum(g['count'] for g in groups)
    if not 1 <= size <= 10000:
        return None
    columns = ['D', 'H', 'X', 'Y', 'Z', 'Tip']
    try:
        begin = values.index('D')
        rows = [{} for _ in range(size)]
        cursor = begin
        for key in columns:
            if values[cursor] != key:
                return None
            column = values[cursor + 1:cursor + 1 + size]
            if len(column) != size:
                return None
            for row, value in zip(rows, column):
                if key == 'Tip':
                    if value not in ['cant.', 'cant', 'față', 'fata', 'faţa', 'fața', 'faţă']:
                        return None
                    row[key] = value
                else:
                    row[key] = float(value.replace(',', '.'))
            cursor += 1 + size
        offset = 0
        for group in groups:
            for row in rows[offset:offset + group['count']]:
                row['description'] = group['description']
            offset += group['count']
        return {'coordinate_space': 'drawing table; not converted to model/world coordinates', 'rows': rows, 'groups': groups}
    except (ValueError, IndexError):
        return None


def inspect(source: Path) -> dict:
    result = {'source': str(source.resolve()), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'geometry_decoded': False, 'coordinates_decoded': False, 'files': []}
    with olefile.OleFileIO(source) as library:
        tree = ET.fromstring(library.openstream('$$Lib_structure$$').read().decode('utf-8-sig'))
        for node in tree.iter('File'):
            name, storage = node.findtext('Name'), node.findtext('Storage')
            data = library.openstream(storage).read()
            item = {'name': name, 'storage': storage, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            if name.lower().endswith('.ldw'):
                item['text_candidates'] = texts(data)
                item['hole_headers'] = [t['text'] for t in item['text_candidates'] if re.search(r'\bgăuri\b|\bgauri\b', t['text'], re.I)]
                item['hole_table'] = hole_table(item['text_candidates'])
                item['part_codes'] = sorted(set(re.findall(r'\b\d{2}(?:\.\d{2}){4}\.\d{3}\b', '\n'.join(t['text'] for t in item['text_candidates']))))
            result['files'].append(item)
    result['counts'] = {'model': sum(f['name'].lower().endswith('.b3d') for f in result['files']),
                        'drawings': sum(f['name'].lower().endswith('.ldw') for f in result['files']),
                        'drawings_with_hole_text': sum(bool(f.get('hole_headers')) for f in result['files']),
                        'complete_hole_tables_recovered': sum(bool(f.get('hole_table')) for f in result['files'])}
    result['coordinates_decoded'] = result['counts']['complete_hole_tables_recovered'] > 0
    result['limitations'] = ['Only complete validated hole tables are interpreted.',
                             'LDW geometry and milling contours have not been decoded.',
                             'Table coordinates remain in the drawing reference system.']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.source)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['counts']))
