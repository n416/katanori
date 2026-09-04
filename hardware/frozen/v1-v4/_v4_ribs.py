# -*- coding: utf-8 -*-
"""リブの線を生成して _v4_ribs_gen.scad を書く（_v4_props.py と同じ型）。
   ① OpenSCAD に「内面の空き」を焼かせる（_v4_ribspace.scad の ribfree_<k>）
   ② その断面で、リブの幅ぜんぶが空いている連続区間だけを拾う
   ③ RIB_MIN より短い区間は捨てる  ⇒ 薄片・切れ端は構造上出ない
   使い方: python hardware/_v4_ribs.py"""
import math, os, struct, subprocess, sys
import numpy as np

OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = ['lwall', 'rwall', 'hatch']   # front は板厚 2.8 で買ったのでリブ無し（_v4_ribs.scad の has_rib）
PITCH, W, MIN_L, P = 8.0, 1.6, 8.0, 0.25
END_CLR = 0.3   # リブの端を皮から逃がす量（格子の目 0.25 の丸めを吸う）
# 板ごとの [厚み軸(0=X,1=Y), 内向きの符号, 面内の軸名]  ※ _v4_ribs.scad の rib_p と同じ並び
AX = {'lwall': (0, +1, ('Y','Z')), 'rwall': (0, -1, ('Y','Z')),
      'hatch': (1, -1, ('X','Z')), 'front': (1, +1, ('X','Z'))}

def read_stl(p):
    d = open(p, 'rb').read()
    if d[:5] == b'solid' and b'facet' in d[:2000]:
        t = d.decode('ascii', 'replace').split(); v = []; i = 0
        while i < len(t):
            if t[i] == 'vertex': v += [float(t[i+1]), float(t[i+2]), float(t[i+3])]; i += 4
            else: i += 1
        return np.array(v).reshape(-1, 3, 3)
    n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(d[84:84+50*n], dtype=np.uint8).reshape(n, 50)
    return a[:, 12:48].copy().view(np.float32).reshape(n, 3, 3).astype(np.float64)

def slice_mask(T, axis, val, us, vs):
    o = [a for a in range(3) if a != axis]; d = T[:, :, axis] - val; segs = []
    for t, dd in zip(T, d):
        if (dd > 0).all() or (dd < 0).all(): continue
        pts = []
        for i in range(3):
            a, b = t[i], t[(i+1) % 3]; da, db = dd[i], dd[(i+1) % 3]
            if da == 0: pts.append(a[o])
            elif da*db < 0:
                s = da/(da-db); pts.append(a[o] + s*(b[o]-a[o]))
        if len(pts) >= 2: segs.append((pts[0], pts[1]))
    G = np.zeros((len(vs), len(us)), bool)
    if not segs: return G
    u0 = np.array([s[0][0] for s in segs]); u1 = np.array([s[1][0] for s in segs])
    v0 = np.array([s[0][1] for s in segs]); v1 = np.array([s[1][1] for s in segs])
    for r, v in enumerate(vs):
        m = ((v0 <= v) & (v1 > v)) | ((v1 <= v) & (v0 > v))
        if not m.any(): continue
        tt = (v - v0[m])/(v1[m]-v0[m]); uc = np.sort(u0[m] + tt*(u1[m]-u0[m]))
        for i in range(0, len(uc)-1, 2):
            G[r, np.searchsorted(us, uc[i]):np.searchsorted(us, uc[i+1])] = True
    return G

def runs(G, L, C, minl):
    """C 方向に PITCH おきに線を置き、幅 W ぜんぶ空いている連続区間を返す [(c, a, b)]

    🔴 2026-09-04 ここで 2 つ取りこぼしていた（リブが皮に 0.7mm3 食い込んだ）:
      ① 線の中心を C の格子に**乗せていなかった**ので、幅の判定が実効 ±0.75 になり 0.05 足りなかった
      ② 区間の端を格子の目のまま返していたので、端が最大 1 マス（0.25mm）はみ出した
    ⇒ 中心は格子へ丸め、幅は 1 マス余分に見て、端は END_CLR だけ内へ詰める。"""
    out = []
    half = int(math.ceil(W/2/P)) + 1          # ① 幅は 1 マス余分に見る
    ends = int(math.ceil(END_CLR/P))          # ② 端を詰めるマス数
    c0 = C[0] + PITCH/2
    while c0 < C[-1]:
        i = int(round((c0 - C[0])/P))
        if half <= i < len(C)-half:
            c = float(C[i])                   # ① 線の中心は格子に乗せる
            band = G[i-half:i+half+1].all(axis=0); s = None
            for j, b in enumerate(list(band) + [False]):
                if b and s is None: s = j
                elif not b and s is not None:
                    a2, b2 = s + ends, j - 1 - ends
                    if b2 > a2 and (b2-a2)*P >= minl:
                        out.append((round(c,3), round(float(L[a2]),3), round(float(L[b2]),3)))
                    s = None
        c0 += PITCH
    return out

segs = []; report = []
for k in PANELS:
    stl = os.path.join(HERE, '_rf_ribfree_%s.stl' % k)
    r = subprocess.run([OPENSCAD, '--backend=manifold', '-D', 'part="ribfree_%s"' % k,
                        '-o', stl, os.path.join(HERE, '_v4_ribspace.scad')],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if not os.path.exists(stl):
        print('%s: 空きが焼けなかった\n%s' % (k, r.stderr[-500:])); sys.exit(1)
    T = read_stl(stl)
    if len(T) == 0:
        report.append('%-6s 空きが空（リブ 0 本）' % k); continue
    axis, sgn, names = AX[k]
    lo = T.reshape(-1,3).min(0); hi = T.reshape(-1,3).max(0)
    o = [a for a in range(3) if a != axis]
    us = np.arange(lo[o[0]], hi[o[0]], P); vs = np.arange(lo[o[1]], hi[o[1]], P)
    # 🔴 帯を 1 枚だけ切ってはいけない。手前だけ塞がっている物（壁に寄り添う線・薄い棚）を
    #    奥の 1 枚は見逃す。2026-09-04、これで当たりが 1.1 → 106.5mm3 に増えた。
    #    ⇒ 深さ方向に NCUT 枚切って、**全部で空いている所だけ**を空きとする。
    NCUT = 8
    cuts = np.linspace(lo[axis]+0.05, hi[axis]-0.05, NCUT)
    G = np.ones((len(vs), len(us)), bool)
    for c in cuts: G &= slice_mask(T, axis, float(c), us, vs)
    n = 0; tot = 0.0
    for d, (Gd, L, C) in enumerate([(G, us, vs), (G.T, vs, us)]):
        for c, a, b in runs(Gd, L, C, MIN_L):
            segs.append((k, d, c, a, b)); n += 1; tot += b-a
    report.append('%-6s %2d 本 / %6.1f mm （空き %.0f mm2）' % (k, n, tot, G.sum()*P*P))
    os.remove(stl)

out = ['// 🔴 自動生成 — `python hardware/_v4_ribs.py`。手で直さない。',
       '// 内面の空きから切り出したリブの線。幅ぜんぶが空いている・%.0fmm 以上 の区間だけ。' % MIN_L,
       '// 中身（innards4）を動かしたら生成し直す。形は docs/CASE-V4-OPEN.md「反り対策のリブ」。',
       '//']
for line in report: out.append('//   ' + line)
out += ['', '// [板, 向き(0=面内の第1軸に走る / 1=第2軸), 線の位置, 始点, 終点]', 'RIB_SEGS = [']
for s in segs:
    out.append('    ["%s", %d, %7.3f, %7.3f, %7.3f],' % s)
out += ['];', '']
open(os.path.join(HERE, '_v4_ribs_gen.scad'), 'w', encoding='utf-8').write('\n'.join(out))
print('\n'.join(report))
print('=> _v4_ribs_gen.scad に %d 本' % len(segs))
