# -*- coding: utf-8 -*-
"""出来上がった製造ファイル（ガーバーとドリル）を、配置のコードとは**別の道**で測る。

    python hardware/pcb/check_fab.py

gen_pcb.py の中の検算は「置くときに使った数字」を見ているので、書き出しの段で
ずれても気づけない。ここは **JLCPCB へ送る物そのもの**（Edge_Cuts のガーバーと
PTH / NPTH のドリル）を読んで、板の座標へ直してから突き合わせる。
発注の前に必ず回す。

🔴 いちばん見たいのは電池の極性。逆接で INA226 から煙が出た事故がある（2026-09-11）。
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import v61_board as B          # noqa: E402
import gen_pcb as G            # noqa: E402

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
    print(f"   ⇒ **奥（Y {max(a[1], b[1]):.2f}）が GND ／ 手前（Y {min(a[1], b[1]):.2f}）が VBAT**")

    # 3. 取付穴
    print("\n取付穴 M2")
    for bx, by in B.HOLES:
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

    print()
    print("合わない所なし" if not bad else "❌ 合わない: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
