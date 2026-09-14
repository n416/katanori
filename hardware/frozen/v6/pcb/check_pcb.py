# -*- coding: utf-8 -*-
"""基板の銅箔どうしの最小すきまを、KiCad とは別の道で測る。

  python check_pcb.py     → 別ネットどうしの最小すきまと、下回っている組を並べる

KiCad の DRC は正しいが、**同じ道具で 2 回測っても独立した観測にはならない**。この文書は
.kicad_pcb を自分で読み、パッド・配線・ビアの形から距離を出して突き合わせる。

⚠ パッドの形を丸と長丸と角で分ける。**丸を角として測ると、通っている線を「短絡」と誤判定する**
  （2026-09-12 に実際にやった。J2 のピンヘッダは丸なのに角として測って −0.10mm と出た）。
⚠ roundrect は角として測る（角の丸みを無視する＝銅を多めに見る）。安全側に外れる。
"""

import collections
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import kisym  # noqa: E402
from kisym import find, find1  # noqa: E402

PCB = HERE / "hub_power" / "hub_power.kicad_pcb"
LIMIT = 0.15   # 案③の設計規則（hub_power.kicad_pro の min_clearance）


def shapes(pcb):
    """(ネット名, 層, 形) を全部集める。形は ('circle',x,y,r) か ('seg',x0,y0,x1,y1,r)
    か ('rect',cx,cy,w,h)。線幅と丸みは半径 r に畳んでおく。"""
    nets = {str(n[1]): str(n[2]).strip('"') for n in find(pcb, "net")}
    out = []
    for f in find(pcb, "footprint"):
        at = find1(f, "at")
        X, Y = float(at[1]), float(at[2])
        A = math.radians(float(at[3]) if len(at) > 3 else 0.0)
        for p in find(f, "pad"):
            kind = str(p[3])
            pa, sz = find1(p, "at"), find1(p, "size")
            px, py = float(pa[1]), float(pa[2])
            sx, sy = float(sz[1]), float(sz[2])
            pang = float(pa[3]) if len(pa) > 3 else 0.0
            rx = px * math.cos(A) + py * math.sin(A)
            ry = -px * math.sin(A) + py * math.cos(A)
            cx, cy = X + rx, Y + ry
            net = find1(p, "net")
            nm = str(net[2]).strip('"') if net else "(なし)"
            if kind == "circle":
                g = ("circle", cx, cy, max(sx, sy) / 2)
            elif kind == "oval":
                # 長丸: 長い方の軸に沿った線分 ＋ 半径
                r = min(sx, sy) / 2
                L = (max(sx, sy) - min(sx, sy)) / 2
                a2 = math.radians(pang) + (0.0 if sx >= sy else math.pi / 2)
                dx, dy = L * math.cos(a2), -L * math.sin(a2)
                g = ("seg", cx - dx, cy - dy, cx + dx, cy + dy, r)
            else:   # rect / roundrect / custom は角として測る（銅を多めに見る＝安全側）
                if abs(pang % 180.0) > 1e-6:
                    sx, sy = sy, sx
                g = ("rect", cx, cy, sx, sy)
            lay = [str(x).strip('"') for x in find1(p, "layers")[1:]]
            cu = ["F.Cu", "B.Cu"] if any("*" in x for x in lay) else [x for x in lay if x.endswith(".Cu")]
            for L2 in cu:
                out.append((nm, L2, g))
    for s in find(pcb, "segment"):
        a, b = find1(s, "start"), find1(s, "end")
        nm = nets.get(str(find1(s, "net")[1]), "?")
        r = float(find1(s, "width")[1]) / 2
        out.append((nm, str(find1(s, "layer")[1]).strip('"'),
                    ("seg", float(a[1]), float(a[2]), float(b[1]), float(b[2]), r)))
    for v in find(pcb, "via"):
        at = find1(v, "at")
        nm = nets.get(str(find1(v, "net")[1]), "?")
        g = ("circle", float(at[1]), float(at[2]), float(find1(v, "size")[1]) / 2)
        for L2 in ("F.Cu", "B.Cu"):
            out.append((nm, L2, g))
    return out


def seg_seg(p, q):
    """線分どうしの最短距離（中心線）。"""
    (ax, ay, bx, by), (cx, cy, dx, dy) = p, q

    def pt_seg(px, py, x0, y0, x1, y1):
        ux, uy = x1 - x0, y1 - y0
        L2 = ux * ux + uy * uy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x0) * ux + (py - y0) * uy) / L2))
        return math.hypot(px - (x0 + t * ux), py - (y0 + t * uy))

    d1 = (bx - ax, by - ay)
    d2 = (dx - cx, dy - cy)
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) > 1e-12:      # 交わっているなら 0
        t = ((cx - ax) * d2[1] - (cy - ay) * d2[0]) / den
        u = ((cx - ax) * d1[1] - (cy - ay) * d1[0]) / den
        if 0 <= t <= 1 and 0 <= u <= 1:
            return 0.0
    return min(pt_seg(ax, ay, cx, cy, dx, dy), pt_seg(bx, by, cx, cy, dx, dy),
               pt_seg(cx, cy, ax, ay, bx, by), pt_seg(dx, dy, ax, ay, bx, by))


def rect_edges(g):
    _, cx, cy, w, h = g
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    return [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)], (x0, y0, x1, y1)


def gap(a, b):
    """2 つの形の銅どうしのすきま（負なら重なっている）。"""
    ka, kb = a[0], b[0]
    if ka == "rect" and kb == "rect":
        _, ax, ay, aw, ah = a
        _, bx, by, bw, bh = b
        return max(abs(ax - bx) - (aw + bw) / 2, abs(ay - by) - (ah + bh) / 2)
    if ka == "rect" or kb == "rect":
        r, o = (a, b) if ka == "rect" else (b, a)
        edges, (x0, y0, x1, y1) = rect_edges(r)
        if o[0] == "circle":
            _, px, py, pr = o
            dx = max(x0 - px, 0, px - x1)
            dy = max(y0 - py, 0, py - y1)
            return math.hypot(dx, dy) - pr
        _, sx, sy, ex, ey, sr = o
        inside = (x0 <= sx <= x1 and y0 <= sy <= y1) or (x0 <= ex <= x1 and y0 <= ey <= y1)
        d = 0.0 if inside else min(seg_seg((sx, sy, ex, ey), e) for e in edges)
        return d - sr
    # 丸と線分だけの組み合わせ
    def as_seg(g):
        return ("seg", g[1], g[2], g[1], g[2], g[3]) if g[0] == "circle" else g
    _, ax, ay, bx, by, ar = as_seg(a)
    _, cx, cy, dx, dy, br = as_seg(b)
    return seg_seg((ax, ay, bx, by), (cx, cy, dx, dy)) - ar - br


def main():
    pcb = kisym.parse(PCB.read_text(encoding="utf-8"))[0]
    objs = shapes(pcb)
    by = collections.defaultdict(list)
    for o in objs:
        by[o[1]].append(o)
    worst = []
    for L, lst in by.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a, b = lst[i], lst[j]
                if a[0] == b[0]:
                    continue
                d = gap(a[2], b[2])
                if d < LIMIT:
                    worst.append((d, L, a[0], b[0], a[2][0], b[2][0]))
    worst.sort()
    print(f"銅箔 {len(objs)} 個・すきまの下限 {LIMIT}mm")
    if not worst:
        # 下限を割る組が無いときは、いちばん近い組を 1 つ出す（「空」と「合格」を分ける）
        allp = []
        for L, lst in by.items():
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    a, b = lst[i], lst[j]
                    if a[0] != b[0]:
                        allp.append((gap(a[2], b[2]), L, a[0], b[0]))
        d, L, na, nb = min(allp)
        print(f"下回った組: 0 件。いちばん近いのは {na} ↔ {nb}（{L}）で {d:.3f}mm")
        return
    print(f"下回った組: {len(worst)} 件")
    for d, L, na, nb, ga, gb in worst[:20]:
        print(f"  {d:+.3f}mm  {na}({ga}) ↔ {nb}({gb})  {L}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
