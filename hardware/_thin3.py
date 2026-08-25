# 薄いと出た塊を「刃（格子の下限に張り付く）」と「本物の壁」に仕分けて並べる（2026-08-25）
#   使い方: python _thin3.py <stl> [格子] [世界座標の原点 x y z]
import sys, numpy as np, math, re, struct
from scipy import ndimage
exec(open('_thin.py', encoding='utf-8').read().split("G = 0.15")[0])
G = float(sys.argv[2]) if len(sys.argv) > 2 else 0.09
L = G
off = np.array([float(v) for v in sys.argv[3:6]]) if len(sys.argv) > 5 else np.zeros(3)
T = tris(sys.argv[1]); T = T - T.reshape(-1, 3).min(0)
V = voxel(T); d = ndimage.distance_transform_edt(V, sampling=(L, G, G)).astype(np.float32)
ridge = V & (d >= ndimage.maximum_filter(d, size=3) - 1e-6) & (d > 0)
m = ridge & (d < 0.30)          # 厚み 0.60 未満
lab, n = ndimage.label(m)
rows = []
for i in range(1, n + 1):
    sel = (lab == i); t = 2 * d[sel].min()
    zs, xs, ys = np.nonzero(sel)
    rows.append((t, int(sel.sum()),
                 xs.min() * G + off[0], xs.max() * G + off[0],
                 ys.min() * G + off[1], ys.max() * G + off[1],
                 zs.min() * L + off[2], zs.max() * L + off[2]))
rows.sort()
edge = [r for r in rows if r[0] <= 2 * G + 1e-6]
real = [r for r in rows if r[0] >  2 * G + 1e-6]
print("格子 %.2f（下限 %.2f）  厚み 0.60 未満の塊 %d 個" % (G, 2 * G, len(rows)))
print("  刃（下限に張り付き＝テーパの先）: %d 個 / %d 点" % (len(edge), sum(r[1] for r in edge)))
print("  本物の壁: %d 個" % len(real))
for t, c, x0, x1, y0, y1, z0, z1 in real[:12]:
    print("    厚み %.2f  %5d点  X %6.1f〜%6.1f  Y %6.1f〜%6.1f  Z %6.1f〜%6.1f" % (t, c, x0, x1, y0, y1, z0, z1))
