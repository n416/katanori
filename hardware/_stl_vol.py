# -*- coding: utf-8 -*-
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
for f in sys.argv[1:]:
    T=read_stl(f)
    if len(T)==0: print('%s  空（重なり 0）'%f); continue
    v=np.abs(np.einsum('ij,ij->i', T[:,0], np.cross(T[:,1],T[:,2])).sum()/6.0)
    lo=T.reshape(-1,3).min(0); hi=T.reshape(-1,3).max(0)
    print('%s  体積 %.3f mm3  三角 %d  Z %.2f〜%.2f'%(f, v, len(T), lo[2], hi[2]))
