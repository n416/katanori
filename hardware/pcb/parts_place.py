# -*- coding: utf-8 -*-
"""板の上の部品を「板の座標・足跡・背の高さ」で一覧にする。

  python parts_place.py            → 標準出力へ
  python parts_place.py -o FILE    → ファイルへ

🔴 読むのは **生成済みの hub_power.kicad_pcb**（gen_pcb.py の PLACE ではない）。
   PLACE は置き場所の狙いで、relax() が重なりを押し離したあとの実位置とは違う。
🔴 背の高さは gen_pcb.py の HEIGHT。**出どころ（📄 かどうか）を必ず一緒に出す。**
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kisym  # noqa: E402
from kisym import find, find1  # noqa: E402
import gen_pcb as G  # noqa: E402

PCB = pathlib.Path(__file__).parent / "hub_power" / "hub_power.kicad_pcb"


def rows():
    pcb = kisym.parse(PCB.read_text(encoding="utf-8"))[0]
    out = []
    for f in find(pcb, "footprint"):
        ref = [str(p[2]) for p in find(f, "property") if str(p[1]) == "Reference"]
        val = [str(p[2]) for p in find(f, "property") if str(p[1]) == "Value"]
        if not ref or ref[0] not in G.PLACE:
            continue
        at = find1(f, "at")
        x, y = float(at[1]), float(at[2])
        ang = float(at[3]) if len(at) > 3 else 0.0
        # 🔴 置いた足形の**図形は回っていない**（KiCad が描くときに回す）。角度を渡すこと
        b = G.courtyard(f, x, y, ang)
        hgt, src = G.HEIGHT.get(ref[0], G.HEIGHT_DEFAULT)
        out.append(dict(ref=ref[0], val=val[0] if val else "", ang=ang,
                        x=x - G.ORG[0], y=G.BOARD_W - (y - G.ORG[1]),
                        x0=b[0] - G.ORG[0], x1=b[2] - G.ORG[0],
                        y0=G.BOARD_W - (b[3] - G.ORG[1]), y1=G.BOARD_W - (b[1] - G.ORG[1]),
                        h=hgt, src=src))
    out.sort(key=lambda r: (-r["h"], r["ref"]))
    return out


# 🔴 線が出る口だけは **筐体の座標（箱）**でも出す。筐体・機構の 2 人が使うのはこちら。
#    箱 = 板 + G.BOX。ここで変換を 1 か所に閉じておかないと、渡すたびに足し算を間違える
DIR_NAME = {(0, 1): "−Y（下へ）", (0, -1): "＋Y（上へ）",
            (-1, 0): "−X（左へ）", (1, 0): "＋X（右へ）"}
BODY = 3.1      # 相手のハウジングが枠の縁から出る量。📄 2 ページ (9.6) − 📄 4 ページ 6 = 3.6、
                # から courtyard の逃げ 0.5 を引いた値


def ports(rs):
    """線が出る口を、箱の座標・線の向き・プラグの通り道つきで出す。"""
    dx0, dy0 = G.BOX
    r = {x["ref"]: x for x in rs}
    o = ["", "## 線が出る口 — **筐体の座標（箱）**", "",
         f"**箱 = 板 + {G.BOX}**（向きは同じ・回転も鏡も無い）。",
         "🔴 **線が出るのはこの 5 つだけ。**J1・J14 は ReSpeaker のピンヘッダが真上から挿さる所で線は 0 本。", "",
         "| ref | 何 | 箱 X | 箱 Y | 背 | 線が抜ける向き |", "|---|---|---|---|---|---|"]
    rows_ = []
    for ref in G.CONN:
        v = r.get(ref)
        if v is None:
            continue
        side, need = G.CONN[ref]
        d = G.OPEN_DIR[(side, int(v["ang"]))]
        b = (v["x0"] + dx0, v["x1"] + dx0, v["y0"] + dy0, v["y1"] + dy0)
        rows_.append((ref, v, d, b, need))
        o.append(f"| {ref} | {v['val']} | {b[0]:.2f}〜{b[1]:.2f} | {b[2]:.2f}〜{b[3]:.2f} | "
                 f"{v['h']:.2f} | **{DIR_NAME[d]}** |")
    o += ["", "### プラグの通り道（箱）", "",
          "🔴 **「相手の実体」は必ず要る。**そこに殻の肉があると挿さらない。",
          "残りは指と線の曲がりのぶんで、板側の検査はこの 10.0 で回している。", "",
          "| ref | 相手の実体（枠の縁から 3.1） | 指と曲げまで（10.0） |", "|---|---|---|"]
    for ref, v, (dx, dy), b, need in rows_:
        def band(n):
            if dx:
                return (f"X {b[1]:.2f}〜{b[1] + n:.2f}" if dx > 0 else f"X {b[0] - n:.2f}〜{b[0]:.2f}")
            return (f"Y {b[2] - n:.2f}〜{b[2]:.2f}" if dy > 0 else f"Y {b[3]:.2f}〜{b[3] + n:.2f}")
        o.append(f"| {ref} | {band(BODY)} | {band(need)} |")
    o.append("")
    o.append("⚠ **板の縁を越える帯がある**（下の縁は箱 Y 3.0・上の縁は箱 Y 84.2）。"
             "板の上に障害物が無いので板側の検査は通るが、**殻の側で空けてもらう必要がある。**")
    return o


def main():
    o = ["# 中継基板（v6）の部品 — 板の座標・足跡・背の高さ", "",
         f"外形 {G.BOARD_L} × {G.BOARD_W}・板厚 1.6。座標は **板の左下が原点・X 右・Y 上**。",
         "部品はすべて **F.Cu（ReSpeaker を向く面）** にあり、**B.Cu には 1 つも無い**。",
         "枠は courtyard（KiCad の足形が持つ占有の枠）。**背は板の面から。**", "",
         "🔴 **出どころの印**: 📄 ＝ データシート／図面で取った ／ ⚠ ＝ 一般値（未確認）", "",
         "| ref | 値 | 芯 X | 芯 Y | 回転 | 枠 X | 枠 Y | 背 | 背の出どころ |",
         "|---|---|---|---|---|---|---|---|---|"]
    rs = rows()
    for r in rs:
        o.append(f"| {r['ref']} | {r['val']} | {r['x']:.2f} | {r['y']:.2f} | {r['ang']:.0f}° | "
                 f"{r['x0']:.2f}〜{r['x1']:.2f} | {r['y0']:.2f}〜{r['y1']:.2f} | "
                 f"**{r['h']}** | {r['src']} |")
    o += ["", f"合計 {len(rs)} 部品。"] + ports(rs) + [
          "", "## 板に開いている穴（部品ではない）", "",
          "| 何 | 板の座標 | 径 |", "|---|---|---|"]
    for px, py, d in G.POSTS:
        o.append(f"| 柱の抜き | ({px}, {py}) | φ{d} |")
    for mx, my in G.MOUNT:
        o.append(f"| 取付穴 M2 | ({mx}, {my}) | φ{G.MOUNT_D} |")
    o.append(f"| 切り欠き | X {G.NOTCH[0]}〜{G.NOTCH[1]}・Y {G.NOTCH[2]} から上端 | — |")
    txt = "\n".join(o) + "\n"
    if len(sys.argv) > 2 and sys.argv[1] == "-o":
        pathlib.Path(sys.argv[2]).write_text(txt, encoding="utf-8")
        print(f"{len(rs)} 部品 → {sys.argv[2]}")
    else:
        print(txt)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
