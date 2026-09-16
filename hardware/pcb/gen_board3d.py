# -*- coding: utf-8 -*-
"""置いてある基板を、部品の 3D モデルごと **STL** に書き出す（2026-09-16 夕）。

    python hardware/pcb/gen_board3d.py     → hardware/pcb/v61_board3d.stl

なぜ作ったか
------------
🔒 ユーザー「STEPをそのまま読み込んで」。
筐体の模型は板の上の物を**ただの直方体**で持っていた。平面は実物の胴（F.Fab）でも、
立体は箱なので、コネクタの殻の口もロックの爪もリレーの蓋も無い。

OpenSCAD は STEP を読めない（読めるのは STL / OFF / AMF / 3MF / DXF / SVG）。
⇒ **KiCad に基板ごとメッシュへ落としてもらう**。`kicad-cli pcb export stl` は
   部品の 3D モデル（STEP）を置いた姿で吐くので、1 回で板と 55 個が揃う。

座標
----
KiCad の 3D の出力は 板の**裏**が Z 0、X は図面のまま、Y は図面の符号を反転した所に出る。
筐体の世界へ持っていく式は下の `OFFSET`。板を動かしたらここも確かめること。

⚠ この STL は**見る物・当てる物**であって、寸法の出どころではない。
   口の座標や背の数字は `v61_parts.scad`（`gen_case_parts.py` が作る表）の側が持つ。
"""

import os
import pathlib
import re
import struct
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kicad_paths as K   # noqa: E402
import v61_board as VB    # noqa: E402

PCB = HERE / "katanori61" / "katanori61.kicad_pcb"
# 板と部品を **別のファイル**に出す。1 つだと OpenSCAD で色を分けられず、全部が同じ色になる
#   （🔒 ユーザー 2026-09-16 夕「真っ黄色はやめてね」）。三角の数は合わせても変わらない
OUT = HERE / "v61_board3d.stl"          # 板そのもの（緑）
OUT_P = HERE / "v61_parts3d.stl"        # 板の上と裏の部品（黒）
# ⭐ 2026-09-16 夕: いったん J1・J2 を外したが、🔒 ユーザー「ピンヘッダ立てることそのものは
#   問題ないでしょ」で戻した。**ピンが立っているのは実物どおり**で、直すべきは
#   ライザーの裏の L 字のメスを**中身の詰まった塊**で描いていた筐体の側だった（case_v6_1.scad）。
#   メスに穴を開けたので、ピンはそこへ入る。⇒ いま外す物は無い
EXCLUDE_3D = set()


def comps():
    """板に載っている部品の名前。置いてある基板ファイルから拾う。"""
    t = PCB.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'\(property "Reference" "([^"]+)"', t)))

# 板の座標 → 筐体の世界。板の左前の角が 図面 (40.0, 77.4) で、世界では ORG_W。
#   世界 X = 3D X + (ORG_W[0] - 40.0)
#   世界 Y = 3D Y + (ORG_W[1] + 77.4)      ← 3D の Y は図面の符号を反転した値
#   世界 Z = 3D Z + 板の裏の高さ（筐体が持つ HUB_AT[2]）
# 🔴 Z だけは筐体の側が決めるので、ここでは 0 のまま出す。筐体の scad で足す。
DRAW_ORG = (40.0, 77.4)


def ascii_to_binary(path):
    """kicad-cli は ASCII STL を吐く。そのままだと 7.4MB なので binary へ畳む。"""
    t = path.read_text(encoding="utf-8", errors="replace")
    tris = []
    for m in re.finditer(
            r"facet\s+normal\s+(\S+)\s+(\S+)\s+(\S+).*?"
            r"vertex\s+(\S+)\s+(\S+)\s+(\S+).*?"
            r"vertex\s+(\S+)\s+(\S+)\s+(\S+).*?"
            r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", t, re.S):
        tris.append([float(v) for v in m.groups()])
    buf = bytearray(b"katanori61 board+parts from kicad-cli".ljust(80, b" "))
    buf += struct.pack("<I", len(tris))
    for v in tris:
        buf += struct.pack("<12fH", *v, 0)
    path.write_bytes(bytes(buf))
    return len(tris)


def bbox(path):
    d = path.read_bytes()
    n = struct.unpack("<I", d[80:84])[0]
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for i in range(n):
        o = 84 + i * 50 + 12
        for k in range(3):
            p = struct.unpack("<3f", d[o + k * 12:o + k * 12 + 12])
            for j in range(3):
                lo[j] = min(lo[j], p[j])
                hi[j] = max(hi[j], p[j])
    return lo, hi, n


def build():
    t0 = time.time()
    keep = ",".join(sorted(r for r in comps() if r not in EXCLUDE_3D)) if EXCLUDE_3D else "*"
    base = [K.CLI, "pcb", "export", "stl", "--force", "--no-dnp", "--subst-models",
            "--component-filter", keep, "--user-origin", "0x0mm"]
    tot = 0
    for path, extra in ((OUT, ["--board-only"]), (OUT_P, ["--no-board-body"])):
        r = subprocess.run(base + extra + ["-o", str(path), str(PCB)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not path.exists():
            sys.exit("kicad-cli が STL を出せなかった:\n" + (r.stdout + r.stderr)[-1500:])
        raw = path.stat().st_size
        n = ascii_to_binary(path)
        tot += n
        print("  %-16s 三角 %6d（ASCII %.1fMB → binary %.1fMB）"
              % (path.name, n, raw / 1e6, path.stat().st_size / 1e6))
    lo, hi, n2 = bbox(OUT_P)
    print("三角 合計 %d 個・%.1f 秒" % (tot, time.time() - t0))
    print("3D の外接箱（部品）  X %.3f..%.3f  Y %.3f..%.3f  Z %.3f..%.3f"
          % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    ox = VB.ORG_W[0] - DRAW_ORG[0]
    oy = VB.ORG_W[1] + DRAW_ORG[1]
    print("筐体の世界へ: translate([%.1f, %.1f, 板の裏の Z]) import(...)" % (ox, oy))
    print("  ⇒ 世界 X %.3f..%.3f / Y %.3f..%.3f / 板の裏から上へ %.3f・下へ %.3f"
          % (lo[0] + ox, hi[0] + ox, lo[1] + oy, hi[1] + oy, hi[2], -lo[2]))
    print("→", OUT, "/", OUT_P)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
