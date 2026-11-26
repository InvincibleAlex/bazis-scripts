"""Read BAZIS material designations through Firebird, with a read-only transaction.

stdin: JSON array of {material: 'name\rarticle', thickness_mm: number}.
No SQL or database filenames are accepted from model data.
"""
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local' / 'firebird-python'))


def password():
    portable=ROOT/'runtime.json'
    if portable.exists():
        default=json.loads(portable.read_text(encoding='utf-8-sig')).get('database',{}).get('password')
        if isinstance(default,str) and default:return default
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    credential=Path(os.environ['APPDATA'])/'BazisExport'/'firebird-password.dpapi'
    legacy=Path.home()/'.bazis-mcp'/'firebird-password.dpapi'
    if not credential.exists():credential=legacy
    if not credential.exists():
        raise RuntimeError('CREDENTIAL_SETUP_REQUIRED')
    encrypted = credential.read_bytes()
    buf = ctypes.create_string_buffer(encrypted)
    src = Blob(len(encrypted), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    out = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    if not crypt.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(out)):
        raise RuntimeError('Credential cannot be decrypted for this Windows user')
    try:
        return ctypes.string_at(out.data, out.size).decode('utf-8')
    finally:
        kernel = ctypes.WinDLL('kernel32')
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree(ctypes.cast(out.data, ctypes.c_void_p))


def read_materials(items):
    import firebirdsql
    from firebirdsql.consts import ISOLATION_LEVEL_READ_COMMITED_RO
    portable=ROOT/'runtime.json'
    if portable.exists():
        cfg=json.loads(portable.read_text(encoding='utf-8-sig'))['database']
        server=cfg['server'];database=cfg['database'];port=cfg['port'];user=cfg.get('user','SYSDBA')
    else:
        cfg = ET.parse(Path(os.environ['APPDATA']) / 'Bazis' / 'BaseSettings.xml').getroot().find('Base_Connect')
        if cfg is None:raise RuntimeError('Database configuration unavailable')
        server=cfg.findtext('Server');database=cfg.findtext('DBName');port=14357;user='SYSDBA'
    if server!='RG' or port!=14357:raise RuntimeError('Unverified database endpoint')
    if not database or Path(database).name.lower() != 'baza de date baly_energies  2.0.fdb':
        raise RuntimeError('Unverified database filename in BAZIS settings')
    connection = firebirdsql.connect(host=server, port=port, database=database,
        user=user, password=password(), charset='UTF8', timeout=5,
        isolation_level=ISOLATION_LEVEL_READ_COMMITED_RO)
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT MON$READ_ONLY FROM MON$TRANSACTIONS WHERE MON$TRANSACTION_ID = CURRENT_TRANSACTION')
        if cursor.fetchone() != (1,):
            raise RuntimeError('Read-only transaction not confirmed')
        result = []
        for item in items:
            row = {'sursa': 'Firebird RG:14357 (direct, read-only)', 'desemnare': None}
            full = item.get('material', '')
            if '\r' not in full:
                row['stare'] = 'Articolul materialului nu este disponibil'
            else:
                name, article = full.split('\r', 1)
                cursor.execute('''SELECT FIRST 2 M.ID_M, A.LABEL_EDGE, A.THICKNESS, M.NAME_MAT, M.ARTICLE
                    FROM MATERIAL M JOIN MATERIAL_ADVANCE A ON A.ID_M=M.ID_M
                    WHERE M.ARTICLE=? AND M.NAME_MAT=? AND A.THICKNESS=?''',
                    (article, name, item['thickness_mm']))
                matches = cursor.fetchall()
                # Firebird VARCHAR equality may ignore trailing spaces. Recheck exact
                # identifiers below before accepting the record.
                if len(matches) != 1:
                    row['stare'] = 'Material negasit' if not matches else 'Material ambiguu'
                else:
                    ident, sign, thickness, db_name, db_article = matches[0]
                    if db_name != name or db_article != article:
                        row['stare'] = 'Numele sau articolul nu coincide exact'
                    else:
                        row.update(id_material=ident, desemnare=sign or None,
                            stare='Citit direct din baza' if sign else 'Desemnare goala in baza')
            result.append(row)
        return result
    finally:
        connection.rollback()
        connection.close()


if __name__ == '__main__':
    try:
        # BAZIS execFileSync sends JSON as UTF-8 bytes. Windows pipe defaults
        # otherwise decode Romanian material names with the local code page.
        sys.stdin.reconfigure(encoding='utf-8')
        items = json.load(sys.stdin)
        if not isinstance(items, list) or len(items) > 100000:
            raise ValueError('Invalid request size')
        print(json.dumps({'ok': True, 'materials': read_materials(items)}, ensure_ascii=True))
    except Exception as error:
        # Do not log credentials or connection exception payloads.
        detail=('Accesul la baza nu este configurat pentru acest utilizator. Rulati Configureaza acces baza.cmd din folderul comun Export Tabele.'
            if str(error)=='CREDENTIAL_SETUP_REQUIRED' else 'Citirea Firebird a esuat; verificati parola utilizatorului si conexiunea la RG:14357.')
        print(json.dumps({'ok': False, 'error': detail}))
        sys.exit(1)
