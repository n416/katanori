# -*- coding: utf-8 -*-
"""AS5600 の取付穴のピッチを、写真から**物差しを外から与えて**出す。
   🔴 _as5600_rect.py は「4 つの穴 = ±8.5」を前提に置いた変換なので、ピッチは測れない
      （残差 0.136mm は「4 つの穴がきれいな正方形だ」としか言っていない）。
   ここでは写真の中の**長さの分かっている物**を物差しにする:
     ① 穴の径 3.55mm（✅ 現物合わせ・hole_gauge.scad。φ3.5 が入り φ3.6 が入らない）
     ② 基板の外形 23.0mm（⚠ 17.0 と同じ 2026-08-01 の定規実測。同じ日の値なので独立ではない）
   使い方: python hardware/_as5600_pitch.py
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
a = np.asarray(Image.open(os.path.join(HERE, 'ref', 'as5600_top.jpg')).convert('RGB')).astype(float)

# --- 白い基板を切り出す（背景は木＝オレンジ）---
# ✅ この切り出しは _as5600_rect.py で通っているものをそのまま使う
board = (a[:, :, 2] / np.maximum(a[:, :, 0], 1) > 0.80) & (a.mean(2) > 90)
board = ndi.binary_closing(board, np.ones((9, 9)))
lab, n = ndi.label(board)
board = lab == int(np.argmax(ndi.sum(board, lab, range(1, n + 1)))) + 1
filled = ndi.binary_fill_holes(board)

# --- 4 つの取付穴（内接円で拾う。しっぽが付いても中心と径が動かない）---
lab2, n2 = ndi.label(filled & ~board)
ys, xs = np.nonzero(filled); cx, cy = xs.mean(), ys.mean()
cand = []
for i in range(1, n2 + 1):
    m = lab2 == i
    if m.sum() < 1500: continue
    d = ndi.distance_transform_edt(m)
    r = d.max()
    if not (25 <= r <= 45): continue
    yy, xx = np.nonzero(d >= r - 0.5)
    ex, ey = xx.mean(), yy.mean()
    cand.append((np.hypot(ex - cx, ey - cy), ex, ey, r))
cand.sort(key=lambda c: -c[0])
assert len(cand) >= 4, '穴が 4 つ見つからない: %d' % len(cand)
cand = cand[:4]
P = np.array([[c[1], c[2]] for c in cand])
R = np.array([c[3] for c in cand])

# 左上・右上・右下・左下 に並べ替え
top = sorted([p for p in P if p[1] < cy], key=lambda p: p[0])
bot = sorted([p for p in P if p[1] > cy], key=lambda p: p[0])
P = np.array([top[0], top[1], bot[1], bot[0]])

sides = [np.hypot(*(P[i] - P[(i + 1) % 4])) for i in range(4)]
diags = [np.hypot(*(P[0] - P[2])), np.hypot(*(P[1] - P[3]))]

# --- 物差し ① 穴の径 ---
px_per_mm_hole = (2 * R.mean()) / 3.55
# --- 物差し ② 基板の外形（角が丸いので、最小面積の回転長方形の辺）---
yy, xx = np.nonzero(filled)
pts = np.stack([xx, yy], 1).astype(float)
best = None
for th in np.arange(0, 90, 0.1):
    c, s = np.cos(np.radians(th)), np.sin(np.radians(th))
    u = pts @ np.array([c, s]); v = pts @ np.array([-s, c])
    w, h = np.ptp(u), np.ptp(v)
    if best is None or w * h < best[0]: best = (w * h, w, h, th)
px_per_mm_edge = ((best[1] + best[2]) / 2) / 23.0

print('穴の中心（画素）: ' + ' '.join('(%.1f,%.1f)' % tuple(p) for p in P))
print('穴の径（画素・4 つ）: ' + ' / '.join('%.1f' % (2 * r) for r in R) +
      '   ばらつき %.1f%%' % (100 * (R.max() - R.min()) / R.mean()))
print('基板の外形（画素）: %.1f x %.1f（傾き %.1f 度）' % (best[1], best[2], best[3]))
print()
for name, k in (('① 穴の径 3.55mm', px_per_mm_hole), ('② 外形 23.0mm', px_per_mm_edge)):
    print('%-18s 1mm = %6.2f 画素' % (name, k))
    print('   辺 4 本: ' + ' / '.join('%.2f' % (s / k) for s in sides) + '  平均 %.2f mm' % (np.mean(sides) / k))
    print('   対角 2 本: ' + ' / '.join('%.2f' % (d / k) for d in diags) +
          '  平均 %.2f mm  ⇒ ピッチ %.2f mm' % (np.mean(diags) / k, np.mean(diags) / k / np.sqrt(2)))
print()
print('模型の値: ピッチ 17.00 / 対角 %.2f' % (17 * np.sqrt(2)))
