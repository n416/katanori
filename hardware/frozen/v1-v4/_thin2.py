# _thin.py の格子を細かくした版（第2引数で格子。既定 0.06）。薄いと出た所を切り出して測り直す用
import sys, numpy as np, math, re, struct
from scipy import ndimage
exec(open('_thin.py', encoding='utf-8').read().split("G = 0.15")[0])
G = float(sys.argv[2]) if len(sys.argv) > 2 else 0.06
L = G
T = tris(sys.argv[1]); T = T - T.reshape(-1, 3).min(0)
V = voxel(T); sp = (L, G, G)
d = ndimage.distance_transform_edt(V, sampling=sp).astype(np.float32)
mx = ndimage.maximum_filter(d, size=3)
ridge = V & (d >= mx - 1e-6) & (d > 0)
print("格子 %.3f  下限 %.2fmm  稜線 %d 点" % (G, 2*G, ridge.sum()))
for th in [G*1.01, 0.15, 0.2, 0.25, 0.3]:
    m = ridge & (d < th)
    if not m.any(): print(f"  厚み {2*th:.2f} 未満: なし"); continue
    lab, n = ndimage.label(m)
    sz = ndimage.sum(m, lab, range(1, n+1))
    print(f"  厚み {2*th:.2f} 未満: {int(m.sum())} 点 / {n} 箇所")
    for i in np.argsort(sz)[::-1][:2]:
        zs, xs, ys = np.nonzero(lab == i+1)
        print(f"      {int(sz[i]):5d}点  X {xs.min()*G:5.2f}〜{xs.max()*G:5.2f}  Y {ys.min()*G:5.2f}〜{ys.max()*G:5.2f}  Z {zs.min()*L:5.2f}〜{zs.max()*L:5.2f}  厚み {2*d[lab==i+1].min():.2f}〜{2*d[lab==i+1].max():.2f}")
