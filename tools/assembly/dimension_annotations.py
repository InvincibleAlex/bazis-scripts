"""Collision-aware text placement for one board view, in PDF points."""
import math
from reportlab.pdfbase import pdfmetrics

class AnnotationLayout:
    def __init__(self,bounds):self.bounds=bounds;self.boxes=[];self.placements=[];self.strokes=[];self.section_marks=[];self.underlines=[]
    @staticmethod
    def overlaps(a,b,gap=1.5):return not(a[2]+gap<b[0] or b[2]+gap<a[0] or a[3]+gap<b[1] or b[3]+gap<a[1])
    def fits(self,box):
        left,bottom,right,top=self.bounds
        return box[0]>=left and box[1]>=bottom and box[2]<=right and box[3]<=top and not any(self.overlaps(box,old) for old in self.boxes)
    def reserve(self,box):self.boxes.append(box)
    def add_stroke(self,c,start,end):
        a,b,cc,d,e,f=c._currentMatrix
        transform=lambda p:(a*p[0]+cc*p[1]+e,b*p[0]+d*p[1]+f)
        self.strokes.append((transform(start),transform(end)))
    @staticmethod
    def stroke_hits_box(start,end,box,padding=1):
        # Liang-Barsky segment clipping against a padded annotation rectangle.
        lo_x,lo_y,hi_x,hi_y=box;lo_x-=padding;lo_y-=padding;hi_x+=padding;hi_y+=padding
        dx=end[0]-start[0];dy=end[1]-start[1];low,high=0.,1.
        for p,q in [(-dx,start[0]-lo_x),(dx,hi_x-start[0]),(-dy,start[1]-lo_y),(dy,hi_y-start[1])]:
            if abs(p)<1e-12:
                if q<0:return False
            elif p<0:low=max(low,q/p)
            else:high=min(high,q/p)
            if low>high:return False
        return True
    def marker_fits(self,box):
        return self.fits(box) and not any(self.stroke_hits_box(a,b,box) for a,b in self.strokes)

    def text_box(self,c,x,y,text,centered=False,secondary_colors=()):
        width=pdfmetrics.stringWidth(str(text),c._fontname,c._fontsize)
        left=x-width/2 if centered else x
        a,b,cc,d,e,f=c._currentMatrix
        bottom=y-2 if not secondary_colors else y-max(2,4+(len(secondary_colors)-1)*2.2)
        points=[(a*px+cc*py+e,b*px+d*py+f) for px,py in [(left,bottom),(left+width,bottom),(left,y+c._fontsize+1),(left+width,y+c._fontsize+1)]]
        return (min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
    def draw(self,c,x,y,text,centered=False,target=None,secondary_colors=()):
        # Search beyond the initial neighborhood; an annotation is never silently dropped.
        candidates=[(0,0)]
        for radius in range(9,190,9):
            for dx,dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(-1,1),(1,-1),(-1,-1)]:candidates.append((radius*dx,radius*dy))
        selected=None
        for dx,dy in candidates:
            box=self.text_box(c,x+dx,y+dy,text,centered,secondary_colors)
            if self.fits(box):selected=(x+dx,y+dy,box);break
        if selected is None:
            # Deterministic free-space fallback within this view's reserved annotation region.
            a,b,cc,d,e,f=c._currentMatrix;det=a*d-b*cc
            for yy in range(math.ceil(self.bounds[1]+10),math.floor(self.bounds[3]-10),10):
                for xx in range(math.ceil(self.bounds[0]+10),math.floor(self.bounds[2]-10),10):
                    lx=(d*(xx-e)-cc*(yy-f))/det;ly=(-b*(xx-e)+a*(yy-f))/det
                    box=self.text_box(c,lx,ly,text,centered,secondary_colors)
                    if self.fits(box):selected=(lx,ly,box);break
                if selected:break
        if selected is None:raise ValueError('Nu există spațiu pentru toate cotele și reperele acestei vederi: '+str(text))
        xx,yy,box=selected;self.reserve(box);self.placements.append((str(text),box))
        if target is not None or abs(xx-x)+abs(yy-y)>2:
            tx,ty=target if target is not None else (x,y-2)
            c.saveState();c.setLineWidth(.18);c.line(tx,ty,xx,yy-2);c.restoreState()
        if centered:c.drawCentredString(xx,yy,str(text))
        else:c.drawString(xx,yy,str(text))
        if secondary_colors:
            width=pdfmetrics.stringWidth(str(text),c._fontname,c._fontsize)
            center=xx if centered else xx+width/2;half=min(3,width*.375)
            a,b,cc,d,e,f=c._currentMatrix
            world=lambda p:(a*p[0]+cc*p[1]+e,b*p[0]+d*p[1]+f)
            c.saveState();c.setLineWidth(.25)
            for i,color in enumerate(secondary_colors):
                y_line=yy-3.5-i*2.2;start=(center-half,y_line);end=(center+half,y_line)
                c.setStrokeColor(color);c.line(*start,*end);self.add_stroke(c,start,end)
                self.underlines.append({'text':str(text),'center':world((center,yy)),'start':world(start),'end':world(end)})
            c.restoreState()
        return box
