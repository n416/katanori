# 組み立てシミュレーションの光線検査（2026-08-23）
#   STL（その手順のときに在る物）へ、軸に平行な円筒の束を撃って
#   「どこまで真っ直ぐ入れるか」を mm で返す。工具の道・ナットの道・指の道に使う
import sys, struct, math, numpy as np

def load(p):
    d = open(p, 'rb').read()
    n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(d[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)
    v = a[:, 12:48].copy().view('<f4').reshape(n, 3, 3).astype(np.float64)
    return v

def clear_len(T, origin, axis, sign, dia, maxlen=200.0, eps=0.05):
    """origin から axis 方向（sign=+1/-1）へ、直径 dia の円筒を進めたとき
       最初に何かに当たるまでの距離 [mm]。当たらなければ maxlen"""
    k = axis; a, b = [i for i in (0, 1, 2) if i != k]
    # 円板の上に光線の出発点を撒く（中心＋同心円）
    # 円板の中を 0.4mm 刻みの格子で撒く（外周のリングだけだと薄い当たりを跨いで見落とす）
    r = dia / 2.0; st = 0.4 if dia <= 20 else 0.6
    n = int(math.ceil(r / st))
    pts = [(i * st, j * st) for i in range(-n, n + 1) for j in range(-n, n + 1)
           if (i * st) ** 2 + (j * st) ** 2 <= r * r + 1e-9]
    for j in range(24):   # 外周は必ず撒く
        t = 2 * math.pi * j / 24; pts.append((r * math.cos(t), r * math.sin(t)))
    A = T[:, :, a]; B = T[:, :, b]; K = T[:, :, k]
    amin, amax = A.min(1), A.max(1); bmin, bmax = B.min(1), B.max(1)
    best = maxlen
    for du, dv in pts:
        pa = origin[a] + du; pb = origin[b] + dv
        m = (amin <= pa) & (amax >= pa) & (bmin <= pb) & (bmax >= pb)
        if not m.any(): continue
        A2, B2, K2 = A[m], B[m], K[m]
        x0, y0 = A2[:, 0], B2[:, 0]; x1, y1 = A2[:, 1], B2[:, 1]; x2, y2 = A2[:, 2], B2[:, 2]
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        ok = np.abs(den) > 1e-12
        if not ok.any(): continue
        l0 = np.where(ok, ((y1 - y2) * (pa - x2) + (x2 - x1) * (pb - y2)) / np.where(ok, den, 1), -1)
        l1 = np.where(ok, ((y2 - y0) * (pa - x2) + (x0 - x2) * (pb - y2)) / np.where(ok, den, 1), -1)
        l2 = 1 - l0 - l1
        inside = ok & (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
        if not inside.any(): continue
        zk = l0[inside] * K2[inside, 0] + l1[inside] * K2[inside, 1] + l2[inside] * K2[inside, 2]
        t = (zk - origin[k]) * sign
        t = t[t > eps]
        if t.size: best = min(best, float(t.min()))
    return best

if __name__ == '__main__':
    print(clear_len(load(sys.argv[1]), np.array([float(x) for x in sys.argv[2].split(',')]),
                    int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])))
