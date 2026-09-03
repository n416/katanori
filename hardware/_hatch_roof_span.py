# -*- coding: utf-8 -*-
"""ハッチの鞘の屋根（刷る向きの Z=3.00 の天井）が、壁から何 mm 張り出しているかを測る。
   柱の要否を「面積」ではなく「張り出し」で見るための道具。素の部品（柱なし）を読む。
   使い方: python hardware/_hatch_roof_span.py [STL] [天井のZ]"""
import struct, sys
import numpy as np
from scipy.ndimage import distance_transform_edt as edt
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
ZC=float(sys.argv[2]) if len(sys.argv)>2 else 3.00
T=read_stl(STL)
P=0.10
lo=T.reshape(-1,3).min(0); hi=T.reshape(-1,3).max(0)
xs=np.arange(lo[0]-P, hi[0]+P, P); ys=np.arange(lo[1]-P, hi[1]+P, P)
def segs(z):
    out=[]
    for t in T:
        d=t[:,2]-z
        if (d>0).all() or (d<0).all(): continue
        pts=[]
        for i in range(3):
            a,b=t[i],t[(i+1)%3]; da,db=d[i],d[(i+1)%3]
            if da==0: pts.append(a[:2])
            elif da*db<0:
                s=da/(da-db); pts.append(a[:2]+s*(b[:2]-a[:2]))
        if len(pts)>=2: out.append((pts[0],pts[1]))
    return out
def fill(z):
    """z の高さで肉の中か（偶奇で塗る）"""
    S=segs(z); G=np.zeros((len(ys),len(xs)),bool)
    y0=np.array([s[0][1] for s in S]); y1=np.array([s[1][1] for s in S])
    x0=np.array([s[0][0] for s in S]); x1=np.array([s[1][0] for s in S])
    for r,y in enumerate(ys):
        m=((y0<=y)&(y1>y))|((y1<=y)&(y0>y))
        if not m.any(): continue
        t=(y-y0[m])/(y1[m]-y0[m]); xc=np.sort(x0[m]+t*(x1[m]-x0[m]))
        for i in range(0,len(xc)-1,2):
            a=np.searchsorted(xs,xc[i]); b=np.searchsorted(xs,xc[i+1])
            G[r,a:b]=True
    return G
A=fill(ZC+0.05); B=fill(ZC-0.05)
ceil=A&~B; sup=A&B
cell=P*P
d=edt(~sup, sampling=P)
dd=d[ceil]
print('STL: %s   天井 Z=%.2f' % (STL, ZC))
print('  天井（下に肉が無い面）  %.1f mm2' % (ceil.sum()*cell))
print('  壁（下から続く肉）      %.1f mm2' % (sup.sum()*cell))
if dd.size:
    print('  壁からの張り出し  最大 %.2fmm / 中央 %.2fmm / 平均 %.2fmm' % (dd.max(), np.median(dd), dd.mean()))
    for th in (0.5,1.0,1.5,2.0,2.5,3.0,4.0):
        print('    %.1fmm より遠い天井 %6.1f mm2' % (th, (dd>th).sum()*cell))

# 絵にする（青＝壁から近い天井 / 赤＝遠い天井 / 灰＝壁（下から続く肉））
from PIL import Image
img=np.full((len(ys),len(xs),3),250,np.uint8)
img[sup]=(150,150,150)
dn=np.clip(d/6.0,0,1)
sel=np.argwhere(ceil)
for r,c in sel:
    t=dn[r,c]; img[r,c]=(int(40+215*t), int(110-60*t), int(200-150*t))
im=Image.fromarray(img[::-1]).resize((len(xs)*2,len(ys)*2), Image.NEAREST)
im.save('hardware/_hatch_roof_span.png')
print('絵: hardware/_hatch_roof_span.png（灰=壁・青=壁に近い天井・赤=遠い天井）')
