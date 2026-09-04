# -*- coding: utf-8 -*-
"""ハッチの柱の列（y=22.11）の断面を SVG で描く。上=直す前 / 下=直した後。
   直す前の STL は `git show HEAD:hardware/stl/v4/v4_hatch.stl > hardware/_hatch_old.stl` で出す（2026-09-03 の回）。"""
import struct
import numpy as np
def read_stl(p):
    d=open(p,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    a=np.frombuffer(d[84:84+50*n],dtype=np.uint8).reshape(n,50)
    return a[:,12:48].copy().view(np.float32).reshape(n,3,3).astype(np.float64)
def maker(T):
    A,B,C=T[:,0],T[:,1],T[:,2]
    def spans(x,y):
        v0=B[:,:2]-A[:,:2]; v1=C[:,:2]-A[:,:2]; v2=np.array([x,y])-A[:,:2]
        den=v0[:,0]*v1[:,1]-v1[:,0]*v0[:,1]; ok=np.abs(den)>1e-12
        u=np.zeros(len(T)); w=np.zeros(len(T))
        u[ok]=(v2[ok,0]*v1[ok,1]-v1[ok,0]*v2[ok,1])/den[ok]
        w[ok]=(v0[ok,0]*v2[ok,1]-v2[ok,0]*v0[ok,1])/den[ok]
        m=ok&(u>=0)&(w>=0)&(u+w<=1)
        z=np.sort(A[m,2]+u[m]*(B[m,2]-A[m,2])+w[m]*(C[m,2]-A[m,2]))
        return [(z[i],z[i+1]) for i in range(0,len(z)-1,2) if z[i+1]-z[i]>1e-6]
    return spans
X0,X1,DX = 3.0, 34.0, 0.04
Y = 22.11
S = 34.0     # mm あたりの px
rows=[('直す前（HEAD の v4_hatch.stl）','hardware/_hatch_old.stl'),
      ('直した後（今の v4_hatch.stl）','hardware/stl/v4/v4_hatch.stl')]
H=7.2
out=['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif">'%(int((X1-X0)*S)+90, int(2*(H*S+58))+20)]
out.append('<rect width="100%" height="100%" fill="#fbfbfb"/>')
for k,(title,path) in enumerate(rows):
    sp=maker(read_stl(path))
    oy=k*(H*S+58)+40
    out.append('<text x="10" y="%d" font-size="15" fill="#222">%s  ／ 断面 y=%.2f・柱の列</text>'%(oy-14,title,Y))
    base=oy+H*S
    out.append('<line x1="60" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#c00" stroke-width="2"/>'%(base,(X1-X0)*S+70,base))
    out.append('<text x="6" y="%.1f" font-size="12" fill="#c00">Z=0</text>'%(base+4))
    out.append('<text x="6" y="%.1f" font-size="12" fill="#888">Z=3</text>'%(base-3.0*S+4))
    out.append('<line x1="60" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ddd" stroke-width="1"/>'%(base-3.0*S,(X1-X0)*S+70,base-3.0*S))
    x=X0
    while x<X1:
        for a,b in sp(x,Y):
            out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#3a6ea5"/>'%(
                70+(x-X0)*S, base-b*S, DX*S+0.6, (b-a)*S))
        x+=DX
out.append('</svg>')
open('hardware/_hatch_props_sec.svg','w',encoding='utf-8').write('\n'.join(out))
print('書いた: hardware/_hatch_props_sec.svg')
