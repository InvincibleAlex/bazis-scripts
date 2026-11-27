from export_performance import measured
"""Depth-test vector line fragments against opaque board faces."""
import math
import numpy as np

def depth(p):
    from export_assembly import VIEW_Y,VIEW_X
    sy,cy=math.sin(VIEW_Y),math.cos(VIEW_Y);sx,cx=math.sin(VIEW_X),math.cos(VIEW_X)
    return -sy*cx*p[0]+sx*p[1]+cy*cx*p[2]

def board_faces(p,offset):
    if p.get('faces'):
        return [[[v[i]+offset[i] for i in range(3)] for v in face] for face in p['faces']]
    b=p['bounds'];frame=p.get('frame')
    if frame:
        origin=frame['origin'];axes=frame['axes']
        vertices=[v for edge in p.get('edges',[]) for v in edge]
        if vertices:
            coords=[[sum((v[j]-origin[j])*a[j] for j in range(3)) for a in axes] for v in vertices]
            lo=[min(v[i] for v in coords) for i in range(3)];hi=[max(v[i] for v in coords) for i in range(3)]
            def point(v):return [origin[j]+sum(v[i]*axes[i][j] for i in range(3))+offset[j] for j in range(3)]
        else:frame=None
    if not frame:
        lo=b['min'];hi=b['max']
        def point(v):return [v[i]+offset[i] for i in range(3)]
    vertices=[point([hi[i] if n&(1<<i) else lo[i] for i in range(3)]) for n in range(8)]
    return [[vertices[i] for i in indices] for indices in [(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]]

class DepthMask:
    def __init__(self,frame,point,scale,depth_function=None):
        self.depth=depth_function or depth
        self.x,self.y,w,h=frame;self.r=2;self.point=point;self.tolerance=.6/max(scale,1e-9)+.05
        self.buffer=np.full((math.ceil(h*self.r)+2,math.ceil(w*self.r)+2),-np.inf,dtype=np.float32)
    @measured('vizibilitate_DepthMask_polygon')
    def polygon(self,vertices,holes=()):
        screen=np.array([self.point(v) for v in vertices]);z=np.array([self.depth(v) for v in vertices])
        pix=(screen-np.array([self.x,self.y]))*self.r
        x0=max(0,math.floor(pix[:,0].min()));x1=min(self.buffer.shape[1],math.ceil(pix[:,0].max())+1)
        y0=max(0,math.floor(pix[:,1].min()));y1=min(self.buffer.shape[0],math.ceil(pix[:,1].max())+1)
        if x1<=x0 or y1<=y0:return
        a=np.column_stack((pix,np.ones(len(pix))))
        coeff,_,rank,_=np.linalg.lstsq(a,z,rcond=None)
        if rank<3:return
        xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
        inside=np.zeros(xx.shape,dtype=bool)
        for i in range(len(pix)):
            p,q=pix[i],pix[(i+1)%len(pix)]
            if abs(q[1]-p[1])<1e-10:continue
            inside^=((p[1]>yy)!=(q[1]>yy))&(xx<(q[0]-p[0])*(yy-p[1])/(q[1]-p[1])+p[0])
        for hole in holes:
            loop=(np.array([self.point(v) for v in hole])-np.array([self.x,self.y]))*self.r
            cutout=np.zeros(xx.shape,dtype=bool)
            for i,p in enumerate(loop):
                q=loop[(i+1)%len(loop)]
                if abs(q[1]-p[1])<1e-10:continue
                cutout^=((p[1]>yy)!=(q[1]>yy))&(xx<(q[0]-p[0])*(yy-p[1])/(q[1]-p[1])+p[0])
            inside&=~cutout
        depths=coeff[0]*xx+coeff[1]*yy+coeff[2]
        buf=self.buffer[y0:y1,x0:x1];np.maximum(buf,np.where(inside,depths,-np.inf),out=buf)
    @measured('vizibilitate_DepthMask_segments')
    def segments(self,a,b):
        aa=np.array(self.point(a));bb=np.array(self.point(b));n=max(2,math.ceil(np.linalg.norm(bb-aa)*self.r*2))
        ts=np.linspace(0,1,n);points=aa[None,:]+ts[:,None]*(bb-aa)[None,:]
        pix=np.floor((points-np.array([self.x,self.y]))*self.r).astype(int)
        valid=(pix[:,0]>=0)&(pix[:,1]>=0)&(pix[:,0]<self.buffer.shape[1])&(pix[:,1]<self.buffer.shape[0])
        surface=np.full(n,-np.inf);surface[valid]=self.buffer[pix[valid,1],pix[valid,0]]
        z=self.depth(a)+ts*(self.depth(b)-self.depth(a));visible=z>=surface-self.tolerance
        indices=np.flatnonzero(np.diff(np.r_[False,visible,False]));result=[]
        for first,last in zip(indices[::2],indices[1::2]):
            lo=max(0,first-.5)/(n-1);hi=min(n-1,last-.5)/(n-1)
            if hi>lo:result.append(([a[i]+lo*(b[i]-a[i]) for i in range(3)],[a[i]+hi*(b[i]-a[i]) for i in range(3)]))
        return result


class VectorDepthMask:
    """Clip projected edges against the actual face boundaries and depth planes."""
    def __init__(self, point):
        self.point=point
        self.faces=[]

    @measured('vizibilitate_VectorDepthMask_polygon')
    def polygon(self, vertices, holes=()):
        outer=[self.point(v) for v in vertices]
        if len(outer)<3:return
        x,y=outer[0]
        matrix=[[u-x,v-y] for u,v in outer[1:]]
        z=depth(vertices[0])
        slope,_,rank,_=np.linalg.lstsq(matrix,[depth(v)-z for v in vertices[1:]],rcond=None)
        if rank<2:return
        loops=[outer]+[[self.point(v) for v in hole] for hole in holes]
        bounds=(min(u for u,v in outer),min(v for u,v in outer),max(u for u,v in outer),max(v for u,v in outer))
        self.faces.append((bounds,loops,x,y,z,*map(float,slope)))

    @staticmethod
    def contains(loop,x,y):
        inside=False
        for (ax,ay),(bx,by) in zip(loop,loop[1:]+loop[:1]):
            if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
        return inside

    @measured('vizibilitate_VectorDepthMask_segments')
    def segments(self,a,b):
        ax,ay=self.point(a);bx,by=self.point(b)
        dx,dy=bx-ax,by-ay
        if math.hypot(dx,dy)<1e-8:return []
        za,zb=depth(a),depth(b)
        xmin,xmax=sorted((ax,bx));ymin,ymax=sorted((ay,by))
        hidden=[]
        for (left,bottom,right,top),loops,x,y,z,sx,sy in self.faces:
            if right<xmin or left>xmax or top<ymin or bottom>ymax:continue
            delta=z+sx*(ax-x)+sy*(ay-y)-za-.05
            change=sx*dx+sy*dy-(zb-za)
            if max(delta,delta+change)<=0:continue
            breaks=[0.,1.]
            if change and 0<-delta/change<1:breaks.append(-delta/change)
            for loop in loops:
                for (ux,uy),(vx,vy) in zip(loop,loop[1:]+loop[:1]):
                    ex,ey=vx-ux,vy-uy
                    det=dx*ey-dy*ex
                    if abs(det)<1e-10:continue
                    px,py=ux-ax,uy-ay
                    t=(px*ey-py*ex)/det
                    cross=(px*dy-py*dx)/det
                    if 0<t<1 and 0<=cross<=1:breaks.append(t)
            breaks.sort()
            for start,end in zip(breaks,breaks[1:]):
                if end-start<1e-8:continue
                t=(start+end)/2
                if delta+change*t<=0:continue
                px,py=ax+t*dx,ay+t*dy
                if self.contains(loops[0],px,py) and not any(self.contains(hole,px,py) for hole in loops[1:]):
                    hidden.append((start,end))
        result=[]
        cursor=0.
        def at(t):return [u+(v-u)*t for u,v in zip(a,b)]
        for start,end in sorted(hidden):
            if start>cursor+1e-7:result.append((at(cursor),at(start)))
            cursor=max(cursor,end)
        if cursor<1-1e-7:result.append((at(cursor),b))
        return result
