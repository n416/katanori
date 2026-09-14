# -*- coding: utf-8 -*-
"""自動配線（Freerouting）を回して、結果を katanori61.kicad_pcb に入れる。

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

OUT = HERE / "katanori61"
NAME = "katanori61"
# 自動配線の実行ファイルは v6 の所に展開したものを使う（git には入れない）
FR = HERE.parents[0] / "frozen" / "v6" / "pcb" / "freerouting" / "freerouting" / "freerouting.exe"
from kicad_paths import CLI  # noqa: E402
_n = [0]


def uid():
    import uuid
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/route/{_n[0]}"))


# 🔴 **必ず gen_pcb.py を回してから回す。**route.py は生成済みの基板へ SES を混ぜるので、
#    配線が入った基板へ 2 回目を回すと結果が変わる（2026-09-13、未配線 1 本が出たり消えたり
#    して「自動配線は非決定的だ」と誤判定した。gen → route の順なら結果は毎回同じ）。
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


def stitch():
    """GND のベタを縫うビアを打つ（2026-09-13）。

    GND は自動配線に渡していない（gen_pcb.py の gnd_zone()）。表と裏に GND のベタを敷いているが、
    **表のベタは配線で島に割れる**ので、島ごとに裏のベタへ落とす穴が要る。
    空いている所を格子で探して、他のネットの銅から離れている点にだけ打つ。
    足りているかどうかは KiCad の DRC（unconnected_items）が言う。ここでは判定しない。
    """
    import check_pcb
    import gen_pcb as G
    pcb = kisym.parse((OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    allobj = check_pcb.shapes(pcb)
    nets = {str(e[2]): e[1] for e in find(pcb, "net")}
    # 🔴 GND の銅からも 0.55 離す。GND なら電気的には触れてよいが、**穴どうしの間隔**は
    #    ネットに関係なく要る（JLCPCB の規則・DRC の hole_to_hole が 4 件出た）
    VIA, DRILL, CLR, PITCH = 0.6, 0.3, 0.55, 3.2
    put = []
    for i in range(int((G.BOARD_L - 2) / PITCH) + 1):
        for j in range(int((G.BOARD_W - 2) / PITCH) + 1):
            u, v = 1.0 + i * PITCH, 1.0 + j * PITCH
            if any(nx0 - 1 < u < nx1 + 1 and v > ny - 1 for nx0, nx1, ny in G.NOTCHES):
                continue
            if any((u - mx) ** 2 + (v - my) ** 2 < (G.MOUNT_D / 2 + G.MOUNT_KEEP + VIA / 2) ** 2
                   for mx, my in G.MOUNT):
                continue
            if any((u - px) ** 2 + (v - py) ** 2 < (d / 2 + G.POST_KEEP + VIA / 2) ** 2
                   for px, py, d in G.POSTS):
                continue
            X, Y = G.bx(u, v)
            me = ("circle", X, Y, VIA / 2)
            if all(check_pcb.gap(me, g) > CLR for _, _, g in allobj):
                put.append((X, Y))
    body = list(pcb)
    for X, Y in put:
        body.append(["via", ["at", f"{X:.4f}", f"{Y:.4f}"], ["size", f"{VIA}"],
                     ["drill", f"{DRILL}"], ["layers", Str("F.Cu"), Str("B.Cu")],
                     ["net", nets["GND"]], ["uuid", Str(uid())]])
    (OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(body) + chr(10), encoding="utf-8")
    print(f"  GND を縫うビアを {len(put)} 個打った（格子 {PITCH}mm・φ{VIA}/{DRILL}）")


def drc():
    rpt = OUT / "drc.json"
    # 🔴 --refill-zones を付けないと、裏の GND のベタが埋まっていない状態で検査される
    #    （2026-09-13・GND を自動配線から外してベタに任せたら、45 パッドが未接続で出た）。
    #    ⚠ --save-board は付けない。KiCad に板を書き直させると、次の merge() が読めなくなる
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all",
                    "--refill-zones", "-o", str(rpt),
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
    stitch()
    drc()
