"""Visible export log and independent PDF worker; never accesses the BAZIS model."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

def run(job, source, output, *, wait_seconds=1800):
    log=Path(str(job)+'.log');state=Path(str(job)+'.state');offset=0
    try:
        print('BAZIS | Export asamblare\n',flush=True)
        deadline=time.monotonic()+wait_seconds
        while True:
            if log.exists():
                with log.open('r',encoding='utf-8') as stream:
                    stream.seek(offset);chunk=stream.read();offset=stream.tell()
                if chunk:print(chunk,end='',flush=True)
            status=state.read_text(encoding='utf-8') if state.exists() else ''
            if status in ('ready','error'):
                # The native reader finishes logging before publishing its state.
                if log.exists():
                    with log.open('r',encoding='utf-8') as stream:
                        stream.seek(offset);chunk=stream.read()
                    if chunk:print(chunk,end='',flush=True)
                if status!='ready':raise RuntimeError('Citirea modelului a esuat. Vezi mesajul BAZIS de mai sus.')
                break
            if time.monotonic()>deadline:raise TimeoutError('BAZIS nu a finalizat citirea modelului in 30 de minute.')
            time.sleep(.25)
        print('\nGenerare PDF in proces separat...',flush=True)
        result=subprocess.run([sys.executable,'-u',str(Path(__file__).with_name('export_assembly.py')),
            '--input',str(source),'--output',str(output),'--progress'],stdout=subprocess.PIPE,text=True,encoding='utf-8')
        if result.returncode:raise RuntimeError('Generatorul PDF a esuat (cod %s). Vezi eroarea de mai sus.'%result.returncode)
        receipt=json.loads(result.stdout)
        if not receipt.get('ok') or not output.is_file() or not output.stat().st_size:raise RuntimeError('PDF neconfirmat.')
        print('\nTERMINAT | %s placi | %s articole feronerie | %s pagini'%(receipt['panels'],receipt['hardware'],receipt['pages']),flush=True)
        print('PDF: '+str(output)+'\nModelul BAZIS nu a fost modificat. Poti inchide terminalul.',flush=True)
        return 0
    except Exception as error:
        print('\nEROARE: '+str(error)+'\nTerminalul ramane deschis pentru verificare.',file=sys.stderr,flush=True)
        return 1
    finally:
        for file in (source,log,state):
            try:file.unlink(missing_ok=True)
            except OSError:pass

def main():
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--job',type=Path,required=True);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();return run(args.job,args.input,args.output)

if __name__=='__main__':sys.exit(main())
