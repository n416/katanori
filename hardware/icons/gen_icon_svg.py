# -*- coding: utf-8 -*-
"""SVG の線（stroke）と塗り（fill）を OpenSCAD の実体に起こす。

OpenSCAD の import() は**塗りしか読まない**ので、線だけで描かれた SVG は
そのままでは取り込めない。この道具は path の点列を読み、線を
「点と点のあいだの hull（丸い端・丸い角）」として .scad に書き出す。
fill が付いた path は、同じ点列の polygon も一緒に書き出す（塗り ＋ 線）。
⚠ 対応するのは M / L / C / Z だけ。曲線（C）は折れ線に割る（粗さ FLAT）。
   それ以外（Q / S / A / H / V）が入っていたら止める。

  python hardware/gen_icon_svg.py hardware/icon_gear_wrench.svg
"""
import io, re, sys, os

FLAT = 0.8   # 曲線を割る粗さ（SVG 単位）。細かいほど点が増える

def bezier(p0, p1, p2, p3):
    """三次ベジエを折れ線にする（始点は返さない）"""
    span = max(abs(p1[0] - p0[0]) + abs(p2[0] - p1[0]) + abs(p3[0] - p2[0]),
               abs(p1[1] - p0[1]) + abs(p2[1] - p1[1]) + abs(p3[1] - p2[1]))
    n = min(max(int(span / FLAT), 4), 64)
    out = []
    for k in range(1, n + 1):
        t = k / float(n); u = 1.0 - t
        out.append((u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
                    u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]))
    return out

def main(src):
    s = io.open(src, encoding="utf-8").read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
    sw = float(re.search(r'stroke-width="([^"]+)"', s).group(1))
    gf = re.search(r'<g[^>]*\sfill="([^"]+)"', s)          # 束ねている <g> の塗り（path 側が優先）
    gfill = gf.group(1) if gf else "none"
    tags = re.findall(r'<path[^>]*>', s)
    ds = [re.search(r'\sd="([^"]+)"', t).group(1) for t in tags]
    bad = set(re.findall(r'[A-Za-z]', " ".join(ds))) - set("MLZmlzCc")
    if bad:
        sys.exit("読めない命令が入っている: %s（M / L / C / Z だけに書き出し直すこと）" % sorted(bad))
    paths, fills = [], []
    for tag, d in zip(tags, ds):
        fm = re.search(r'\sfill="([^"]+)"', tag)
        filled = (fm.group(1) if fm else gfill) not in ("none", "")
        toks = re.findall(r'[A-Za-z]|-?\d*\.?\d+', d)
        pts, i, cur, cmd = [], 0, None, None
        while i < len(toks):
            t = toks[i]
            if re.match(r'[A-Za-z]', t):
                cmd = t; i += 1
                if cmd in "Zz" and pts:
                    pts.append(pts[0]); cur = pts[0]
                continue
            if cmd in "MmLl":
                x, y = float(toks[i]), float(toks[i + 1]); i += 2
                if cmd.islower() and cur: x, y = cur[0] + x, cur[1] + y
                cur = (x, y); pts.append(cur)
                if cmd == "M": cmd = "L"                    # M の 2 組目からは L（SVG の決まり）
                elif cmd == "m": cmd = "l"
            elif cmd in "Cc":
                v = [float(z) for z in toks[i:i + 6]]; i += 6
                if cmd == "c" and cur: v = [cur[k % 2] + v[k] for k in range(6)]
                pts.extend(bezier(cur, (v[0], v[1]), (v[2], v[3]), (v[4], v[5])))
                cur = (v[4], v[5])
            else:
                sys.exit("命令の無い座標が先頭にある: %s" % d[:40])
        if len(pts) > 1:
            paths.append(pts); fills.append(filled)
    # SVG の y は下向き。上向きへ直す
    h = vb[3]
    paths = [[(x, h - y) for x, y in p] for p in paths]
    xs = [x for p in paths for x, _ in p]; ys = [y for p in paths for _, y in p]
    x0, x1, y0, y1 = min(xs) - sw / 2, max(xs) + sw / 2, min(ys) - sw / 2, max(ys) + sw / 2
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    paths = [[(round(x - cx, 3), round(y - cy, 3)) for x, y in p] for p in paths]
    polys = [p[:-1] if p[0] == p[-1] else p for p, k in zip(paths, fills) if k]
    name = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(os.path.dirname(src), name + ".scad")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("// %s から自動生成（hardware/gen_icon_svg.py）。直接いじらない\n" % os.path.basename(src))
        f.write("// 線を「点と点のあいだの hull」で描く。角と端は丸（元の stroke-linejoin/cap と同じ）\n")
        if polys:
            f.write("// 塗りの付いていた path は polygon でも描く（塗り ＋ 線）\n")
        f.write("function %s_size() = [%.3f, %.3f];   // 線の太さ込みの外形（SVG 単位）\n" % (name, x1 - x0, y1 - y0))
        f.write("function %s_sw()   = %.3f;           // 元の線の太さ（SVG 単位）\n" % (name, sw))
        f.write("%s_PATHS = [\n" % name.upper())
        for p in paths:
            f.write("  [" + ", ".join("[%g,%g]" % q for q in p) + "],\n")
        f.write("];\n")
        if polys:
            f.write("%s_FILLS = [\n" % name.upper())
            for p in polys:
                f.write("  [" + ", ".join("[%g,%g]" % q for q in p) + "],\n")
            f.write("];\n")
        f.write("module %s(sw = %.3f) {\n" % (name, sw))
        if polys:
            f.write("    for (p = %s_FILLS) polygon(p);\n" % name.upper())
        f.write("    for (p = %s_PATHS) for (i = [0 : len(p) - 2])\n" % name.upper())
        f.write("        hull() { translate(p[i]) circle(d = sw, $fn = 16); translate(p[i+1]) circle(d = sw, $fn = 16); }\n")
        f.write("}\n")
    print("%s  外形 %.2f x %.2f（SVG 単位）／ 線 %.1f ／ 折れ線 %d 本・点 %d ／ 塗り %d 枚"
          % (out, x1 - x0, y1 - y0, sw, len(paths), sum(len(p) for p in paths), len(polys)))

if __name__ == "__main__":
    main(sys.argv[1])
