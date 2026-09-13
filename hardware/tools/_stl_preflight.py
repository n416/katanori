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
SPRUE_W = 2.0   # 🔒 桟の幅（fit_gauge.scad / peg_bore_gauge の作法）。これでつながった物は別と数える
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
    # 🔒 2026-09-01 **1 枚あたりの接地**（つながっている領域の最大）。合計とは別物。
    #   剥がれ・角の欠けは「1 枚の板の大きさ」で効くので、実績 585 / 1709 と比べるのはこちら。
    #   合計（grip）はプレート全体の剥離力なので、LCD 比の判定にはそのまま使う。
    #   ⚠ 基準の数字は変えていない。当てる数字を変えただけ
    #   （ユーザー指摘 2026-09-01「角が欠けるのは、それが 1 枚の大きな板だった場合でしょ？」）
    # 🔒 **桟でしかつながっていない物は別々に数える。**桟は 2.0 × 1.5（fit_gauge.scad 冒頭
    #   「輪と枠を桟（2.0×1.5・ニッパーで切る）で 1 枚につなぐ」／ peg_bore_gauge と同じ）。
    #   ⚠ 新しい数字ではない。既にリポジトリに宣言してある作法の値をそのまま使う。
    #   やり方: 桟の半分（1.0mm）だけ縮めると幅 2.0 の首は消える。残った塊を数え、
    #   同じだけ膨らませて元の接地と重ねたものが「1 枚ぶん」。
    G=np.zeros(nu*nv,bool); G[col[(zs<=z0+DZ*0.5)&(ze>z0+DZ*0.5)]]=True
    A2=G.reshape(nu,nv)
    er=max(1,int(round((SPRUE_W/2.0)/pitch)))
    E=A2.copy()
    for _ in range(er):
        F=E.copy()
        F[1:,:]&=E[:-1,:]; F[:-1,:]&=E[1:,:]; F[:,1:]&=E[:,:-1]; F[:,:-1]&=E[:,1:]
        F[0,:]=False; F[-1,:]=False; F[:,0]=False; F[:,-1]=False
        E=F
    grip_max=0.0; seenE=np.zeros_like(E)
    for i0,j0 in np.argwhere(E):
        if seenE[i0,j0]: continue
        q=deque([(i0,j0)]); seenE[i0,j0]=True; comp=[(i0,j0)]
        while q:
            i,j=q.popleft()
            for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
                ii,jj=i+di,j+dj
                if 0<=ii<nu and 0<=jj<nv and E[ii,jj] and not seenE[ii,jj]:
                    seenE[ii,jj]=True; q.append((ii,jj)); comp.append((ii,jj))
        M=np.zeros_like(E)
        for i,j in comp: M[i,j]=True
        for _ in range(er):
            F=M.copy()
            F[1:,:]|=M[:-1,:]; F[:-1,:]|=M[1:,:]; F[:,1:]|=M[:,:-1]; F[:,:-1]|=M[:,1:]
            M=F
        grip_max=max(grip_max,float((M&A2).sum())*cell)
    if grip_max==0.0: grip_max=grip   # 全部が桟より細い（＝1 枚が極小）ときは合計で見る
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
    return grip, long_mm, isl, ceil, ze.max()-z0, grip_max

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


# ---- 急な立ち上がり（2026-09-02） ----
# 🔒 ユーザー定義: 「一つ前のスライスから次のスライスの最大範囲の差」。
#    ある層で新しく出た肉が、**直下の肉からどれだけ離れているか**。その最大値（mm）。
# 🔴 面積で言ってはいけない。ユーザー「面積で言われると、なんとなく小さいから大丈夫かなと
#    思ってしまう。非常に危険」。実際この機の失敗 3 件は全部「小さい面積」だった
#    （蓋の枠 3.4mm² / 耳 17mm²）。1 層の増分（mm²）でも分かれない
#    （floor は +92mm² で無事、shutter は +14mm² で失敗）。
# ✅ 較正（刷って結果が分かっている v4 の部品・2026-09-02）:
#      無事 … lwall 1.25 / lock 1.25 / rwall 1.75 / **floor 4.00**
#      失敗 … **tub 6.83**（耳が斜めに出た。庇で落ちた唯一の部品）
#      ⇒ 境目は 4.00 と 6.83 の間。しきい値は「無事だった最大」に置いてある。
#   ⚠ 残り 2 件の失敗（蓋の枠 0.10mm・フロントの縁 0.40mm）は立ち上がり 3.26 / 0.35 と小さい。
#     あれは**厚みの方**で落ちている。この 2 つは別の壊れ方なので、別々に見ること。
RISE_WARN = 4.0

# 🔴 2026-09-03 ユーザー「これは急な立ち上がりというよりも、開始点ですね」
#   「差分という意味なら無限大です。立ち上がりの計算なんかおかしいんじゃないですか」。**そのとおりだった。**
#   それまで steep_rise は「新しく出た肉」から**直下の肉ではなく、平面上でいちばん近い肉**までを測っていた
#   （edt(~prev) は前の層の肉ぜんぶが相手なので、隣に立っている無関係な柱までの距離が出る）。
#   ⇒ 下に何も無い島でも 1.95mm のような**有限の値**が出て、しきい値 4.00 を素通りした。
#   実際 CHITUBOX のスライスで、帯 A（Z 18.5）・帯 B/C（Z 24.1）に宙から始まる肉が出ていた。
#   ⇒ **2 つに分ける。**
#     ・開始点（island）… 直下にも真横にも肉が無い所から始まる肉。**距離は ∞ で、しきい値は無い。**
#       これは 0 でなければならない（数と場所で言う。面積は言わない）。
#     ・立ち上がり（rise）… 直下の肉に**つながっている**庇が、その付け根からどれだけ出ているか。
#       こちらは実績 4.00mm と比べてよい（つながっている幅とセットで読める数字）。
def layer_starts(tris, pitch=0.15, dz=0.05):
    """宙から始まる肉（開始点）を全部返す。[(z, x, y, 面積mm²), ...]"""
    try:
        from scipy.ndimage import label, binary_dilation
    except ImportError:
        return None
    col,zs,ze,us,vs,nu,nv = zcolumns(tris, pitch)
    zz = np.arange(dz/2, ze.max(), dz)
    prev=None; out=[]
    for z in zz:
        m=np.zeros(nu*nv, bool); np.logical_or.at(m, col, (zs<=z)&(ze>z))
        g=m.reshape(nu,nv)
        if prev is not None and prev.any():
            new = g & ~prev
            if new.any():
                near = binary_dilation(prev)        # 直下の肉と、その 1 マス隣（＝つながって出た庇）
                lab,n = label(new)
                for k in range(1, n+1):
                    sel = lab==k
                    if (sel & near).any():
                        continue                    # 下の肉につながっている ＝ 庇であって開始点ではない
                    ii,jj = np.nonzero(sel)
                    out.append((float(z), float(us[ii].mean()), float(vs[jj].mean()),
                                float(sel.sum())*pitch*pitch))
        prev=g
    return out


def steep_rise(tris, pitch=0.25, dz=0.05):
    """つながって出た庇の、付け根からの出（mm）。開始点（島）はここに入れない（上の 🔴）"""
    try:
        from scipy.ndimage import distance_transform_edt as edt, label, binary_dilation
    except ImportError:
        return None
    col,zs,ze,us,vs,nu,nv = zcolumns(tris, pitch)
    zz = np.arange(dz/2, ze.max(), dz)
    prev=None; best=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    for z in zz:
        m=np.zeros(nu*nv, bool); np.logical_or.at(m, col, (zs<=z)&(ze>z))
        g=m.reshape(nu,nv)
        if prev is not None and prev.any():
            new = g & ~prev
            if new.any():
                near = binary_dilation(prev)
                lab,n = label(new)
                att = np.zeros_like(new)
                for k in range(1, n+1):
                    sel = lab==k
                    if (sel & near).any():
                        att |= sel                  # つながっている塊だけを測る
                if att.any():
                    d = edt(~prev, sampling=(pitch,pitch))
                    r = float(d[att].max())
                    if r > best[0]:
                        far = att & (d > r - pitch)      # いちばん離れている所（＝立ち上がりの先端）
                        ii,jj = np.nonzero(far)
                        best=(r, float(z), float(att.sum())*pitch*pitch,
                              float(us[ii].min()), float(us[ii].max()),
                              float(vs[jj].min()), float(vs[jj].max()))
        prev=g
    return best


for p in sorted(glob.glob(sys.argv[1])):
    tris=read_stl(p); v=tris.reshape(-1,3)
    bd=bodies(tris)
    z0=v[:,2].min()
    flag=" 🔴 プレートから %.3f 浮いている" % z0 if z0>0.05 else ""
    print("== %-20s 底 Z=%.3f%s  外形 %.2f x %.2f x %.2f  中身 %d 個" % (
        os.path.basename(p), z0, flag, v[:,0].max()-v[:,0].min(), v[:,1].max()-v[:,1].min(), v[:,2].max()-v[:,2].min(), len(bd)))
    # 🔴 2026-09-02 前は「中身が 2 個以上 ＝ 全部 🔴 欠片」だった。**壊れて欠けたのか、
    #   元々別々の部品なのかを区別していない。** 六角ゲージ（独立した 7 マス）が 🔴 欠片 7 と出た
    #   （ユーザー「欠片 7 ってなんですかその検算」）。
    #   ⇒ 分ける材料は持っている: **プレートに着いていない塊が問題**で、着いている塊は別部品。
    if len(bd)>1:
        # ⚠ プレートに着いている塊は**何も言わない**。数は見出しの「中身 N 個」に出ている
        #   （ユーザー「それを注意にする意味が分からない」）。言うのは浮いている物だけ。
        for m in sorted([m for m in bd if m[2]>0.05], key=lambda m:m[2]):
            print("   🔴 浮いている塊  X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f（底が %.2f）"
                  % (m[0],m[3],m[1],m[4],m[2],m[5],m[2]))
    grip,long_mm,isl,ceil,hh,grip_max=grip_and_islands(tris)
    # 🔒 2026-09-03 **接地の警告（585 / 1709）は消した。** ユーザー「この警告意味無いので消してください。
    #   ビルドプレートを磨くようになってから失敗なんて一度もないのです」。
    #   記録とも合う: あの 3 つの実績（base 1709・frame 585・bridge 513）は**傷のあるプレート**で取った値で、
    #   2026-08-06 の研ぎ直しのあと同じ橋が「めっちゃ簡単に取れた。綺麗。」になり、**傷が原因だったことが
    #   独立に裏付けられている**（PRINT.md §4「変わった変数はプレートだけ」）。⇒ 面積は数字だけ残す。
    #   ⚠ 消したのは「剥がれにくさ」の警告だけ。LCD の 30%（土台のたわみ・rules.json の alone_grip_mm2）は別で、
    #     あちらは刷るぞーが見ている。
    print("   接地 %.0f mm2（1 枚あたり %.0f）" % (grip, grip_max))
    # 🔒 2026-09-02 「支えの無い天井 ◯mm²」「島 ◯mm²」の 2 行を**急な立ち上がりに統合した**。
    #   ユーザー「面積は惑わせ、混乱させる元凶だから急な立ち上がりに統合だね。だって無駄過ぎない？」。
    #   🔴 **面積は合否に関係がない。** 落ちるかどうかを決めているのは、肉の厚み（mm）と、
    #   支えからの出（mm）。面積はその 2 つを面で塗りつぶした数字なので、**同じ面積で刷れる形も
    #   刷れない形も作れる。** データが増えても関係が出てくる種類の数字ではない。
    #   ⇒ 面積は「どこにあるか」を指すのにだけ使う。判断には使わない。
    # 🔴 2026-09-03 **開始点は立ち上がりと別に出す**（上の layer_starts の 🔴）。
    #    しきい値は無い。宙から始まる肉は 1 か所でも刷れない。
    st = layer_starts(tris)
    if st is None:
        print("   宙から始まる肉 … scipy が無いので測っていない")
    elif st:
        print("   🔴 **宙から始まる肉（開始点）が %d か所**。しきい値は無い ── 下に何も無いので差は ∞。" % len(st))
        for z, x, y, a in sorted(st, key=lambda r: r[0])[:8]:
            print("      Z %6.2f（層 %4d）  X %7.2f  Y %7.2f  面積 %.2fmm²" % (z, int(round(z / DZ)), x, y, a))
        if len(st) > 8:
            print("      … ほか %d か所" % (len(st) - 8))
        print("      直す先は形か支柱。**ここに柱を立てるか、置き方を変える。**")
    else:
        print("   宙から始まる肉 0 か所")
    rs = steep_rise(tris)
    if rs is None:
        print("   急な立ち上がり … scipy が無いので測っていない")
    elif rs[0] > RISE_WARN:
        print("   🔴 急な立ち上がり **%.2fmm**（Z %.2f・X %.1f..%.1f Y %.1f..%.1f）" % (rs[0],rs[1],rs[3],rs[4],rs[5],rs[6]))
        print("      実績: 無事は floor の %.2fmm まで／tub は 6.83mm で耳が斜めに出た" % RISE_WARN)
        # 🔴 2026-09-02 **この数字だけで直すと外す。** 橋の 5.00mm は「幅 4.0mm の線で壁に
        #   つながった、奥行き 5.0mm の棚」で、欠陥ではなかった（ユーザー「そこは壁自体の
        #   立ち上がりがあるので柱いるんですか？」）。棚の奥行きも、片持ちの出っ張りも、
        #   先端までの距離が同じなら同じ数字になる。⇒ **つながっている幅とセットで読む。**
        #   落ちた tub の耳は「一辺だけで持たれて 7.25mm」。形が違う。
        print("      ⚠ この数字は先端までの距離。**つながっている幅**と一緒に見ること。")
        print("        幅広く壁につながった棚なら、同じ数字でも欠陥ではない（橋 5.00mm がその例）。")
    else:
        print("   急な立ち上がり %.2fmm（Z %.2f）。実績で無事な範囲（≤ %.2fmm）の内側" % (rs[0], rs[1], RISE_WARN))
    if grip<40.0:
        print("   🔴 点で立っている（接地 %.0f mm2 < つまみの棒の 1 層 38mm2）。あれは 1 個置きで軸がズレた → **置き方と、一緒に置く相手を決めてから刷る**" % grip)
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
            # 🔒 2026-09-02 **形を名指しして、mm で言う。面積は出さない。**
            #   ユーザー「毎度毎度これを私が脳内で考えるのがばかばかしいと思わない？…無駄！！」
            #   前は「0.152..0.287 mm 先細り 面積 4.12mm2 …」と数字だけ並べていて、
            #   読む側が CAD を開いて「これは何の形か」を考える仕事が残っていた。
            o=[i for i in range(3) if i!=ax]
            w0,w1=pts[cl,0].min(),pts[cl,0].max(); h0,h1=pts[cl,1].min(),pts[cl,1].max()
            # ⚠ 2026-09-13 調査: **この 0.42 には出どころが無い。**
            #   ・このファイルが作られた fc2bb42（2026-08-27）で最初から書かれていて、
            #     コミット本文にも根拠の記載が無い
            #   ・docs/PRINT.md の 0.42（800 行）は**支柱の「合計/断面」の比**で、肉厚とは無関係
            #   ・PRINT.md §2 の薄壁の下限は **0.3mm（1回目のテスト）**
            #   ⇒ **実測値だと思って使わないこと。**2026-09-13 の筐体 v6 では 3 スレッドが
            #      「0.30 と 0.42 の両方を超える形にする」という運用で揃えた（争わない方が安い）。
            #   ⬜ 由来が分かったら、ここか PRINT.md §2 に書くこと。
            if (mx-mn)<0.06:
                mark = "🔴 " if mn < 0.42 else ""
                what = "%s平たい肉 %.2fmm" % (mark, me)
                note = "（実績の下限 0.42 を割る）" if mn < 0.42 else "（0.42 は超えている）"
            elif me<(mn+mx)*0.62:
                what = "先細りの縁 %.2f→%.2fmm" % (mn, mx)
                note = "（面取りやツメの先端なら不良ではない。立った壁なら 0.42 を割っている）"
            else:
                what = "?（平行でも先細りでもない）%.2f..%.2fmm" % (mn, mx)
                note = ""
            print("   %s  %s %.1f x %s %.1f mm の面  %s %.1f..%.1f / %s %.1f..%.1f（%s=%.2f）%s" % (
                what, "XYZ"[o[0]], w1-w0, "XYZ"[o[1]], h1-h0,
                "XYZ"[o[0]], w0, w1, "XYZ"[o[1]], h0, h1, "XYZ"[ax], tt[cl].mean(), note))
            any_=True
    if not any_: print("   （%.2fmm 未満の面は無し）"%LIM)
