# -*- coding: utf-8 -*-
"""出来上がった製造ファイル（ガーバーとドリル）を、配置のコードとは**別の道**で測る。

    python hardware/pcb/check_fab.py

gen_pcb.py の中の検算は「置くときに使った数字」を見ているので、書き出しの段で
ずれても気づけない。ここは **JLCPCB へ送る物そのもの**（Edge_Cuts のガーバーと
PTH / NPTH のドリル）を読んで、板の座標へ直してから突き合わせる。
発注の前に必ず回す。

🔴 いちばん見たいのは電池の極性。逆接で INA226 から煙が出た事故がある（2026-09-11）。
"""
import csv
import math
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import v61_board as B          # noqa: E402
import gen_pcb as G            # noqa: E402
import jlc_fp                  # noqa: E402
from kicad_paths import CLI    # noqa: E402

FAB = HERE / "katanori61" / "fab" / "gerber"
NAME = "katanori61"


def drill(path):
    """Excellon を読む。⚠ ドリルは Y が負で入る（図面の Y を符号反転したもの）。"""
    tools, cur, holes = {}, None, []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"T(\d+)C([\d.]+)", ln)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r"T(\d+)$", ln)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"X([-\d.]+)Y([-\d.]+)", ln)
        if m and cur:
            x, y = float(m.group(1)), -float(m.group(2))
            holes.append((x - G.ORG[0], B.W - (y - G.ORG[1]), tools[cur]))
    return holes


def near(holes, bx, by, tol=0.06):
    return [h for h in holes if abs(h[0] - bx) < tol and abs(h[1] - by) < tol]


def ipc356():
    """KiCad が書き出すパッドの位置 → {(ref, 番号): [(x, y), …]}（CPL と同じ座標・Y 上向き・mm）"""
    out = FAB.parent / "_pads.356"
    r = subprocess.run([CLI, "pcb", "export", "ipcd356", "-o", str(out),
                        str(HERE / "katanori61" / f"{NAME}.kicad_pcb")], capture_output=True)
    if r.returncode:
        sys.exit("IPC-D-356 が書き出せない")
    pads = {}
    for ln in out.read_text(encoding="utf-8", errors="replace").splitlines():
        # 327 = 表面のパッド・317 = 穴を通すパッド（USB-C のシェルの足）・367 = 銅の無い穴（USB-C の位置決めの突起）
        if ln[:3] not in ("327", "317", "367"):
            continue
        # 列の位置は IPC-D-356 の決まり: 20〜25 列が部品・27〜30 列がピン・X / Y は 0.0001 インチ
        ref, pin = ln[20:26].strip(), ("穴" if ln[:3] == "367" else ln[27:31].strip())
        m = re.search(r"X([+-]\d+)Y([+-]\d+)", ln[38:])
        pads.setdefault((ref, pin), []).append((int(m.group(1)) * 0.00254, int(m.group(2)) * 0.00254))
    out.unlink()
    return pads


def placement():
    kpads = ipc356()
    lcsc = {}
    with open(FAB.parent / "bom.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            for ref in r["Designator"].split(","):
                lcsc[ref] = (r["JLCPCB Part #"], r["Footprint"])
    bad = []
    with open(FAB.parent / "cpl.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    worst = []
    for r in rows:
        ref = r["Designator"]
        lc, fp = lcsc[ref]
        res = jlc_fp.fetch(lc)
        if res is None:
            print(f"   ❌ {ref} {lc}: EasyEDA に足形が無い")
            bad.append(ref)
            continue
        _, epads, names = jlc_fp.easy_pads(res)
        kp = {pin: ps for (rf, pin), ps in kpads.items() if rf == ref}
        m = jlc_fp.pair(fp, kp, epads, names)
        placed = jlc_fp.place(float(r["Mid X"]), float(r["Mid Y"]), float(r["Rotation"]), lc)
        # JLCPCB の足形のパッド 1 つずつ、KiCad の同じピンのパッドまでの距離（同じ番号が複数なら近い方）
        d = max(min(math.dist(a, b) for a in placed[e] for b in kp[k]) for k, e in m.items())
        # 番号で組にならなかった JLCPCB のパッド（シェルの足など）も、KiCad のどれかのパッドに乗ること
        anyk = [b for pin, ps in kp.items() if pin != "穴" for b in ps]
        for e in set(placed) - set(m.values()):
            d = max(d, max(min(math.dist(a, b) for b in anyk) for a in placed[e]))
        # JLCPCB の足形の穴（位置決めの突起）は、KiCad の穴に入ること
        holes = jlc_fp.place_holes(float(r["Mid X"]), float(r["Mid Y"]), float(r["Rotation"]), lc)
        if holes:
            if "穴" not in kp:
                print(f"   ❌ {ref}: JLCPCB の足形に穴が {len(holes)} 個あるのに、板に無い")
                bad.append(f"{ref} の穴")
            else:
                d = max(d, max(min(math.dist(a, b) for b in kp["穴"]) for a in holes))
        worst.append((d, ref, lc, sum(len(v) for v in placed.values()) + len(holes)))
        # 0.5: jlc_fp.solve と同じ（足形どうしのランドの伸びの違いは 0.4 まで出る。ピンを 1 本取り違えると 0.5 以上）
        if d > 0.5:
            bad.append(f"{ref} の実装")
    worst.sort(reverse=True)
    for d, ref, lc, n in worst[:6]:
        print(f"   {ref:5s} {lc:10s} パッドと穴 {n:2d} 個・最大のずれ {d:.2f}" + ("  ❌" if d > 0.5 else ""))
    print(f"   （ほか {len(worst) - 6} 個はずれ {worst[6][0]:.2f} 以下）")
    return bad


def main():
    bad = []
    pth, npth = drill(FAB / f"{NAME}-PTH.drl"), drill(FAB / f"{NAME}-NPTH.drl")
    print(f"ドリル: PTH {len(pth)} 個・NPTH {len(npth)} 個")

    # 1. 外形
    t = (FAB / f"{NAME}-Edge_Cuts.gbr").read_text(encoding="utf-8", errors="replace")
    pts = [(int(a) / 1e6, int(b) / 1e6) for a, b in re.findall(r"X(-?\d+)Y(-?\d+)D0[12]", t)]
    w = max(p[0] for p in pts) - min(p[0] for p in pts)
    h = max(p[1] for p in pts) - min(p[1] for p in pts)
    ok = abs(w - B.L) < 0.01 and abs(h - B.W) < 0.01
    print(f"外形: {w:.3f} × {h:.3f}（板は {B.L:.3f} × {B.W:.3f}）{'' if ok else ' ❌'}")
    if not ok:
        bad.append("外形")

    # 2. 🔴 電池の極性（gen_pcb.py の検算表を出どころにする。数字をここに写さない）
    print("\n🔴 電池の口の極性")
    for pin, nm in (("1", "GND（−）"), ("2", "VBAT（＋）")):
        bx, by = G.CHECK_PADS[("J10", pin)]
        f = near(pth, bx, by)
        print(f"   J10.{pin} {nm}  板 ({bx:.3f}, {by:.3f}) → "
              + (f"φ{f[0][2]:.2f} が 1 個" if len(f) == 1 else f"❌ {len(f)} 個"))
        if len(f) != 1:
            bad.append(f"J10.{pin}")
    a, b = G.CHECK_PADS[("J10", "1")], G.CHECK_PADS[("J10", "2")]
    # ⭐ 2026-09-16 夕: J10 が縦になってパッドの並びが前後から左右へ変わったので、**並んでいる軸を見て**言う。
    #    前は「奥が GND／手前が VBAT」と決め打ちで、左右に並んだいまは両方同じ Y になって意味を成さなかった
    if abs(a[0] - b[0]) >= abs(a[1] - b[1]):
        g, v = ("右", "左") if a[0] > b[0] else ("左", "右")
        print(f"   ⇒ **{g}（X {a[0]:.2f}）が GND ／ {v}（X {b[0]:.2f}）が VBAT**（板を**表から**見た左右）")
    else:
        g, v = ("奥", "手前") if a[1] > b[1] else ("手前", "奥")
        print(f"   ⇒ **{g}（Y {a[1]:.2f}）が GND ／ {v}（Y {b[1]:.2f}）が VBAT**")

    # 3. 取付穴
    print("\n取付穴 M2")
    for bx, by in list(B.HOLES) + list(B.GUIDE_HOLES):   # 取付穴 4 ＋ 軸のガイドの足 3
        f = near(npth, bx, by) or near(pth, bx, by)
        print(f"   ({bx}, {by}) → " + (f"φ{f[0][2]:.2f}" if f else "❌ 無い"))
        if not f:
            bad.append(f"取付穴 ({bx}, {by})")

    # 4. ライザーのピンの列
    print("\nライザー")
    for ref, x0, n, y in (("J1", 1.770, 7, B.RISER_XIAO[2]), ("J2", 37.240, 4, B.RISER_OLED[2])):
        got = [near(pth, x0 + i * 2.54, y) for i in range(n)]
        mark = "".join("o" if len(g) == 1 else "x" for g in got)
        print(f"   {ref} {n} 本（Y {y}）: {mark}")
        if mark.count("x"):
            bad.append(ref)

    # 5. 🔴 実装の向きと位置（2026-09-18）
    #   CPL の 1 行どおりに **JLCPCB の足形**（品番ごとの EasyEDA の足形）を置いて、そのパッドが
    #   **KiCad が書き出したパッドの位置**（IPC-D-356・板の上の実際の位置）に乗るかを見る。
    #   fab.py は「足形どうしを重ねて角度を出す」、ここは「出した角度で置いてみる」で、道が逆になる
    print("\n実装の向きと位置（CPL どおりに JLCPCB の足形を置く）")
    bad += placement()

    print()
    print("合わない所なし" if not bad else "❌ 合わない: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
