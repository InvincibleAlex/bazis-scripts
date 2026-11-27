"""Collision-aware text placement for one board view, in PDF points."""
import math
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.rl_accel import fp_str
from itertools import combinations

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

    def text_box(self,c,x,y,text,centered=False,secondary_colors=(),secondary_rail=None):
        width=pdfmetrics.stringWidth(str(text),c._fontname,c._fontsize)
        left=x-width/2 if centered else x
        a,b,cc,d,e,f=c._currentMatrix
        bottom=y-2 if not secondary_colors else y-max(2,4+(len(secondary_colors)-1)*2.2)
        if secondary_colors and secondary_rail is not None:bottom=min(bottom,secondary_rail-4-(len(secondary_colors)-1)*2.2)
        points=[(a*px+cc*py+e,b*px+d*py+f) for px,py in [(left,bottom),(left+width,bottom),(left,y+c._fontsize+1),(left+width,y+c._fontsize+1)]]
        return (min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
    def draw(self,c,x,y,text,centered=False,target=None,secondary_colors=(),leader=True,secondary_rail=None,*,avoid_strokes=False,marker=None,marker_anchor=None):
        # Search beyond the initial neighborhood; an annotation is never silently dropped.
        candidates=[(0,0)]
        for radius in range(9,190,9):
            for dx,dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(-1,1),(1,-1),(-1,-1)]:candidates.append((radius*dx,radius*dy))
        def available(box,xx,yy):
            if not avoid_strokes:return self.fits(box)
            if not self.marker_fits(box):return False
            if target is None:return True
            a,b,cc,d,e,f=c._currentMatrix
            def world(x,y):return (a*x+cc*y+e,b*x+d*y+f)
            start=world(*target);end=world(xx,yy-2)
            return not any(self.stroke_hits_box(start,end,old,padding=.3) for old in self.boxes)

        selected=None
        for dx,dy in candidates:
            if secondary_rail is not None and y+dy<secondary_rail+1.5:continue
            box=self.text_box(c,x+dx,y+dy,text,centered,secondary_colors,secondary_rail)
            if available(box,x+dx,y+dy):selected=(x+dx,y+dy,box);break
        if selected is None:
            # Deterministic free-space fallback within this view's reserved annotation region.
            a,b,cc,d,e,f=c._currentMatrix;det=a*d-b*cc
            for yy in range(math.ceil(self.bounds[1]+10),math.floor(self.bounds[3]-10),10):
                for xx in range(math.ceil(self.bounds[0]+10),math.floor(self.bounds[2]-10),10):
                    lx=(d*(xx-e)-cc*(yy-f))/det;ly=(-b*(xx-e)+a*(yy-f))/det
                    if secondary_rail is not None and ly<secondary_rail+1.5:continue
                    box=self.text_box(c,lx,ly,text,centered,secondary_colors,secondary_rail)
                    if available(box,lx,ly):selected=(lx,ly,box);break
                if selected:break
        if selected is None:raise ValueError('Nu există spațiu pentru toate cotele și reperele acestei vederi: '+str(text))
        xx,yy,box=selected;self.reserve(box);self.placements.append((str(text),box))
        line_index=None
        if leader and (target is not None or abs(xx-x)+abs(yy-y)>2):
            tx,ty=target if target is not None else (x,y-2)
            c.saveState();c.setLineWidth(.18);line_index=len(c._code);c.line(tx,ty,xx,yy-2);c.restoreState()
            if avoid_strokes:self.add_stroke(c,(tx,ty),(xx,yy-2))
        if hasattr(self,'markers'):
            if marker:
                self.capture(c,xx,yy,text,marker,marker_anchor or target or (x,y-2),line_index,
                             (tx,ty) if line_index is not None else None)
            else:
                self.fixed_text.append((str(text),self.glyph_bounds(c,xx,yy,text,centered)))
        if centered:c.drawCentredString(xx,yy,str(text))
        else:c.drawString(xx,yy,str(text))
        if secondary_colors:
            width=pdfmetrics.stringWidth(str(text),c._fontname,c._fontsize)
            center=xx if centered else xx+width/2;half=min(3,width*.375)
            a,b,cc,d,e,f=c._currentMatrix
            world=lambda p:(a*p[0]+cc*p[1]+e,b*p[0]+d*p[1]+f)
            c.saveState();c.setLineWidth(.25)
            for i,color in enumerate(secondary_colors):
                y_line=(yy-3.5 if secondary_rail is None else secondary_rail-3.5)-i*2.2;start=(center-half,y_line);end=(center+half,y_line)
                c.setStrokeColor(color);c.line(*start,*end);self.add_stroke(c,start,end)
                self.underlines.append({'text':str(text),'center':world((center,yy)),'start':world(start),'end':world(end)})
            c.restoreState()
        return box

    def start_cleanup(self):
        self.markers=[]
        self.fixed_text=[]
        self.fixed_shapes=[]
        self.cleanup_strokes=[]

    @staticmethod
    def glyph_bounds(c,x,y,text,centered=False):
        width=pdfmetrics.stringWidth(str(text),c._fontname,c._fontsize)
        ascent,descent=pdfmetrics.getAscentDescent(c._fontname,c._fontsize)
        if centered:x-=width/2
        a,b,d,e,tx,ty=c._currentMatrix
        points=[(a*u+d*v+tx,b*u+e*v+ty) for u in (x,x+width) for v in (y+descent,y+ascent)]
        return tuple(f(p[i] for p in points) for f in (min,max) for i in (0,1))

    def capture(self,c,x,y,text,kind,anchor,line_index=None,old_origin=None):
        # Eligible labels are painted in page-space. Rotated dimensional text
        # stays fixed and is measured with its final canvas transform.
        if tuple(c._currentMatrix)!=(1,0,0,1,0,0):
            self.fixed_text.append((str(text),self.glyph_bounds(c,x,y,text)))
            return
        self.markers.append(dict(text=str(text),kind=kind,position=(x,y),box=self.glyph_bounds(c,x,y,text),
                                 index=len(c._code),anchor=anchor,line=line_index,old_origin=old_origin,size=c._fontsize,
                                 color=tuple(getattr(c._fillColorObj, 'rgb', lambda: c._fillColorObj)())))

    @staticmethod
    def _segment_intersects(a,b,c,d):
        def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
        return (all(max(min(a[i],b[i]),min(c[i],d[i]))<=min(max(a[i],b[i]),max(c[i],d[i])) for i in (0,1))
                and cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0)

    def cleanup(self,c,scale=1):
        markers=self.markers
        # No extra gap is imposed on existing text. Candidate positions get
        # the existing annotation margin of 1.5 pt between texts.
        obstacles=self.fixed_text+self.fixed_shapes
        strokes=self.strokes+self.cleanup_strokes
        boxes=[m['box'] for m in markers]
        leaders=[(m['old_origin'],(m['position'][0],m['position'][1]-2)) if m['line'] is not None else None for m in markers]
        initial=[]
        graph={i:set() for i in range(len(markers))}
        hits={}
        for i,m in enumerate(markers):
            hit=[name for name,box in obstacles if self.overlaps(m['box'],box,0)]
            if any(self.stroke_hits_box(a,b,m['box'],padding=.15) for a,b in strokes):
                hit.append('linie sau contur')
            if any(line and j!=i and self.stroke_hits_box(*line,m['box'],padding=.15) for j,line in enumerate(leaders)):
                hit.append('linie de indicație')
            hits[i]=hit
        for i,j in combinations(range(len(markers)),2):
            if self.overlaps(boxes[i],boxes[j],0):
                graph[i].add(j);graph[j].add(i)
        for i in range(len(markers)):
            hits[i].extend(markers[j]['text'] for j in sorted(graph[i]))
            if hits[i]:initial.append(i)
        groups=[]
        pending=set(initial)
        while pending:
            group=[];queue=[min(pending)]
            while queue:
                i=queue.pop()
                if i not in pending:continue
                pending.remove(i);group.append(i);queue.extend(sorted(graph[i],reverse=True))
            groups.append(sorted(group))
        patches={};changes=[];moved=set()
        group_of={i:n for n,group in enumerate(groups,1) for i in group}
        for group_number,group in enumerate(groups,1):
            # Fixed-obstacle collisions must move. In text-only pairs, retaining
            # the first valid original avoids moving both labels.
            for i in sorted(group,key=lambda i:(len(hits[i])==len(graph[i]),i)):
                m=markers[i];original=m['box'];x,y=m['position']
                if not any(self.overlaps(boxes[i],boxes[j],0) for j in graph[i]) and len(hits[i])==len(graph[i]):
                    continue
                found=None
                reach=min(21,3*m['size'])
                offsets=sorted((dx*dx+dy*dy,abs(dy),dy,dx) for dx in range(-2*int(reach/2),2*int(reach/2)+1,2)
                               for dy in range(-2*int(reach/2),2*int(reach/2)+1,2) if 0<dx*dx+dy*dy<=reach*reach)
                for _,__,dy,dx in offsets:
                    box=tuple(v+(dx if n%2==0 else dy) for n,v in enumerate(original))
                    if any((box[j]<self.bounds[j] if j<2 else box[j]>self.bounds[j]) for j in range(4)):continue
                    if any(self.overlaps(box,b,1.5) for j,b in enumerate(boxes) if j!=i):continue
                    if any(self.overlaps(box,b,1.5) for _,b in obstacles):continue
                    if any(self.stroke_hits_box(a,b,box,padding=.15) for a,b in strokes):continue
                    others=[line for j,line in enumerate(leaders) if j!=i and line]
                    if any(self.stroke_hits_box(*line,box,padding=.15) for line in others):continue
                    anchor=m['anchor']
                    # Keep the label on its original side of the anchor.
                    if sum((p-q)*(u-q) for p,q,u in zip((x+dx,y+dy),anchor,(x,y)))<0:continue
                    line=None
                    if m['line'] is not None or math.hypot(dx,dy)>m['size']/2:
                        end=tuple(max(box[j],min(anchor[j],box[j+2])) for j in (0,1))
                        line=(anchor,end)
                        if math.dist(*line)>min(28,4*m['size']):continue
                        if any(self.stroke_hits_box(*line,b,padding=.15) for j,b in enumerate(boxes) if j!=i):continue
                        if any(self.stroke_hits_box(*line,b,padding=.15) for _,b in obstacles):continue
                        if any(self._segment_intersects(*line,*other) for other in others):continue
                        # Connections can leave their own contour/section line
                        # at the anchor. Crossings elsewhere are rejected.
                        if any(self._segment_intersects(*line,a,b) and
                               not self.stroke_hits_box(a,b,(*anchor,*anchor),padding=.3) for a,b in strokes):continue
                    found=(dx,dy,box,line);break
                if found is None:continue
                dx,dy,boxes[i],leaders[i]=found
                index=m['index'];old=f'1 0 0 1 {fp_str(x,y)} Tm'
                if old not in c._code[index]:
                    raise ValueError('Comandă PDF neașteptată pentru reperul '+m['text'])
                new=c._code[index].replace(old,f'1 0 0 1 {fp_str(x+dx,y+dy)} Tm',1)
                if leaders[i]:
                    a,b=leaders[i]
                    leader=f'n {fp_str(*a)} m {fp_str(*b)} l S'
                    if m['line'] is None:new='q .18 w '+fp_str(*m['color'])+' RG '+leader+' Q '+new
                    else:patches[m['line']]=leader
                patches[index]=new
                moved.add(i)
                changes.append(dict(marker=m['text'],kind=m['kind'],group=group_number,collision_with=hits[i],
                    status='moved',original_pt=[x,y],final_pt=[x+dx,y+dy],distance_mm=math.hypot(dx,dy)*scale*25.4/72,
                    leader='adapted' if m['line'] is not None else 'new' if leaders[i] else None,
                    leader_mm=math.dist(*leaders[i])*scale*25.4/72 if leaders[i] else 0,
                    leader_points_pt=leaders[i],verified=True))
        for i in initial:
            if i in moved:continue
            box=boxes[i]
            unresolved=(any(self.overlaps(box,other,0) for j,other in enumerate(boxes) if j!=i)
                        or any(self.overlaps(box,other,0) for _,other in obstacles)
                        or any(self.stroke_hits_box(a,b,box,padding=.15) for a,b in strokes)
                        or any(line and j!=i and self.stroke_hits_box(*line,box,padding=.15) for j,line in enumerate(leaders)))
            changes.append(dict(marker=markers[i]['text'],kind=markers[i]['kind'],group=group_of[i],collision_with=hits[i],
                                status='unresolved' if unresolved else 'resolved_by_neighbor',
                                original_pt=markers[i]['position'],final_pt=markers[i]['position']))
        for index,command in patches.items():c._code[index]=command
        fixed_pairs=sum(self.overlaps(a,b,0) for (_,a),(_,b) in combinations(self.fixed_text,2))
        return dict(markers=len(markers),collision_pairs=sum(map(len,hits.values()))-sum(map(len,graph.values()))//2,
                    groups=len(groups),fixed_text_pairs=fixed_pairs,positions=changes)
