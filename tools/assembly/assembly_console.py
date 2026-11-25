"""Visible export log and independent PDF worker; never accesses the BAZIS model."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import threading
import re

class LiveConsole:
    def __init__(self):
        self.enabled=sys.stdout.isatty();self.lock=threading.RLock();self.done=threading.Event();self.thread=None;self.percent=0
    def update(self,message):
        stages={'Citire model:':5,'Feronerie ':10,'Placa ':10,'Citire terminata:':30,
            'Calcul nativ al gaurilor':35,'Calcul gauri terminat':45,'Pregatire date':50,
            'Date pregatite.':55,'Generare PDF':60,'Calcul ordine':65,'Desen:':70,
            'Inventar':73,'Pregătire placă':76,'Pasul':80,'Salvare raport':99,'TERMINAT |':100}
        for key,value in stages.items():
            if key in message:self.percent=max(self.percent,value)
        match=re.search(r'Finalizare pagina (\d+) / (\d+)',message)
        if match and int(match[2]):self.percent=max(self.percent,min(98,85+int(13*int(match[1])/int(match[2]))))
    def line(self,index):
        filled=self.percent//5
        return '['+'█'*filled+'░'*(20-filled)+f'] {self.percent}% ['+'|/-\\'[index%4]+']'
    def clear(self):
        if self.enabled:sys.stdout.write('\r'+' '*65+'\r');sys.stdout.flush()
    def write(self,message,end='\n',error=False):
        with self.lock:
            self.update(message)
            self.clear();print(message,end=end,file=sys.stderr if error else sys.stdout,flush=True)
    def start(self):
        if not self.enabled:return
        def animate():
            i=0
            while not self.done.wait(.15):
                with self.lock:
                    sys.stdout.write('\r'+self.line(i));sys.stdout.flush();i+=1
        self.thread=threading.Thread(target=animate,daemon=True);self.thread.start()
    def stop(self):
        self.done.set()
        if self.thread:self.thread.join(timeout=2)
        with self.lock:
            self.clear()
            if self.enabled and self.percent==100:print(self.line(0),flush=True)

def run_renderer(args,console):
    child=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1)
    def forward():
        for line in child.stderr:console.write(line.rstrip('\r\n'))
    reader=threading.Thread(target=forward,daemon=True);reader.start()
    output=child.stdout.read();code=child.wait();reader.join()
    child.stdout.close();child.stderr.close()
    return subprocess.CompletedProcess(args,code,output)

def run(job, source, output=None, *, wait_seconds=1800):
    log=Path(str(job)+'.log');state=Path(str(job)+'.state');offset=0
    console=LiveConsole()
    try:
        console.write('BAZIS | Export asamblare\n');console.start()
        Path(str(job)+'.opened').write_text('ready',encoding='utf-8')
        deadline=time.monotonic()+wait_seconds
        while True:
            if log.exists():
                with log.open('r',encoding='utf-8') as stream:
                    stream.seek(offset);chunk=stream.read();offset=stream.tell()
                if chunk:console.write(chunk,end='')
            status=state.read_text(encoding='utf-8') if state.exists() else ''
            if status in ('ready','error','cancelled'):
                # The native reader finishes logging before publishing its state.
                if log.exists():
                    with log.open('r',encoding='utf-8') as stream:
                        stream.seek(offset);chunk=stream.read()
                    if chunk:console.write(chunk,end='')
                if status=='cancelled':console.write('Export anulat.');return 0
                if status!='ready':raise RuntimeError('Citirea modelului a esuat. Vezi mesajul BAZIS de mai sus.')
                break
            if time.monotonic()>deadline:raise TimeoutError('BAZIS nu a finalizat citirea modelului in 30 de minute.')
            time.sleep(.25)
        console.write('\nGenerare PDF in proces separat...')
        if output is None:output=Path(Path(str(job)+'.output').read_text(encoding='utf-8'))
        result=run_renderer([sys.executable,'-u',str(Path(__file__).with_name('export_assembly.py')),
            '--input',str(source),'--output',str(output),'--progress'],console)
        if result.returncode:raise RuntimeError('Generatorul PDF a esuat (cod %s). Vezi eroarea de mai sus.'%result.returncode)
        receipt=json.loads(result.stdout)
        if not receipt.get('ok') or not output.is_file() or not output.stat().st_size:raise RuntimeError('PDF neconfirmat.')
        console.write('\nTERMINAT | %s placi | %s articole feronerie | %s pagini'%(receipt['panels'],receipt['hardware'],receipt['pages']))
        console.write('PDF: '+str(output)+'\nModelul BAZIS nu a fost modificat.')
        return 0
    except Exception as error:
        console.write('\nEROARE: '+str(error),error=True)
        return 1
    finally:
        console.stop()
        for file in (source,log,state,Path(str(job)+'.opened'),Path(str(job)+'.output')):
            try:file.unlink(missing_ok=True)
            except OSError:pass

def main():
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--job',type=Path,required=True);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path)
    args=parser.parse_args();return run(args.job,args.input,args.output)

if __name__=='__main__':sys.exit(main())
