# -*- coding: utf-8 -*-
"""リブ有り／無しの STL を比べて、増えた体積と外形を出す。
   使い方: python hardware/_v4_ribcheck.py <panel>"""
import sys, struct, numpy as np
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
def vol(T):
    a,b,c=T[:,0],T[:,1],T[:,2]
    return float(np.abs(np.sum(np.einsum('ij,ij->i',a,np.cross(b,c)))/6.0))
k=sys.argv[1]
A=read_stl('hardware/_rib_on_%s.stl'%k); B=read_stl('hardware/_rib_off_%s.stl'%k)
va,vb=vol(A),vol(B)
la,ha=A.reshape(-1,3).min(0),A.reshape(-1,3).max(0)
lb,hb=B.reshape(-1,3).min(0),B.reshape(-1,3).max(0)
d=(ha-la)-(hb-lb)
print('%-6s リブ無し %8.1f mm3 → 有り %8.1f mm3   増 %+7.1f mm3 (%+.1f%%)'%(k,vb,va,va-vb,100*(va-vb)/vb))
print('       外形の差 X %+.3f  Y %+.3f  Z %+.3f  （0 でないと板の外へ出ている）'%(d[0],d[1],d[2]))
