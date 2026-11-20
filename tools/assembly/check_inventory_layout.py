from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from inventory_layout import label_positions,inventory_rows
pdfmetrics.registerFont(TTFont('Body','C:/Windows/Fonts/arial.ttf'))
parts=[{'id':str(i),'label':i+1,'designation':f'00.01.{i:03d}','name':'Orizontală','width':1327,'height':430,'thickness':18,
        'bounds':{'min':[0,i%3,0],'max':[100,i%3+18,20]}} for i in range(32)]
labels=label_positions(parts,lambda p:(p[0],p[1]),(0,0,360,440))
assert len(labels)==32
for i,(p,(x,y),side) in enumerate(labels):
    assert 8<=x<=352 and 8<=y<=432
    for _,(xx,yy),_ in labels[i+1:]:assert abs(x-xx)>=16 or abs(y-yy)>=16
for p,lines,height in inventory_rows(parts,400):
    text=' '.join(lines);assert text.index('1327')<text.index('Orizontală');assert height>=14
print('PASS: 32 external numbered circles do not overlap; compact rows retain dimensions before names')
