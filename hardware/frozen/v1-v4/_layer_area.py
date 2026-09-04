# -*- coding: utf-8 -*-
"""刷る向きの STL を 1 層ずつ切って、断面積とその増分（層ごとの跳ね）を出す。
   光造形で効くのは剥離力＝断面積なので、面積の跳ねは「その層で急に強く引かれる」場所を指す。
   使い方: python hardware/_layer_area.py <STL> [層の厚み] [升の大きさ]"""
import struct, sys
import numpy as np
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
STL=sys.argv[1]; DZ=float(sys.argv[2]) if len(sys.argv)>2 else 0.05
P=float(sys.argv[3]) if len(sys.argv)>3 else 0.15
T=read_stl(STL)
lo=T.reshape(-1,3).min(0); hi=T.reshape(-1,3).max(0)
xs=np.arange(lo[0]-P, hi[0]+P, P); ys=np.arange(lo[1]-P, hi[1]+P, P)
def area(z):
    S=[]
    for t in T:
        d=t[:,2]-z
        if (d>0).all() or (d<0).all(): continue
        pts=[]
        for i in range(3):
            a,b=t[i],t[(i+1)%3]; da,db=d[i],d[(i+1)%3]
            if da==0: pts.append(a[:2])
            elif da*db<0:
                s=da/(da-db); pts.append(a[:2]+s*(b[:2]-a[:2]))
        if len(pts)>=2: S.append((pts[0],pts[1]))
    if not S: return 0.0
    y0=np.array([s[0][1] for s in S]); y1=np.array([s[1][1] for s in S])
    x0=np.array([s[0][0] for s in S]); x1=np.array([s[1][0] for s in S])
    n=0
    for y in ys:
        m=((y0<=y)&(y1>y))|((y1<=y)&(y0>y))
        if not m.any(): continue
        t2=(y-y0[m])/(y1[m]-y0[m]); xc=np.sort(x0[m]+t2*(x1[m]-x0[m]))
        for i in range(0,len(xc)-1,2):
            n+=max(0,int(np.searchsorted(xs,xc[i+1]))-int(np.searchsorted(xs,xc[i])))
    return n*P*P
zs=np.arange(lo[2]+DZ*0.5, hi[2], DZ)
A=np.array([area(z) for z in zs])
d=np.r_[A[0], np.diff(A)]
print('%s  層 %.3fmm  升 %.2fmm  層数 %d' % (STL, DZ, P, len(zs)))
print('  断面積 最大 %.1f mm2（Z %.2f）' % (A.max(), zs[A.argmax()]))
print('  層ごとの増分 最大 %+.1f mm2（Z %.2f）／ 減 %+.1f mm2（Z %.2f）' % (
      d.max(), zs[d.argmax()], d.min(), zs[d.argmin()]))
print('  増分の大きい層（上位 8）')
for k in np.argsort(-np.abs(d))[:8]:
    print('    Z %5.2f  断面 %7.1f mm2  増分 %+8.1f mm2' % (zs[k], A[k], d[k]))
