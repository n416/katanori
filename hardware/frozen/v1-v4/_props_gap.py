# -*- coding: utf-8 -*-
"""支え同士の隙間を数える。_v4_props.scad の one_cone / one_prop を読み、
   柱・枝・円錐を「線分＋半径」として、別の支えとの表面どうしの最短距離を出す。
   基準: GAP 0.4（癒着しない・実績 0.36 の外）。使い方: python hardware/_props_gap.py [部品名]"""
import re, sys
import numpy as np
PART = sys.argv[1] if len(sys.argv) > 1 else 'hatch'
GAP = 0.4
src = open('hardware/_v4_props.scad', encoding='utf-8').read()
line = [l for l in src.split('\n') if l.startswith('module props_%s(' % PART)][0]
D = dict(re.findall(r'(PROP_D2|PROP_TIP2|HEAD_D2|HEAD_L2|PROP_BITE2) = ([\d.]+)', src))
PD, PT, HD, HL = float(D['PROP_D2']), float(D['PROP_TIP2']), float(D['HEAD_D2']), float(D['HEAD_L2'])
sup = []
for a in re.findall(r'one_cone\(([^)]*)\)', line):
    cx, cy, h, px, py, top = [float(v) for v in a.split(',')]
    sup.append([((px, py, 0.3), (px, py, top), PD / 2),            # 柱
                ((px, py, top), (cx, cy, h - HL), HD / 2),          # 球＋枝
                ((cx, cy, h - HL), (cx, cy, h), HD / 2)])           # 円錐（太い端で見る＝厳しめ）
for a in re.findall(r'one_prop\(([^)]*)\)', line):
    x, y, b, h = [float(v) for v in a.split(',')]
    sup.append([((x, y, b), (x, y, h - 0.8), PD / 2), ((x, y, h - 0.8), (x, y, h), PT / 2)])
def seg_dist(p0, p1, q0, q1):
    p0, p1, q0, q1 = map(np.array, (p0, p1, q0, q1))
    u, v, w = p1 - p0, q1 - q0, p0 - q0
    a, b, c, d, e = u@u, u@v, v@v, u@w, v@w
    D0 = a * c - b * b
    if D0 < 1e-12: s = 0.0; t = (e / c) if c > 1e-12 else 0.0
    else: s = (b * e - c * d) / D0; t = (a * e - b * d) / D0
    s = min(1.0, max(0.0, s)); t = min(1.0, max(0.0, t))
    # 端で切ったので 1 回だけ詰め直す
    t = min(1.0, max(0.0, ((p0 + s * u - q0) @ v) / c)) if c > 1e-12 else 0.0
    s = min(1.0, max(0.0, ((q0 + t * v - p0) @ u) / a)) if a > 1e-12 else 0.0
    return float(np.linalg.norm((p0 + s * u) - (q0 + t * v)))
worst = (1e9, None); bad = 0
for i in range(len(sup)):
    for j in range(i + 1, len(sup)):
        for (a0, a1, ra) in sup[i]:
            for (b0, b1, rb) in sup[j]:
                g = seg_dist(a0, a1, b0, b1) - ra - rb
                if g < worst[0]: worst = (g, (i, j))
                if g < GAP: bad += 1
print('部品 %s   支え %d 本' % (PART, len(sup)))
print('  支え同士の隙間  最小 %.3f mm（基準 %.2f）' % (worst[0], GAP))
print('  基準を割った組み合わせ %d 組' % bad)
