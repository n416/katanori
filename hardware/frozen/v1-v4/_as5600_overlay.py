# -*- coding: utf-8 -*-
"""AS5600 の実物写真に、つまみの座の柱の座面（C 字）を重ねる。
   基準点は基板の 4 つの取り付け穴（中心間 17.0mm）。写真の傾きも縮尺も、この 4 点から決まる。

   使い方:
     python hardware/_as5600_overlay.py <写真> x1,y1 x2,y2 x3,y3 x4,y4 [出力.png]
       4 点は穴の中心の画素座標。**左上・右上・右下・左下の順**（写真の見たままの順）。

   🔒 形の数字は knob_v5.scad から読む（二重に持たない）。
"""
import io, os, re, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
src = io.open(os.path.join(HERE, 'knob_v5.scad'), encoding='utf-8').read()
_env = {}
def num(name):
    m = re.search(r'^%s\s*=\s*([^;]+);' % name, src, re.M)
    if not m: raise SystemExit('%s が knob_v5.scad に見つからない' % name)
    v = eval(m.group(1).strip(), {'__builtins__': {}}, _env)   # 2.0 + SHRINK + 0.3 のような式も読む
    _env[name] = v
    return v
SHRINK = num('SHRINK'); HOLE_PITCH = num('HOLE_PITCH'); STANDOFF = num('STANDOFF_D_LO')
RELIEF_ANG = num('POST_RELIEF_ANG'); M2_D = num('M2_D')
PCB = 23.0
P = HOLE_PITCH / 2

if len(sys.argv) < 6: raise SystemExit(__doc__)
photo = sys.argv[1]
pts_px = np.array([[float(v) for v in a.split(',')] for a in sys.argv[2:6]], float)
out = sys.argv[6] if len(sys.argv) > 6 else os.path.join(HERE, 'ref', 'as5600_overlay.png')

# 穴の位置（mm）: 画面の見たままの順（左上・右上・右下・左下）。画面の y は下向きなので mm の y も下向きに取る
pts_mm = np.array([[-P, -P], [P, -P], [P, P], [-P, P]], float)

# mm → 画素 のアフィン（最小二乗）
A = np.hstack([pts_mm, np.ones((4, 1))])
M, *_ = np.linalg.lstsq(A, pts_px, rcond=None)
def to_px(xy):
    xy = np.atleast_2d(np.asarray(xy, float))
    return (np.hstack([xy, np.ones((len(xy), 1))]) @ M)
res = np.hypot(*(to_px(pts_mm) - pts_px).T)
scale = np.hypot(*(to_px([[1, 0]])[0] - to_px([[0, 0]])[0]))
print('当てはめの残差 %.1f 画素（4 点）／縮尺 %.2f 画素 = 1mm' % (res.max(), scale))

im = Image.open(photo).convert('RGB')
ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
def poly(pts_mm_list, fill=None, outline=None, w=3):
    d.polygon([tuple(p) for p in to_px(pts_mm_list)], fill=fill, outline=outline, width=w)

# 基板の輪郭
poly([[-PCB/2, -PCB/2], [PCB/2, -PCB/2], [PCB/2, PCB/2], [-PCB/2, PCB/2]], outline=(0, 160, 60, 255), w=3)

# 柱の座面（C 字）: 円 φSTANDOFF から 扇形 RELIEF_ANG を抜く。開きは「列に沿って内側」＝ y の内側へ
for sx in (-1, 1):
    for sy in (-1, 1):
        cx, cy = sx * P, sy * P
        import math
        base = math.degrees(math.atan2(-cy, -cx))   # 基板の中心へ斜めに開く（画面座標の +y は下）
        a0, a1 = base + RELIEF_ANG / 2, base + 360 - RELIEF_ANG / 2
        arc = [[cx + STANDOFF/2 * np.cos(np.radians(a)), cy + STANDOFF/2 * np.sin(np.radians(a))]
               for a in np.linspace(a0, a1, 80)]
        poly([[cx, cy]] + arc, fill=(230, 180, 40, 110), outline=(210, 150, 20, 255), w=3)
# 柱の中の M2 の通し穴
for sx in (-1, 1):
    for sy in (-1, 1):
        cx, cy = sx * P, sy * P
        r = (M2_D) / 2
        circ = [[cx + r*np.cos(np.radians(a)), cy + r*np.sin(np.radians(a))] for a in np.linspace(0, 360, 60)]
        poly(circ, outline=(200, 30, 30, 255), w=2)

im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
im.save(out)
print('書いた:', out)
