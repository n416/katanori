# -*- coding: utf-8 -*-
"""ハッチの口の中に、柱（φ2.0・垂直・プレートからラフトごと）を降ろせる場所があるかを測る。
   ①肉から MIN_GAP 逃げて Z 0〜天井を貫ける升 ＝ 柱の足場（＝ラフトを置ける所）
   ②天井の各点から、その足場までの横の距離（＝球＋円錐＋枝で渡す量）
   使い方: python hardware/_hatch_post_room.py [STL] [天井のZ]"""
import struct, sys
import numpy as np
from scipy.ndimage import distance_transform_edt as edt, label
from PIL import Image
PROP_D, MIN_GAP = 2.0, 0.3
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
T=read_stl(STL); P=0.10
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
    S=segs(z); G=np.zeros((len(ys),len(xs)),bool)
    if not S: return G
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
ZL=[0.05,0.15,0.35,0.55,0.70,1.00,1.40,1.80,2.20,2.60,2.90]
blk=np.zeros_like(ceil)
for z in ZL: blk |= fill(z)
free=~blk
dfree=edt(free, sampling=P)                      # 空きの升から肉までの距離
stand=free & (dfree >= PROP_D/2 + MIN_GAP)       # φ2.0 の柱を降ろせる升
cell=P*P
print('STL %s  天井 Z=%.2f' % (STL, ZC))
print('  天井 %.1f mm2 ／ 壁（下から続く肉）%.1f mm2' % (ceil.sum()*cell, sup.sum()*cell))
print('  Z 0〜%.2f を貫いて空いている所      %.1f mm2' % (ZC, free.sum()*cell))
print('  そのうち φ2.0 の柱が肉から 0.3 逃げて立てる所 %.1f mm2' % (stand.sum()*cell))
if stand.any():
    dst=edt(~stand, sampling=P)
    dd=dst[ceil]
    print('  天井の各点から、その足場までの横の距離  中央 %.2fmm / 最大 %.2fmm' % (np.median(dd), dd.max()))
    for th in (0.0,1.0,2.0,3.0,4.0,6.0):
        print('    %.1fmm より遠い天井 %6.1f mm2' % (th, (dd>th).sum()*cell))
    lab,n=label(stand)
    sz=[(lab==k).sum()*cell for k in range(1,n+1)]
    sz.sort(reverse=True)
    print('  足場のかたまり %d 個。大きい順 %s mm2' % (n, ' '.join('%.1f'%v for v in sz[:6])))
img=np.full((len(ys),len(xs),3),250,np.uint8)
img[blk]=(215,215,215)
img[sup]=(150,150,150)
img[ceil]=(70,120,210)
img[stand]=(60,190,110)
Image.fromarray(img[::-1]).resize((len(xs)*2,len(ys)*2), Image.NEAREST).save('hardware/_hatch_post_room.png')
print('絵: hardware/_hatch_post_room.png（薄灰=肉・濃灰=壁・青=天井・緑=柱を降ろせる所）')
