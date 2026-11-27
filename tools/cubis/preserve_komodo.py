"""Extend blank Komodo rows, then merge authored inputs preserving native parts."""
import sys,json,re,copy,zipfile,subprocess
from pathlib import Path
template,authored,manifest,out=map(Path,sys.argv[1:])
data=json.loads(manifest.read_text(encoding='utf-8'));last=max(49,19+len(data['rows']))
extended=manifest.with_suffix('.template.xlsx')
with zipfile.ZipFile(template) as z:
 text=z.read('xl/worksheets/sheet1.xml').decode()
 if last>49:
  row=re.search(r'<row\b(?=[^>]*\br="21")[^>]*>.*?</row>',text,re.S)[0]
  additions=''
  for n in range(50,last+1):
   clone=row.replace('r="21"',f'r="{n}"')
   clone=re.sub(r'r="([A-K])21"',lambda m:f'r="{m[1]}{n}"',clone)
   additions+=clone
  text=text.replace('</sheetData>',additions+'</sheetData>')
  text=text.replace('ref="A2:K49"',f'ref="A2:K{last}"')
 text=text.replace('sqref="F20:F43"',f'sqref="F20:F{last}"')
 with zipfile.ZipFile(extended,'w',zipfile.ZIP_DEFLATED) as w:
  for info in z.infolist():w.writestr(copy.copy(info),text.encode() if info.filename=='xl/worksheets/sheet1.xml' else z.read(info.filename))
try:
 subprocess.run([sys.executable,str(Path(__file__).with_name('preserve_template.py')),str(extended),str(authored),str(manifest),str(out)],check=True)
finally:extended.unlink(missing_ok=True)
