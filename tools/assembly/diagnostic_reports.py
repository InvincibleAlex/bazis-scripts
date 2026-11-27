"""Stable storage for the latest diagnostic reports for each model."""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory


def report_base(output, model):
    if not model or not Path(model).is_absolute():
        raise ValueError('Calea absolută a modelului este necesară pentru salvarea rapoartelor.')
    model_path = Path(model).resolve()
    identity = os.path.normcase(str(model_path))
    key = sha256(identity.encode('utf8')).hexdigest()
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', model_path.stem)[:32].rstrip(' .')
    return Path(output).parent / '@Diagnostic' / f'{stem or "Model"}-{key}'


def write_report(base, suffix, content, *, indent=2):
    target = base.parent / (base.name + suffix)
    target.parent.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix='.raport-', dir=target.parent) as directory:
        staged = Path(directory) / 'report.json'
        staged.write_text(json.dumps(content, ensure_ascii=False, indent=indent), encoding='utf8')
        staged.replace(target)
    return target
