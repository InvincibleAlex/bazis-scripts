"""Worker lifecycle test: native failure, PDF failure and successful handoff."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import sys
import time
from unittest.mock import patch
import assembly_console

for mode in ('native_error','pdf_error','success','cancelled','deferred_output'):
    with tempfile.TemporaryDirectory(prefix='assembly-console-test-') as directory:
        root=Path(directory);job=root/'job';source=root/'input.json';output=root/'output.pdf'
        source.write_text('{}');Path(str(job)+'.log').write_text('Citire placi\n',encoding='utf-8')
        Path(str(job)+'.state').write_text('error' if mode=='native_error' else 'cancelled' if mode=='cancelled' else 'ready')
        if mode=='deferred_output':Path(str(job)+'.output').write_text(str(output),encoding='utf-8')
        calls=[]
        def render(args,console):
            calls.append(args);assert '--progress' in args
            output.with_suffix('.assembly.json').write_text('debug report')
            if mode in ('success','deferred_output'):output.write_bytes(b'%PDF-test')
            return type('Result',(),{'returncode':1 if mode=='pdf_error' else 0,
                'stdout':json.dumps({'ok':True,'panels':2,'hardware':3,'pages':4})})()
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),patch.object(assembly_console,'run_renderer',render):
            result=assembly_console.run(job,source,None if mode=='deferred_output' else output,wait_seconds=1)
        assert result==(0 if mode in ('success','cancelled','deferred_output') else 1)
        assert ('TERMINAT' in out.getvalue())==(mode in ('success','deferred_output'))
        assert ('EROARE' in err.getvalue())==(mode in ('native_error','pdf_error'))
        assert len(calls)==(0 if mode in ('native_error','cancelled') else 1)
        cleaned=mode in ('success','deferred_output')
        assert source.exists()!=cleaned and Path(str(job)+'.state').exists()!=cleaned and Path(str(job)+'.log').exists()!=cleaned
        assert Path(str(job)+'.opened').exists()!=cleaned
        if cleaned:assert not Path(str(job)+'.output').exists()
        if calls:assert output.with_suffix('.assembly.json').exists()!=cleaned
print('PASS: console success, native failure, renderer failure, progress flag and temporary job cleanup')
class FakeTTY(io.StringIO):
    def isatty(self):return True
terminal=FakeTTY()
with contextlib.redirect_stdout(terminal):
    console=assembly_console.LiveConsole();console.start();time.sleep(.35);console.write('Etapa noua');console.stop()
assert '0% [' in terminal.getvalue() and 'Etapa noua' in terminal.getvalue()
console=assembly_console.LiveConsole();console.update('Generare PDF in proces separat...')
assert console.line(3)=='['+'█'*12+'░'*8+'] 60% [\\]'
console.update('Feronerie 50');assert console.percent==60
console.update('Finalizare pagina 5 / 10');assert console.percent==91
console.update('TERMINAT | 10 pagini');assert console.percent==100
output=io.StringIO()
with contextlib.redirect_stdout(output):
    console=assembly_console.LiveConsole()
    result=assembly_console.run_renderer([sys.executable,'-c',"import sys;print('Pagina 1 / 2',file=sys.stderr);print('{}')"],console)
assert result.returncode==0 and result.stdout.strip()=='{}' and 'Pagina 1 / 2' in output.getvalue()
print('PASS: loading animation and live renderer stderr preserve the result receipt')
