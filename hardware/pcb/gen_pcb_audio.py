# -*- coding: utf-8 -*-
"""音声の板（ReSpeaker Lite の場所・82.024 × 34.007・4 層・両面に部品）に部品を置き、.kicad_pcb と DSN を書く。

  python gen_sch_voice.py && python check_sch_voice.py   → 回路図（katanori61_audio/）
  python gen_pcb_audio.py                                 → katanori61_audio/katanori61_audio.kicad_pcb と .dsn
  python route.py --board katanori61_audio                → 自動配線・GND の縫い・DRC

座標（docs/VOICE-BOARD.md 11 章）: **ReSpeaker Lite と同じ「XIAO 面から見て 左から x ／ 下から b」**。
  KiCad の上から見た面（F.Cu）＝ XIAO 面（後ろ・背の高い物）、B.Cu ＝ マイク面（前・低い物だけ）。
  図面の座標へは gen_pcb.bx(x, b)（Y を反転）。筐体の世界座標は X ＝ 2.000 + x、Z ＝ 41.507 − b
  （⇒ b の小さい辺が天井側、大きい辺が床とハブの側）。

面の割り当て: Voice PE の板を**裏から見た鏡像**で写す（X を鏡、向きは 180 − a）。
  Voice PE の裏（XU316・コーデック・電源）→ この板の F.Cu（XIAO 面）
  Voice PE の表（マイク・XU316 の真裏のパスコン）→ この板の B.Cu（マイク面）
  ⇒ Voice PE の「チップの真裏にパスコン」がそのまま成り立つ。マイクは前を向く。
"""

import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_pcb as G  # noqa: E402
import gen_sch_voice as GV  # noqa: E402
import kisym  # noqa: E402
import voicepe  # noqa: E402
import dsn  # noqa: E402
from kisym import Str, find, find1  # noqa: E402

NAME = "katanori61_audio"
G.OUT = HERE / NAME
G.NAME = NAME
COPPER = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

# ======== 板の形（ReSpeaker Lite の公式 CAD・docs/RESPEAKER-LITE.md 5.6） ========
# gen_pcb の道具（bx・courtyard・place_footprint・route.py の stitch）が読む値をこの板のものに差し替える
G.BOARD_L, G.BOARD_W = 82.024, 34.007
CORNER_R = 1.27
G.NOTCHES = [(0.0, 0.0, G.BOARD_W + 1), (G.BOARD_L, G.BOARD_L, G.BOARD_W + 1)]   # 欠きは無い（幅 0 の欠き）
G.MOUNT = [(2.492, 31.577), (60.202, 2.657)]     # φ2.20・ReSpeaker Lite と同じ（v6.1 の筐体にダボは無いが、ねじ留めの余地に残す）
G.MOUNT_D = 2.20
G.POSTS = []
HOLE_KEEP_R = 2.1                                  # 穴の周りに部品を置かない半径（M2 のねじの頭 φ3.8 の半分 ＋ 0.2）

# ======== 規則（1 枚案で決めた値・docs/VOICE-BOARD.md 10 章） ========
# ⚠ パッドどうしは足形そのものが狭い（XU316 0.146・U118 0.123）ので、ネットクラスは 0.12、線・穴・ベタは kicad_dru で 0.15
TRACK, CLEAR, VIA = 0.2, 0.15, (0.45, 0.2)
PAD_PAD_MIN = 0.12

_load = G.load_fp


def load_fp(fp_id):
    lib, name = fp_id.split(":", 1)
    if lib == "voicepe":
        return kisym.parse((voicepe.PRETTY / f"{name}.kicad_mod").read_text(encoding="utf-8"))[0]
    return _load(fp_id)


G.load_fp = load_fp

# ======== 筐体が決める物（docs/VOICE-BOARD.md 11 章） ========
MIC_AT = {"U104": (5.487, 17.002), "U105": (76.487, 17.002)}   # ReSpeaker Lite の U4・U5 の中心（前板の穴がここを向く）
RISER_B = {"J21": 24.627, "J22": 9.397}                        # XIAO のピンの 2 列（1 番は x 2.932）
RISER_X0 = 2.932
SPK_BOX = (73.94, 13.04, 80.94, 20.99)                         # ReSpeaker Lite の J2（スピーカーの口）の枠


def keepouts():
    """[(x0, b0, x1, b1, 面, 入ってよい部品)]。面は "F"（XIAO 面）か "B"（マイク面）。"""
    L, W = G.BOARD_L, G.BOARD_W
    k = []
    for mx, my in G.MOUNT:
        k += [(mx - HOLE_KEEP_R, my - HOLE_KEEP_R, mx + HOLE_KEEP_R, my + HOLE_KEEP_R, s, None) for s in "FB"]
    # XIAO 面: 左右の壁のリブ（ReSpeaker の形から自動で引いてある）・ハブの板の前の縁（背 2.9 まで ⇒ ESP32 を入れない）
    k += [(0, 0, 1.7, W, "F", None), (80.35, 0, L, W, "F", None)]
    k.append((0, 31.9, L, W, "F", frozenset(r for r in GV_REFS if r not in TALL)))
    # マイク面: 床の座の唇（0.2）・OLED の L 足（0.185）・OLED のフィルム（0.185〜接触）・押さえ（上の縁を 0.3 押す）
    k += [(6.0, 31.0, 74.35, W, "B", None),
          (5.2, 0, 11.2, 0.9, "B", None), (70.9, 0, 76.9, 0.9, "B", None),
          (34.8, 15.71, 47.3, 19.21, "B", None)]
    k += [(30.5 - 0.5, 0, 35.8 + 0.5, 0.8, s, None) for s in "FB"] + [(48.0 - 0.5, 0, 50.4 + 0.5, 0.8, s, None) for s in "FB"]
    # マイク面の FPC のコネクタ（背 1.2 まで）: マイクと 1.2 を超える物を入れない（今の写しでは該当なし・保険）
    k.append((32.05, 15.71, 50.05, 19.21, "B", frozenset()))
    return k


# 背の高い物（ハブの縁の帯 b ≥ 31.9 に入れない）。ESP32 モジュール 3.2・コネクタ・インダクタ
TALL = {"U5", "J21", "J22", "J23", "L101", "L102"}
GV_REFS = set()     # build() で回路図の部品を入れる

# ======== まとまりと区画（板の座標 x0, b0, x1, b1） ========
# ESP32 はライザーの近く（画面・USB・会話ボタン・I2C の線が短い）、XU316 は真ん中、
# コーデックとアンプはスピーカーの口の近く（右）、電源はライザーの 5V の入口の近く（左の 2 列のあいだ）。
# ⚠ 音の面の詰め（スイッチング電源とマイク・コーデックの距離、GNDA）はまだ。まず置けて配線が通るかを見る
REGIONS = {
    "vpower": (8.0, 11.2, 18.8, 23.0),
    "esp": (20.2, 1.0, 40.0, 31.5),
    "xmos": (40.0, 1.0, 61.0, 31.5),
    "codec": (61.0, 1.0, 80.0, 31.5),
}
GROUP_OF = {"Power": "vpower", "DAC": "codec", "XMOS": "xmos", "ESP32": "esp"}
ESP_AT = (30.1, 16.0)                  # U5 の枠（19.5 × 20.15）の中心。ライザーの J21・J22 の枠（x 〜19.95）の右
ESP_SMALL = {"R46": (21.5, 28.0), "C43": (23.5, 28.0), "R47": (38.5, 28.0), "C44": (38.5, 4.0),
             "C45": (36.5, 4.0), "R48": (21.5, 4.0)}
BACK_EXTRA = {"J16": (54.0, 26.0), "TP1": (22.0, 3.0), "TP2": (24.5, 3.0), "TP3": (27.0, 3.0), "TP4": (29.5, 3.0),
              "C301": (9.0, 17.0), "C302": (73.0, 17.0)}


def fit(points, region, mirror_x=False):
    """点の集まりを、縦横比を保って区画の中へ縮めて置く（大きくはしない）。"""
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    w, h = max(xs) - min(xs) or 1.0, max(ys) - min(ys) or 1.0
    rx0, ry0, rx1, ry1 = region
    # 🔴 2026-09-15、区画に収まるまで縮めたら Voice PE の XU316 の周りが 0.26 倍になり、板は空いているのに
    #    XU316 とコーデックの周りだけ詰まって自動配線が進まなかった（ユーザー「これだけスカスカなのに通らない」）。
    #    ⇒ 0.45 倍より小さくしない（はみ出た分は legalize が近くの空きへ置く）
    s = max(0.45, min(1.0, (rx1 - rx0 - 3.0) / w, (ry1 - ry0 - 3.0) / h))
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    out = {}
    for r, (x, y) in points.items():
        dx = (x - cx) * s * (-1 if mirror_x else 1)
        dy = (y - cy) * s
        out[r] = ((rx0 + rx1) / 2 + dx, (ry0 + ry1) / 2 + dy)
    return out


def box_origin(fp_id, ang, cx, cy, back=False):
    """枠の中心が (cx, cy)（板の座標）に来る原点。"""
    f = load_fp(fp_id)
    if back:
        f = G.mirror_y(f)
    b = full_box(f, 0.0, 0.0, ang)
    # full_box は図面の座標（Y 下向き）。板の座標では Y を反転する
    return cx - (b[0] + b[2]) / 2, cy + (b[1] + b[3]) / 2


def build_place(comps):
    """{ref: (x, b, 角度)} と 裏に置く部品の集合。"""
    place, back = {}, set()
    vfp = voicepe.footprints()
    # --- 筐体が決める物 ---
    for r, b in RISER_B.items():
        place[r] = (RISER_X0, b, 90)          # 90°: 足が +x へ並ぶ（1 番が x 2.932）
    place["J23"] = (*box_origin(comps["J23"]["fp"], 0, (SPK_BOX[0] + SPK_BOX[2]) / 2, (SPK_BOX[1] + SPK_BOX[3]) / 2), 0)
    for r, (x, b) in MIC_AT.items():
        f = vfp[GV_SRC[r]]
        a = float(find1(f, "at")[3]) if len(find1(f, "at")) > 3 else 0.0
        place[r] = (*box_origin(comps[r]["fp"], (180 - a) % 360, x, b, back=True), round(180 - a) % 360)
        back.add(r)
    # --- マイクの足元（Voice PE で近い方のマイクからのずれを、鏡にして写す） ---
    vmic = {GV.vref(v): (float(find1(vfp[v], "at")[1]), float(find1(vfp[v], "at")[2])) for v in ("U4", "U5")}
    for vr in GV.COPY["MIC"].split():
        r = GV.vref(vr)
        if r in MIC_AT:
            continue
        f = vfp[vr]
        at = find1(f, "at")
        vx, vy = float(at[1]), float(at[2])
        near = min(vmic, key=lambda m: math.hypot(vx - vmic[m][0], vy - vmic[m][1]))
        mx, mb = MIC_AT[near]
        a = float(at[3]) if len(at) > 3 else 0.0
        # 裏から見るので X は反転（x ＝ mx − ΔX）。図面の Y は下向き、板の b は上向きなので b ＝ mb − ΔY
        place[r] = (mx - (vx - vmic[near][0]), mb - (vy - vmic[near][1]), round(180 - a) % 360)
        if str(find1(f, "layer")[1]) == "F.Cu":
            back.add(r)
    # --- Voice PE の残りのまとまり（裏から見た鏡像を区画へ縮める） ---
    for sheet, gname in GROUP_OF.items():
        pts, angs = {}, {}
        for vr in GV.COPY[sheet].split():
            f = vfp[vr]
            at = find1(f, "at")
            a = float(at[3]) if len(at) > 3 else 0.0
            r = GV.vref(vr)
            pts[r] = (float(at[1]), -float(at[2]))
            angs[r] = (180 - a) % 360
            if str(find1(f, "layer")[1]) == "F.Cu":
                back.add(r)
        for r, (x, b) in fit(pts, REGIONS[gname], mirror_x=True).items():
            place[r] = (x, b, round(angs[r]) % 360)
    # --- ESP32 と、新しく足した物 ---
    place["U5"] = (*box_origin(comps["U5"]["fp"], 0, *ESP_AT), 0)
    for r, (x, b) in ESP_SMALL.items():
        place[r] = (x, b, 0)
    for r, (x, b) in BACK_EXTRA.items():
        place[r] = (x, b, 0)
        back.add(r)
    missing = sorted(set(r for r in comps if not r.startswith("#")) - set(place))
    if missing:
        sys.exit("置き場所が決まっていない部品: " + " ".join(missing))
    return place, back


FIXED = {"J21", "J22", "J23", "U104", "U105", "U5"}

# ======== 空いた所へ置く（表と裏を分けて見る） ========
GRID = 0.1           # 占有の升目 [mm]
GAP = 0.05           # 枠どうしの最小の隙間（courtyard は元から逃げを含む）
EDGE = 0.4           # 板の縁から部品の枠まで


def margin_of(npads):
    """部品の周りに空ける幅。足の多い IC は線を引き出す余白が要る。
    🔴 2026-09-15（1 枚案）、全部 0.05 で詰めたら XU316 の 16〜25 番ピンが引き出せなかった。"""
    # 🔴 2026-09-15、2 端子を 0.1 にしたら部品の間に線が通らず、XU316 とコーデックの周りが詰まった。
    #    0.3 ＝ 隣どうしで 0.6 空く ＝ 線 0.2 ＋ すきま 0.15 × 2 が 1 本通る
    return 1.0 if npads >= 16 else 0.5 if npads >= 6 else 0.3


def exempt(k, r):
    """立入禁止 k の 6 番目（入ってよい部品。ref 1 つか集合）に r が入っているか。"""
    return k[5] is not None and (r in k[5] if isinstance(k[5], (set, frozenset)) else k[5] == r)


def legalize(boxes, side, fixed, keep, margins=None):
    """重なりの無い置き方にする（1 枚案の gen_pcb_voice.py から移した）。

    🔴 押し離し（relax）は、元の板の並びを区画へ縮めた塊を解けなかった（2026-09-15・79 組残った）。
    ⇒ 固定の物と立入禁止を先に升目へ塗り、動かせる部品を**大きい順**に、置きたい位置から
      渦巻きに外へ探して、最初に空いていた所へ置く。重なりは原理的に 0。
    """
    import numpy as np
    L, W, M = G.BOARD_L, G.BOARD_W, EDGE
    nx, ny = int(math.ceil(L / GRID)), int(math.ceil(W / GRID))
    occ = {"F": np.zeros((ny, nx), bool), "B": np.zeros((ny, nx), bool)}

    def cells(b, pad=GAP):
        return (max(0, int((b[0] - pad) / GRID)), max(0, int((b[1] - pad) / GRID)),
                min(nx, int(math.ceil((b[2] + pad) / GRID))), min(ny, int(math.ceil((b[3] + pad) / GRID))))

    for r in fixed:
        x0, y0, x1, y1 = cells(boxes[r])
        occ[side[r]][y0:y1, x0:x1] = True
    for k in keep:
        if k[5] is None:
            x0, y0, x1, y1 = cells(k)
            occ[k[4]][y0:y1, x0:x1] = True
    moved = {}
    order = sorted((r for r in boxes if r not in fixed),
                   key=lambda r: -(boxes[r][2] - boxes[r][0]) * (boxes[r][3] - boxes[r][1]))
    for r in order:
        b = boxes[r]
        w, h = b[2] - b[0], b[3] - b[1]
        s = side[r]
        mg = (margins or {}).get(r, GAP)
        own = np.zeros_like(occ[s])
        for k in keep:                           # 部品ごとの立入禁止（入ってよい部品が決まっている物）
            if k[5] is not None and not exempt(k, r) and k[4] == s:
                x0, y0, x1, y1 = cells(k, 0)
                own[y0:y1, x0:x1] = True
        grid = occ[s] | own
        best = None
        for ring in range(0, int(60 / 0.2)):
            rad = ring * 0.2
            n = max(1, int(2 * math.pi * rad / 0.2))
            for i in range(n):
                t = 2 * math.pi * i / n
                x0 = b[0] + rad * math.cos(t)
                y0 = b[1] + rad * math.sin(t)
                if x0 < M or y0 < M or x0 + w > L - M or y0 + h > W - M:
                    continue
                c = cells((x0, y0, x0 + w, y0 + h), mg)
                if not grid[c[1]:c[3], c[0]:c[2]].any():
                    best = (x0, y0)
                    break
            if best:
                break
        if not best:
            sys.exit(f"{r} を置く空きが無い（置きたい位置から 60mm 以内）")
        boxes[r] = [best[0], best[1], best[0] + w, best[1] + h]
        x0_, y0_, x1_, y1_ = cells(boxes[r], mg)       # 余白ごと塗る（後から来た物が余白に入らない）
        occ[s][y0_:y1_, x0_:x1_] = True
        moved[r] = math.hypot(best[0] - b[0], best[1] - b[1])
    return moved


def full_box(fp, X, Y, ang):
    """足形の枠（図面の座標）。courtyard に**パッドの外形**と**丸の本当の半径**を足した物。
    🔴 2026-09-15（1 枚案）、courtyard だけで置いたらパッドどうしが 25 か所で触れた。"""
    xs, ys = [], []
    b = G.courtyard(fp, 0.0, 0.0, 0.0)
    xs += [b[0], b[2]]
    ys += [b[1], b[3]]

    def walk(n):
        if isinstance(n, list):
            if n and n[0] == "fp_circle":
                lay = find1(n, "layer")
                if lay and "CrtYd" in str(lay[1]):
                    c, e = find1(n, "center"), find1(n, "end")
                    rr = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
                    xs.extend([float(c[1]) - rr, float(c[1]) + rr])
                    ys.extend([float(c[2]) - rr, float(c[2]) + rr])
            for e in n:
                if isinstance(e, list):
                    walk(e)
    walk(fp)
    for p in find(fp, "pad"):
        at, sz = find1(p, "at"), find1(p, "size")
        pa = math.radians(float(at[3]) if len(at) > 3 else 0.0)
        hx, hy = float(sz[1]) / 2 + 0.05, float(sz[2]) / 2 + 0.05
        for sx, sy in ((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)):
            xs.append(float(at[1]) + sx * math.cos(pa) + sy * math.sin(pa))
            ys.append(float(at[2]) - sx * math.sin(pa) + sy * math.cos(pa))
    pts = [G.rot_xy(a, c, ang) for a in (min(xs), max(xs)) for c in (min(ys), max(ys))]
    return (X + min(p[0] for p in pts), Y + min(p[1] for p in pts),
            X + max(p[0] for p in pts), Y + max(p[1] for p in pts))


def convex_hull(points):
    """凸包（反時計回り・Andrew の方法）。"""
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def dsn_pad(p):
    """パッド 1 つ → 自動配線に渡す形。多角形のパッドと斜めのパッドは、実物を囲う凸包の多角形にして渡す。
    🔴 2026-09-15（1 枚案）、マイクの LDO（U118・X2SON4）の多角形のパッドを小さく渡し、線が 0.044 まで寄った。"""
    d = G.fp_pad(p)
    at = find1(p, "at")
    pa = float(at[3]) if len(at) > 3 else 0.0
    hx, hy = d["size"][0] / 2, d["size"][1] / 2
    rect = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    prim = find1(p, "primitives")
    if prim or pa % 90:
        a = math.radians(pa)
        poly = [(float(xy[1]), float(xy[2])) for gp in find(prim, "gr_poly") for xy in find(find1(gp, "pts"), "xy")] \
            if prim else []
        d["poly"] = convex_hull([(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))
                                 for x, y in (poly or rect) + rect])
        d["rot"] = 0.0
    return d


def board_box(fp, x, b, ang):
    """足形の枠を板の座標（Y 上向き）で。"""
    X, Y = G.bx(x, b)
    bb = full_box(fp, X, Y, ang)
    return [bb[0] - G.ORG[0], G.BOARD_W - (bb[3] - G.ORG[1]), bb[2] - G.ORG[0], G.BOARD_W - (bb[1] - G.ORG[1])]


def outline():
    """角 R1.27 の長方形（ReSpeaker Lite の公式 CAD と同じ）。"""
    L, W, R = G.BOARD_L, G.BOARD_W, CORNER_R
    o = [G.seg(*G.bx(R, 0), *G.bx(L - R, 0)), G.seg(*G.bx(L, R), *G.bx(L, W - R)),
         G.seg(*G.bx(L - R, W), *G.bx(R, W)), G.seg(*G.bx(0, W - R), *G.bx(0, R))]
    for cx, cb, a0 in ((R, R, 180), (L - R, R, 270), (L - R, W - R, 0), (R, W - R, 90)):
        pts = [G.bx(cx + R * math.cos(math.radians(a0 + t)), cb + R * math.sin(math.radians(a0 + t))) for t in (0, 45, 90)]
        o.append(["gr_arc", ["start", f"{pts[0][0]:.3f}", f"{pts[0][1]:.3f}"], ["mid", f"{pts[1][0]:.3f}", f"{pts[1][1]:.3f}"],
                  ["end", f"{pts[2][0]:.3f}", f"{pts[2][1]:.3f}"], ["stroke", ["width", "0.1"], ["type", "default"]],
                  ["layer", Str("Edge.Cuts")], ["uuid", Str(G.uid())]])
    return o


def outline_poly():
    """ベタと DSN の外形（角の丸は 8 分割の折れ線で近似・内側に寄る向き）。"""
    L, W, R = G.BOARD_L, G.BOARD_W, CORNER_R
    pts = []
    for cx, cb, a0 in ((L - R, R, 270), (L - R, W - R, 0), (R, W - R, 90), (R, R, 180)):
        pts += [(cx + R * math.cos(math.radians(a0 + t)), cb + R * math.sin(math.radians(a0 + t))) for t in range(0, 91, 15)]
    return pts


def build():
    comps, pads, nets = G.netlist()
    G.NETNUM.clear()
    G.NETNUM.update(nets)
    GV_REFS.update(r for r in comps if not r.startswith("#"))
    GV_SRC.update({p["ref"]: p["src"] for p in GV.AUDIO if p.get("src")})
    place, back = build_place(comps)
    boxes, side, raw = {}, {}, {}
    for r, (x, b, a) in place.items():
        f = load_fp(comps[r]["fp"])
        if r in back:
            f = G.mirror_y(f)
        raw[r] = (f, x, b, a)
        boxes[r] = board_box(f, x, b, a)
        side[r] = "B" if r in back else "F"
    keep = keepouts()
    # 貫通の足（ライザーのピン・スピーカーの口）は裏にも出る ⇒ 裏にも立入禁止
    for r in FIXED:
        f, x, b, a = raw[r]
        X, Y = G.bx(x, b)
        for p in find(f, "pad"):
            if str(p[2]) not in ("thru_hole", "np_thru_hole"):
                continue
            q = find1(p, "at")
            dx, dy = G.rot_xy(float(q[1]), float(q[2]), a)
            rr = max(float(v) for v in find1(p, "size")[1:3]) / 2 + 0.3
            cx, cy = X + dx - G.ORG[0], G.BOARD_W - (Y + dy - G.ORG[1])
            keep.append((cx - rr, cy - rr, cx + rr, cy + rr, "B" if side[r] == "F" else "F", None))
    movable = set(place) - FIXED
    margins = {r: margin_of(len([p for p in find(raw[r][0], "pad") if str(p[1])])) for r in place}
    moved = legalize(boxes, side, FIXED & set(place), keep, margins)
    far = sorted(moved.items(), key=lambda kv: -kv[1])[:8]
    print("  空いた所へ置いた。狙いから遠くへ行った物: " + "・".join(f"{r} {d:.1f}" for r, d in far))
    for r in movable:
        f, x, b, a = raw[r]
        b0 = board_box(f, x, b, a)
        place[r] = (x + boxes[r][0] - b0[0], b + boxes[r][1] - b0[1], a)
    # 検査: 同じ面の重なり・立入禁止
    bad = []
    rs = sorted(boxes)
    for i, ra in enumerate(rs):
        for rb in rs[i + 1:]:
            p, q = boxes[ra], boxes[rb]
            if side[ra] == side[rb] and p[0] < q[2] - 1e-6 and q[0] < p[2] - 1e-6 and p[1] < q[3] - 1e-6 and q[1] < p[3] - 1e-6:
                bad.append((ra, rb))
    for ra, rb in bad[:40]:
        print(f"  重なり {ra} ↔ {rb}")
    hit = []
    for r in movable:
        p = boxes[r]
        for k in keep:
            if k[4] == side[r] and not exempt(k, r) and p[0] < k[2] - 1e-6 and k[0] < p[2] - 1e-6 and p[1] < k[3] - 1e-6 and k[1] < p[3] - 1e-6:
                hit.append((r, k[:4]))
    for r, k in hit[:40]:
        print(f"  立入禁止に入っている {r}: {k}")
    area = {"F": 0.0, "B": 0.0}
    for r, p in boxes.items():
        area[side[r]] += (p[2] - p[0]) * (p[3] - p[1])
    print(f"  枠の合計 XIAO 面（F）{area['F']:.0f} mm²・マイク面（B）{area['B']:.0f} mm²（板 {G.BOARD_L * G.BOARD_W:.0f}）")

    # ---- 板を書く ----
    placed, insts = [], []
    for r, (x, b, a) in place.items():
        X, Y = G.bx(x, b)
        node, f = G.place_footprint(r, comps[r], X, Y, a, pads, back=r in back)
        placed.append(node)
        pl = []
        for p in find(f, "pad"):
            if not str(p[1]) or str(p[2]) == "np_thru_hole":
                continue
            d = dsn_pad(p)
            d["side"] = "B.Cu" if r in back else "F.Cu"
            pl.append(d)
        insts.append(dict(ref=r, fp=comps[r]["fp"], x=X, y=Y, ang=a, pads=pl))
    doc = ["kicad_pcb", ["version", "20241229"], ["generator", Str("katanori/gen_pcb_audio.py")],
           ["generator_version", Str("9.0")],
           ["general", ["thickness", "1.6"], ["legacy_teardrops", "no"]],
           ["paper", Str("A3")],
           ["layers",
            ["0", Str("F.Cu"), "signal"], ["4", Str("In1.Cu"), "power"], ["6", Str("In2.Cu"), "signal"],
            ["2", Str("B.Cu"), "signal"],
            ["9", Str("F.Adhes"), "user", Str("F.Adhesive")], ["11", Str("B.Adhes"), "user", Str("B.Adhesive")],
            ["13", Str("F.Paste"), "user"], ["15", Str("B.Paste"), "user"],
            ["5", Str("F.SilkS"), "user", Str("F.Silkscreen")], ["7", Str("B.SilkS"), "user", Str("B.Silkscreen")],
            ["1", Str("F.Mask"), "user"], ["3", Str("B.Mask"), "user"],
            ["17", Str("Dwgs.User"), "user", Str("User.Drawings")],
            ["19", Str("Cmts.User"), "user", Str("User.Comments")],
            ["25", Str("Edge.Cuts"), "user"], ["27", Str("Margin"), "user"],
            ["31", Str("F.CrtYd"), "user", Str("F.Courtyard")], ["29", Str("B.CrtYd"), "user", Str("B.Courtyard")],
            ["35", Str("F.Fab"), "user"], ["33", Str("B.Fab"), "user"]],
           ["setup",
            # 積層は Voice PE と同じ（プリプレグ 0.1 ＋ コア 1.24 ＋ プリプレグ 0.1）・1.6mm（docs/VOICE-BOARD.md 6 章）
            ["stackup",
             ["layer", Str("F.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 1"), ["type", Str("prepreg")], ["thickness", "0.1"], ["material", Str("FR4")]],
             ["layer", Str("In1.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 2"), ["type", Str("core")], ["thickness", "1.24"], ["material", Str("FR4")]],
             ["layer", Str("In2.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 3"), ["type", Str("prepreg")], ["thickness", "0.1"], ["material", Str("FR4")]],
             ["layer", Str("B.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["copper_finish", Str("None")], ["dielectric_constraints", "no"]],
            ["pad_to_mask_clearance", "0"]],
           ["net", "0", Str("")]]
    for nm, num in sorted(nets.items(), key=lambda kv: kv[1]):
        doc.append(["net", str(num), Str(nm)])
    poly = ["polygon", ["pts"] + [["xy", f"{G.bx(*q)[0]:.3f}", f"{G.bx(*q)[1]:.3f}"] for q in outline_poly()]]
    zones = [["zone", ["net", str(nets["GND"])], ["net_name", Str("GND")], ["layer", Str(lay)],
              ["uuid", Str(G.uid())], ["name", Str("GND")], ["hatch", "edge", "0.5"],
              ["connect_pads", "yes", ["clearance", "0.2"]], ["min_thickness", "0.2"],
              ["filled_areas_thickness", "no"],
              ["fill", "yes", ["thermal_gap", "0.2"], ["thermal_bridge_width", "0.4"]], poly] for lay in COPPER]
    doc += outline() + G.mounting_holes() + placed + zones
    (G.OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(doc) + "\n", encoding="utf-8")
    pro = G.OUT / f"{NAME}.kicad_pro"
    d = json.loads(pro.read_text(encoding="utf-8"))
    d.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {}).update(
        {"min_clearance": PAD_PAD_MIN, "min_track_width": 0.15, "min_via_diameter": VIA[0],
         "min_through_hole_diameter": VIA[1], "min_via_annular_width": 0.1, "min_hole_clearance": 0.2,
         "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3})
    # ⚠ ネットクラスの間隔はパッドどうしにも効き、kicad_dru の条件付き規則が当たらない組ではこちらが使われる
    #    （1 枚案・CLEAR にしたら XU316 の隣り合うパッド 0.146 が 56 件の違反になった）
    d.setdefault("net_settings", {}).setdefault("classes", [{"name": "Default"}])[0].update(
        {"clearance": PAD_PAD_MIN, "track_width": TRACK, "via_diameter": VIA[0], "via_drill": VIA[1]})
    pro.write_text(json.dumps(d, indent=2), encoding="utf-8")
    NL = chr(10)
    (G.OUT / f"{NAME}.kicad_dru").write_text(NL.join([
        "(version 1)",
        f'(rule "track_zone_{CLEAR}"',
        f"  (constraint clearance (min {CLEAR}mm))",
        "  (condition \"A.Type != 'Pad' || B.Type != 'Pad'\"))", ""]), encoding="utf-8")
    print(f"{len(placed)} 部品・ネット {len(nets)} 本 → {G.OUT / (NAME + '.kicad_pcb')}")
    # DSN
    bnd = [G.bx(*q) for q in outline_poly()]
    ko = []
    for mx, my in G.MOUNT:
        X, Y = G.bx(mx, my)
        rr = G.MOUNT_D / 2 + G.MOUNT_KEEP
        ko.append((X - rr, Y - rr, X + rr, Y + rr))
    for it in insts:
        f = raw[it["ref"]][0]
        for q in find(f, "pad"):
            if str(q[2]) != "np_thru_hole":
                continue
            dd = G.fp_pad(q)
            dx, dy = G.rot_xy(dd["at"][0], dd["at"][1], it["ang"])
            rr = max(dd["size"]) / 2 + 0.35
            ko.append((it["x"] + dx - rr, it["y"] + dy - rr, it["x"] + dx + rr, it["y"] + dy + rr))
    netpins = {}
    for (ref, pin), net in pads.items():
        netpins.setdefault(net, []).append((ref, pin))
    np_, nn = dsn.write_dsn(G.OUT / f"{NAME}.dsn", NAME, insts, netpins, bnd, ko, copper=COPPER,
                           via=VIA, track_um=round(TRACK * 10000), clear_um=round(CLEAR * 10000))
    print(f"自動配線へ: {np_} 部品・{nn} ネット → {G.OUT / (NAME + '.dsn')}")
    if bad or hit:
        sys.exit(f"重なり {len(bad)} 組・立入禁止 {len(hit)} 件")


GV_SRC = {}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
