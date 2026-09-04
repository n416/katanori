# -*- coding: utf-8 -*-
"""ハッチの外面（刷る向きの Z=0.05）に開いている口を数える。大きさと、板の縁までの距離。
   使い方: python hardware/_hatch_openings.py [STL] [高さ]"""
import struct, sys
import numpy as np
from scipy.ndimage import label
def read_stl(p):
    d=open(p,'rb').read()
    if d[:5]==b'solid' and b'facet' in d[:2000]:
        t=d.decode('ascii','replace').split(); v=[]; i=0
        while i<len(t):
            if t[i]=='vertex': v+=[float(t[i+1]),float(t[i+2]),float(t[i+3])]; i+=4
            else: i+=1
        return np.array(v).reshape(-1,3,3)
    n=struct.unpack('<I',d[80:84])[0]
    a=np.frombuffer(d[84:84+50*n],dtype=np.uint8).reshape(n,50)
    return a[:,12:48].copy().view(np.float32).reshape(n,3,3).astype(np.float64)
STL=sys.argv[1] if len(sys.argv)>1 else 'hardware/_hatch_bare.stl'
Z=float(sys.argv[2]) if len(sys.argv)>2 else 0.05
T=read_stl(STL); P=0.05
lo=T.reshape(-1,3).min(0); hi=T.reshape(-1,3).max(0)
xs=np.arange(lo[0]-P,hi[0]+P,P); ys=np.arange(lo[1]-P,hi[1]+P,P)
S=[]
for t in T:
    d=t[:,2]-Z
    if (d>0).all() or (d<0).all(): continue
    pts=[]
    for i in range(3):
        a,b=t[i],t[(i+1)%3]; da,db=d[i],d[(i+1)%3]
        if da==0: pts.append(a[:2])
        elif da*db<0:
            s=da/(da-db); pts.append(a[:2]+s*(b[:2]-a[:2]))
    if len(pts)>=2: S.append((pts[0],pts[1]))
G=np.zeros((len(ys),len(xs)),bool)
y0=np.array([s[0][1] for s in S]); y1=np.array([s[1][1] for s in S])
x0=np.array([s[0][0] for s in S]); x1=np.array([s[1][0] for s in S])
for r,y in enumerate(ys):
    m=((y0<=y)&(y1>y))|((y1<=y)&(y0>y))
    if not m.any(): continue
    t2=(y-y0[m])/(y1[m]-y0[m]); xc=np.sort(x0[m]+t2*(x1[m]-x0[m]))
    for i in range(0,len(xc)-1,2):
        G[r,np.searchsorted(xs,xc[i]):np.searchsorted(xs,xc[i+1])]=True
lab,n=label(~G)
edge=set(np.r_[lab[0,:],lab[-1,:],lab[:,0],lab[:,-1]].tolist())
print('%s  高さ Z=%.2f の面' % (STL, Z))
print('板 X %.2f〜%.2f (%.2f)  Y %.2f〜%.2f (%.2f)  肉 %.1f mm2'
      % (lo[0],hi[0],hi[0]-lo[0],lo[1],hi[1],hi[1]-lo[1],G.sum()*P*P))
rows=[]
for k in range(1,n+1):
    if k in edge: continue
    m=(lab==k); a=m.sum()*P*P
    if a<0.5: continue
    r,c=np.nonzero(m)
    rows.append((a, xs[c.min()],xs[c.max()],ys[r.min()],ys[r.max()]))
for a,ax,bx,ay,by in sorted(rows, reverse=True):
    print('  口 %7.1f mm2   %6.2f x %5.2f   X %6.2f〜%6.2f  Y %6.2f〜%6.2f   縁まで 左 %5.2f / 右 %5.2f / 下 %5.2f / 上 %5.2f'
          % (a, bx-ax, by-ay, ax,bx, ay,by, ax-lo[0], hi[0]-bx, ay-lo[1], hi[1]-by))
