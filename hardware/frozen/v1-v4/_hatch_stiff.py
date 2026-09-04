# -*- coding: utf-8 -*-
"""長手（X）に曲げるときの弱い所を探す。X を一定にして Y-Z 断面を切り、
   面積と、水平軸まわりの断面二次モーメント I を出す。I が小さい所ほど曲げに弱い。
   使い方: python hardware/_hatch_stiff.py [STL]"""
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
STL=sys.argv[1] if len(sys.argv)>1 else 'hardware/stl/v4/v4_hatch.stl'
T=read_stl(STL); A,B,C=T[:,0],T[:,1],T[:,2]
def spans(x,y):
    v0=B[:,:2]-A[:,:2]; v1=C[:,:2]-A[:,:2]; v2=np.array([x,y])-A[:,:2]
    den=v0[:,0]*v1[:,1]-v1[:,0]*v0[:,1]; ok=np.abs(den)>1e-12
    u=np.zeros(len(T)); w=np.zeros(len(T))
    u[ok]=(v2[ok,0]*v1[ok,1]-v1[ok,0]*v2[ok,1])/den[ok]
    w[ok]=(v0[ok,0]*v2[ok,1]-v2[ok,0]*v0[ok,1])/den[ok]
    m=ok&(u>=0)&(w>=0)&(u+w<=1)
    z=np.sort(A[m,2]+u[m]*(B[m,2]-A[m,2])+w[m]*(C[m,2]-A[m,2]))
    return [(z[i],z[i+1]) for i in range(0,len(z)-1,2) if z[i+1]-z[i]>1e-6]
lo=T.reshape(-1,3).min(0); hi=T.reshape(-1,3).max(0)
DY=0.15; DZ=0.05
ys=np.arange(lo[1]+DY/2, hi[1], DY)
rows=[]
for x in np.arange(lo[0]+0.5, hi[0]-0.5, 0.5):
    zc=[]; ar=0.0
    for y in ys:
        for a,b in spans(x,y):
            n=max(1,int((b-a)/DZ))
            zz=a+(np.arange(n)+0.5)*(b-a)/n
            w=(b-a)/n*DY
            zc.append((zz,w)); ar+=w*n
    if not zc: rows.append((x,0.0,0.0)); continue
    Z=np.concatenate([z for z,_ in zc]); W=np.concatenate([np.full(len(z),w) for z,w in zc])
    zbar=(Z*W).sum()/W.sum()
    I=((Z-zbar)**2*W).sum()
    rows.append((x, W.sum(), I))
rows=[r for r in rows if r[1]>0]
Is=np.array([r[2] for r in rows]); Xs=np.array([r[0] for r in rows])
k=int(np.argmin(Is))
print('%s' % STL)
print('  X %.1f〜%.1f を 0.5mm おきに切った Y-Z 断面' % (Xs[0], Xs[-1]))
print('  断面二次モーメント I  最小 %.1f mm4（X %.1f）／ 中央 %.1f ／ 最大 %.1f mm4' % (
      Is.min(), Xs[k], np.median(Is), Is.max()))
print('  面積 最小 %.1f mm2 ／ 中央 %.1f mm2' % (min(r[1] for r in rows), np.median([r[1] for r in rows])))
print('  I が中央の 1/3 を下回る区間の長さ %.1f mm' % ((Is < np.median(Is)/3).sum()*0.5))
print('  弱い順に 6 か所: %s' % ' '.join('X%.1f(I%.0f)' % (Xs[i], Is[i]) for i in np.argsort(Is)[:6]))
