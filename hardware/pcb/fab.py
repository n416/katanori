# -*- coding: utf-8 -*-
"""JLCPCB に出す製造ファイルを書き出す。

  python fab.py     → hardware/pcb/katanori61/fab/ に
                      ガーバー一式・穴（Excellon）・部品表（BOM）・実装位置（CPL）・zip

実装を頼むのは**表面実装の部品だけ**。スルーホール（リレー・ピンヘッダ・JST・2SC1815・1N4148・
会話ボタン）は手元にある物を自分で付ける前提なので、部品表からも実装位置からも外す。
外した物は画面に一覧で出す（黙って落とさない）。

🔴 **CPL の回転は KiCad の値をそのまま渡さない**（JLC_ROT・2026-09-17）。回した部品と、
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

# ---- CPL の回転の補正（2026-09-17）----
# 🔴 KiCad が出す回転をそのまま CPL に書くと、極性のある部品が回って載る。
#   JLCPCB は **自分の部品ライブラリの向き**を 0 度として CPL の角度を足すので、
#   KiCad の足形の 0 度と揃っていない足形はその差だけずれる。差は (足形, 品番) ごとに決まる。
#   ⇒ CPL の角度 ＝ (KiCad の角度 ＋ 下の補正) % 360。
#
# ⚠ **正規表現の表（JLCKicadTools の cpl_rotations_db.csv）をそのまま回さないこと。**
#   この板の 14 種類に当てると 6 種類しか拾わず、**U1 と J13 を黙って素通りさせる**
#   （2026-09-17 に実際に走らせて確かめた）:
#     ・`^(.*?_|V)?QFN-(16|20|24|28|40)` は `Texas_RSA_VQFN-16…` に当たらない
#       （`.*?_` は `Texas_RSA_` までしか食えず、次が `VQFN` になる）
#     ・`^USB_C_Receptacle_HRO_TYPE-C-31-M-12*` は、前の足を外して**改名した**
#       `USB_C_HRO_TYPE-C-31-M-12_NoFrontLegs` に当たらない
#   拾えないのが USB-C と昇圧 IC なので、「補正した」という安心だけが残る。
#   ⇒ **足形の名前ちょうどの表**にして、0 の物も出どころを書く。表に無い足形が出たら止める。
#
# 出どころの印:
#   📄 = 公開の補正表に当たる（https://github.com/matthewlai/JLCKicadTools
#        jlc_kicad_tools/cpl_rotations_db.csv・当てた正規表現を併記）
#   ⚠  = 表に**当たらない**ので系統から見た類推。**発注のプレビューで必ず向きを見る**
#   ?  = 極性はあるが表に項目が無い ＝ 揃っているとみて 0。ついでにプレビューで見る
#   ―  = 2 本足で向きが無い
JLC_ROT = {
    # 極性のある物
    "SOT-23": (-90, "📄 `^SOT-23`"),
    "QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm": (270, "📄 `^(.*?_|V)?QFN-(16|20|24|28|40)(-|_|$)`"),
    "TSSOP-10_3x3mm_P0.5mm": (270, "📄 `^TSSOP-`"),
    "SOIC-8_3.9x4.9mm_P1.27mm": (270, "📄 `^SOIC-`"),
    "Texas_RSA_VQFN-16-1EP_4x4mm_P0.65mm_EP2.7x2.7mm":
        (270, "⚠ 表の VQFN の行に当たらない。QFN の系統から 270 と置いた"),
    # ⭐ 2026-09-17: 足形を自作の NoFrontLegs から **素の 4 本足**へ戻した（胴の出が 1.3 に下がり、
    #   前寄りのシェルの足が板に載るようになったため）。改名していないので表にそのまま当たる。
    "USB_C_Receptacle_HRO_TYPE-C-31-M-12":
        (180, "📄 `^USB_C_Receptacle_HRO_TYPE-C-31-M-12*`"),
    "D_SOD-123": (0, "? 表に項目が無い（＝揃っているとみる）"),
    "LED_0805_2012Metric": (0, "? 表に項目が無い（＝揃っているとみる）"),
    "Relay_DPDT_Omron_G6S-2F": (0, "? 表にあるのは G6K-2F-Y（別品）で G6S には当たらない"),
    # 向きの無い物（2 本足・または表に項目が無い）
    "R_0603_1608Metric": (0, "― 2 本足"),
    "R_0805_2012Metric": (0, "― 2 本足"),
    "R_1206_3216Metric": (0, "― 2 本足"),
    "C_0805_2012Metric": (0, "― 2 本足"),
    "C_1206_3216Metric": (0, "― 2 本足"),
    "L_Changjiang_FNR4018S": (0, "― 2 本足"),
}


def jlc_rotation(fp_short, kicad_rot):
    """KiCad の回転を JLCPCB の CPL の回転に直す。→ (角度, 補正, 出どころ)"""
    corr, src = JLC_ROT[fp_short]
    return (kicad_rot + corr) % 360, corr, src


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
    # 🔴 回転だけは KiCad の値をそのまま渡さない（JLC_ROT を見よ）。
    #   表に無い足形が出たら**止める**。0 でも出どころを書かせるため
    fp_of = {p["ref"]: p["fp"].split(":")[-1] for p in ps}
    unknown = sorted({fp_of[r["Ref"]] for r in rows if fp_of[r["Ref"]] not in JLC_ROT})
    if unknown:
        sys.exit("回転の補正が決まっていない足形: " + ", ".join(unknown)
                 + "\n  fab.py の JLC_ROT に (補正角, 出どころ) を足すこと。0 でも出どころを書く。")
    turned, watch, maybe = [], [], []
    with open(FAB / "cpl.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            fp = fp_of[r["Ref"]]
            rot, corr, src = jlc_rotation(fp, float(r["Rot"]))
            w.writerow([r["Ref"], r["PosX"], r["PosY"], r["Side"], f"{rot:.6f}"])
            if corr:
                turned.append((r["Ref"], fp, float(r["Rot"]), corr, rot, src))
            if src.startswith("⚠"):
                watch.append((r["Ref"], fp, rot, src))
            elif src.startswith("?"):
                maybe.append(r["Ref"])
    (FAB / "_pos.csv").unlink()

    zip_path = OUT / f"{NAME}_gerber"
    shutil.make_archive(str(zip_path), "zip", GERBER)
    print(f"ガーバーと穴 → {FAB}（zip: {zip_path}.zip）")
    print(f"部品表 {len(groups)} 種類・{len(smd)} 個 → {FAB / 'bom.csv'}")
    print(f"実装位置 {len(smd)} 個 → {FAB / 'cpl.csv'}")
    print("実装を頼まない（自分で付ける）部品 %d 個: %s"
          % (len(tht), ", ".join(sorted(p["ref"] for p in tht))))
    print(f"回転の補正（KiCad → JLCPCB）: {len(turned)} 個を回した")
    for ref, fp, k, corr, rot, src in sorted(turned):
        print(f"  {ref:5s} {fp:48s} {k:+6.0f} {corr:+5d} → {rot:5.0f}   {src}")
    if watch:
        print(f"🔴 発注のプレビューで向きを見る部品 {len(watch)} 個"
              "（公開の補正表に当たらない ＝ 出どころが類推）:")
        for ref, fp, rot, src in sorted(watch):
            print(f"  {ref:5s} {fp:48s} → {rot:5.0f}   {src}")
    if maybe:
        print("  ついでに見る（極性はあるが表に項目が無く 0 のまま）: "
              + ", ".join(sorted(maybe)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
