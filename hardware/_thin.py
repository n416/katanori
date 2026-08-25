# 肉の厚みの検査: 0.15mm の柱でボクセル化し、内部の距離場の稜線（局所最大）を拾う。
# 厚み t の板の稜線は t/2 になるので、稜線の小さい所＝薄い肉。
import sys, numpy as np, math, re, struct
from scipy import ndimage
exec(open('_islands.py', encoding='utf-8').read().split("T0 = tris")[0])
G = 0.15; L = 0.15
T = tris(sys.argv[1]); T = T - T.reshape(-1, 3).min(0)
V = voxel(T); sp = (L, G, G)
d = ndimage.distance_transform_edt(V, sampling=sp).astype(np.float32)
mx = ndimage.maximum_filter(d, size=3)
ridge = V & (d >= mx - 1e-6) & (d > 0)
vals = d[ridge]
print("体積 %.0fmm3  稜線 %d 点  肉厚 = 稜線x2" % (V.sum()*G*G*L, ridge.sum()))
# 🔴 この格子の下限は 2G。面取りや斜面の「刃」は厚み 0 まで痩せるが、ここには全部 2G と出るので、
#    壁と刃の区別が付かない。2G が並んだら _thin2.py で格子を細かくして測り直す
#    （細かくして値が下がれば刃・下がらなければ本物の壁）。
print("  [注] 下限 %.2fmm（格子 %.2f × 2）。これ以下は全部この値で出る＝テーパの先と区別が付かない" % (2 * G, G))
for th in [0.21, 0.3, 0.4, 0.5, 0.8]:
    m = ridge & (d < th)
    if not m.any(): print(f"  厚み {2*th:.2f}mm 未満の稜線: なし"); continue
    lab, n = ndimage.label(m)
    sz = ndimage.sum(m, lab, range(1, n+1))
    print(f"  厚み {2*th:.2f}mm 未満の稜線: {int(m.sum())} 点 / {n} 箇所")
    for i in np.argsort(sz)[::-1][:3]:
        zs, xs, ys = np.nonzero(lab == i+1)
        print(f"      {int(sz[i]):4d}点  X {xs.min()*G:5.1f}〜{xs.max()*G:5.1f}  Y {ys.min()*G:5.1f}〜{ys.max()*G:5.1f}  Z {zs.min()*L:5.1f}〜{zs.max()*L:5.1f}  厚み {2*d[lab==i+1].min():.2f}〜{2*d[lab==i+1].max():.2f}")
