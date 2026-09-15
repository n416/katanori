# -*- coding: utf-8 -*-
"""音声の核（voice_core.py）だけを試しに板へ入れて、区画の中の DRC を見る。

  python core_check.py        → build/core_check/ に板を書いて DRC（katanori61_voice/ は書き換えない）

核の外は自動配線していない（未配線だらけ）ので、ここで見るのは:
  ・区画の中にある違反（間隔・短絡・重なり・穴）
  ・核の部品だけで閉じるネット（境界を越えないネット）の未接続
境界を越えるネットの未接続は数えない（自動配線がつなぐ）。取り決めは docs/VOICE-CORE-HANDOFF.md。
"""

import collections
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_pcb_voice as P  # noqa: E402
import kicad_paths  # noqa: E402
import kisym  # noqa: E402
from kisym import find, find1  # noqa: E402

SRC = HERE / P.NAME
OUT = HERE / "build" / "core_check"


def board_xy(pos):
    """DRC の座標（図面・mm）→ 板の座標（Y 上向き）。"""
    return pos["x"] - P.G.ORG[0], P.G.BOARD_W - (pos["y"] - P.G.ORG[1])


def inside(pos, m=0.0):
    x, y = board_xy(pos)
    x0, y0, x1, y1 = P.CORE_REGION
    return x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if P.load_core() is None:
        sys.exit("voice_core.py が無い")
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("kicad_sch", "kicad_pro"):
        shutil.copy(SRC / f"{P.NAME}.{ext}", OUT / f"{P.NAME}.{ext}")
    P.G.OUT = OUT
    P.build()
    pcb_path = OUT / f"{P.NAME}.kicad_pcb"
    # 核の部品だけで閉じるネット
    tree = kisym.parse(pcb_path.read_text(encoding="utf-8"))[0]
    members = collections.defaultdict(set)
    for fp in find(tree, "footprint"):
        refs = [str(p[2]) for p in find(fp, "property") if str(p[1]) == "Reference"]
        if not refs:
            continue
        for pad in find(fp, "pad"):
            n = find1(pad, "net")
            if n:
                members[str(n[-1])].add(refs[0])
    closed = {n for n, rs in members.items() if rs <= P.CORE_REFS and len(rs) > 1 and not n.startswith("unconnected")}
    rpt = OUT / "drc.json"
    subprocess.run([kicad_paths.CLI, "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones",
                    "-o", str(rpt), str(pcb_path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    d = json.loads(rpt.read_text(encoding="utf-8"))
    skip = {"lib_footprint_issues", "silk_overlap", "silk_over_copper", "silk_edge_clearance",
            "nonmirrored_text_on_back_layer"}
    cnt = collections.Counter()
    rows = []
    for v in d["violations"]:
        if v["type"] in skip or not any(inside(i["pos"]) for i in v["items"]):
            continue
        cnt[(v["type"], v["severity"])] += 1
        rows.append("  " + v["type"] + ": " + v["description"] + " | " + " | ".join(
            "%s @板(%.2f, %.2f)" % ((i["description"],) + board_xy(i["pos"])) for i in v["items"]))
    unc = []
    for u in d.get("unconnected_items", []):
        nets = {s[s.index("[") + 1:s.index("]")] for s in (i["description"] for i in u["items"]) if "[" in s}
        if nets & closed:
            unc.append("  " + " | ".join("%s @板(%.2f, %.2f)" % ((i["description"],) + board_xy(i["pos"]))
                                         for i in u["items"]))
    print(f"区画 {P.CORE_REGION} の中の違反")
    for (t, s), n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(f"  {t:28s} {s:8s} {n}")
    print("\n".join(rows[:80]))
    print(f"核だけで閉じるネット {len(closed)} 本のうち、未接続 {len(unc)} 件")
    print("\n".join(unc[:80]))
    print(f"板: {pcb_path}")


if __name__ == "__main__":
    main()
