# -*- coding: utf-8 -*-
"""自動配線（Freerouting）を回して、結果を hub_power.kicad_pcb に入れる。

  python route.py            … DSN を渡して回し、SES を取り込む
  python route.py --ses      … 既にある SES を取り込むだけ

配線と貫通穴は毎回すべて置き換える（前の配線が混ざると、どこまでが今回の結果か分からなくなる）。
"""

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import kisym  # noqa: E402
from kisym import Str, find, find1  # noqa: E402
import dsn  # noqa: E402

OUT = HERE / "hub_power"
NAME = "hub_power"
FR = HERE.parent / "_tmp_pcb" / "freerouting" / "freerouting" / "freerouting.exe"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
_n = [0]


def uid():
    import uuid
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/route/{_n[0]}"))


def run_freerouting():
    if not FR.exists():
        sys.exit(f"Freerouting が無い: {FR}")
    r = subprocess.run([str(FR), "-de", str(OUT / f"{NAME}.dsn"), "-do", str(OUT / f"{NAME}.ses"),
                        "-l", "en", "-mt", "1", "-mp", "40"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for line in (r.stdout + r.stderr).splitlines():
        if "stage completed" in line or "stage interrupted" in line:
            print("  " + line.split("INFO")[-1].strip())
    if not (OUT / f"{NAME}.ses").exists():
        sys.exit("SES が出てこなかった:\n" + (r.stdout + r.stderr)[-2000:])


def merge():
    pcb = kisym.parse((OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    nets = {str(e[2]): e[1] for e in find(pcb, "net")}
    refs = {}
    for f in find(pcb, "footprint"):
        at = find1(f, "at")
        ref = [p for p in find(f, "property") if str(p[1]) == "Reference"]
        if ref:
            refs[str(ref[0][2])] = (float(at[1]), float(at[2]))
    wires, vias = dsn.read_ses(OUT / f"{NAME}.ses", refs)
    body = [e for e in pcb if not (isinstance(e, list) and e[0] in ("segment", "via"))]
    n_seg = 0
    for net, layer, w, pts in wires:
        if net not in nets:
            sys.exit(f"SES のネット '{net}' が基板に無い")
        for a, b in zip(pts, pts[1:]):
            # ⚠ 生の値ではなく**書き出す桁で**比べる。0.00001 違うだけの 2 点は 0.4f に丸めると
            #    同じ点になり、長さ 0 の配線が残って KiCad が「端が浮いている」と数える
            sa, sb = (f"{a[0]:.4f}", f"{a[1]:.4f}"), (f"{b[0]:.4f}", f"{b[1]:.4f}")
            if sa == sb:
                continue
            body.append(["segment", ["start", sa[0], sa[1]],
                         ["end", sb[0], sb[1]], ["width", f"{w:.3f}"],
                         ["layer", Str(layer)], ["net", nets[net]], ["uuid", Str(uid())]])
            n_seg += 1
    for net, x, y in vias:
        body.append(["via", ["at", f"{x:.4f}", f"{y:.4f}"], ["size", "0.8"], ["drill", "0.4"],
                     ["layers", Str("F.Cu"), Str("B.Cu")], ["net", nets[net]], ["uuid", Str(uid())]])
    (OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(body) + "\n", encoding="utf-8")
    print(f"  配線 {n_seg} 本・貫通穴 {len(vias)} 個を入れた")


def drc():
    rpt = OUT / "drc.json"
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "-o", str(rpt),
                    str(OUT / f"{NAME}.kicad_pcb")], capture_output=True, text=True,
                   encoding="utf-8", errors="replace")   # ⚠ 既定は cp932 で、日本語の行で落ちる
    import collections
    import json
    d = json.loads(rpt.read_text(encoding="utf-8"))
    cnt = collections.Counter()
    for key in ("violations", "unconnected_items", "schematic_parity"):
        for v in d.get(key, []):
            cnt[(key, v["type"], v["severity"])] += 1
    for (key, typ, sev), n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(f"  {key:20s} {typ:28s} {sev:8s} {n}")
    if not cnt:
        print("  DRC: 指摘なし")
    return d


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--ses" not in sys.argv:
        run_freerouting()
    merge()
    drc()
