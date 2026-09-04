# -*- coding: utf-8 -*-
"""ハッチを X 一定で縦に切った断面（Y-Z）を SVG で描く。柱・球・枝・円錐・ラフトの並びを見る。
   使い方: python hardware/_hatch_cone_sec.py [X ...]（既定 11.55 17.18）"""
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
T=read_stl('hardware/stl/v4/v4_hatch.stl')
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
XS=[float(a) for a in sys.argv[1:]] or [11.55, 17.18]
Y0,Y1,DY = 17.0, 36.0, 0.03
S=44.0; H=4.6
out=['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif">'%(
        int((Y1-Y0)*S)+100, len(XS)*int(H*S+62)+16),
     '<rect width="100%" height="100%" fill="#fbfbfb"/>']
for k,x in enumerate(XS):
    oy=k*(H*S+62)+42; base=oy+H*S
    out.append('<text x="10" y="%d" font-size="15" fill="#222">X = %.2f で縦に切った断面（左が電池の口の外・右が奥）</text>'%(oy-16,x))
    out.append('<line x1="70" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#c00" stroke-width="2"/>'%(base,(Y1-Y0)*S+80,base))
    out.append('<text x="8" y="%.1f" font-size="12" fill="#c00">Z=0</text>'%(base+4))
    for zz,lab in ((0.70,'0.7'),(3.00,'3.0')):
        out.append('<line x1="70" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ddd" stroke-width="1"/>'%(base-zz*S,(Y1-Y0)*S+80,base-zz*S))
        out.append('<text x="8" y="%.1f" font-size="12" fill="#888">Z=%s</text>'%(base-zz*S+4,lab))
    y=Y0
    while y<Y1:
        for a,b in spans(x,y):
            out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#3a6ea5"/>'%(
                80+(y-Y0)*S, base-b*S, DY*S+0.6, (b-a)*S))
        y+=DY
out.append('</svg>')
open('hardware/_hatch_cone_sec.svg','w',encoding='utf-8').write('\n'.join(out))
print('書いた: hardware/_hatch_cone_sec.svg  X =', XS)
