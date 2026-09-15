# -*- coding: utf-8 -*-
"""JLCPCB に出す製造ファイルを書き出す。

  python fab.py     → hardware/pcb/katanori61/fab/ に
                      ガーバー一式・穴（Excellon）・部品表（BOM）・実装位置（CPL）・zip

実装を頼むのは**表面実装の部品だけ**。スルーホール（リレー・ピンヘッダ・JST・2SC1815・1N4148・
会話ボタン）は手元にある物を自分で付ける前提なので、部品表からも実装位置からも外す。
外した物は画面に一覧で出す（黙って落とさない）。
"""

import csv
import math
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import kisym  # noqa: E402
from kisym import find, find1  # noqa: E402

from kicad_paths import CLI  # noqa: E402
OUT = HERE / "katanori61"
FAB = OUT / "fab"
GERBER = FAB / "gerber"      # zip にするのはここだけ（部品表と実装位置は別に上げる）
NAME = "katanori61"


def run(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("失敗: " + " ".join(args) + "\n" + r.stdout + r.stderr)


def parts():
    """基板から (ref, 値, 足形, LCSC, x, y, 回転, 実装するか) を読む。"""
    pcb = kisym.parse((OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    out = []
    for f in find(pcb, "footprint"):
        props = {str(p[1]): str(p[2]) for p in find(f, "property")}
        ref = props.get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        at = find1(f, "at")
        attr = find1(f, "attr")
        kind = str(attr[1]) if attr else ""
        smd = kind == "smd"
        out.append(dict(ref=ref, value=props.get("Value", ""), fp=str(f[1]),
                        lcsc=props.get("LCSC", ""), x=float(at[1]), y=float(at[2]),
                        rot=float(at[3]) if len(at) > 3 else 0.0, smd=smd))
    return out


def main():
    FAB.mkdir(parents=True, exist_ok=True)
    if GERBER.exists():
        shutil.rmtree(GERBER)
    GERBER.mkdir()
    pcb = str(OUT / f"{NAME}.kicad_pcb")
    # 🔴 --check-zones: 基板ファイルにはベタの塗りを保存していないので、書き出しのとき塗り直す。無いと GND ベタが空のガーバーになる（2026-09-16 夕に発見。それまでの fab の B_Cu は塗り 0 面だった）
    run("pcb", "export", "gerbers", "-o", str(GERBER) + "\\", "--no-protel-ext", "--check-zones",
        "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts", pcb)
    run("pcb", "export", "drill", "-o", str(GERBER) + "\\", "--format", "excellon",
        "--drill-origin", "absolute", "--excellon-units", "mm", "--excellon-separate-th", pcb)

    ps = parts()
    smd = [p for p in ps if p["smd"]]
    tht = [p for p in ps if not p["smd"]]
    missing = [p["ref"] for p in smd if not p["lcsc"]]
    if missing:
        sys.exit("LCSC の番号が無い表面実装の部品: " + ", ".join(sorted(missing)))

    # 部品表（JLCPCB の列名）: **LCSC の番号と足形**でまとめる（値の綴りが 1k / 1K と
    # 揺れていても同じ部品なので 1 行にする）
    groups = {}
    for p in smd:
        groups.setdefault((p["fp"], p["lcsc"]), []).append(p)
    with open(FAB / "bom.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "JLCPCB Part #"])
        for (fp, lcsc), ps2 in sorted(groups.items(), key=lambda kv: kv[1][0]["ref"]):
            w.writerow([ps2[0]["value"], ",".join(sorted(p["ref"] for p in ps2)),
                        fp.split(":")[-1], lcsc])

    # 実装位置（CPL）は KiCad に出させて、列の名前だけ JLCPCB に合わせる
    # （座標の向きを自分で計算すると間違える。出どころは KiCad ただ 1 つにする）
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front",
        "--smd-only", "--exclude-dnp", "-o", str(FAB / "_pos.csv"), pcb)
    with open(FAB / "_pos.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(FAB / "cpl.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            w.writerow([r["Ref"], r["PosX"], r["PosY"], r["Side"], r["Rot"]])
    (FAB / "_pos.csv").unlink()

    zip_path = OUT / f"{NAME}_gerber"
    shutil.make_archive(str(zip_path), "zip", GERBER)
    print(f"ガーバーと穴 → {FAB}（zip: {zip_path}.zip）")
    print(f"部品表 {len(groups)} 種類・{len(smd)} 個 → {FAB / 'bom.csv'}")
    print(f"実装位置 {len(smd)} 個 → {FAB / 'cpl.csv'}")
    print("実装を頼まない（自分で付ける）部品 %d 個: %s"
          % (len(tht), ", ".join(sorted(p["ref"] for p in tht))))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
