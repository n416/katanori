# -*- coding: utf-8 -*-
"""ハッチを水平に切った断面（輪郭線）を SVG で描く。柱が肉の中に居るのか、口（空)の中に居るのかを見る。
   使い方: python hardware/_hatch_plan_sec.py [高さ Z ...]（既定 0.35 1.50 2.80）"""
import struct, sys
import numpy as np
def read_stl(p):
    d=open(p,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    a=np.frombuffer(d[84:84+50*n],dtype=np.uint8).reshape(n,50)
    return a[:,12:48].copy().view(np.float32).reshape(n,3,3).astype(np.float64)
T=read_stl('hardware/stl/v4/v4_hatch.stl')
ZS=[float(a) for a in sys.argv[1:]] or [0.35,1.50,2.80]
def sec(z):
    segs=[]
    for t in T:
        d=t[:,2]-z
        if (d>0).all() or (d<0).all(): continue
        pts=[]
        for i in range(3):
            a,b=t[i],t[(i+1)%3]; da,db=d[i],d[(i+1)%3]
            if da==0: pts.append(a[:2])
            elif da*db<0:
                s=da/(da-db); pts.append(a[:2]+s*(b[:2]-a[:2]))
        if len(pts)>=2: segs.append((pts[0],pts[1]))
    return segs
lo=np.array([0.0,14.0,0.0]); hi=np.array([68.0,36.0,0.0])   # 電池の口のまわりだけ切り出す
S=11.0; M=24
W=(hi[0]-lo[0])*S+2*M; H=(hi[1]-lo[1])*S+2*M
out=['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif">'%(W,len(ZS)*(H+34)+10),
     '<rect width="100%" height="100%" fill="#fbfbfb"/>']
for k,z in enumerate(ZS):
    oy=k*(H+34)+30
    out.append('<text x="8" y="%.0f" font-size="15" fill="#222">Z = %.2f mm で水平に切った断面（線が肉の縁）</text>'%(oy-8,z))
    d=[]
    for (p,q) in sec(z):
        if min(p[0],q[0])<lo[0] or max(p[0],q[0])>hi[0] or min(p[1],q[1])<lo[1] or max(p[1],q[1])>hi[1]: continue
        d.append('M%.1f %.1fL%.1f %.1f'%(
            M+(p[0]-lo[0])*S, oy+H-2*M-(p[1]-lo[1])*S, M+(q[0]-lo[0])*S, oy+H-2*M-(q[1]-lo[1])*S))
    out.append('<path d="%s" stroke="#3a6ea5" stroke-width="1.1" fill="none"/>'%(''.join(d)))
out.append('</svg>')
open('hardware/_hatch_plan_sec.svg','w',encoding='utf-8').write('\n'.join(out))
print('書いた: hardware/_hatch_plan_sec.svg  Z =', ZS)
