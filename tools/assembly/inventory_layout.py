"""Compact board list and separate numbered rails around the body drawing."""
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from export_assembly import center,BLUE

def label_positions(parts,point,frame):
    x,y,w,h=frame;ranked=sorted(parts,key=lambda p:(point(center(p))[0],p['label']))
    result=[];split=(len(ranked)+1)//2
    for side,items in ((-1,ranked[:split]),(1,ranked[split:])):
        items=sorted(items,key=lambda p:point(center(p))[1])
        wanted=[point(center(p))[1] for p in items]
        gap=min(20,(h-22)/max(1,len(items)-1));ys=[]
        for yy in wanted:ys.append(max(y+11,yy,ys[-1]+gap if ys else y+11))
        if ys and ys[-1]>y+h-11:
            ys[-1]=y+h-11
            for i in range(len(ys)-2,-1,-1):ys[i]=min(ys[i],ys[i+1]-gap)
        for p,yy in zip(items,ys):result.append((p,(x+10 if side<0 else x+w-10,yy),side))
    return result

def draw_numbered_labels(c,parts,point,frame,color=BLUE):
    c.saveState();c.setStrokeColor(color);c.setLineWidth(.2)
    positions=label_positions(parts,point,frame)
    for p,(x,y),side in positions:
        anchor=point(center(p));c.line(*anchor,x-side*18,y);c.line(x-side*18,y,x-side*8,y)
        c.setFillColor(color);c.circle(x,y,8,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1);c.setFont('Body',7);c.drawCentredString(x,y-2.4,str(p['label']))
    c.restoreState();return positions

def inventory_rows(parts,width,font_size=6.5):
    rows=[]
    for p in parts:
        code=p.get('designation') or p['id'];dims=f"{p['width']:g} × {p['height']:g} × {p['thickness']:g}"
        line=f"{code}   {dims}   {p['name']}"
        lines=simpleSplit(line,'Body',font_size,width-25)
        rows.append((p,lines,max(14,len(lines)*8+5)))
    return rows

def draw_inventory_rows(c,rows,x,y,width,font_size=6.5):
    c.saveState()
    for p,lines,height in rows:
        c.setFillColor(BLUE);c.setFont('Body',font_size);c.drawString(x,y,f"{p['label']:02d}")
        c.setFillColorRGB(.12,.12,.12)
        for i,line in enumerate(lines):c.drawString(x+22,y-i*8,line)
        c.setStrokeColor(HexColor('#d5d9dc'));c.setLineWidth(.2);c.line(x,y-height+5,x+width,y-height+5)
        y-=height
    c.restoreState()
