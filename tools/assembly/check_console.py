"""Worker lifecycle test: native failure, PDF failure and successful handoff."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import assembly_console

for mode in ('native_error','pdf_error','success'):
    with tempfile.TemporaryDirectory(prefix='assembly-console-test-') as directory:
        root=Path(directory);job=root/'job';source=root/'input.json';output=root/'output.pdf'
        source.write_text('{}');Path(str(job)+'.log').write_text('Citire placi\n',encoding='utf-8')
        Path(str(job)+'.state').write_text('error' if mode=='native_error' else 'ready')
        calls=[]
        def render(args,**kwargs):
            calls.append(args);assert '--progress' in args
            if mode=='success':output.write_bytes(b'%PDF-test')
            return type('Result',(),{'returncode':1 if mode=='pdf_error' else 0,
                'stdout':json.dumps({'ok':True,'panels':2,'hardware':3,'pages':4})})()
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),patch.object(assembly_console.subprocess,'run',render):
            result=assembly_console.run(job,source,output,wait_seconds=1)
        assert result==(0 if mode=='success' else 1)
        assert ('TERMINAT' in out.getvalue())==(mode=='success')
        assert ('EROARE' in err.getvalue())==(mode!='success')
        assert len(calls)==(0 if mode=='native_error' else 1)
        assert not source.exists() and not Path(str(job)+'.state').exists() and not Path(str(job)+'.log').exists()
print('PASS: console success, native failure, renderer failure, progress flag and temporary job cleanup')
