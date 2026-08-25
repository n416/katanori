# 置き方ごとの「浮き島」検出。STL を回して 0.4mm 角の柱でボクセル化し、
# 下の層に何も無い連結成分を島として拾う。
import sys, struct, math, re
import numpy as np
from scipy import ndimage

def tris(p):
    d = open(p, 'rb').read()
    if d[:5] == b'solid' and b'facet' in d[:400]:
        v = np.array([float(x) for x in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', d.decode('utf8', 'ignore')) for x in x])
        return v.reshape(-1, 3, 3)
    n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(d[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)
    f = a[:, 12:48].copy().view('<f4').reshape(n, 3, 3).astype(np.float64)
    return f

def rot(T, rx, ry):
    for ax, deg in ((0, rx), (1, ry)):
        if deg == 0: continue
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        M = np.array([[1, 0, 0], [0, c, -s], [0, s, c]]) if ax == 0 else np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        T = T @ M.T
    T = T - T.reshape(-1, 3).min(0)
    return T

G = 0.4   # 柱の一辺
L = 0.4   # 解析の層厚（実機は 0.05。島の有無を見る目的）

def voxel(T):
    mx, my, mz = T.reshape(-1, 3).max(0)
    nx, ny, nz = int(mx / G) + 2, int(my / G) + 2, int(mz / L) + 2
    cols, zc = [], []
    for t in T:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        x0, x1 = min(ax, bx, cx), max(ax, bx, cx); y0, y1 = min(ay, by, cy), max(ay, by, cy)
        i0, i1 = int(x0 / G), int(x1 / G) + 1; j0, j1 = int(y0 / G), int(y1 / G) + 1
        if i1 <= i0 or j1 <= j0: continue
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing='ij')
        px, py = (ii + 0.5) * G, (jj + 0.5) * G
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12: continue
        l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / d
        l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / d
        l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not m.any(): continue
        z = l1 * az + l2 * bz + l3 * cz
        cols.append((ii[m] * ny + jj[m]).astype(np.int64)); zc.append(z[m])
    cols = np.concatenate(cols); zc = np.concatenate(zc)
    k = np.clip((zc / L).astype(int), 0, nz - 1)
    cnt = np.zeros((nz, nx * ny), dtype=np.int32)
    np.add.at(cnt, (k, cols), 1)
    inside = (np.cumsum(cnt, axis=0) % 2 == 1).reshape(nz, nx, ny)
    return inside

def report(name, T0, rx, ry):
    T = rot(T0, rx, ry)
    V = voxel(T)
    px = G * G
    foot = V[0].sum() * px
    isl = []
    for k in range(1, V.shape[0]):
        if not V[k].any(): continue
        lab, n = ndimage.label(V[k])
        below = ndimage.binary_dilation(V[k - 1])
        for s in range(1, n + 1):
            m = lab == s
            if not (m & below).any():
                ys, xs = np.nonzero(m)
                isl.append((k * L, m.sum() * px, ((xs.mean() + .5) * G, (ys.mean() + .5) * G)))
    tot = sum(a for _, a, _ in isl)
    print(f"{name:28s} 高さ{T[:,:,2].max():5.1f}  接地面積{foot:7.1f}  島 {len(isl):3d}個 合計面積{tot:7.1f}")
    return isl

T0 = tris(sys.argv[1] if len(sys.argv) > 1 else 'stl/v3/v3_bridge.stl')
cases = [("① 直置き(いまのSTL)", 0, 0), ("② X軸に20度", 20, 0), ("③ Y軸に20度", 0, 20),
         ("④ X20+Y20", 20, 20), ("⑤ X軸に45度", 45, 0), ("⑥ 立てる(Y90)", 0, 90),
         ("⑦ 立てる+15度(Y90,X15)", 15, 90)]
out = {}
for nm, rx, ry in cases:
    out[nm] = report(nm, T0, rx, ry)
for nm, isl in out.items():
    big = sorted(isl, key=lambda a: -a[1])[:5]
    if big: print(nm, "  大きい島:", [(f"Z{z:.1f}", f"{a:.1f}mm2", f"({c[0]:.0f},{c[1]:.0f})") for z, a, c in big])
