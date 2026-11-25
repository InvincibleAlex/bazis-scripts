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
        assert not source.exists() and not Path(str(job)+'.state').exists() and not Path(str(job)+'.log').exists()
        assert not Path(str(job)+'.opened').exists() and not Path(str(job)+'.output').exists()
print('PASS: console success, native failure, renderer failure, progress flag and temporary job cleanup')
class FakeTTY(io.StringIO):
    def isatty(self):return True
terminal=FakeTTY()
with contextlib.redirect_stdout(terminal):
    console=assembly_console.LiveConsole();console.start();time.sleep(.35);console.write('Etapa noua');console.stop()
assert 'Se lucreaza...' in terminal.getvalue() and 'Etapa noua' in terminal.getvalue()
output=io.StringIO()
with contextlib.redirect_stdout(output):
    console=assembly_console.LiveConsole()
    result=assembly_console.run_renderer([sys.executable,'-c',"import sys;print('Pagina 1 / 2',file=sys.stderr);print('{}')"],console)
assert result.returncode==0 and result.stdout.strip()=='{}' and 'Pagina 1 / 2' in output.getvalue()
print('PASS: loading animation and live renderer stderr preserve the result receipt')
