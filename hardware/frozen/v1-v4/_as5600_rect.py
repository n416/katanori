# -*- coding: utf-8 -*-
"""AS5600 の写真を、基板の座標（mm）へ起こす。基準は 4 つの取り付け穴（中心間 17.0mm）。
   出力: ref/as5600_rect.png（1mm = RES 画素・原点は基板の中心・mm の目盛り付き）
   使い方: python hardware/_as5600_rect.py
"""
import os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
RES = 24.0        # 1mm = 24 画素
HALF = 14.0       # 中心から ±14mm を出す
im = Image.open(os.path.join(HERE, 'ref', 'as5600_top.jpg')).convert('RGB')
a = np.asarray(im).astype(float)

# --- 穴を見つける（基板の白い領域の中の穴）---
board = (a[:, :, 2] / np.maximum(a[:, :, 0], 1) > 0.80) & (a.mean(2) > 90)
board = ndi.binary_closing(board, np.ones((9, 9)))
lab, n = ndi.label(board); board = lab == int(np.argmax(ndi.sum(board, lab, range(1, n + 1)))) + 1
holes = ndi.binary_fill_holes(board) & ~board
lab2, n2 = ndi.label(holes)
cand = []
for i in range(1, n2 + 1):
    m = lab2 == i
    if m.sum() < 1500: continue
    d = ndi.distance_transform_edt(m); r = d.max()
    if not (25 <= r <= 45): continue
    yy, xx = np.nonzero(d >= r - 0.5)
    cand.append((r, xx.mean(), yy.mean()))
ys, xs = np.nonzero(board); cx, cy = xs.mean(), ys.mean()
# 穴は基板の中心から 12.02mm（=sqrt(8.5^2+8.5^2)）に居る。中心に近い候補（チップや列）は捨てる
cand.sort(key=lambda c: -np.hypot(c[1] - cx, c[2] - cy))
cand = cand[:4]
assert len(cand) == 4, '穴が 4 つ見つからない: %d' % len(cand)
top = sorted([c for c in cand if c[2] < cy], key=lambda c: c[1])
bot = sorted([c for c in cand if c[2] > cy], key=lambda c: c[1])
order = [top[0], top[1], bot[1], bot[0]]                            # 左上・右上・右下・左下
px = np.array([[c[1], c[2]] for c in order])
mm = np.array([[-8.5, -8.5], [8.5, -8.5], [8.5, 8.5], [-8.5, 8.5]])  # 画面の y は下向き
print('穴の径（内接円）: ' + ' / '.join('φ%.2f' % (2 * c[0] / (np.hypot(*(px[1] - px[0])) / 17.0)) for c in order))

A = np.hstack([mm, np.ones((4, 1))])
M, *_ = np.linalg.lstsq(A, px, rcond=None)
res = np.hypot(*((np.hstack([mm, np.ones((4, 1))]) @ M) - px).T)
print('当てはめの残差 %.2f 画素 = %.3f mm' % (res.max(), res.max() / (np.hypot(*(px[1] - px[0])) / 17.0)))

W = int(2 * HALF * RES)
out = Image.new('RGB', (W, W), (255, 255, 255))
# 逆写像でサンプリング
gx, gy = np.meshgrid(np.arange(W), np.arange(W))
mmx = gx / RES - HALF; mmy = gy / RES - HALF
src = np.stack([mmx, mmy, np.ones_like(mmx)], -1) @ M
sx = np.clip(src[..., 0].round().astype(int), 0, a.shape[1] - 1)
sy = np.clip(src[..., 1].round().astype(int), 0, a.shape[0] - 1)
out = Image.fromarray(a[sy, sx].astype(np.uint8))
d = ImageDraw.Draw(out)
def P(x, y): return (int((x + HALF) * RES), int((y + HALF) * RES))
for v in range(-14, 15):                                   # 1mm ごとの目盛り
    c = (255, 0, 0) if v % 5 == 0 else (255, 160, 160)
    d.line([P(v, -HALF), P(v, HALF)], fill=c, width=1)
    d.line([P(-HALF, v), P(HALF, v)], fill=c, width=1)
d.rectangle([P(-11.5, -11.5), P(11.5, 11.5)], outline=(0, 200, 90), width=2)
for sx_ in (-1, 1):
    for sy_ in (-1, 1):
        d.ellipse([P(sx_ * 8.5 - 1.9, sy_ * 8.5 - 1.9), P(sx_ * 8.5 + 1.9, sy_ * 8.5 + 1.9)], outline=(0, 120, 255), width=2)
out.save(os.path.join(HERE, 'ref', 'as5600_rect.png'))
print('書いた: ref/as5600_rect.png（1mm =', RES, '画素・赤の細線 1mm・太線 5mm・緑 = 基板 23 角・青 = 穴 φ3.8）')
