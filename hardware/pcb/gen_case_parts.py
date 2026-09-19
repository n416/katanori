# -*- coding: utf-8 -*-
"""置いてある基板から、筐体の `PCB_PARTS` を**丸ごと生成**する（2026-09-16 夕）。

    python hardware/pcb/gen_case_parts.py        → hardware/pcb/v61_parts.scad を書く
    python hardware/pcb/gen_case_parts.py --list → 表を画面に出すだけ（書かない）

なぜ作ったか
------------
筐体の `case_v6_1.scad` が持っていた `PCB_PARTS` は**手書きの 9 行**で、板に載る 55 個のうち
46 個が模型に存在しなかった。存在しない物には当たらないので、当たり検査の 0 は
「問題なし」ではなく「**見ていない**」を意味していた（docs/HANDOFF-2026-09-16.md 3.3）。
J4・J6 の口の向きを「空いているから縦にできる」と言いかけたのも、その空きが
**46 個抜けた模型で測った空き**だったためである。

⇒ 手書きの表を 9 個から育てるのをやめ、**`katanori61.kicad_pcb` から起こす**。
   板が動けばこの道具を回し直すだけで筐体の模型が追いつく。

何を基板から取り、何を手で持つか
--------------------------------
基板から取る（動かせない・置き直せば変わる）:
  ・平面の形  … **胴（F.Fab / B.Fab）**の外接枠。courtyard は KiCad が付けた逃げ込みの
                「置き場所の予約」で物の形ではないので使わない
  ・面        … F.Cu / B.Cu
  ・足の枠    … 板を貫くパッド（thru_hole / np_thru_hole）の外接枠

手で持つ（基板ファイルに書いていない）:
  ・背        … `gen_pcb.py` の HEIGHT（📄 が付いた物はデータシート・⚠ は一般値）
  ・抜く向き・通り道・足の長さ … 下の PORTS。口だけが持つ
"""

import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_pcb as G                     # noqa: E402  HEIGHT と板の座標系をここから借りる
import v61_board as VB                  # noqa: E402

K3D = G.FPDIR.parent / "3dmodels"      # KiCad が同梱している 3D モデル（足形と同じ置き場の隣）
PCB = HERE / "katanori61" / "katanori61.kicad_pcb"
OUT = HERE / "v61_parts.scad"

# ---- 口だけが持つ物（基板ファイルに書いていない）----
#   向き: +1 +Y / −1 −Y / +3 +X / −3 −X / +2 上（板から離れる）/ −2 下（板から離れる）/ 0 なし
#   通り道: 嵌合した相手のハウジングが胴の外へ出る量。JST-PH は 2.0（📄 ePH.pdf 1 ページ）
#   足: 板を貫いて反対の面へ出る長さ
PH_MATE_OUT = 2.0
TH_LEG = 1.8        # ⚠ 一般値。スルーホールのポストが板（1.6）を貫いた残り
RISER_LEG = 3.0     # 🔒 2.54 ヘッダの規格の姿（樹脂 2.5・ピン 6.0・足 3.0）
# 🔴 筐体は名前で引く（pcb_part("J10 BAT") / pcb_mouth("J4  SPK IN") / j5_frame()）。
#    ここの綴りを変えると筐体側が undef になって黙って壊れるので、既存の綴りをそのまま使う
CASE_NAME = {"J4": "J4  SPK IN", "J5": "J5  SPK OUT", "J6": "J6  BTN2",
             "J7": "J7  REED", "J10": "J10 BAT", "SW2": "SW2 POWER",
             "J1": "J1  RISER XIAO", "J2": "J2  RISER OLED", "K31": "K31 RELAY"}
PORTS = {
    "J4":  (2,  PH_MATE_OUT, TH_LEG, "スピーカー IN。**縦**・上へ抜く（2026-09-16 夕に横出しから）"),
    "J5":  (-3, PH_MATE_OUT, TH_LEG, "スピーカー OUT。横出し・口は −X（左の縁）"),
    "J6":  (2,  PH_MATE_OUT, TH_LEG, "会話ボタン。**縦**・上へ抜く（2026-09-16 夕に横出しから）"),
    "J7":  (2,  PH_MATE_OUT, TH_LEG, "リード。縦・上へ抜く（2026-09-19 にトグルをやめて 2 ピン）"),
    "J10": (-2, PH_MATE_OUT, TH_LEG, "電池。板の裏・縦・下へ抜く"),
    "J1":  (0,  0.0, RISER_LEG, "XIAO のライザーを受けるオスのピンヘッダ 1x07"),
    "J2":  (0,  0.0, RISER_LEG, "OLED のライザーを受けるオスのピンヘッダ 1x04"),
    "J13": (0,  0.0, 0.0, "充電の USB-C。口は板の**後ろの縁（ハッチ側）**の X 中央から 1.3 外へ出る（筐体は別に持っている）"),
}
# 背が HEIGHT に無く、既定（1.45）だと実物と違う物。⚠ が付く物は一般値
HEIGHT_FIX = {
    # gen_pcb.py の HEIGHT を直したので、いまここに置く物は無い。
    # 表と実物が食い違ったらまず gen_pcb.py の HEIGHT を直すこと（あそこが出どころ）
}
# データシートの外形がリードを含む物は、胴と足を分けて置く（背の高い胴だけが蓋に当たる）
SPLIT = {
    "K31": (0.5, "G6S-2F のリード。データシートの 15.3 × 10.7 はリード込みの外形で、"
                 "背 9.33 の胴は 14.8 × 7.4（KiCad の F.Fab）"),
}


def toks(s):
    out = []
    stack = [out]
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "(":
            new = []
            stack[-1].append(new)
            stack.append(new)
            i += 1
        elif c == ")":
            stack.pop()
            i += 1
        elif c == '"':
            j = s.index('"', i + 1)
            stack[-1].append(s[i + 1:j])
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in "()":
                j += 1
            stack[-1].append(s[i:j])
            i = j
    return out[0]


def allof(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def get(node, key):
    r = allof(node, key)
    return r[0] if r else None


def layer_box(fp, want):
    """その層の図形の外接枠（足形の局所座標）。"""
    xs, ys = [], []

    def walk(n):
        if isinstance(n, list):
            if n and n[0] in ("fp_line", "fp_poly", "fp_rect", "fp_circle", "fp_arc"):
                lay = get(n, "layer")
                if lay and want in str(lay[1]):
                    for k in ("start", "end", "center", "mid"):
                        for e in allof(n, k):
                            xs.append(float(e[1]))
                            ys.append(float(e[2]))
                    for pts in allof(n, "pts"):
                        for e in allof(pts, "xy"):
                            xs.append(float(e[1]))
                            ys.append(float(e[2]))
            for e in n:
                if isinstance(e, list):
                    walk(e)
    walk(fp)
    return (min(xs), max(xs), min(ys), max(ys)) if xs else None


def read_board():
    d = toks(PCB.read_text(encoding="utf-8"))
    edge = []
    for fam in ("gr_line", "gr_rect", "gr_poly", "gr_arc"):
        for g in allof(d, fam):
            lay = get(g, "layer")
            if lay and lay[1] == "Edge.Cuts":
                for k in ("start", "end", "center", "mid"):
                    for e in allof(g, k):
                        edge.append((float(e[1]), float(e[2])))
    ox = min(p[0] for p in edge)
    oy1 = max(p[1] for p in edge)

    rows = []
    for fp in allof(d, "footprint"):
        ref = None
        for pr in allof(fp, "property"):
            if pr[1] == "Reference":
                ref = pr[2]
        if not ref or ref.startswith("#"):
            continue
        at = get(fp, "at")
        fx, fy = float(at[1]), float(at[2])
        ang = float(at[3]) if len(at) > 3 else 0.0
        a = math.radians(ang)
        back = get(fp, "layer")[1].startswith("B.")

        def place(b):
            if not b:
                return None
            pts = [(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))
                   for x in (b[0], b[1]) for y in (b[2], b[3])]
            return (fx + min(p[0] for p in pts) - ox, fx + max(p[0] for p in pts) - ox,
                    oy1 - (fy + max(p[1] for p in pts)), oy1 - (fy + min(p[1] for p in pts)))

        crt = place(layer_box(fp, "CrtYd"))
        fab = place(layer_box(fp, "Fab")) or crt
        xs, ys = [], []
        for pd in allof(fp, "pad"):
            if pd[2] not in ("thru_hole", "np_thru_hole"):
                continue
            pat = get(pd, "at")
            lx, ly = float(pat[1]), float(pat[2])
            prot = float(pat[3]) if len(pat) > 3 else 0.0
            sz = get(pd, "size")
            w, h = float(sz[1]), float(sz[2])
            if abs((ang + prot) % 180 - 90) < 1e-6:
                w, h = h, w
            gx = fx + lx * math.cos(a) + ly * math.sin(a)
            gy = fy - lx * math.sin(a) + ly * math.cos(a)
            xs += [gx - ox - w / 2, gx - ox + w / 2]
            ys += [oy1 - gy - h / 2, oy1 - gy + h / 2]
        legbox = (min(xs), max(xs), min(ys), max(ys)) if xs else None
        rows.append(dict(ref=ref, fab=fab, crt=crt, back=back, legbox=legbox,
                         fp=fp[1].split(":")[-1], fp_id=str(fp[1])))
    return sorted(rows, key=lambda r: (r["ref"][0], int("".join(c for c in r["ref"] if c.isdigit()) or 0)))


# ---- 背を KiCad の 3D モデル（STEP）から測る（2026-09-16 夕）----
# 🔒 ユーザー「そもそもだけど、表面実装の抵抗とかがなんでこんな分厚いの？ 全部同じような形してるし」
#   そのとおりで、それまで背は `gen_pcb.py` の HEIGHT_DEFAULT（1.45）を 45 個に配っていた。
#   1.45 は「0805 の抵抗とコンデンサと LED はこれ以下」という**上限**で、実寸ではない。
#   0805 の抵抗の実際は **0.45** で、3.2 倍厚く描いていた。
#
# ⇒ 足形が指している STEP を読んで、点の Z の最大を背にする。
#   出どころは KiCad が同梱している 3D モデルで、手元で読み直せる。
#
# 🔴 手の値が勝つのは、出どころが 📄（データシート）か 🔒（ユーザー／担当の決め）のときだけ。
#   ピンヘッダ（J1・J2）がその例で、STEP はピンの 6.0 まで入って 8.5 になるが、
#   要るのは板の上に立っている樹脂 2.5 である（ピンはライザーの裏の L 字が咥える）。
_STEP_CACHE = {}


def step_height(fp_id):
    """足形が指している STEP の Z の最大（mm）。見つからなければ None。"""
    if fp_id in _STEP_CACHE:
        return _STEP_CACHE[fp_id]
    out = None
    try:
        fp = G.load_fp(fp_id)
        mdl = None
        for e in fp:
            if isinstance(e, list) and e and e[0] == "model":
                mdl = str(e[1])
                break
        if mdl:
            tail = mdl.split("}", 1)[-1].lstrip("/\\")
            q = K3D / tail
            if q.exists():
                t = q.read_text(encoding="utf-8", errors="replace")
                zs = [float(m.group(1)) for m in re.finditer(
                    r"CARTESIAN_POINT\s*\(\s*''\s*,\s*\(\s*[-0-9.E+]+\s*,\s*[-0-9.E+]+\s*,\s*([-0-9.E+]+)\s*\)", t)]
                if zs:
                    out = round(max(zs), 2)
    except SystemExit:
        out = None
    _STEP_CACHE[fp_id] = out
    return out


def height_of(ref, fp_id=None):
    if ref in HEIGHT_FIX:
        return HEIGHT_FIX[ref]
    hand = G.HEIGHT.get(ref)
    if hand and (hand[1].startswith("📄") or hand[1].startswith("🔒")):
        return hand                       # データシート／決めが勝つ
    if fp_id:
        z = step_height(fp_id)
        if z:
            return (z, "📐 KiCad の 3D モデル（STEP）の Z の最大")
    return hand or G.HEIGHT_DEFAULT


def build():
    rows = read_board()
    out = []
    for r in rows:
        ref = r["ref"]
        h, src = height_of(ref, r.get("fp_id"))
        d, path, leg, note = PORTS.get(ref, (0, 0.0, 0.0, ""))
        if not r["legbox"]:
            leg = 0.0
        lb = r["legbox"] or r["fab"]
        out.append(dict(ref=ref, fab=r["fab"], h=h, src=src, dirn=d, path=path,
                        leg=leg, legbox=lb, side=-1 if r["back"] else 1,
                        note=note, fp=r["fp"]))
        if ref in SPLIT:
            lh, lnote = SPLIT[ref]
            # リードは courtyard（＝リード込みの外形）で置く
            out.append(dict(ref=ref + " LEADS", fab=r["crt"], h=lh, src=lnote, dirn=0,
                            path=0.0, leg=0.0, legbox=r["crt"], side=1, note=lnote, fp=r["fp"]))
    return out


def fmt(rows):
    lines = []
    lines.append("// ⚠ この表は **生成物**である。手で書き換えないこと。")
    lines.append("//   出どころ: hardware/pcb/katanori61/katanori61.kicad_pcb")
    lines.append("//   作り直し: python hardware/pcb/gen_case_parts.py")
    lines.append("//   板が動いたら回し直す。平面の形は**胴（F.Fab）**で、courtyard の逃げは入っていない。")
    lines.append("//")
    lines.append("//   [名前, x0, x1, y0, y1, 背, 抜く向き, 面, 通り道, 足, 足の枠]")
    lines.append("PCB_PARTS = [")
    for r in rows:
        if r["fab"] is None:
            continue
        f = r["fab"]
        lb = r["legbox"]
        legbox = "[%.3f, %.3f, %.3f, %.3f]" % lb if r["leg"] > 0 else "[]"
        note = ("   // " + r["fp"] + ("・" + r["note"] if r["note"] else "")
                + "・背 " + r["src"])
        nm = CASE_NAME.get(r["ref"], r["ref"])
        if r["ref"].endswith(" LEADS"):
            nm = CASE_NAME.get(r["ref"][:-6], r["ref"][:-6]) + " LEADS"
        lines.append('    [%-18s, %8.3f, %8.3f, %8.3f, %8.3f, %5.2f, %2d, %2d, %4.1f, %4.1f, %s],%s'
                     % ('"' + nm + '"', f[0], f[1], f[2], f[3], r["h"], r["dirn"], r["side"],
                        r["path"], r["leg"], legbox, note))
    lines.append("];")
    # ⭐ 2026-09-19: つまみの軸のガイドの足の穴（v61_board.GUIDE_HOLES・板の座標）。筐体のガイド（case_v6_1.scad の kguide）がここから引く
    lines.append("PCB_GUIDE_HOLES = [%s];   // 軸のガイドの足の穴（板の座標）。出どころ: hardware/pcb/v61_board.py の GUIDE_HOLES"
                 % ", ".join("[%.3f, %.3f]" % h for h in VB.GUIDE_HOLES))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    rows = build()
    real = [r for r in rows if r["fab"]]
    print("板の上の物 %d 個を基板ファイルから起こした" % len(real))
    tall = sorted((r for r in real), key=lambda r: -r["h"])[:8]
    print("背の高い順:", "・".join("%s %.2f" % (r["ref"], r["h"]) for r in tall))
    est = [r["ref"] for r in real if r["src"].startswith("⚠")]
    meas = [r for r in real if r["src"].startswith("📐")]
    print("背を 3D モデルで測った: %d 個 ／ ⚠ 一般値のまま: %d 個 %s"
          % (len(meas), len(est), (" … " + " ".join(est)) if est else ""))
    ch = [(r["ref"], G.HEIGHT.get(r["ref"], G.HEIGHT_DEFAULT)[0], r["h"]) for r in meas]
    ch = [c for c in ch if abs(c[1] - c[2]) > 0.05]
    if ch:
        print("前と 0.05 以上ちがう %d 個:" % len(ch))
        for ref, a, b in sorted(ch, key=lambda c: -(c[1] - c[2]))[:12]:
            print("   %-5s %.2f → %.2f" % (ref, a, b))
    if "--list" not in sys.argv:
        OUT.write_text(fmt(rows), encoding="utf-8")
        print("→", OUT)
