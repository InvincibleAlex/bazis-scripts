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
    def __init__(self,frame,point,scale):
        self.x,self.y,w,h=frame;self.r=2;self.point=point;self.tolerance=.6/max(scale,1e-9)+.05
        self.buffer=np.full((math.ceil(h*self.r)+2,math.ceil(w*self.r)+2),-np.inf,dtype=np.float32)
    def polygon(self,vertices):
        screen=np.array([self.point(v) for v in vertices]);z=np.array([depth(v) for v in vertices])
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
        depths=coeff[0]*xx+coeff[1]*yy+coeff[2]
        buf=self.buffer[y0:y1,x0:x1];np.maximum(buf,np.where(inside,depths,-np.inf),out=buf)
    def segments(self,a,b):
        aa=np.array(self.point(a));bb=np.array(self.point(b));n=max(2,math.ceil(np.linalg.norm(bb-aa)*self.r*2))
        ts=np.linspace(0,1,n);points=aa[None,:]+ts[:,None]*(bb-aa)[None,:]
        pix=np.floor((points-np.array([self.x,self.y]))*self.r).astype(int)
        valid=(pix[:,0]>=0)&(pix[:,1]>=0)&(pix[:,0]<self.buffer.shape[1])&(pix[:,1]<self.buffer.shape[0])
        surface=np.full(n,-np.inf);surface[valid]=self.buffer[pix[valid,1],pix[valid,0]]
        z=depth(a)+ts*(depth(b)-depth(a));visible=z>=surface-self.tolerance
        indices=np.flatnonzero(np.diff(np.r_[False,visible,False]));result=[]
        for first,last in zip(indices[::2],indices[1::2]):
            lo=max(0,first-.5)/(n-1);hi=min(n-1,last-.5)/(n-1)
            if hi>lo:result.append(([a[i]+lo*(b[i]-a[i]) for i in range(3)],[a[i]+hi*(b[i]-a[i]) for i in range(3)]))
        return result
