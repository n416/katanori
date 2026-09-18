# -*- coding: utf-8 -*-
"""JLCPCB に出す製造ファイルを書き出す。

  python fab.py     → hardware/pcb/katanori61/fab/ に
                      ガーバー一式・穴（Excellon）・部品表（BOM）・実装位置（CPL）・zip

実装を頼むのは**表面実装の部品だけ**。スルーホール（リレー・ピンヘッダ・JST・2SC1815・1N4148・
会話ボタン）は手元にある物を自分で付ける前提なので、部品表からも実装位置からも外す。
外した物は画面に一覧で出す（黙って落とさない）。

🔴 **CPL の回転と位置は KiCad の値をそのまま渡さない**（jlc_fp.py・2026-09-18）。回した部品と、
   プレビューで目で見るべき部品を最後に一覧で出す。
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
import jlc_fp  # noqa: E402
from kisym import find, find1  # noqa: E402

from kicad_paths import CLI  # noqa: E402
OUT = HERE / "katanori61"
FAB = OUT / "fab"
def board_copper(pcb):
    """板の .kicad_pcb に書いてある銅の層を、上から順に返す。"""
    import re as _re
    t = pathlib.Path(pcb).read_text(encoding="utf-8")
    i = t.index("(layers")
    j = t.index("Edge.Cuts", i)
    lays = _re.findall('"((?:F|B|In[0-9]+)[.]Cu)"', t[i:j])
    def rank(n):                      # F.Cu → 0 / In1.Cu → 1 / … / B.Cu → 99
        if n == "F.Cu":
            return 0
        if n == "B.Cu":
            return 99
        return int(n[2:n.index(".")])
    return sorted(set(lays), key=rank)


GERBER = FAB / "gerber"      # zip にするのはここだけ（部品表と実装位置は別に上げる）
NAME = "katanori61"

# ---- CPL の回転と位置の補正 ----
# 🔴 KiCad が出す回転と位置をそのまま CPL に書くと、極性のある部品が回って・ずれて載る。
#   JLCPCB は **品番ごとの自分の足形**（EasyEDA）の 0 度に CPL の角度を足し、その足形の原点を CPL の座標に置く。
#   ⇒ 品番の足形を KiCad の足形に重ねて、角度と原点のずれを出す（jlc_fp.py）。
#
# ⭐ 2026-09-18: 前は公開の補正表（JLCKicadTools）を足形の名前で当てていた。いまの JLCPCB の足形と重ねると
#   U1（+270 → 0）・Q2 / Q31（−90 → 180）・K31（0 → 270・原点 1.27）・J13（180 → 0・原点 1.57）が違っていた。
#   その前（2026-09-17）は、表の正規表現が U1 と J13 を拾わないので名前ちょうどの表にしていた。
#
# 🔴 品番に EasyEDA の足形が無ければ**止める**（品番を替える）。「プレビューで見る」で逃がさない ──
#   足形が無ければ JLCPCB のプレビューにも正しい向きは出ず、誰も確かめられない（2026-09-18・Q1 の CBI 品で起きた）


def kicad_pads(f):
    """足形の中のパッド（回転前の足形の座標・Y 下向き）→ {番号: [(x, y), …]}"""
    pads = {}
    for p in find(f, "pad"):
        n = str(p[1])
        if n:
            at = find1(p, "at")
            pads.setdefault(n, []).append((float(at[1]), float(at[2])))
    return pads


def jlc_place(p, kicad_rot, x_up, y_up):
    """KiCad の 1 行を JLCPCB の CPL の 1 行に直す。→ (x, y, 角度, 補正, 出どころ)。座標は Y 上向き。"""
    fp = p["fp"].split(":")[-1]
    s = jlc_fp.solve(fp, p["pads"], p["lcsc"])
    if s is None:
        sys.exit(f"{p['ref']} {p['lcsc']}: EasyEDA に足形が無い ＝ 実装の向きを誰も確かめられない。"
                 "同じ部品で足形のある品番へ替えること（gen_sch.py の LCSC）")
    corr = s["corr"]
    rot = (kicad_rot + corr) % 360
    # d は「KiCad の足形を θ 回した後の、EasyEDA のパッドの位置 − KiCad のパッドの位置」（EasyEDA の原点から見て Y 下向き）。
    #   板の上のパッド ＝ JLCPCB の原点 ＋ R(rot)·(KiCad の足形 ＋ … ) なので、JLCPCB の原点 ＝ KiCad の原点 − R(rot)·d。
    #   ⚠ 2026-09-18 に一度 ＋ で書き、check_fab.py の置いてみる検算で J13 が 3.14（1.57 の 2 倍）ずれて見つかった
    dx, dy = jlc_fp.rot(s["d"], rot)
    src = f"📐 {s['title']} に {s['n']} 個のパッドで重ねた（食い違い {s['err']:.2f}）"
    return x_up - dx, y_up + dy, rot, corr, src


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
                        rot=float(at[3]) if len(at) > 3 else 0.0, smd=smd, pads=kicad_pads(f)))
    return out


def main():
    FAB.mkdir(parents=True, exist_ok=True)
    if GERBER.exists():
        shutil.rmtree(GERBER)
    GERBER.mkdir()
    pcb = str(OUT / f"{NAME}.kicad_pcb")
    # 🔴 --check-zones: 基板ファイルにはベタの塗りを保存していないので、書き出しのとき塗り直す。無いと GND ベタが空のガーバーになる（2026-09-16 夕に発見。それまでの fab の B_Cu は塗り 0 面だった）
    run("pcb", "export", "gerbers", "-o", str(GERBER) + "\\", "--no-protel-ext", "--check-zones",
        # ⚠ 層は **板から読む**。ここに書き写すと、4 層にしたとき内層が黙って落ちる
        #   （2026-09-17・In1/In2 のガーバーが出ないまま zip ができていた）
        "--layers", ",".join(board_copper(pcb))
        + ",F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts", pcb)
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
    # 🔴 回転と位置は KiCad の値をそのまま渡さない（jlc_place を見よ）
    by_ref = {p["ref"]: p for p in ps}
    moved = []
    with open(FAB / "cpl.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            k = float(r["Rot"])
            x, y, rot, corr, src = jlc_place(by_ref[r["Ref"]], k, float(r["PosX"]), float(r["PosY"]))
            w.writerow([r["Ref"], f"{x:.6f}", f"{y:.6f}", r["Side"], f"{rot:.6f}"])
            shift = math.hypot(x - float(r["PosX"]), y - float(r["PosY"]))
            if corr or shift >= 0.3:
                moved.append((r["Ref"], by_ref[r["Ref"]]["lcsc"], k, corr, rot, shift, src))
    (FAB / "_pos.csv").unlink()

    zip_path = OUT / f"{NAME}_gerber"
    shutil.make_archive(str(zip_path), "zip", GERBER)
    print(f"ガーバーと穴 → {FAB}（zip: {zip_path}.zip）")
    print(f"部品表 {len(groups)} 種類・{len(smd)} 個 → {FAB / 'bom.csv'}")
    print(f"実装位置 {len(smd)} 個 → {FAB / 'cpl.csv'}")
    print("実装を頼まない（自分で付ける）部品 %d 個: %s"
          % (len(tht), ", ".join(sorted(p["ref"] for p in tht))))
    print(f"KiCad → JLCPCB の足形: {len(moved)} 個を回した・ずらした（ずれ 0.3 未満は書かない）")
    for ref, lcsc, k, corr, rot, shift, src in sorted(moved):
        print(f"  {ref:5s} {lcsc:10s} {k:+6.0f} {corr:+5.0f} → {rot:5.0f}  原点 {shift:.2f}   {src}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
