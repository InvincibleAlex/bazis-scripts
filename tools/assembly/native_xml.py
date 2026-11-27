"""Offline candidate for a single, isolated native specification per export."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from export_performance import measured, observe, start, stop


class SourceError(ValueError):
    pass


class SourceChoice(SourceError):
    pass


def inside(path, root):
    return path == root or root in path.parents


def located(path, root):
    result = path.resolve(strict=True)
    if not inside(result, root):
        raise SourceError(f'Calea rezolvată iese din proiect: {path}')
    return result


@measured('identificare_proiect_XML')
def find_source(model, selected=None, project_root=None):
    model = Path(model)
    if not model.is_absolute() or model.suffix.lower() != '.b3d':
        raise SourceError('Salvați modelul BAZIS și verificați calea nativă .b3d.')
    model = model.resolve(strict=True)
    with model.open('rb'):
        pass
    root = Path(project_root).resolve(strict=True) if project_root else model.parent
    if root == root.parent or not inside(model, root):
        raise SourceError('Directorul proiectului trebuie să conțină modelul activ.')
    matching = [p for p in model.parent.iterdir()
                if p.name.lstrip('@').strip().casefold() == model.stem.casefold()
                and p.is_dir()]
    if selected:
        selected = Path(selected)
        if not selected.is_absolute() or selected.suffix.lower() != '.xml':
            raise SourceError('Alegeți un fișier XML cu o cale absolută.')
        xml = located(selected, root)
        return model, root, xml.parent, xml
    if len(matching) > 1:
        raise SourceChoice('Mai multe directoare de predare corespund modelului. Alegeți XML-ul.')
    delivery = located(matching[0], root) if matching else model.parent
    candidates = []
    for path in delivery.iterdir():
        if path.suffix.lower() != '.xml':
            continue
        target = located(path, root)
        if target.is_file() and not any(os.path.samefile(target, other) for other in candidates):
            candidates.append(target)
    if len(candidates) != 1:
        raise SourceChoice(f'{len(candidates)} XML-uri candidate în {delivery}. Alegeți specificația modelului.')
    return model, root, delivery, candidates[0]


def value(node, tag):
    return (node.findtext(tag) or '').strip()


def quantity(text):
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise SourceError(f'Cantitate sau lungime XML invalidă: {text!r}') from None
    if not number.is_finite() or number < 0:
        raise SourceError(f'Cantitate sau lungime XML invalidă: {text!r}')
    return number


def number_text(number):
    return format(number, 'f').rstrip('0').rstrip('.') if number.as_tuple().exponent < 0 else format(number, 'f')


@measured('validare_identitate_XML')
def identify(tree, context):
    if tree.tag != 'Проект':
        raise SourceError('XML-ul nu este o specificație nativă de proiect BAZIS.')
    if not re.fullmatch(r'\d+(?:\.\d+)+', tree.get('Версия', '')):
        raise SourceError('Versiunea BAZIS lipsește sau este invalidă în antetul XML.')
    if context.get('scope') != 'whole_model':
        raise SourceError('Candidatul acceptă doar exportul modelului integral, fără selecție de corp.')
    products = tree.findall('Изделие')
    if len(products) != 1 or value(products[0], 'ТипОбъекта') != 'Модель' or not products[0].findall('./СписокЭлементов/*'):
        raise SourceError('Specificația nu conține un singur produs de tip model integral cu structură.')
    product = products[0]
    order = context.get('order', {})
    for field, actual in [('name', value(product, 'Заказ')), ('product_name', value(product, 'Наименование')),
                          ('product_code', value(product, 'Артикул'))]:
        expected = str(order.get(field) or '').strip()
        if not expected or expected != actual:
            raise SourceError(f'Identitatea {field} nu poate fi confirmată: model {expected!r}, XML {actual!r}.')
    if tree.get('Наименование', '').strip() != value(product, 'Заказ'):
        raise SourceError('Identitatea proiectului diferă de comanda înscrisă pentru produsul XML.')
    if order.get('code') and str(order['code']).strip() != tree.get('Номер', '').strip():
        raise SourceError('Numărul comenzii diferă între model și XML.')
    if quantity(value(product, 'Количество')) != 1:
        raise SourceError('Cantitatea de produs din XML nu este 1. Domeniul diferă de o instanță de model.')
    return product


@measured('centralizare_XML')
def collect(product):
    hardware = defaultdict(Decimal)
    unresolved = []
    profiles = []
    geometry = defaultdict(list)
    def walk(element, multiplier):
        raw = value(element, 'Количество')
        count = multiplier * (quantity(raw) if raw else 1)
        typ = value(element, 'ТипОбъекта')
        material = element.find('ОсновнойМатериал')
        name = value(element, 'Наименование')
        mark = value(element, 'Обозначение')
        if typ == 'Панель' and mark and all(value(element, key) for key in ('Длина', 'Ширина')):
            pairs = [('Длина','Ширина'), ('Длина_готовой_детали','Ширина_готовой_детали')]
            geometry[mark].append(dict(count=int(count), dimensions=[
                [value(element,a),value(element,b)] for a,b in pairs if value(element,a) and value(element,b)]))
        if typ == 'Профиль':
            dims = [value(element, k) for k in ('Длина', 'Длина_детали_без_облицовки', 'Длина_готовой_детали')]
            code = value(material, 'Код') if material is not None else ''
            # Length agreement is necessary, but a terminal operation still needs a cut-specific definition.
            extras = [el.tag for el in element if (len(el) or (el.text or '').strip())
                      and el.tag not in {'ТипОбъекта','Наименование','Код','КодДетали','Длина','Ширина',
                                         'Длина_детали_без_облицовки','Ширина_детали_без_облицовки',
                                         'Длина_готовой_детали','Ширина_готовой_детали','Количество',
                                         'Позиция','Обозначение','ОсновнойМатериал'}]
            nums = [quantity(d) for d in dims if d]
            if not code or not raw or len(nums) != 3 or len(set(nums)) != 1 or not nums[0] or count != int(count) or extras:
                unresolved.append(dict(kind='profile', name=name, mark=mark, dimensions=dims, extra=extras))
            else:
                profiles.append((code, value(material, 'Наименование') or name, nums[0], int(count), value(element, 'КодДетали')))
        elif material is not None:
            kind = value(material, 'Класс')
            code = value(material, 'Код')
            label = value(material, 'Наименование')
            unit = value(material, 'ЕдИзм')
            material_id = value(material, 'SyncID') or value(material, 'ID')
            if kind == 'M3' and label and unit in {'buc.', 'set'} and value(material, 'Количество'):
                hardware[(code, label, unit, material_id)] += quantity(value(material, 'Количество')) * multiplier
            elif (kind == 'M3' or (not kind and typ in {'Фурнитура', 'Сборка'})):
                unresolved.append(dict(kind='material', name=label or name, mark=mark, article=code))
        if typ == 'Блок' and material is None and not value(element, 'Код') and not mark and name:
            unresolved.append(dict(kind='uncoded_block', name=name))
        for child in element.findall('./СписокЭлементов/*'):
            walk(child, count)
    walk(product, Decimal(1))
    profile_rows = []
    # Distinct parts at one article/length stay separate when their cut equivalence is unproven.
    groups = defaultdict(list)
    for code, name, length, count, mark in profiles:
        groups[(code, name, length)].append((count, mark))
    for (code, name, length), pieces in sorted(groups.items()):
        by_part = defaultdict(int)
        for index, (count, part) in enumerate(pieces):
            by_part[(part, 0 if part else index)] += count
        if len(by_part) > 1:
            unresolved.append(dict(kind='terminal_equivalence', article=code, length=number_text(length), count=sum(by_part.values())))
        for count in by_part.values():
            profile_rows.append([str(len(profile_rows)+1), code, name, number_text(length).replace('.',','), str(count)])
    hardware_rows = [[str(i), code, label, f'{number_text(n)} {unit}']
                     for i, ((code,label,unit,_), n) in enumerate(sorted(hardware.items(), key=lambda x:x[0][1].casefold()),1) if n]
    return hardware_rows, profile_rows, sum(x[3] for x in profiles), unresolved, dict(geometry)


def exception_summary(hardware, issues):
    grouped = Counter()
    for item in issues:
        label = item.get('name') or item.get('article') or item.get('mark') or '(fără reper)'
        grouped[(item['kind'], label)] += 1
    rows = [dict(kind=kind, name=label, records=count)
            for (kind, label), count in sorted(grouped.items())]
    codes = {row[1] for row in hardware}
    if 'OP 550-H100' not in codes and ('uncoded_block', 'Picior 100 mm, ajustabil') in grouped:
        rows.insert(0, dict(kind='estimate_reference', article='OP 550-H100',
            name='Picior ajustabil: fără contribuție identificată în XML. Cantitate neatribuită.'))
    return rows


def file_identity(info):
    # Preserve Windows file IDs and nanosecond timestamps across the BAZIS
    # JavaScript JSON round-trip, which represents numbers as binary64.
    return [str(part) for part in (info.st_dev, info.st_ino, info.st_size,
                                   info.st_mtime_ns, info.st_ctime_ns)]


def file_hash(path):
    with Path(path).open('rb') as stream:
        return sha256(stream.read()).hexdigest()


def prepare(context, selected=None, confirm=None, project_root=None):
    clock = time.perf_counter
    start = clock()
    model, root, delivery, xml = find_source(context.get('model',''), selected, project_root)
    identified = clock()
    if context.get('dirty') is True:
        raise SourceError('Salvați modificările din BAZIS și regenerați XML-ul.')
    model_info = model.stat()
    xml_info = xml.stat()
    if xml_info.st_mtime_ns < model_info.st_mtime_ns:
        raise SourceError('XML-ul este anterior modelului salvat. Regenerați specificația.')
    with xml.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_mtime_ns, opened.st_size) != (xml_info.st_mtime_ns, xml_info.st_size):
            raise SourceError('Specificația XML s-a schimbat înainte de citire.')
        raw = stream.read()
    if b'<!DOCTYPE' in raw.upper().replace(b'\x00', b''):
        raise SourceError('Declarațiile DTD nu sunt acceptate în specificație.')
    try:
        tree = ET.fromstring(raw)
    except ET.ParseError as error:
        raise SourceError(f'Specificație XML incompletă sau coruptă: {xml}') from error
    parsed = clock()
    product = identify(tree, context)
    validated = clock()
    hardware, profiles, physical, unresolved, geometry = collect(product)
    finish = clock()
    if file_identity(xml_info) != file_identity(xml.stat()):
        raise SourceError('Specificația XML s-a schimbat în timpul citirii.')
    manifest = dict(run_id=str(uuid.uuid4()), model=str(model), project=str(root), delivery=str(delivery),
        xml=str(xml), xml_modified=datetime.fromtimestamp(xml_info.st_mtime).astimezone().isoformat(),
        xml_sha256=sha256(raw).hexdigest(), xml_file_identity=file_identity(xml_info), model_sha256=file_hash(model), scope=context['scope'],
        identity='Comandă, produs și articol compatibile. Structură de model integral.',
        revision='Confirmare explicită a utilizatorului. Revizie nativă neconfirmată.',
        order=context['order'], version=tree.get('Версия'), destination=context.get('destination'),
        hardware=hardware, profiles=profiles, physical_profiles=physical, unresolved=unresolved, geometry=geometry,
        exceptions=exception_summary(hardware, unresolved), production_validated=False,
        seconds=dict(discovery=identified-start, parse=parsed-identified, identity=validated-parsed, aggregation=finish-validated))
    if confirm is None or not confirm(manifest):
        raise SourceError('Revizia specificației nu a fost confirmată pentru această rulare.')
    verify_files(manifest)
    return manifest


def verify_files(manifest):
    if file_identity(Path(manifest['xml']).stat()) != manifest['xml_file_identity']:
        raise SourceError('Specificația XML s-a schimbat după validare. Reluați exportul.')
    if file_hash(manifest['model']) != manifest['model_sha256']:
        raise SourceError('Modelul salvat s-a schimbat după validare. Reluați exportul.')

def review_geometry(report, manifest):
    # Compare only codes exposed by both sources. XML lengths can use a different
    # finished/debiting convention, so numeric discrepancies remain diagnostic.
    xml_rows = manifest['geometry']
    panel_counts = Counter()
    numeric_matches = 0
    dimensional_differences = []
    for panel in report.get('panels', []):
        code = str(panel.get('designation') or '')
        if not code:
            continue
        panel_counts[code] += 1
        if panel.get('width') is None or panel.get('height') is None:
            continue
        native = sorted([float(panel['width']), float(panel['height'])])
        dimensions = [sorted(map(float, pair)) for row in xml_rows.get(code, []) for pair in row['dimensions']]
        if any(all(abs(a-b) <= 0.01 for a,b in zip(pair,native)) for pair in dimensions):
            numeric_matches += 1
        elif dimensions:
            dimensional_differences.append(dict(code=code, panel_dimensions=native, xml_dimensions=dimensions))
    if report.get('panels') and not panel_counts:
        raise SourceError('Geometria extrasă nu oferă repere de placă pentru verificarea XML.')
    absent = sorted(set(panel_counts)-set(xml_rows))
    missing = [code for code in panel_counts if code in xml_rows and panel_counts[code]>sum(row['count'] for row in xml_rows[code])]
    if absent or missing:
        raise SourceError('Repere XML absente sau cu multiplicitate insuficientă: '+', '.join(absent+missing))
    return dict(common_panel_instances=sum(panel_counts.values()), geometry_panel_instances=len(report.get('panels', [])),
                dimension_matches_at_0_01_mm=numeric_matches, dimensional_differences=dimensional_differences,
                revision_proven=False)

@measured('apeluri_dialoguri_XML_total')
def dialog(mode, text='', initial=''):
    import subprocess
    import base64
    data = base64.b64encode(json.dumps([mode,text,initial],ensure_ascii=False).encode()).decode()
    command = r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('PAYLOAD'))|ConvertFrom-Json
$owner=New-Object System.Windows.Forms.Form
$owner.TopMost=$true
$owner.ShowInTaskbar=$false
$owner.Opacity=0
$owner.Show()
try {
  if($v[0] -eq 'file'){
    $d=New-Object System.Windows.Forms.OpenFileDialog
    $d.Filter='Specificație XML (*.xml)|*.xml'
    $d.InitialDirectory=$v[2]
    $d.Title=$v[1]
    $watch=[Diagnostics.Stopwatch]::StartNew(); $answer=$d.ShowDialog($owner); $watch.Stop()
    if($answer -eq 'OK'){$d.FileName}
    $d.Dispose()
  } elseif($v[0] -eq 'folder'){
    $d=New-Object System.Windows.Forms.FolderBrowserDialog
    $d.Description=$v[1]
    $d.SelectedPath=$v[2]
    $watch=[Diagnostics.Stopwatch]::StartNew(); $answer=$d.ShowDialog($owner); $watch.Stop()
    if($answer -eq 'OK'){$d.SelectedPath}
    $d.Dispose()
  } else {
    $watch=[Diagnostics.Stopwatch]::StartNew()
    [System.Windows.Forms.MessageBox]::Show($owner,$v[1],'Confirmare XML pentru această rulare',
      [System.Windows.Forms.MessageBoxButtons]::YesNo,[System.Windows.Forms.MessageBoxIcon]::Question,
      [System.Windows.Forms.MessageBoxDefaultButton]::Button2)
    $watch.Stop()
  }
  [Console]::Error.WriteLine("PAIC13:"+$watch.ElapsedMilliseconds)
} finally {$owner.Dispose()}
""".replace('PAYLOAD',data)
    encoded=base64.b64encode(command.encode('utf-16-le')).decode()
    proc=subprocess.run(['powershell.exe','-NoProfile','-STA','-EncodedCommand',encoded],
                        capture_output=True,encoding='utf-8',check=True,
                        creationflags=subprocess.CREATE_NO_WINDOW)
    for line in proc.stderr.splitlines():
        if line.startswith('PAIC13:') and line[7:].isdigit():
            observe('asteptare_dialoguri_XML', int(line[7:])/1000)
    return proc.stdout.strip().lstrip('\ufeff')


def main():
    start()
    import tempfile
    parser = argparse.ArgumentParser()
    parser.add_argument('context', type=Path)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    try:
        context = json.loads(args.context.read_text(encoding='utf-8'))
        def confirm(d):
            return dialog('confirm',
                f'Model: {d["model"]}\nXML: {d["xml"]}\nModificat: {d["xml_modified"]}\n\n'
                'Revizia și eventualele modificări nesalvate nu pot fi confirmate nativ. '
                'Confirmați că modelul este salvat și că XML-ul provine din versiunea sa actuală?')=='Yes'
        try:
            result = prepare(context, confirm=confirm)
        except SourceChoice as error:
            initial=Path(context['model']).resolve(strict=True).parent
            path=dialog('file',str(error),str(initial))
            if not path:
                raise SourceError('Selectarea specificației a fost anulată.') from None
            project=None
            if not inside(Path(path).resolve(strict=True), initial):
                project=dialog('folder','Confirmați rădăcina comună a proiectului, fără proiectele învecinate.',str(initial))
                if not project:
                    raise SourceError('Directorul proiectului nu a fost confirmat.')
            result=prepare(context,selected=path,confirm=confirm,project_root=project)
        dest=Path(context['destination'])
        if not dest.is_absolute() or dest.suffix.lower()!='.pdf':
            raise SourceError('Indicați o destinație PDF absolută.')
        with tempfile.TemporaryFile(dir=dest.parent), tempfile.TemporaryFile(dir=args.receipt.parent):
            pass
        if dest.exists():
            with dest.open('r+b'):
                pass
        result["_performance"]=stop()
        args.receipt.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()






