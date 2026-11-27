"""Inspect saved BAZIS settings and prepare byte-preserving, reversible changes.

This is a disk adapter, not an API for a currently open BAZIS dialog. BAZIS writes
some .xml files with numeric tag names/control characters, so the bounded scanner
below preserves bytes instead of repairing/reserializing the user's document.
"""
from __future__ import annotations

from collections import Counter
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable
import uuid

from .transport import BridgeClient, atomic_json, read_json


# Explicit configuration files only; account/online data and material databases
# are deliberately outside this adapter.
FILES = {
    'ActionData.xml', 'BaseSettings.xml', 'BirkaFormSettings.xml', 'BirkaSettings.xml',
    'CabActionData.xml', 'CabCurrent.xml', 'CabFurnSettings.xml', 'CabGrids.xml',
    'CabSettings.xml', 'CabSLKM.xml', 'CabUserInterface.xml', 'CNCActionData.xml',
    'CNCSettings.xml', 'CNCUserInterface.xml', 'CNCViewConfig.xml', 'CreateDrawings.xml',
    'CutEdge.xml', 'CutSettings/CutApplySettings.xml', 'CutSettings/CutFormControlSize.xml',
    'CutSettings/CutMaterialSelect.xml', 'CutSettings/CutMaterialSettings.xml',
    'CutSettings/CutProgrammParams.xml', 'CutSettings/CutSelectPostProc.xml',
    'CutSettings/CutSettings.xml', 'CutSettings/InputSettings.xml',
    'CutSettings/OutputSettings.xml', 'EstCorrespMaterials.xml', 'EstimateSettings.xml',
    'FRSettings.xml', 'FurnMaterials.xml', 'MasterBox.xml', 'MasterDoor.xml',
    'Package_Form.xml', 'Package_Materials.xml', 'Package_Settings.xml',
    'Package_Templates.xml', 'Raskr.xml', 'ScriptEditor.xml', 'Settings.xml',
    'UserInterface.xml', 'UserInterfaceEstimate.xml', 'UserInterfaceFurnMaterials.xml',
    'UserInterfaceMatbase.xml', 'UserInterfacePackage.xml', 'UserInterfaceRaskr.xml',
    'UserInterfaceWoodWorker.xml', 'VBODrawingOptions.xml', 'VRay.xml',
}
MAX_FILE = 16 * 1024 * 1024
MAX_VALUE = 8192
SENSITIVE = re.compile(r'password|passwd|pwd|secret|token|credential|authorization|apikey|privatekey', re.I)
# A setting that launches a script/program isn't an ordinary appearance toggle.
EXECUTION = re.compile(r'script|autorun|autostart|executable|commandline|startup|postproc', re.I)
TAG = re.compile(rb'<(?:!--[\s\S]*?--|!\[CDATA\[[\s\S]*?\]\]|\?[\s\S]*?\?|/?[\w:.\-\x80-\xff]+(?:\s+[^<>]*?)?\s*/?)>')
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z')
LABELS = {
    'MakeAssemblies': 'Creare desene de asamblare',
    'ShowGabaritSizes': 'Dimensiuni de gabarit',
    'DrawPanelsTextureDirection': 'Orientare textură',
    'MakeObjectsBlocks': 'Salvare ca blocuri',
    'DrawMstb': 'Scară foaie', 'ViewOffset': 'Spațiu între vizualizări',
    'ShowCuts': 'Desenare secțiuni pe desen',
    'AutoTransformBlock': 'Rotire bloc în sistemul său de coordonate',
    'AssemblyOnDoors': 'Pentru panouri frontale',
    'AssemblyOnBoxes': 'Pentru sertare', 'AssemblyOnBlock': 'Pentru blocuri',
    'Assembly': 'Pentru model',
}


class SettingsError(ValueError):
    pass


def revision(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Node:
    tag: str
    path: str
    parent: Node | None
    start: int
    end: int = 0
    children: list[Node] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    raw: bytes = b''
    self_closing: bool = False

    def context(self) -> list[str]:
        result = []
        p = self.parent
        while p:
            names = [n for n in p.children if n.tag == 'Name' and not n.children]
            if names:
                name = decode(names[0].raw)
                if name and not SENSITIVE.search(p.path):
                    result.append(name)
            p = p.parent
        return result[::-1]


def decode(raw: bytes) -> str:
    # Only XML's five predefined/numeric entities; no DTD/external entities.
    value = raw.decode('utf-8')
    if re.search(r'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[\da-fA-F]+);)', value):
        raise SettingsError('Unsupported entity in settings value')
    return html.unescape(value)


def scan(data: bytes) -> list[Node]:
    if len(data) > MAX_FILE:
        raise SettingsError('Settings file exceeds size limit')
    if not data.lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'<'):
        raise SettingsError('Binary BAZIS format: not supported by the saved XML settings adapter')
    if re.search(rb'<!\s*(?:DOCTYPE|ENTITY)', data, re.I):
        raise SettingsError('DTD and entity declarations are not supported')
    stack: list[Node] = []
    nodes: list[Node] = []
    root_count = 0
    pos = 0
    for m in TAG.finditer(data):
        between = data[pos:m.start()]
        if b'<' in between or (not stack and between.strip(b'\xef\xbb\xbf \r\n\t')):
            raise SettingsError('Unsupported or malformed markup')
        token = m.group()
        if token.startswith((b'<?', b'<!--')):
            # Mixed text/comments are retained but not writable as a simple value.
            if stack and not stack[-1].children:
                stack[-1].self_closing = True
        elif token.startswith(b'<![CDATA['):
            raise SettingsError('CDATA settings need a dedicated adapter')
        elif token.startswith(b'</'):
            tag = token[2:-1].strip().decode('utf-8')
            if not stack or stack[-1].tag != tag:
                raise SettingsError('Unbalanced settings tags')
            node = stack.pop()
            node.end = m.start()
            node.raw = data[node.start:node.end] if not node.children else b''
            if node.children and between.strip():
                raise SettingsError('Mixed-content settings need a dedicated adapter')
        else:
            if stack and between.strip():
                raise SettingsError('Mixed-content settings need a dedicated adapter')
            tag = re.match(rb'<([\w:.\-\x80-\xff]+)', token).group(1).decode('utf-8')
            parent = stack[-1] if stack else None
            if parent:
                parent.counts[tag] += 1
                path = f'{parent.path}/{tag}[{parent.counts[tag]}]'
            else:
                root_count += 1
                path = f'/{tag}[1]'
            node = Node(tag, path, parent, m.end(), self_closing=token.rstrip().endswith(b'/>'))
            if parent:
                parent.children.append(node)
            nodes.append(node)
            if not node.self_closing:
                stack.append(node)
        pos = m.end()
    if stack or root_count != 1 or data[pos:].strip():
        raise SettingsError('Incomplete settings document')
    return [n for n in nodes if not n.children]


def value_kind(value: str) -> str:
    if value in ('Y', 'N', 'true', 'false', 'True', 'False'):
        return 'boolean'
    if NUMBER.fullmatch(value):
        return 'number'
    return 'text'


def serialize_value(value: str | bool | int | float, old: str) -> str:
    kind = value_kind(old)
    if kind == 'boolean':
        if not isinstance(value, bool):
            raise SettingsError('Boolean setting requires a JSON boolean')
        pairs = {'Y': ('Y', 'N'), 'N': ('Y', 'N'), 'true': ('true', 'false'),
                 'false': ('true', 'false'), 'True': ('True', 'False'), 'False': ('True', 'False')}
        return pairs[old][0 if value else 1]
    if kind == 'number':
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise SettingsError('Numeric setting requires a number')
        value = str(value)
        if not NUMBER.fullmatch(value):
            raise SettingsError('Expected a finite decimal number using a dot')
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise SettingsError('Invalid number') from exc
        if not number.is_finite() or abs(number) > Decimal('1e15'):
            raise SettingsError('Number is out of range')
        if re.fullmatch(r'[+-]?\d+', old) and number != number.to_integral_value():
            raise SettingsError('Integer setting requires an integer value')
        if re.fullmatch(r'[+-]?\d+', old):
            return str(int(number))
        return value
    if not isinstance(value, str):
        raise SettingsError('Text setting requires a string')
    if len(value) > MAX_VALUE or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', value):
        raise SettingsError('Text is too long or contains control characters')
    return value


def bazis_processes() -> list[dict]:
    """Read process names without controlling any application windows."""
    if os.name != 'nt':
        raise SettingsError('Applying settings requires a Windows process check')
    class ProcessEntry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = kernel.Process32FirstW.argtypes
    kernel.Process32FirstW.restype = kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise SettingsError('Cannot inspect running BAZIS processes')
    names = {'bazis.exe', 'cabinet.exe', 'cab.exe', 'cnc.exe', 'raskr.exe', 'cutting.exe',
             'estimate.exe', 'smeta.exe', 'salon.exe', 'orderman.exe', 'stock.exe', 'priceman.exe'}
    found = []
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(handle, ctypes.byref(entry)):
            raise SettingsError('Cannot enumerate BAZIS processes')
        while True:
            if entry.szExeFile.casefold() in names:
                found.append({'pid': entry.th32ProcessID, 'name': entry.szExeFile})
            if not kernel.Process32NextW(handle, ctypes.byref(entry)):
                if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                    raise SettingsError('Process enumeration was incomplete')
                break
    finally:
        kernel.CloseHandle(handle)
    return found


class SettingsStore:
    def __init__(self, client: BridgeClient, root: Path | None = None,
                 processes: Callable[[], list[dict]] = bazis_processes):
        self.client = client
        self.root = root or Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Bazis'
        self.processes = processes

    def _path(self, file_id: str) -> Path:
        if file_id not in FILES:
            raise SettingsError('Unknown settings file_id; use bazis_settings_catalog')
        path = self.root / file_id
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise SettingsError('Settings path leaves the configured root')
        return path

    def _read(self, file_id: str) -> tuple[bytes, list[Node]]:
        path = self._path(file_id)
        if path.stat().st_size > MAX_FILE:
            raise SettingsError('Settings file exceeds size limit')
        data = path.read_bytes()
        return data, scan(data)

    def _row(self, n: Node) -> dict:
        hidden = bool(SENSITIVE.search(n.path))
        value = decode(n.raw) if not hidden else '[redacted]'
        blocked = hidden or bool(EXECUTION.search(n.path)) or n.self_closing or len(value) > MAX_VALUE
        return {'setting_id': n.path, 'name': n.tag, 'label': LABELS.get(n.tag, n.tag),
                'context': n.context() if not hidden else [], 'value': value,
                'value_type': value_kind(value), 'can_stage': not blocked,
                'semantics': 'mapped' if n.tag in LABELS else 'raw; verify meaning before changing'}

    def catalog(self) -> dict:
        items = []
        for file_id in sorted(FILES):
            path = self._path(file_id)
            if not path.is_file():
                continue
            try:
                data, nodes = self._read(file_id)
                items.append({'file_id': file_id, 'status': 'readable', 'setting_count': len(nodes),
                              'revision': revision(data)})
            except (SettingsError, UnicodeError) as exc:
                items.append({'file_id': file_id, 'status': 'unsupported', 'reason': str(exc)})
        return {'source': 'saved_configuration', 'live_dialog_access': False,
                'root': str(self.root), 'items': items,
                'notice': 'Saved values may differ from unsaved dialogs. No claim of every BAZIS setting.'}

    def read(self, file_id: str, query: str = '', offset: int = 0, limit: int = 100) -> dict:
        if offset < 0 or not 1 <= limit <= 500:
            raise SettingsError('Invalid page')
        data, nodes = self._read(file_id)
        rows = [self._row(n) for n in nodes]
        if query:
            words = query.casefold().split()
            rows = [r for r in rows if all(w in json.dumps(r, ensure_ascii=False).casefold() for w in words)]
        return {'source': 'saved_configuration', 'live_dialog_access': False, 'file_id': file_id,
                'revision': revision(data), 'total': len(rows), 'offset': offset,
                'items': rows[offset:offset+limit],
                'next_offset': offset+limit if offset+limit < len(rows) else None}

    def _workspace(self) -> Path:
        path = self.client.config_path.parent / 'settings'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def stage(self, file_id: str, expected_revision: str, changes: list[dict]) -> dict:
        if not self.client.config().get('allow_edits', False):
            raise SettingsError('Edits are disabled by local configuration')
        if not 1 <= len(changes) <= 100:
            raise SettingsError('Provide 1 to 100 explicit changes')
        data, nodes = self._read(file_id)
        if revision(data) != expected_revision:
            raise SettingsError('SETTINGS_CHANGED: reread the settings before staging')
        index = {n.path: n for n in nodes}
        seen = set()
        edits, diffs = [], []
        for c in changes:
            setting_id = c.get('setting_id')
            if setting_id in seen or setting_id not in index:
                raise SettingsError('Duplicate or unknown setting_id')
            seen.add(setting_id)
            node = index[setting_id]
            row = self._row(node)
            if not row['can_stage']:
                raise SettingsError('This field needs a dedicated adapter and cannot be staged')
            old = decode(node.raw)
            if c.get('expected_value') != old:
                raise SettingsError('Expected value mismatch')
            new = serialize_value(c.get('value'), old)
            if node.tag == 'DrawMstb' and Decimal(new) <= 0:
                raise SettingsError('Drawing scale must be greater than zero')
            if node.tag == 'ViewOffset' and Decimal(new) < 0:
                raise SettingsError('View spacing cannot be negative')
            if old == new:
                raise SettingsError('Change does not modify the setting')
            # Numeric/boolean formatting is kept explicit; XML escaping prevents markup injection.
            encoded = html.escape(new, quote=False).replace('\r', '&#13;').encode('utf-8')
            edits.append((node.start, node.end, encoded))
            diffs.append({'setting_id': setting_id, 'label': row['label'],
                          'context': row['context'], 'before': old, 'after': new})
        result = data
        for start, end, encoded in sorted(edits, reverse=True):
            result = result[:start] + encoded + result[end:]
        scan(result)
        stage_id = uuid.uuid4().hex
        folder = self._workspace() / stage_id
        folder.mkdir()
        (folder / 'before.xml').write_bytes(data)
        (folder / 'after.xml').write_bytes(result)
        manifest = {'stage_id': stage_id, 'file_id': file_id, 'source_root': str(self.root.resolve()),
                    'before_revision': revision(data), 'after_revision': revision(result),
                    'state': 'staged', 'changes': diffs}
        atomic_json(folder / 'manifest.json', manifest)
        return dict(manifest, preview_file=str(folder / 'after.xml'), applied_to_bazis=False,
                    notice='Prepared copy only. Applying requires BAZIS applications to be closed.')

    def _stage(self, stage_id: str) -> tuple[Path, dict]:
        if not re.fullmatch(r'[a-f0-9]{32}', stage_id):
            raise SettingsError('Invalid stage_id')
        folder = self._workspace() / stage_id
        manifest = read_json(folder / 'manifest.json')
        if manifest.get('stage_id') != stage_id or manifest.get('source_root') != str(self.root.resolve()):
            raise SettingsError('Settings stage belongs to another configuration')
        return folder, manifest

    def _guard(self):
        if not self.client.config().get('allow_edits', False):
            raise SettingsError('Edits are disabled by local configuration')
        running = self.processes()
        if running:
            raise SettingsError('BAZIS_RUNNING: save your work and close BAZIS applications first; '
                                + ', '.join(f"{p['name']} ({p['pid']})" for p in running))

    def apply(self, stage_id: str, *, restore: bool = False) -> dict:
        self._guard()
        folder, manifest = self._stage(stage_id)
        expected_state = 'applied' if restore else 'staged'
        if manifest['state'] != expected_state:
            raise SettingsError(f"Stage is {manifest['state']}; expected {expected_state}. Do not replay.")
        path = self._path(manifest['file_id'])
        original = (folder / 'before.xml').read_bytes()
        modified = (folder / 'after.xml').read_bytes()
        if revision(original) != manifest['before_revision'] or revision(modified) != manifest['after_revision']:
            raise SettingsError('Settings stage failed integrity validation')
        wanted = modified if restore else original
        replacement = original if restore else modified
        if revision(path.read_bytes()) != revision(wanted):
            raise SettingsError('SETTINGS_CHANGED: active file changed; refusing to overwrite it')
        scan(replacement)
        # Exclusive per-file adapter lock, optimistic revision check and recheck
        # processes immediately before replacing the file. This is not an OS-level
        # lock against manually starting BAZIS during the operation.
        lock = self._workspace() / (hashlib.sha256(str(path.resolve()).encode()).hexdigest() + '.lock')
        try:
            handle = lock.open('x')
        except FileExistsError as exc:
            raise SettingsError('Another settings operation is active; inspect its journal before retrying') from exc
        temp_path = None
        try:
            with handle:
                self._guard()
                if revision(path.read_bytes()) != revision(wanted):
                    raise SettingsError('SETTINGS_CHANGED: active file changed during apply')
                with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.bazis-mcp-', suffix='.tmp', delete=False) as stream:
                    temp_path = Path(stream.name)
                    stream.write(replacement)
                    stream.flush()
                    os.fsync(stream.fileno())
                operation = 'restore' if restore else 'apply'
                atomic_json(folder / f'{operation}-journal.json', {'state': 'started', 'stage_id': stage_id,
                            'expected_revision': revision(wanted), 'replacement_revision': revision(replacement)})
                self._guard()
                if revision(path.read_bytes()) != revision(wanted):
                    raise SettingsError('SETTINGS_CHANGED: active file changed before replace')
                os.replace(temp_path, path)
                verified = revision(path.read_bytes()) == revision(replacement)
                if not verified:
                    raise SettingsError('Write outcome uncertain; inspect settings and journal before retrying')
                manifest['state'] = 'restored' if restore else 'applied'
                atomic_json(folder / 'manifest.json', manifest)
                atomic_json(folder / f'{operation}-journal.json', {'state': 'completed', 'stage_id': stage_id})
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)
            lock.unlink(missing_ok=True)
        return {'stage_id': stage_id, 'file_id': manifest['file_id'], 'state': manifest['state'],
                'revision': revision(replacement), 'backup_file': str(folder / 'before.xml'),
                'live_dialog_access': False, 'notice': 'Saved configuration updated. Reopen BAZIS to validate loading.'}

    def result(self, stage_id: str) -> dict:
        folder, manifest = self._stage(stage_id)
        current = revision(self._path(manifest['file_id']).read_bytes())
        return dict(manifest, current_revision=current,
                    current_matches='before' if current == manifest['before_revision'] else
                    'after' if current == manifest['after_revision'] else 'different',
                    journals={p.stem: read_json(p) for p in folder.glob('*-journal.json')})
