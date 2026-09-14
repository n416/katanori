# -*- coding: utf-8 -*-
"""反り対策のリブの線を生成する（v6.1）。python hardware/tools/ribs_gen61.py

🔒 ユーザー 2026-09-14: tools/ribs_gen.py（v5 用）の写し。読む .scad と書く先だけ違う。

case_v6_1.scad の part="ribfree_<板>" が出す 2D（リブの空きを線の半幅だけ縮めた形）を SVG に書き出し、
格子の線（ピッチ RIB_P）との交わりから「幅が丸ごと空いている区間」を取り、RIB_LMIN 以上の区間だけを
hardware/parts/ribs_v61_gen.scad の RIB_SEGS に書く。case_v6_1.scad の rib_2d() がこれを読む。

  seg = [板, 向き(0 = 2D の x に走る / 1 = y に走る), 線の位置, 始点, 終点]   2D の座標は case_v6_1 の flat() と同じ（壁: (Z, Y) ／ ハッチ・フロント: (X, Z)）

🔴 中身・線・板を動かしたら回し直すこと。忘れるとリブが古い空きのまま。
   OpenSCAD の 2D の offset で座標を 100 倍に伸ばして長さを篩う方法は精度が壊れて上に角が出た（2026-09-05）。
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
SCAD = os.path.join(HW, 'case_v6_1.scad')
OUT = os.path.join(HW, 'parts', 'ribs_v61_gen.scad')
TMP = os.path.join(HW, '_tmp_v5')
OPENSCAD = r'C:\Program Files\OpenSCAD (Nightly)\openscad.com'
PLATES = ['lwall', 'rwall', 'hatch', 'front']   # v6.1: ブリッジは無い
RIB_P, RIB_LMIN = 8.0, 4.0     # case_v6_1.scad と同じ値（ピッチ・最短。🔒 ユーザー 2026-09-05「4mm 未満は出さない」）
LO, HI = -200, 200


def svg_polys(path):
    txt = open(path, encoding='utf-8').read()
    d = ' '.join(re.findall(r'<path[^>]*d="([^"]*)"', txt, re.S))
    polys = []
    for sub in re.split(r'\bM\b', d):
        pts = re.findall(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', sub)
        if len(pts) >= 3:
            polys.append([(float(x), -float(y)) for x, y in pts])   # SVG は y が下向き。OpenSCAD は −y で書く
    return polys


def crossings(polys, axis, c):
    """axis 0: 線 y = c と辺の交点の x を返す。axis 1: 線 x = c と辺の交点の y"""
    xs = []
    for poly in polys:
        n = len(poly)
        for i in range(n):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
            a0, b0, a1, b1 = (x0, y0, x1, y1) if axis == 0 else (y0, x0, y1, x1)
            if (b0 <= c) == (b1 <= c):
                continue   # 線をまたがない（端点が線上のときは片側に数える）
            t = (c - b0) / (b1 - b0)
            xs.append(a0 + t * (a1 - a0))
    return sorted(xs)


def segments(polys, k):
    segs = []
    for axis in (0, 1):
        u = LO
        while u <= HI:
            xs = crossings(polys, axis, u)
            for i in range(0, len(xs) - 1, 2):   # 偶奇則: 中に入る区間
                a, b = xs[i], xs[i + 1]
                if b - a >= RIB_LMIN:
                    segs.append((k, axis, u, round(a, 3), round(b, 3)))
            u += RIB_P
    return segs


def main():
    os.makedirs(TMP, exist_ok=True)
    allsegs = []
    for k in PLATES:
        svg = os.path.join(TMP, 'ribfree_%s.svg' % k)
        r = subprocess.run([OPENSCAD, '--backend=manifold', '-D', 'part="ribfree_%s"' % k, '-o', svg, SCAD],
                           capture_output=True, text=True)
        if not os.path.exists(svg):
            print(k, 'SVG が出ない:', r.stderr[-400:]); continue
        polys = svg_polys(svg)
        segs = segments(polys, k)
        allsegs += segs
        print('%-6s 輪郭 %d 本 → 線 %d 本・合計 %.0fmm' % (k, len(polys), len(segs), sum(s[4] - s[3] for s in segs)))
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('// 反り対策のリブの線（自動生成: python hardware/tools/ribs_gen61.py。手で編集しない）\n')
        f.write('// seg = [板, 向き(0 = 2D の x に走る / 1 = y), 線の位置, 始点, 終点]。2D は case_v6_1 の flat() の座標（壁: (Z, Y) ／ ハッチ・フロント: (X, Z)）\n')
        f.write('RIB_SEGS = [\n')
        for s in allsegs:
            f.write('  ["%s", %d, %g, %g, %g],\n' % s)
        f.write('];\n')
    print('wrote', OUT, len(allsegs))


if __name__ == '__main__':
    main()
