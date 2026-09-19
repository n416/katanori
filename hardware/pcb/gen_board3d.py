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

import math
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
# ⭐ 2026-09-19 🔒 ユーザー「シルクをモデルにも反映させてください」: シルク（表・裏）だけを別のファイルに（白）。
#   KiCad は厚み 0 の平らな面で出す（板の面から 0.075 浮く）。そのままでは F6（manifold）で消えるので、
#   三角を 2D の図形にして v61_silk.scad に書き、case_v6_1.scad が厚みを付ける。当てる検査には入れない
#   （case_v6_1.scad の PCB_SILK。検査の道具は -D PCB_SILK=false で呼ぶ）
OUT_S = HERE / "_silk3d.stl"          # 一時（2D の scad へ直したら消す）
OUT_SS = HERE / "v61_silk.scad"
# ⭐ 2026-09-19 🔒 ユーザー「USBポートとphヘッダーは白に」: 白くする口だけを別のファイルに。
#   ピンヘッダ（J1・J2）は「樹脂部分は黒です」で部品の側（黒）に残す
OUT_C = HERE / "v61_conn3d.stl"
CONN_3D = ("J4", "J5", "J6", "J7", "J10", "J13")   # PH 5・USB-C
# 🔒 ユーザー「樹脂だけ黒です。ピンは白ですよ」: ピンヘッダは樹脂とピンを分ける。KiCad の 3D モデルでは別々の塊なので、
#   パッドの芯のすぐ周りの三角（ピン 0.64 角）を白の口のファイルへ、残り（樹脂）を黒の部品のファイルへ足す
PINHDR_3D = ("J1", "J2")
PIN_R = 0.4           # パッドの芯からこの距離（XY）に収まる三角をピンとみなす [mm]（ピン 0.64 角の半分 0.32 ＋ 余り）
TMP_H = HERE / "_pinhdr3d.stl"
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


def read_tris(path):
    d = path.read_bytes()
    n = struct.unpack("<I", d[80:84])[0]
    return [struct.unpack("<12f", d[84 + i * 50:84 + i * 50 + 48]) for i in range(n)]


def write_tris(path, tris):
    buf = bytearray(b"katanori61 board+parts from kicad-cli".ljust(80, b" "))
    buf += struct.pack("<I", len(tris))
    for v in tris:
        buf += struct.pack("<12fH", *v, 0)
    path.write_bytes(bytes(buf))


def pad_xy(refs):
    """refs の足形のパッドの芯（3D の座標: X は図面のまま・Y は図面の符号を反転）。"""
    import kisym
    from kisym import find, find1
    pcb = kisym.parse(PCB.read_text(encoding="utf-8"))[0]
    out = []
    for f in find(pcb, "footprint"):
        r = [str(p[2]) for p in find(f, "property") if str(p[1]) == "Reference"]
        if not r or r[0] not in refs:
            continue
        at = find1(f, "at")
        fx, fy, fa = float(at[1]), float(at[2]), math.radians(float(at[3]) if len(at) > 3 else 0.0)
        for q in find(f, "pad"):
            pa = find1(q, "at")
            x, y = float(pa[1]), float(pa[2])
            dx, dy = x * math.cos(fa) + y * math.sin(fa), -x * math.sin(fa) + y * math.cos(fa)
            out.append((fx + dx, -(fy + dy)))
    return out


def split_pins(tris, pads):
    """3 つの頂点がどれもパッドの芯から PIN_R 以内（XY）にある三角をピン、残りを樹脂とする。
    ⚠ KiCad のピンヘッダのメッシュは樹脂とピンがつながっていて、塊ごとには分けられなかった。
    返り値は (ピンの三角, 樹脂の三角)。"""
    def near(x, y):
        return any(abs(x - px) <= PIN_R and abs(y - py) <= PIN_R for px, py in pads)
    pins, body = [], []
    for t in tris:
        (pins if all(near(t[3 + 3 * k], t[4 + 3 * k]) for k in range(3)) else body).append(t)
    return pins, body


def cap(tris):
    """分けて開いた穴（片側だけに使われている辺の輪）に扇形の三角を張って閉じる。
    ピンの付け根もピン穴も 0.64 角の四角（凸）なので扇形で足りる。返り値は足した三角の数。"""
    key = lambda x, y, z: (round(x, 4), round(y, 4), round(z, 4))
    pos, edges = {}, set()
    for t in tris:
        ks = []
        for k in range(3):
            v = t[3 + 3 * k:6 + 3 * k]
            kk = key(*v)
            pos[kk] = v
            ks.append(kk)
        for a, b in ((ks[0], ks[1]), (ks[1], ks[2]), (ks[2], ks[0])):
            edges.add((a, b))
    nxt = {a: b for a, b in edges if (b, a) not in edges}
    added = 0
    while nxt:
        a0, b = nxt.popitem()
        loop = [a0]
        while b != a0 and b in nxt:
            loop.append(b)
            b = nxt.pop(b)
        if b != a0 or len(loop) < 3:
            sys.exit("穴の輪が閉じない（%d 点）" % len(loop))
        for i in range(1, len(loop) - 1):           # 辺の向きを逆にして張る（b → a）
            p0, p1, p2 = pos[loop[0]], pos[loop[i + 1]], pos[loop[i]]
            u = [p1[j] - p0[j] for j in range(3)]
            w = [p2[j] - p0[j] for j in range(3)]
            nrm = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
            tris.append(tuple(nrm) + tuple(p0) + tuple(p1) + tuple(p2))
            added += 1
    return added


def silk_scad(tris, path, board_top):
    """シルクの平らな三角（KiCad の --include-silkscreen）を 2D の図形として scad に書く。
    厚み 0 の面は F6（manifold）で消えるので、case_v6_1.scad が linear_extrude で厚みを付ける。
    表と裏は Z で分ける（表は板の上・裏は板の下）。"""
    lay = {"top": [], "bot": []}
    for t in tris:
        z = (t[5] + t[8] + t[11]) / 3
        lay["top" if z > 0.5 else "bot"].append([(t[3], t[4]), (t[6], t[7]), (t[9], t[10])])
    zs = {k: [] for k in lay}
    for t in tris:
        zs["top" if t[5] > 0.5 else "bot"].append(t[5])
    rows = ["// 自動生成: hardware/pcb/gen_board3d.py（KiCad のシルクの三角を 2D にした物）。手で直さない",
            "// 座標は KiCad の 3D（X は図面のまま・Y は図面の符号を反転）。Z は SILK_Z が持つ",
            "SILK_BOARD_TOP = %.4f;   // 板の上の面（v61_board3d.stl の上端）。板の下の面は 0" % board_top]
    for k, ts in lay.items():
        pts = [p for tri in ts for p in tri]
        rows.append("SILK_Z_%s = %.4f;" % (k.upper(), sum(zs[k]) / len(zs[k])))
        rows.append("module silk_%s2d() polygon(points = [%s], paths = [%s]);" % (
            k, ",".join("[%.4f,%.4f]" % p for p in pts),
            ",".join("[%d,%d,%d]" % (3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(ts)))))
    path.write_text(chr(10).join(rows) + chr(10), encoding="utf-8")
    return {k: len(v) for k, v in lay.items()}


def build():
    t0 = time.time()
    rest = ",".join(sorted(r for r in comps() if r not in EXCLUDE_3D and r not in CONN_3D and r not in PINHDR_3D))
    conn = ",".join(r for r in CONN_3D if r not in EXCLUDE_3D)
    base = [K.CLI, "pcb", "export", "stl", "--force", "--no-dnp", "--subst-models", "--user-origin", "0x0mm"]
    tot = 0
    for path, extra in ((OUT, ["--board-only"]),
                        (OUT_P, ["--no-board-body", "--component-filter", rest]),
                        (OUT_C, ["--no-board-body", "--component-filter", conn]),
                        (OUT_S, ["--no-board-body", "--no-components", "--include-silkscreen"]),
                        (TMP_H, ["--no-board-body", "--component-filter", ",".join(PINHDR_3D)])):
        r = subprocess.run(base + extra + ["-o", str(path), str(PCB)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not path.exists():
            sys.exit("kicad-cli が STL を出せなかった:\n" + (r.stdout + r.stderr)[-1500:])
        raw = path.stat().st_size
        n = ascii_to_binary(path)
        tot += n
        print("  %-16s 三角 %6d（ASCII %.1fMB → binary %.1fMB）"
              % (path.name, n, raw / 1e6, path.stat().st_size / 1e6))
    pins, body = split_pins(read_tris(TMP_H), pad_xy(PINHDR_3D))
    TMP_H.unlink()
    if not pins or not body:
        sys.exit("ピンヘッダの樹脂とピンを分けられなかった（ピン %d・樹脂 %d 三角）" % (len(pins), len(body)))
    # 分けた所は開いた穴になる（ピンの付け根・樹脂のピン穴）。閉じないと F6（manifold）でファイルごと捨てられる
    n_cb, n_cp = cap(body), cap(pins)
    write_tris(OUT_P, read_tris(OUT_P) + body)
    write_tris(OUT_C, read_tris(OUT_C) + pins)
    print("  穴をふさいだ三角: 樹脂 %d・ピン %d" % (n_cb, n_cp))
    n_s = silk_scad(read_tris(OUT_S), OUT_SS, bbox(OUT)[1][2])
    OUT_S.unlink()
    print("  シルク → %s（表 %d・裏 %d 三角の 2D）" % (OUT_SS.name, n_s["top"], n_s["bot"]))
    print("  ピンヘッダ %s: 樹脂 %d 三角 → %s・ピン %d 三角 → %s" % ("・".join(PINHDR_3D), len(body), OUT_P.name, len(pins), OUT_C.name))
    (lo1, hi1, _), (lo2, hi2, _) = bbox(OUT_P), bbox(OUT_C)   # 部品は口と残りの 2 つに分けたので、合わせた外接箱
    lo, hi = [min(a, b) for a, b in zip(lo1, lo2)], [max(a, b) for a, b in zip(hi1, hi2)]
    print("三角 合計 %d 個・%.1f 秒" % (tot, time.time() - t0))
    print("3D の外接箱（部品）  X %.3f..%.3f  Y %.3f..%.3f  Z %.3f..%.3f"
          % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    ox = VB.ORG_W[0] - DRAW_ORG[0]
    oy = VB.ORG_W[1] + DRAW_ORG[1]
    print("筐体の世界へ: translate([%.1f, %.1f, 板の裏の Z]) import(...)" % (ox, oy))
    print("  ⇒ 世界 X %.3f..%.3f / Y %.3f..%.3f / 板の裏から上へ %.3f・下へ %.3f"
          % (lo[0] + ox, hi[0] + ox, lo[1] + oy, hi[1] + oy, hi[2], -lo[2]))
    print("→", OUT, "/", OUT_P, "/", OUT_C, "/", OUT_SS)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
