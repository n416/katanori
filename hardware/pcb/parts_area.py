# -*- coding: utf-8 -*-
"""板の上で部品が占める面積（courtyard の外接矩形）を、生成済みの .kicad_pcb から測る。

  python parts_area.py                     → 置いてある部品を大きい順に並べて合計を出す
  python parts_area.py --fp <足形名>...     → まだ置いていない足形を KiCad の標準ライブラリから測る

外形を引き直すときに「この部品たちは何 mm2 要るのか」を目分量でなく出すためのもの。
🔴 測っているのは **courtyard の外接矩形**で、部品の実際の外形ではない。
   回転している部品は矩形が膨らむので、合計はいくらか多めに出る。
🔴 高さは .kicad_pcb に入っていない。背の高さは docs/POWER.md の表を見ること。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kisym  # noqa: E402
from kisym import find, find1  # noqa: E402

PCB = pathlib.Path(__file__).parent / "hub_power" / "hub_power.kicad_pcb"
FPDIR = pathlib.Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")


def _crtyd_box(fp):
    """footprint の節から courtyard の外接矩形（幅, 高さ）を出す。無ければ None。"""
    xs, ys = [], []
    for kind in ("fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc"):
        for g in find(fp, kind):
            lay = find1(g, "layer")
            if not lay or "CrtYd" not in str(lay[1]):
                continue
            for key in ("start", "end", "center", "mid"):
                pt = find1(g, key)
                if pt:
                    xs.append(float(pt[1]))
                    ys.append(float(pt[2]))
            pts = find1(g, "pts")
            if pts:
                for xy in find(pts, "xy"):
                    xs.append(float(xy[1]))
                    ys.append(float(xy[2]))
    return (max(xs) - min(xs), max(ys) - min(ys)) if xs else None


def boxes():
    pcb = kisym.parse(PCB.read_text(encoding="utf-8"))[0]
    for fp in find(pcb, "footprint"):
        ref = ""
        for p in find(fp, "property"):
            if len(p) > 2 and str(p[1]).strip('"') == "Reference":
                ref = str(p[2]).strip('"')
        b = _crtyd_box(fp)
        if b:
            yield ref, b[0], b[1]


def lib_box(name):
    """KiCad の標準ライブラリの足形 1 つを測る。name は 'ライブラリ:足形' か足形だけ。"""
    if ":" in name:
        lib, fpn = name.split(":", 1)
        cands = [FPDIR / (lib + ".pretty") / (fpn + ".kicad_mod")]
    else:
        fpn = name
        cands = list(FPDIR.glob(f"*.pretty/{fpn}.kicad_mod"))
    for c in cands:
        if c.exists():
            return fpn, _crtyd_box(kisym.parse(c.read_text(encoding="utf-8"))[0])
    return fpn, None


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--fp":
        # 置く前の足形を測る（口を L 字にするか縦にするかを決めるときに使った）
        for name in sys.argv[2:]:
            fpn, b = lib_box(name)
            if b is None:
                print(f"{fpn:<45} 見つからない")
            else:
                print(f"{fpn:<45} {b[0]:6.2f} x {b[1]:6.2f} = {b[0] * b[1]:7.1f}")
        return
    rows = sorted(((r, w, h, w * h) for r, w, h in boxes()), key=lambda t: -t[3])
    out = [f"{r:<6} {w:6.2f} x {h:6.2f} = {a:8.2f}" for r, w, h, a in rows]
    out.append(f"--- {len(rows)} 部品・合計 {sum(t[3] for t in rows):.0f} mm2")
    print("\n".join(out))


if __name__ == "__main__":
    main()
