# -*- coding: utf-8 -*-
"""刷る向きの STL から支柱の位置を決めて hardware/_v4_props.scad を書き出す。
   🔒 2026-08-27 ユーザー「柱は輪郭に立てる。距離は近似」。つまみの deck_props と同じ形:
      天井の**輪郭**（外周・穴の縁）から 1.3mm の輪を 1 本目に、内側へ 3.0mm ずつ輪を重ねる。
      輪の上は約 3.0mm 間隔。距離は 8 近傍の近似でよい。
   🔴 2026-08-27 に 2 度作り直し、3 度目（この版・1 から書き直し）:
      ① 「深い順に置く」に勝手に置き換えて散らばった詰め物にした（指示違反）
      ② 柱を「真下がプレートまで空いている所」にしか立てられず、下に肉のある区間で
         輪が欠けた（座の左の弧・ユーザーが丸で指摘）。柱は**下の肉の上からも立てる**
      ③ 覆い残りで柱を間引く判定が置いた順に効いて、輪に穴が開いた。判定は置く前に固定する
   使い方: python hardware/_v4_props.py   （素の形は -D PROPS_OFF=true で焼く）
"""
import io, os, subprocess, sys
import numpy as np

OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, '_pf'); os.makedirs(TMP, exist_ok=True)

# ---- 検査と同じ read_stl / zcolumns を**別の名前空間**へ読む ----
# 🔴 exec を自分のグローバルへ流すと、あちらの PITCH = 0.25 がこちらの 3.0 を上書きする
#    （ピッチ 0.25mm ＝ 全セルに柱・ブリッジで 23,917 本の事故）。ns 辞書に隔離する。
_ns = {}
_src = io.open(os.path.join(HERE, '_stl_preflight.py'), encoding='utf-8').read()
exec(_src[:_src.index("for p in sorted(glob.glob(")], _ns)
read_stl = _ns['read_stl']; zcolumns = _ns['zcolumns']

P = 0.25          # レイの間隔
DZ = 0.05         # 層の高さ（PRINT.md §1）
REACH = 2.0       # 支えからこれ以上離れた天井は持たれていない（ピッチ 3.0 の半分＋α）
PROP_D = 2.0      # 柱の径（knob_v5 実績。φ1.4 は薄皮のまま面ごと剥がれた）
MIN_GAP = 0.3     # 柱と輪郭の逃げ
PITCH = 3.0       # 輪の間隔・輪の上の間隔（隣まで 4mm を超えない実績値）
FILL_PITCH = 2.4  # 埋めの最小間隔（隣との隙間 0.4 ＝ 癒着の実績 0.36 の外）
PARTS = ['top', 'hatch', 'bridge', 'strap_a', 'strap_b', 'strap_c', 'seat']   # seat = 充電基板の受け（2026-08-27・D-1 で独立した部品になった）


def bake(part):
    p = os.path.join(TMP, 'bare_%s.stl' % part)
    subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', p,
                    '-D', 'PROPS_OFF=true', '-D', 'part="print_%s"' % part,
                    os.path.join(HERE, 'case_v4.scad')], check=True, capture_output=True)
    return p


def dil(a):
    o = a.copy()
    o[1:, :] |= a[:-1, :]; o[:-1, :] |= a[1:, :]
    o[:, 1:] |= a[:, :-1]; o[:, :-1] |= a[:, 1:]
    return o


def erode8(m):
    o = m.copy()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == dy == 0: continue
            t = np.zeros_like(m)
            xs = slice(max(0, dx), m.shape[0] + min(0, dx)); xd = slice(max(0, -dx), m.shape[0] + min(0, -dx))
            ys = slice(max(0, dy), m.shape[1] + min(0, dy)); yd = slice(max(0, -dy), m.shape[1] + min(0, -dy))
            t[xd, yd] = m[xs, ys]
            o &= t
    return o


out = ['// 🔴 自動生成。手で直さない。作り直しは `python hardware/_v4_props.py`',
       '//    位置は刷る向きの素の STL（PROPS_OFF=true）の天井の輪郭から決めている。',
       'PROP_D2 = 2.0; PROP_TIP2 = 1.2; PROP_NECK2 = 0.8; PROP_BITE2 = 0.3;',
       'module one_prop(x, y, base, h) translate([x, y, base]) {',
       '    cylinder(d = PROP_D2, h = max(0.01, h - base - PROP_NECK2), $fn = 16);',
       '    translate([0, 0, max(0, h - base - PROP_NECK2)])',
       '        cylinder(d = PROP_TIP2, h = min(PROP_NECK2, h - base) + PROP_BITE2, $fn = 12);',
       '}', '']
rep = []
for part in PARTS:
    tris = read_stl(bake(part))
    col, zs, ze, us, vs, nu, nv = zcolumns(tris, P)
    z0 = zs.min(); cell = P * P
    nr = int(round(REACH / P))
    picks = []
    # 🔴 間隔と覆いの帳簿は**層ごと**に取る。全層で 1 つの帳簿にすると、会話ボタンの受け（天井 6.20）の真下に
    #    皿（天井 2.25）の柱が居るだけで「もう近くに柱がある」と間引かれ、6.20 の天井が丸ごと持たれないまま
    #    「残り 0.0」と報告された（2026-08-27）。別の層の柱は別の高さの物で、同じ xy に重なってよい（積み重なるだけ）。
    ps2 = (PITCH / P) ** 2; fs2 = (FILL_PITCH / P) ** 2
    for lay in np.unique(np.round((zs - z0) / DZ).astype(int)):
        if lay <= 0: continue
        h = z0 + lay * DZ; z = h + DZ * 0.5
        O = np.zeros(nu * nv, bool); O[col[(zs <= z) & (ze > z)]] = True
        S = np.zeros(nu * nv, bool); S[col[(zs <= z - DZ) & (ze > z - DZ)]] = True
        Ngf = O & ~S
        if Ngf.sum() * cell < 1.0: continue
        Og = O.reshape(nu, nv); Ng = Ngf.reshape(nu, nv)
        reach = (S & O).reshape(nu, nv)
        for _ in range(nr): reach = dil(reach) & Og
        need = Ng & ~reach
        if need.sum() * cell < 0.5: continue
        # 柱の足元 = その柱の真下にある一番高い肉の上面（無ければプレート 0）
        sel = ze <= h - 0.02
        tmp = np.zeros(nu * nv)
        np.maximum.at(tmp, col[sel], ze[sel])
        basegrid = tmp.reshape(nu, nv)
        # 輪郭からの距離（8 近傍の近似）
        dist = np.zeros((nu, nv), np.int16)
        cur = Ng.copy(); d = 0
        while cur.any():
            d += 1; dist[cur] = d; cur = erode8(cur)
        dmax = dist.max() * P
        # 判定は**置く前に固定**: 「持たれない天井が届く範囲に在るか」を静的な地図で見る
        needD = need.copy()
        for _ in range(nr + int(round(PITCH / P))): needD = dil(needD)
        # 天井の重心（輪を角度順に回るための基準）
        ci, cj = np.argwhere(Ng).mean(axis=0)
        # 🔒 2026-08-27 ユーザー「最も外の輪郭以外にはラフトを貼って」= 手本の deck_props と同じ:
        #    内側の支柱は 0.3mm のラフトに載せて 1 枚で剥がす。プレート直立ちは**外周の輪郭の輪**だけ
        #    （穴の縁の輪は「外周」ではないのでラフト側）。外周かどうかは、天井の外の空白のうち
        #    グリッドの縁とつながっている領域（comp_outer）に近いかで見分ける。
        comp_outer = ~Ng
        edge = np.zeros_like(comp_outer); edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
        seed = comp_outer & edge
        while True:
            nxt = dil(seed) & comp_outer
            if (nxt == seed).all(): break
            seed = nxt
        comp_outer = seed
        ro = int(round((PROP_D / 2 + MIN_GAP) / P)) + 2
        n_ring = n_fill = 0
        placed = []
        r = PROP_D / 2 + MIN_GAP
        while r <= dmax + P:
            band = np.argwhere(Ng & (np.abs(dist * P - r) <= P))
            band = sorted(band.tolist(), key=lambda c: np.arctan2(c[1] - cj, c[0] - ci))
            for i, j in band:
                if not needD[i, j]: continue                       # この辺りの天井は縁が持っている
                if h - basegrid[i, j] < 0.4: continue              # 下の肉がほぼ届いている ＝ 柱は要らない
                if any((i - a) ** 2 + (j - b) ** 2 < ps2 for a, b in placed): continue
                is_outer = (r < PROP_D / 2 + MIN_GAP + P and
                            comp_outer[max(0, i - ro):min(nu, i + ro + 1), max(0, j - ro):min(nv, j + ro + 1)].any())
                on_raft = (not is_outer) and basegrid[i, j] < 0.01
                picks.append((us[i], vs[j], basegrid[i, j], h, on_raft)); placed.append((i, j))
                n_ring += 1
            r += PITCH
        # 覆い残りを埋める（深い所から・間隔 2.4 まで詰めてよい）
        cov = reach.copy()
        for i, j in placed:
            cov[max(0, i - nr):min(nu, i + nr + 1), max(0, j - nr):min(nv, j + nr + 1)] = True
        rem = need & ~cov
        for i, j in sorted(np.argwhere(rem).tolist(), key=lambda c: -dist[c[0], c[1]]):
            if not rem[i, j]: continue
            if h - basegrid[i, j] < 0.4: continue
            if any((i - a) ** 2 + (j - b) ** 2 < fs2 for a, b in placed): continue
            picks.append((us[i], vs[j], basegrid[i, j], h, basegrid[i, j] < 0.01)); placed.append((i, j))
            rem[max(0, i - nr):min(nu, i + nr + 1), max(0, j - nr):min(nv, j + nr + 1)] = False
            n_fill += 1
        rep.append((part, h, need.sum() * cell, n_ring, n_fill, rem.sum() * cell))
    BARE = {'top': 'top_print()', 'hatch': 'hatch_print()',
            'bridge': 'translate([0, 0, -(BAT_Z - BRG_T)]) brg_v4()',
            'strap_a': 'strap_print(STRAP_BANDS[0])', 'strap_b': 'strap_print(STRAP_BANDS[1])',
            'strap_c': 'strap_print(STRAP_BANDS[2])',
            'seat': 'translate([TC4_ZT, 0, -LW_X]) rotate([0, -90, 0]) tc_seat4()'}[part]
    out.append('module props_%s() { %s }' % (part, ' '.join(
        'one_prop(%.2f, %.2f, %.2f, %.2f);' % p[:4] for p in picks)))
    layers = {}
    for x, y, b, h, on_raft in picks:
        if on_raft: layers.setdefault(h, []).append((x, y))
    if layers:
        hulls = ' '.join('hull() { %s }' % ' '.join(
            'translate([%.2f, %.2f]) circle(d = PROP_D2, $fn = 16);' % (x, y) for x, y in pts)
            for pts in layers.values())
        out.append('module raft_%s() difference() {' % part)
        out.append('    linear_extrude(0.3) union() { %s }' % hulls)
        out.append('    // 部品がプレートに着く足の周り 0.5 を空ける（手本のラフト ↔ ピンの隙間 0.4 と同等）')
        out.append('    translate([0, 0, -0.1]) linear_extrude(0.6) offset(r = 0.5) projection(cut = true) translate([0, 0, -0.15]) %s;' % BARE)
        out.append('}')
    else:
        out.append('module raft_%s() {}' % part)
io.open(os.path.join(HERE, '_v4_props.scad'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('%-9s %7s %12s %6s %6s %12s' % ('部品', '天井Z', '要る面積', '輪', '埋め', '残り'))
for r in rep: print('%-9s %7.2f %9.1f mm2 %6d %6d %9.1f mm2' % r)
