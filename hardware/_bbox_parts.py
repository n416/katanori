# STL を「つながっている塊」ごとに分けて bbox と体積を出す（どの部品に当たっているかを見る用）
import sys, struct, re
import numpy as np
def tris(p):
    d=open(p,'rb').read()
    if d[:5]==b'solid' and b'facet' in d[:400]:
        v=np.array(re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)',d.decode('utf8','ignore')),dtype=float)
        return v.reshape(-1,3,3)
    n=struct.unpack('<I',d[80:84])[0]
    a=np.frombuffer(d[84:84+n*50],dtype=np.uint8).reshape(n,50)
    return a[:,12:48].copy().view('<f4').reshape(n,3,3).astype(np.float64)
def vol(T):
    a,b,c=T[:,0],T[:,1],T[:,2]
    return abs(np.sum(np.einsum('ij,ij->i',a,np.cross(b,c)))/6)
for p in sys.argv[1:]:
    T=tris(p)
    if len(T)==0: print(f"{p}: empty"); continue
    key={}; par=list(range(len(T)))
    def find(i):
        while par[i]!=i: par[i]=par[par[i]]; i=par[i]
        return i
    def uni(i,j):
        a,b=find(i),find(j)
        if a!=b: par[a]=b
    for i,t in enumerate(T):
        for v in t:
            k=tuple(np.round(v,3))
            if k in key: uni(i,key[k])
            else: key[k]=i
    g={}
    for i in range(len(T)): g.setdefault(find(i),[]).append(i)
    print(f"{p}: {len(g)} 塊")
    for n,(r,idx) in enumerate(sorted(g.items(), key=lambda kv:-vol(T[kv[1]]))):
        S=T[idx]; mn=S.reshape(-1,3).min(0); mx=S.reshape(-1,3).max(0)
        print(f"  #{n+1} vol={vol(S):7.2f}mm3  X {mn[0]:7.2f}〜{mx[0]:7.2f}  Y {mn[1]:6.2f}〜{mx[1]:6.2f}  Z {mn[2]:6.2f}〜{mx[2]:6.2f}")
