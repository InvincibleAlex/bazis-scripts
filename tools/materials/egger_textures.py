"""Download exact official EGGER CAD textures; optionally link one existing PAL.

No material creation/deletion, guessed decor matches or credential storage.
Downloaded manufacturer assets are not covered by this repository's code license.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import re
import socket
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def official_url(url):
    parsed=urllib.parse.urlsplit(url)
    host=(parsed.hostname or '').lower()
    if parsed.scheme!='https' or not (host=='egger.com' or host.endswith('.egger.com') or host=='egger-cdn.com' or host.endswith('.egger-cdn.com')):
        raise ValueError('Only official EGGER HTTPS resources are allowed')
    return url


def fetch(url,max_bytes):
    official_url(url)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BAZIS-Texture-Importer/1.0'}),timeout=30,context=context) as response:
        official_url(response.url)
        data=response.read(max_bytes+1)
        if len(data)>max_bytes:raise ValueError('Download exceeds size limit')
        return data


def cad_download(html,code,finish):
    block=re.search(r'<egger-decorimagedownloads\b[^>]*>(.*?)</egger-decorimagedownloads>',html,re.S|re.I)
    script=re.search(r'<script\b[^>]*>(.*?)</script>',block[1],re.S|re.I) if block else None
    if not script:raise ValueError('Official CAD download metadata not found')
    items=json.loads(script[1])['data']['downloads']['imageDownloadItems']
    expected=f'{code} {finish}'
    matches=[item for item in items if item.get('code','').strip().upper()==expected and
             ('cad' in item.get('name','').lower() or item.get('fileType')=='Raport') and
             item.get('anonymous') is True and not item.get('awsSignatureRequired')]
    if len(matches)!=1:raise ValueError('No unique public CAD image for exact decor and finish')
    return official_url(matches[0]['url']['url'])


def download(code,finish,texture_root,page_url=None):
    from PIL import Image
    if not re.fullmatch(r'[A-Z]\d{3,5}',code):raise ValueError('Invalid EGGER decor code')
    if not re.fullmatch(r'[A-Z]{1,3}\d{1,3}',finish):raise ValueError('Invalid finish')
    if page_url is None:
        match=re.fullmatch(r'ST(\d+)',finish)
        if not match:raise ValueError('Provide the official page URL for a non-ST finish')
        page_url=f'https://www.egger.com/en/furniture-interior-design/decors/{code}_{match[1]}'
    folder=texture_root/'Egger'/'Official';folder.mkdir(parents=True,exist_ok=True)
    target=folder/f'{code}_{finish}.png';manifest=target.with_suffix('.source.json')
    if target.exists():
        if not manifest.exists():raise FileExistsError('Existing image without source record; refusing overwrite')
        record=json.loads(manifest.read_text(encoding='utf-8'))
        if record.get('code')!=code or record.get('finish')!=finish or record.get('sha256')!=hashlib.sha256(target.read_bytes()).hexdigest():
            raise ValueError('Existing texture/source integrity mismatch')
        return target,record
    html=fetch(page_url,5_000_000).decode('utf-8')
    url=cad_download(html,code,finish);raw=fetch(url,40_000_000)
    with Image.open(BytesIO(raw)) as image:
        image.load()
        if min(image.size)<128:raise ValueError('Image resolution too small for a CAD texture')
        dpi=image.info.get('dpi')
        dpi=[float(value) for value in dpi] if dpi else None
        record={'code':code,'finish':finish,'page':page_url,'image':url,'pixels':list(image.size),
                'dpi':dpi,'downloaded_at':datetime.now().astimezone().isoformat()}
        if dpi and all(value>0 for value in dpi):
            record['repeat_mm']=[round(pixels/resolution*25.4,2) for pixels,resolution in zip(image.size,dpi)]
        temporary=target.with_suffix('.tmp')
        try:
            options={}
            if image.info.get('icc_profile'):options['icc_profile']=image.info['icc_profile']
            if dpi:options['dpi']=tuple(dpi)
            image.convert('RGB').save(temporary,format='PNG',**options)
            record['sha256']=hashlib.sha256(temporary.read_bytes()).hexdigest()
            serialized=json.dumps(record,ensure_ascii=False,indent=2)
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)
    manifest.write_text(serialized,encoding='utf-8')
    return target,record


def link_existing(reader_script,material_id,code,finish,target,texture_root,backup_dir):
    """One explicit ID, exact article, PAL only, no change to physical texture scale."""
    spec=importlib.util.spec_from_file_location('configured_material_reader',reader_script)
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    import firebirdsql
    cfg=json.loads((reader.ROOT/'runtime.json').read_text(encoding='utf-8-sig'))['database']
    connection=firebirdsql.connect(host=socket.gethostbyname(cfg['server']),port=cfg['port'],database=cfg['database'],
        user=cfg.get('user','SYSDBA'),password=reader.password(),charset='UTF8',timeout=10)
    try:
        cur=connection.cursor()
        cur.execute('SELECT M.NAME_MAT,M.ARTICLE,M.HAS_TEXTURE,A.THICKNESS FROM MATERIAL M JOIN MATERIAL_ADVANCE A ON A.ID_M=M.ID_M WHERE M.ID_M=?',(material_id,))
        rows=cur.fetchall()
        if len(rows)!=1:raise ValueError('Material ID is not unique')
        name,article,has_texture,thickness=rows[0]
        if not re.match(r'^PAL\b',name,re.I) or thickness==16:raise ValueError('Only PAL, excluding 16 mm, is allowed')
        if re.sub(r'\s+','',article.upper())!=code+finish:raise ValueError('Material article does not exactly match the downloaded decor and finish')
        cur.execute('SELECT * FROM PARAM_TEXTURE WHERE ID_M=? WITH LOCK',(material_id,))
        columns=[d[0] for d in cur.description];rows=cur.fetchall()
        if len(rows)!=1:raise ValueError('Existing native texture settings are required')
        before=dict(zip(columns,rows[0]));relative=str(target.resolve().relative_to(texture_root.resolve())).replace('/','\\')
        vray=before.get('VRAY')
        if vray:
            tree=ET.fromstring(vray);path=tree.find('MapDiffuse/Path');enabled=tree.find('MapDiffuse/Enabled')
            if path is None or enabled is None:raise ValueError('Unsupported native VRay diffuse settings')
            path.text=relative;enabled.text='Y';vray=ET.tostring(tree,encoding='unicode')
        backup_dir.mkdir(parents=True,exist_ok=True)
        backup=backup_dir/f'texture-{material_id}-{datetime.now():%Y%m%d-%H%M%S-%f}.json'
        backup.write_text(json.dumps({'material_id':material_id,'name':name,'article':article,'has_texture':has_texture,
            'before':before,'after_path':relative},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
        cur.execute('UPDATE PARAM_TEXTURE SET NAME_TEXTURE=?,VRAY=? WHERE ID_M=?',(relative,vray,material_id))
        cur.execute('UPDATE MATERIAL SET HAS_TEXTURE=1 WHERE ID_M=?',(material_id,))
        cur.execute('SELECT NAME_TEXTURE FROM PARAM_TEXTURE WHERE ID_M=?',(material_id,))
        if cur.fetchone()!=(relative,):raise ValueError('Texture link verification failed')
        connection.commit()
        return {'material_id':material_id,'relative_path':relative,'backup':str(backup)}
    except Exception:
        connection.rollback();raise
    finally:connection.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code',required=True);parser.add_argument('--finish',required=True)
    parser.add_argument('--texture-root',required=True,type=Path);parser.add_argument('--page-url')
    parser.add_argument('--link-material',type=int);parser.add_argument('--reader-script',type=Path)
    parser.add_argument('--backup-dir',type=Path)
    args=parser.parse_args()
    if args.link_material is not None and (not args.reader_script or not args.backup_dir):
        parser.error('Linking requires --reader-script and --backup-dir')
    code=args.code.upper();finish=args.finish.upper()
    target,record=download(code,finish,args.texture_root,args.page_url)
    result={'ok':True,'file':str(target),'pixels':record['pixels'],'linked':False}
    if args.link_material is not None:
        result.update(link_existing(args.reader_script,args.link_material,code,finish,target,args.texture_root,args.backup_dir),linked=True)
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
