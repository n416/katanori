# -*- coding: utf-8 -*-
"""刷る前に STL を機械で検算する（docs/PRINT.md ＋ 記憶 stl-preflight-check）。
  使い方: python hardware/_stl_preflight.py "hardware/_pf/print_*.stl" [薄肉のしきい値 mm]
  見るもの ①底の Z が 0 か ②中身が 1 個か（宙に浮いた欠片が無いか）③しきい値より薄い面
  ③は「平行」（= 本物の薄肉）と「先細り」（= 面取りやツメの先端。不良ではない）を分けて出す。
"""
import glob, os, struct, sys
import numpy as np
from collections import deque

def read_stl(p):
    d=open(p,'rb').read()
    if d[:5]==b'solid' and b'facet' in d[:2000]:
        t=d.decode('ascii','replace').split(); vals=[]; i=0
        while i<len(t):
            if t[i]=='vertex': vals+=[float(t[i+1]),float(t[i+2]),float(t[i+3])]; i+=4
            else: i+=1
        return np.array(vals).reshape(-1,3,3)
    n=struct.unpack('<I',d[80:84])[0]
    arr=np.frombuffer(d[84:84+50*n],dtype=np.uint8).reshape(n,50)
    return arr[:,12:48].copy().view(np.float32).reshape(n,3,3).astype(np.float64)

PITCH=0.25      # レイの間隔
COSMIN=0.75     # 面をかすめただけの当たりを捨てる（法線とレイの向きの内積）
LIM=float(sys.argv[2]) if len(sys.argv)>2 else 0.30

def bodies(tris):
    """中身の数と、それぞれの bbox。頂点を丸めてつなぐ"""
    vid={}; tid=[]
    for t in tris:
        tid.append(tuple(vid.setdefault((round(v[0],4),round(v[1],4),round(v[2],4)),len(vid)) for v in t))
    par=list(range(len(vid)))
    def find(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for a,b,c in tid:
        for u,v in ((a,b),(b,c)):
            ru,rv=find(u),find(v)
            if ru!=rv: par[ru]=rv
    box={}
    for t,ti in zip(tris,tid):
        r=find(ti[0]); m=box.setdefault(r,[1e9]*3+[-1e9]*3)
        for v in t:
            for i in range(3): m[i]=min(m[i],v[i]); m[3+i]=max(m[3+i],v[i])
    return list(box.values())


# ---- ④ 接地面積（PRINT.md §4 の実績）と ⑤ 島 ----
#   実績: base 1709mm2 = 剥がれず・プレートに傷・部品が折れた / frame 585mm2 = 角が欠けた / bridge 513mm2 = 無事
#   🔒 長い部品（おおむね 40mm 超）に逃げ溝を張ってはいけない。蝶番になって破断した（4 枚で確定）。
#      長い部品は犠牲タブ（見本: knob_jig.scad の bridge_print・両端 7 x 8 x 1.2）
GRIP_BAD = 1709.0; GRIP_WARN = 585.0; LONG = 40.0
#   🔴 島（浮いた欠片）だけを見る検査は**縁で繋がった天井を素通りする**。つまみの皿もそれで合格してしまう
#      （2026-08-27 ユーザー指摘）。下向きの天井は「支えからどれだけ離れているか」で見る。
#      実績: 支柱のピッチ 3.0 ＝ 隣まで 4mm を超えない。支えから REACH 以上離れた天井は持たれていない。
#      基準値: knob_v5_deck.stl（支柱入り）は 500mm2 の天井のうち持たれていないのが 19mm2
DZ = 0.05      # 層の高さ（PRINT.md §1）
REACH = 2.0    # 支えからこれ以上離れた天井は持たれていない（ピッチ 3.0 の半分＋α）

def zcolumns(tris, pitch):
    """Z 方向のレイ。柱ごとの (入り, 出) の区間と、格子の形を返す"""
    U=tris[:,:,0]; V=tris[:,:,1]; W=tris[:,:,2]
    us=np.arange(U.min()+pitch*0.5137,U.max(),pitch); vs=np.arange(V.min()+pitch*0.4271,V.max(),pitch)
    nu,nv=len(us),len(vs)
    HR=[];HT=[]
    u0,u1,u2=U[:,0],U[:,1],U[:,2]; v0,v1,v2=V[:,0],V[:,1],V[:,2]
    den=(v1-v2)*(u0-u2)+(u2-u1)*(v0-v2)
    for k in np.nonzero(np.abs(den)>1e-12)[0]:
        au,bu,cu=u0[k],u1[k],u2[k]; av,bv,cv=v0[k],v1[k],v2[k]
        i0=int(np.searchsorted(us,min(au,bu,cu))); i1=int(np.searchsorted(us,max(au,bu,cu)))
        j0=int(np.searchsorted(vs,min(av,bv,cv))); j1=int(np.searchsorted(vs,max(av,bv,cv)))
        if i1<=i0 or j1<=j0: continue
        UU=us[i0:i1][:,None]; VV=vs[j0:j1][None,:]; d=den[k]
        l1=((bv-cv)*(UU-cu)+(cu-bu)*(VV-cv))/d; l2=((cv-av)*(UU-cu)+(au-cu)*(VV-cv))/d; l3=1-l1-l2
        m=(l1>=0)&(l2>=0)&(l3>=0)
        if not m.any(): continue
        w=l1*W[k,0]+l2*W[k,1]+l3*W[k,2]; ii,jj=np.nonzero(m)
        HR.append((ii+i0)*nv+(jj+j0)); HT.append(w[ii,jj])
    r=np.concatenate(HR); t=np.concatenate(HT)
    o=np.lexsort((t,r)); r,t=r[o],t[o]
    st=np.r_[True,r[1:]!=r[:-1]]; grp=np.cumsum(st)-1
    pos=np.arange(len(r))-np.r_[0,np.cumsum(np.bincount(grp))[:-1]][grp]
    keep=(pos%2==0)&np.r_[r[1:]==r[:-1],False]
    i=np.nonzero(keep)[0]
    return r[i], t[i], t[i+1], us, vs, nu, nv

def grip_and_islands(tris, pitch=0.25):
    col,zs,ze,us,vs,nu,nv=zcolumns(tris,pitch)
    z0=zs.min()
    cell=pitch*pitch
    grip=((zs<=z0+DZ*0.5)&(ze>z0+DZ*0.5)).sum()*cell
    long_mm=max(us.max()-us.min(), vs.max()-vs.min())
    isl=[]
    for lay in np.unique(np.round((zs-z0)/DZ).astype(int)):
        if lay<=0: continue
        z=z0+lay*DZ+DZ*0.5
        O=np.zeros(nu*nv,bool); O[col[(zs<=z)&(ze>z)]]=True
        S=np.zeros(nu*nv,bool); S[col[(zs<=z-DZ)&(ze>z-DZ)]]=True
        new=np.nonzero(O&~S)[0]
        if not len(new): continue
        seen=np.zeros(nu*nv,bool)
        for c0 in new:
            if seen[c0]: continue
            q=deque([c0]); seen[c0]=True; comp=[c0]; sup=False
            while q:
                c=q.popleft()
                if S[c]: sup=True; break
                i,j=divmod(c,nv)
                for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
                    ii,jj=i+di,j+dj
                    if 0<=ii<nu and 0<=jj<nv:
                        n2=ii*nv+jj
                        if O[n2] and not seen[n2]: seen[n2]=True; q.append(n2); comp.append(n2)
            if not sup:
                a=np.array(comp); xi,yi=a//nv,a%nv
                if len(comp)*cell>=0.25:
                    isl.append((z0+lay*DZ,len(comp)*cell,us[xi].min(),us[xi].max(),vs[yi].min(),vs[yi].max()))
    # 下向きの天井（縁で繋がっていても、支えから REACH 以上離れていれば持たれていない）
    def dil(a):
        o=a.copy(); o[1:,:]|=a[:-1,:]; o[:-1,:]|=a[1:,:]; o[:,1:]|=a[:,:-1]; o[:,:-1]|=a[:,1:]; return o
    nmax=int(np.ceil(REACH/pitch))+2
    ceil=[]
    for lay in np.unique(np.round((zs-z0)/DZ).astype(int)):
        if lay<=0: continue
        z=z0+lay*DZ+DZ*0.5
        O=np.zeros(nu*nv,bool); O[col[(zs<=z)&(ze>z)]]=True
        S=np.zeros(nu*nv,bool); S[col[(zs<=z-DZ)&(ze>z-DZ)]]=True
        new=O&~S
        if not new.any(): continue
        Og=O.reshape(nu,nv); Ng=new.reshape(nu,nv); reach=(S&O).reshape(nu,nv)
        for _ in range(nmax): reach=dil(reach)&Og
        un=Ng&~reach
        if un.sum()*cell>=0.5:
            xi,yi=np.nonzero(un)
            ceil.append((z0+lay*DZ, un.sum()*cell, Ng.sum()*cell, us[xi].min(),us[xi].max(),vs[yi].min(),vs[yi].max()))
    return grip, long_mm, isl, ceil, ze.max()-z0

def scan(tris, axis):
    u,v=[i for i in range(3) if i!=axis]
    U=tris[:,:,u]; V=tris[:,:,v]; W=tris[:,:,axis]
    nrm=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]); ln=np.linalg.norm(nrm,axis=1); ln[ln==0]=1
    cosf=np.abs(nrm[:,axis]/ln)
    us=np.arange(U.min()+PITCH*0.5137,U.max(),PITCH); vs=np.arange(V.min()+PITCH*0.4271,V.max(),PITCH)
    nv=len(vs)
    HR=[];HT=[];HF=[]
    u0,u1,u2=U[:,0],U[:,1],U[:,2]; v0,v1,v2=V[:,0],V[:,1],V[:,2]
    den=(v1-v2)*(u0-u2)+(u2-u1)*(v0-v2)
    for k in np.nonzero(np.abs(den)>1e-12)[0]:
        au,bu,cu=u0[k],u1[k],u2[k]; av,bv,cv=v0[k],v1[k],v2[k]
        i0=int(np.searchsorted(us,min(au,bu,cu))); i1=int(np.searchsorted(us,max(au,bu,cu)))
        j0=int(np.searchsorted(vs,min(av,bv,cv))); j1=int(np.searchsorted(vs,max(av,bv,cv)))
        if i1<=i0 or j1<=j0: continue
        UU=us[i0:i1][:,None]; VV=vs[j0:j1][None,:]; d=den[k]
        l1=((bv-cv)*(UU-cu)+(cu-bu)*(VV-cv))/d; l2=((cv-av)*(UU-cu)+(au-cu)*(VV-cv))/d; l3=1-l1-l2
        m=(l1>=0)&(l2>=0)&(l3>=0)
        if not m.any(): continue
        w=l1*W[k,0]+l2*W[k,1]+l3*W[k,2]; ii,jj=np.nonzero(m)
        HR.append((ii+i0)*nv+(jj+j0)); HT.append(w[ii,jj]); HF.append(np.full(ii.size,k))
    r=np.concatenate(HR); t=np.concatenate(HT); f=np.concatenate(HF)
    o=np.lexsort((t,r)); r,t,f=r[o],t[o],f[o]
    start=np.r_[True,r[1:]!=r[:-1]]; grp=np.cumsum(start)-1
    pos=np.arange(len(r))-np.r_[0,np.cumsum(np.bincount(grp))[:-1]][grp]
    same=np.r_[r[1:]==r[:-1],False]
    good=(pos%2==0)&same&(cosf[f]>COSMIN)&(np.r_[cosf[f[1:]],0]>COSMIN)
    seg=np.where(good,np.r_[t[1:]-t[:-1],0],np.inf)
    idx=np.nonzero(seg<LIM)[0]
    return [(seg[i],us[r[i]//nv],vs[r[i]%nv],t[i]) for i in idx],u,v


for p in sorted(glob.glob(sys.argv[1])):
    tris=read_stl(p); v=tris.reshape(-1,3)
    bd=bodies(tris)
    z0=v[:,2].min()
    flag=" 🔴 プレートから %.3f 浮いている" % z0 if z0>0.05 else ""
    print("== %-20s 底 Z=%.3f%s  外形 %.2f x %.2f x %.2f  中身 %d 個" % (
        os.path.basename(p), z0, flag, v[:,0].max()-v[:,0].min(), v[:,1].max()-v[:,1].min(), v[:,2].max()-v[:,2].min(), len(bd)))
    if len(bd)>1:
        for m in sorted(bd,key=lambda m:m[2]):
            print("   🔴 欠片  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f" % (m[0],m[3],m[1],m[4],m[2],m[5]))
    grip,long_mm,isl,ceil,hh=grip_and_islands(tris)
    if grip>GRIP_BAD: v="🔴 base.stl（1709・剥がれず/プレート傷/部品折れ）を超えている"
    elif grip>GRIP_WARN: v="⚠ frame（585・角が欠けた）を超えている"
    else: v="✅ bridge（513・無事）の側"
    print("   接地 %.0f mm2  %s" % (grip, v))
    if grip>GRIP_WARN:
        print("      → %s（長辺 %.0fmm）" % ("**犠牲タブ**（逃げ溝は蝶番になって破断する）" if long_mm>LONG else "逃げ溝で 4 割落とせる", long_mm))
    if ceil:
        tot=sum(c[1] for c in ceil)
        print("   🔴 支えの無い天井 %.0f mm2（%d 層）。**縁で繋がっていても持たれていない**（支えから %.1fmm 超）" % (tot,len(ceil),REACH))
        for z,a,t2,x0,x1,y0,y1 in sorted(ceil,key=lambda c:-c[1])[:4]:
            print("      Z %6.2f  %7.2f / %7.2f mm2  X %.1f..%.1f Y %.1f..%.1f" % (z,a,t2,x0,x1,y0,y1))
    else:
        print("   支えの無い天井 なし")
    if grip<40.0:
        print("   🔴 点で立っている（接地 %.0f mm2 < つまみの棒の 1 層 38mm2）。あれは 1 個置きで軸がズレた → **置き方と、一緒に置く相手を決めてから刷る**" % grip)
    print("   島 %d か所（0.25mm2 以上）%s" % (len(isl), "" if not isl else "："))
    for z,a,x0,x1,y0,y1 in sorted(isl,key=lambda f:-f[1])[:4]:
        print("      Z %6.2f  %6.2f mm2  X %.1f..%.1f Y %.1f..%.1f" % (z,a,x0,x1,y0,y1))
    any_=False
    for ax in (0,1,2):
        hits,u,vv=scan(tris,ax)
        if not hits: continue
        pts=np.array([[h[1],h[2]] for h in hits]); th=np.array([h[0] for h in hits]); tt=np.array([h[3] for h in hits])
        used=np.zeros(len(hits),bool)
        while True:
            free=np.nonzero(~used)[0]
            if not len(free): break
            seed=free[np.argmin(th[free])]; cl=[seed]; used[seed]=True; qi=0
            while qi<len(cl):
                c=cl[qi]; qi+=1
                d=np.abs(pts[:,0]-pts[c,0])+np.abs(pts[:,1]-pts[c,1])
                nb=np.nonzero((~used)&(d<0.6)&(np.abs(tt-tt[c])<1.0))[0]
                used[nb]=True; cl+=list(nb)
            cl=np.array(cl)
            area=len(cl)*PITCH*PITCH
            if area<0.35: continue
            mn,me,mx=th[cl].min(),th[cl].mean(),th[cl].max()
            kind="平行" if (mx-mn)<0.06 else ("先細り" if me<(mn+mx)*0.62 else "?")
            o=[i for i in range(3) if i!=ax]
            print("   %6.3f..%.3f mm (mean %.3f) %s [%s向き]  面積 %5.2f mm2  %s %.1f..%.1f  %s %.1f..%.1f  %s=%.2f" % (
                mn,mx,me,kind,"XYZ"[ax],area,"XYZ"[o[0]],pts[cl,0].min(),pts[cl,0].max(),
                "XYZ"[o[1]],pts[cl,1].min(),pts[cl,1].max(),"XYZ"[ax],tt[cl].mean()))
            any_=True
    if not any_: print("   （%.2fmm 未満の面は無し）"%LIM)
