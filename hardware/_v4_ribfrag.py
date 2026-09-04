# -*- coding: utf-8 -*-
"""リブの STL を、繋がった塊ごとに分けて大きさを出す。小さすぎる切れ端を見つけるため。
   使い方: python hardware/_v4_ribfrag.py <panel>"""
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
k=sys.argv[1]
T=read_stl('hardware/_ribs_%s.stl'%k)
if len(T)==0:
    print('%s  リブが 1 つも出ていない（空）'%k); sys.exit()
# 頂点を丸めて共有点で繋ぐ union-find
V=np.round(T.reshape(-1,3),3)
uq,inv=np.unique(V,axis=0,return_inverse=True)
par=np.arange(len(uq))
def find(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
def uni(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: par[rb]=ra
f=inv.reshape(-1,3)
for tri in f: uni(tri[0],tri[1]); uni(tri[0],tri[2])
root=np.array([find(i) for i in range(len(uq))])
grp={}
for i,tri in enumerate(f): grp.setdefault(root[tri[0]],[]).append(i)
rows=[]
for r,idx in grp.items():
    S=T[idx]; a,b,c=S[:,0],S[:,1],S[:,2]
    v=float(abs(np.sum(np.einsum('ij,ij->i',a,np.cross(b,c)))/6.0))
    lo=S.reshape(-1,3).min(0); hi=S.reshape(-1,3).max(0); d=hi-lo
    rows.append((v,sorted(d,reverse=True)))
rows.sort(reverse=True)
tot=sum(r[0] for r in rows)
print('%s  リブ %d 塊 / 合計 %.0f mm3'%(k,len(rows),tot))
small=[r for r in rows if r[1][0] < 8.0]
print('  一番長い 5 つ: '+' / '.join('%.0fmm3(長さ%.1f)'%(v,d[0]) for v,d in rows[:5]))
print('  🔴 長さ 8mm 未満の切れ端: %d 個 / %.0f mm3（全体の %.1f%%）'%(len(small),sum(r[0] for r in small),100*sum(r[0] for r in small)/tot))
for v,d in sorted(small,reverse=True)[:6]:
    print('     %.1f mm3   %.1f x %.1f x %.1f'%(v,d[0],d[1],d[2]))
