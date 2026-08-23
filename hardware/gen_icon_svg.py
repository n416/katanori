# -*- coding: utf-8 -*-
"""SVG の線（stroke）を OpenSCAD の実体に起こす。

OpenSCAD の import() は**塗りしか読まない**ので、線だけで描かれた SVG は
そのままでは取り込めない。この道具は path の点列を読み、線を
「点と点のあいだの hull（丸い端・丸い角）」として .scad に書き出す。
⚠ 対応するのは M / L / Z だけ（曲線は入っていない前提。入っていたら止める）。

  python hardware/gen_icon_svg.py hardware/icon_gear_wrench.svg
"""
import io, re, sys, os

def main(src):
    s = io.open(src, encoding="utf-8").read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
    sw = float(re.search(r'stroke-width="([^"]+)"', s).group(1))
    ds = re.findall(r'<path[^>]*\sd="([^"]+)"', s)
    bad = set(re.findall(r'[A-Za-z]', " ".join(ds))) - set("MLZmlz")
    if bad:
        sys.exit("曲線などの命令が入っている: %s（直線だけに書き出し直すこと）" % sorted(bad))
    paths = []
    for d in ds:
        toks = re.findall(r'[A-Za-z]|-?\d*\.?\d+', d)
        pts, i, cur = [], 0, None
        while i < len(toks):
            t = toks[i]
            if t in "MLml":
                x, y = float(toks[i + 1]), float(toks[i + 2]); i += 3
                if t.islower() and cur: x, y = cur[0] + x, cur[1] + y
                cur = (x, y); pts.append(cur)
            elif t in "Zz":
                if pts: pts.append(pts[0])
                i += 1
            else:                      # 命令の省略（続きの座標）
                x, y = float(toks[i]), float(toks[i + 1]); i += 2
                cur = (x, y); pts.append(cur)
        if len(pts) > 1: paths.append(pts)
    # SVG の y は下向き。上向きへ直す
    h = vb[3]
    paths = [[(x, h - y) for x, y in p] for p in paths]
    xs = [x for p in paths for x, _ in p]; ys = [y for p in paths for _, y in p]
    x0, x1, y0, y1 = min(xs) - sw / 2, max(xs) + sw / 2, min(ys) - sw / 2, max(ys) + sw / 2
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    paths = [[(round(x - cx, 3), round(y - cy, 3)) for x, y in p] for p in paths]
    name = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(os.path.dirname(src), name + ".scad")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("// %s から自動生成（hardware/gen_icon_svg.py）。直接いじらない\n" % os.path.basename(src))
        f.write("// 線を「点と点のあいだの hull」で描く。角と端は丸（元の stroke-linejoin/cap と同じ）\n")
        f.write("function %s_size() = [%.3f, %.3f];   // 線の太さ込みの外形（SVG 単位）\n" % (name, x1 - x0, y1 - y0))
        f.write("function %s_sw()   = %.3f;           // 元の線の太さ（SVG 単位）\n" % (name, sw))
        f.write("%s_PATHS = [\n" % name.upper())
        for p in paths:
            f.write("  [" + ", ".join("[%g,%g]" % q for q in p) + "],\n")
        f.write("];\n")
        f.write("module %s(sw = %.3f) {\n" % (name, sw))
        f.write("    for (p = %s_PATHS) for (i = [0 : len(p) - 2])\n" % name.upper())
        f.write("        hull() { translate(p[i]) circle(d = sw, $fn = 16); translate(p[i+1]) circle(d = sw, $fn = 16); }\n")
        f.write("}\n")
    print("%s  外形 %.2f x %.2f（SVG 単位）／ 線 %.1f ／ 折れ線 %d 本・点 %d"
          % (out, x1 - x0, y1 - y0, sw, len(paths), sum(len(p) for p in paths)))

if __name__ == "__main__":
    main(sys.argv[1])
