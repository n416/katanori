# -*- coding: utf-8 -*-
"""uuu.png から起こしたスパナの輪郭から、画素の階段と手の震えだけを落とす。
形は変えない: 平滑化のあと外形を 204.750 角へ正規化し直すので、壁やハッチでの大きさは動かない。
使い方: python hardware/_wrench_smooth.py [sigma]  -> icon_wrench_u.scad を書き換える
        引数なしで走らせると比べる絵 (_wrench_smooth.png) だけ作る"""
import io, re, math, sys

SRC = 'icon_wrench_u.scad'
SPAN = 204.750

def load():
    s = io.open(SRC, encoding='utf-8').read()
    body = s[s.index('ICON_WRENCH_U_PTS'):]
    return [(float(a), float(b)) for a, b in
            re.findall(r'\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]', body)]

def resample(P, n):
    d = [math.dist(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    L = sum(d); step = L / n
    out = []; i = 0; acc = 0.0
    for k in range(n):
        t = k * step
        while acc + d[i] < t:
            acc += d[i]; i = (i + 1) % len(P)
        u = (t - acc) / d[i] if d[i] else 0.0
        a, b = P[i], P[(i + 1) % len(P)]
        out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    return out

def smooth(P, sigma):
    if sigma <= 0: return P[:]
    r = max(1, int(3 * sigma))
    w = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]
    t = sum(w); w = [v / t for v in w]
    n = len(P); out = []
    for i in range(n):
        x = sum(P[(i + k) % n][0] * w[k + r] for k in range(-r, r + 1))
        y = sum(P[(i + k) % n][1] * w[k + r] for k in range(-r, r + 1))
        out.append((x, y))
    return out

def normalize(P):
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2
    k = SPAN / max(max(xs) - min(xs), max(ys) - min(ys))
    return [((x - cx) * k, (y - cy) * k) for x, y in P]

def rdp(P, eps):
    def seg(pts):
        if len(pts) < 3: return pts
        a, b = pts[0], pts[-1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        best, bi = -1, 0
        for i in range(1, len(pts) - 1):
            p = pts[i]
            h = abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / L if L else math.dist(p, a)
            if h > best: best, bi = h, i
        if best <= eps: return [a, b]
        return seg(pts[:bi + 1])[:-1] + seg(pts[bi:])
    n = len(P)
    far = max(range(n), key=lambda i: math.dist(P[0], P[i]))
    return seg(P[:far + 1])[:-1] + seg(P[far:] + [P[0]])[:-1]

def build(P, sigma, n=1200, eps=0.12):
    return rdp(normalize(smooth(resample(P, n), sigma * n / 751.7)), eps)

def write_scad(P):
    s = io.open(SRC, encoding='utf-8').read()
    i = s.index('ICON_WRENCH_U_PTS'); j = s.index('];', i) + 2
    body = 'ICON_WRENCH_U_PTS = [\n' + ''.join('  [%.3f, %.3f],\n' % p for p in P).rstrip(',\n') + '\n];'
    io.open(SRC, 'w', encoding='utf-8').write(s[:i] + body + s[j:])

if __name__ == '__main__':
    P = load()
    if len(sys.argv) > 1:
        s = float(sys.argv[1]); Q = build(P, s)
        write_scad(Q); print('wrote sigma=%.1f pts=%d' % (s, len(Q)))
    else:
        from PIL import Image, ImageDraw
        SIG = [0.0, 2.5, 6.0, 10.0]
        W = 520; im = Image.new('RGB', (W * len(SIG), W + 40), (245, 245, 245))
        dr = ImageDraw.Draw(im)
        for k, s in enumerate(SIG):
            Q = build(P, s) if s else P
            f = (W - 60) / SPAN
            dr.polygon([(k * W + W / 2 + x * f, W / 2 + 20 + y * f) for x, y in Q], fill=(200, 120, 40))
            # 🔴 絵は必ず「彫った面から見た向き」= 口が右上 で描く（正はユーザーの見る向き）
            dr.text((k * W + 20, W + 14), 'sigma %.1f  pts %d' % (s, len(Q)), fill=(40, 40, 40))
        im.save('_wrench_smooth.png'); print('made _wrench_smooth.png')
