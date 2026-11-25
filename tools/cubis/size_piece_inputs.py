"""Size exported piece inputs only; retain template formulas and other sheets."""
import copy
import math
import re
import xml.etree.ElementTree as ET

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
def number(column):
    value=0
    for c in column:value=value*26+ord(c)-64
    return value

def validate_styles(styles):
    root=ET.fromstring(styles)
    for name in ('cellStyleXfs','cellXfs'):
        records=root.find('{'+NS+'}'+name)
        if records is None:continue
        if int(records.get('count',len(records)))!=len(records):raise ValueError('Invalid style count: '+name)
        order={'alignment':0,'protection':1,'extLst':2}
        for record in records:
            tags=[child.tag.rsplit('}',1)[-1] for child in record]
            ranks=[order.get(tag,-1) for tag in tags]
            if -1 in ranks or ranks!=sorted(ranks) or len(tags)!=len(set(tags)):
                raise ValueError('Invalid Excel CT_Xf child order: '+str(tags))

def size_inputs(sheet,styles,first,last,columns,material,notes,resize_columns=True):
    styles_root=ET.fromstring(styles);xfs=styles_root.find('{'+NS+'}cellXfs');added=[];cache={}
    def style(index,wrap):
        key=(index,wrap)
        if key not in cache:
            xf=copy.deepcopy(xfs[index]);alignment=xf.find('{'+NS+'}alignment')
            if alignment is None:
                alignment=ET.Element('{'+NS+'}alignment')
                # CT_Xf requires alignment BEFORE protection and extLst.
                insert_at=next((i for i,child in enumerate(xf) if child.tag.rsplit('}',1)[-1] in ('protection','extLst')),len(xf))
                xf.insert(insert_at,alignment)
            alignment.set('wrapText','1' if wrap else '0');xf.set('applyAlignment','1')
            cache[key]=len(xfs)+len(added);added.append(ET.tostring(xf,encoding='unicode').replace(' xmlns="'+NS+'"',''))
        return cache[key]
    root=ET.fromstring(sheet);values={}
    for row in root.findall('{'+NS+'}sheetData/{'+NS+'}row'):
        r=int(row.get('r'))
        if not first<=r<=last:continue
        for cell in row:
            col=re.match('[A-Z]+',cell.get('r',''))
            if not col or col[0] not in columns:continue
            inline=cell.find('{'+NS+'}is');v=cell.find('{'+NS+'}v')
            values[(r,col[0])]=''.join(inline.itertext()) if inline is not None else (v.text or '') if v is not None else ''
    widths={col:min(60 if col==notes else 52,max(30 if col==notes else 9,max((max(map(len,v.splitlines()),default=0) for (r,c),v in values.items() if c==col),default=0)+2)) for col in columns}
    if not resize_columns:
        for column in columns:
            spec=next((c for c in root.findall('{'+NS+'}cols/{'+NS+'}col') if int(c.get('min'))<=number(column)<=int(c.get('max'))),None)
            widths[column]=float(spec.get('width',9)) if spec is not None else 9
    for r in range(first,last+1):
        pattern=r'(<row\b(?=[^>]*\br="'+str(r)+r'")[^>]*>)(.*?)(</row>)'
        match=re.search(pattern,sheet,re.S)
        if not match:continue
        body=match[2]
        for col in columns:
            address=col+str(r);pattern_cell=r'<c\b(?=[^>]*\br="'+address+r'")[^>]*?(?:/>|>.*?</c>)'
            cell=re.search(pattern_cell,body,re.S)
            if cell:
                xml=cell[0];existing=re.search(r'\bs="(\d+)"',xml);index=int(existing[1]) if existing else 0
                xml=re.sub(r'\s+s="\d+"','',xml,count=1)
                xml=xml.replace('<c ','<c s="'+str(style(index,col==material))+'" ',1)
                body=body[:cell.start()]+xml+body[cell.end():]
            elif col==notes:
                at=len(body)
                for other in re.finditer(r'<c\b[^>]*\br="([A-Z]+)\d+"',body):
                    if number(other[1])>number(col):at=other.start();break
                body=body[:at]+'<c r="'+address+'" s="'+str(style(0,False))+'"/>'+body[at:]
        # Observation length never influences row height; it remains one line.
        text=values.get((r,material),'');lines=sum(max(1,math.ceil(len(line)/max(1,widths[material]-2))) for line in text.split('\n'))
        height=max(15,min(60,lines*15));opening=re.sub(r'\s+(ht|customHeight)="[^"]*"','',match[1]);opening=opening[:-1]+' ht="'+str(height)+'" customHeight="1">'
        sheet=sheet[:match.start()]+opening+body+match[3]+sheet[match.end():]
    found=re.search(r'<cols\b[^>]*>.*?</cols>',sheet,re.S)
    old=ET.fromstring('<root xmlns="'+NS+'">'+found[0]+'</root>')[0] if found else []
    specs={}
    for item in old:
        for i in range(int(item.get('min')),int(item.get('max'))+1):specs[i]=dict(item.attrib,min=str(i),max=str(i))
    for col,width in widths.items():
        i=number(col);specs.setdefault(i,{'min':str(i),'max':str(i)})
        specs[i].update(width=str(width),customWidth='1',bestFit='1')
    cols='<cols>'+''.join(ET.tostring(ET.Element('col',specs[i]),encoding='unicode') for i in sorted(specs))+'</cols>'
    if resize_columns:
        sheet=sheet[:found.start()]+cols+sheet[found.end():] if found else sheet.replace('<sheetData>',cols+'<sheetData>',1)
    if added:
        styles=styles.replace('</cellXfs>',''.join(added)+'</cellXfs>',1)
        styles=re.sub(r'(<cellXfs\b[^>]*\bcount=")\d+("[^>]*>)',lambda m:m[1]+str(len(xfs)+len(added))+m[2],styles,count=1)
    validate_styles(styles)
    return sheet,styles
