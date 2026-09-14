# -*- coding: utf-8 -*-
"""統合基板（v6.1 ＋ Voice PE の音声部）に部品を置き、4 層の .kicad_pcb と自動配線の DSN を書く。

  python gen_pcb_voice.py   → hardware/pcb/katanori61_voice/katanori61_voice.kicad_pcb と .dsn
  python route.py --board katanori61_voice   → 自動配線・GND の縫い・DRC

板の外形・穴・口の位置は v6.1（v61_board.py）と同じ。gen_pcb.py の道具（足形を置く・枠を測る・外形・
取付穴）をそのまま使い、置き場所と層だけをここで決める（docs/VOICE-BOARD.md 10 章）。

置き方:
  ・筐体が決めた物（口・USB-C・AS5600・ライザーの受け）は v6.1 と同じ枠で固定する。
  ・残りは「まとまり」ごとに区画を決め、**元の板での相対位置**を保ったまま区画へ縮めて置く。
      v6.1 の電源 … v6 の板で自動配線が通った並び（gen_pcb.PLACE_V6）
      音声部     … Voice PE の板の並び。Voice PE は大半が裏面なので、裏から見た鏡像として表へ置く
  ・重なった所だけを押し離す（パスコンは IC のそばに残る）。
層: F.Cu（部品・配線）／In1.Cu（GND の面）／In2.Cu（配線と GND）／B.Cu（配線と GND・電池の外の帯だけ部品）
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
import v61_board as VB  # noqa: E402
import voicepe  # noqa: E402
import dsn  # noqa: E402
from kisym import Str, find, find1  # noqa: E402

NAME = "katanori61_voice"
G.OUT = HERE / NAME
G.NAME = NAME
COPPER = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
# Voice PE の設計規則に寄せた値（線 0.156・間隔 0.125・穴 0.4064/0.2032）。JLCPCB の 4 層で作れる範囲に丸めた
# 🔴 間隔 0.12: マイクの LDO（U118・X2SON4）の足形はパッド 3–5 の間が 0.123 しかなく、0.127 では
#    どう引いても違反になる（2026-09-15・Freerouting が最初から数えていた 16 件の一部）。JLCPCB の 4 層は 0.09 まで作れる
# 🔒 ユーザー 2026-09-15「ごっちゃごちゃ。簡単にショートしそう」: 線 0.2・すきま 0.15 に緩める
#    （v6.1 の電源部の受動部品を 0402／0603 にして空けた面積を回す）。0.12・0.09 は JLCPCB で作れる下限寄りだった。
#    ⚠ パッドどうしは足形そのものが狭い（XU316 0.146・U118 0.123）ので、kicad_dru でパッド間だけ 0.12 を許す
TRACK, CLEAR, VIA = 0.2, 0.15, (0.45, 0.2)
PAD_PAD_MIN = 0.12

_load = G.load_fp


def load_fp(fp_id):
    lib, name = fp_id.split(":", 1)
    if lib == "voicepe":
        return kisym.parse((voicepe.PRETTY / f"{name}.kicad_mod").read_text(encoding="utf-8"))[0]
    return _load(fp_id)


G.load_fp = load_fp

# ======== 固定する物（v6.1 と同じ枠） ========
BOX = dict(G.BOX_PLACE)
for r in ("J1", "J4", "K31"):           # XIAO の受け・SPK IN・リレーは無い
    BOX.pop(r, None)
# 画面の口は 1x07（後から SPI）。1 番の位置は v6.1 の OLED の口と同じで、+X へ 3 本延びる
BOX["J2"] = (G.SOCK7, 90, VB.RISER_OLED[0] - 0.5, VB.RISER_OLED[2] - VB.RISER_D / 2,
             VB.RISER_OLED[0] - 0.5 + 18.79, VB.RISER_OLED[2] + VB.RISER_D / 2)
# 前のマイクのライザーの口は、XIAO のライザーの枠（板の左の縁から）に 1x05 で置く
BOX["J15"] = ("Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical", 90,
              -0.01, VB.RISER_XIAO[2] - VB.RISER_D / 2, 13.71, VB.RISER_XIAO[2] + VB.RISER_D / 2)
BACK_SIDE = {"J10"}
FIXED = {"J13", "J2", "J5", "J6", "J7", "J10", "J15", "U4", "U5"}

# ======== まとまりと区画（板の座標 x0, y0, x1, y1） ========
V61_GROUPS = {
    "ina": ((1.0, 21.0, 13.5, 31.0), ["U3", "R41", "C41"]),
    "power": ((14.0, 17.0, 37.0, 31.0), None),        # None = 残りの v6.1 の電源の部品ぜんぶ
}
VPE_GROUPS = {
    "xmos": ((14.0, 0.6, 36.5, 16.4),
             "U2 U3 X1 C2 C3 R3 R4 R1 C1 C6 C55 C56 C57 C60 C143 C43 C44 C45 C46 C47 C48 C49 C50 C51 "
             "C52 C53 C54 C142 C58 C41 FB6 FB7 FB9 Q3 R29 R63 R31 C92 R59 R41 "
             "R60 R70 R71 R72 R73 R103 R104 R105"),
    "micsup": ((0.6, 0.6, 13.5, 9.4), "R2 R8 R7 C4 C5 C12 C110 R11 U6 U18 R28 Q4 R12 R114"),
    # 🔒 2026-09-15 ユーザー（Freerouting の画面を見て）「右下のほうかなり開いてる」:
    #    電源を手前の右隅へ移し、コーデックとアンプに中央の手前を広く使わせる
    "codec": ((37.0, 6.8, 62.0, 16.4), " ".join(GV.COPY["DAC"].split())),
    "vpower": ((62.5, 0.6, 81.4, 10.0), " ".join(GV.COPY["Power"].split())),
    "espr": ((37.0, 0.6, 62.0, 2.8), " ".join(GV.COPY["ESP32"].split())),
}
ESP_BOX = (37.6, 16.9)                  # U5 の枠の左前の角（枠 19.5 × 20.1）
ESP_SMALL = {"R46": (58.5, 34.0), "C43": (58.5, 36.0), "R47": (36.0, 34.5), "C44": (35.5, 20.0),
             "C45": (35.5, 22.5), "R48": (4.0, 7.0), "TP1": (60.0, 1.5), "TP2": (62.0, 1.5),
             "TP3": (64.0, 1.5), "TP4": (66.0, 1.5)}


def fit(points, region, mirror_x=False):
    """点の集まりを、縦横比を保って区画の中へ縮めて置く（大きくはしない）。"""
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    w, h = max(xs) - min(xs) or 1.0, max(ys) - min(ys) or 1.0
    rx0, ry0, rx1, ry1 = region
    s = min(1.0, (rx1 - rx0 - 3.0) / w, (ry1 - ry0 - 3.0) / h)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    out = {}
    for r, (x, y) in points.items():
        dx = (x - cx) * s * (-1 if mirror_x else 1)
        dy = (y - cy) * s
        out[r] = ((rx0 + rx1) / 2 + dx, (ry0 + ry1) / 2 + dy)
    return out


def build_place(comps):
    place = {}
    # --- 固定 ---
    for r, (fp, a, x0, y0, x1, y1) in BOX.items():
        if r in comps:
            ox, oy = G.org_from_box(G.FP_OVERRIDE.get(r, fp), a, x0, y0, x1, y1, back=r in BACK_SIDE)
            place[r] = (ox, oy, a)
    place.update({k: v for k, v in G.FIXED_V61.items() if k in ("U4", "C42")})
    # --- v6.1 の電源（v6 の板の並びを区画へ） ---
    v6 = {}
    for r, (x, y, a) in G.PLACE_V6.items():
        if r in comps and r not in place and isinstance(a, int) and r not in GV.DROP_V61:
            # PLACE_V6 は v6 の板（44 × 81.2・縦）。gen_pcb.v61() と同じ回し方で板の座標へ
            v6[r] = ((y - 25.5), (35.0 - x), (a - 90) % 360)
    ina_refs = set(V61_GROUPS["ina"][1])
    for gname, (region, refs) in V61_GROUPS.items():
        members = {r: v6[r][:2] for r in v6 if (r in ina_refs) == (gname == "ina")}
        for r, (x, y) in fit(members, region).items():
            place[r] = (x, y, v6[r][2])
    # --- ESP32 ---
    fp = load_fp(comps["U5"]["fp"])
    b = G.courtyard(fp, 0, 0, 0)
    place["U5"] = (ESP_BOX[0] - b[0], ESP_BOX[1] + b[3], 0)
    for r, (x, y) in ESP_SMALL.items():
        place[r] = (x, y, 0)
    # --- 音声部（Voice PE の並びを、裏から見た鏡像として区画へ） ---
    vfp = voicepe.footprints()
    for gname, (region, refs) in VPE_GROUPS.items():
        pts, angs = {}, {}
        for vr in refs.split():
            f = vfp[vr]
            at = find1(f, "at")
            back = str(find1(f, "layer")[1]) == "B.Cu"
            a = float(at[3]) if len(at) > 3 else 0.0
            # 図面の座標（Y 下向き）で X を鏡にすると、裏の部品は表の向き 180 − a になる
            # （M_x · R(a) · M_y = R(180 − a)。表の部品も同じ式で、2 端子の物は形が対称なので問題ない）
            pts[GV.vref(vr)] = (float(at[1]), -float(at[2]))      # 板の座標は Y 上向き
            angs[GV.vref(vr)] = (180 - a) % 360 if back else (180 - a) % 360
        for r, (x, y) in fit(pts, region, mirror_x=True).items():
            place[r] = (x, y, round(angs[r]) % 360)
    # --- JTAG のテストパッド（J16）は XU316 の左隣を狙う ---
    #   🔒 ユーザー 2026-09-15: 20 ピンの J105（裏の右の帯・XU316 から 45mm）をやめ、XU316 のそばのパッドにした
    ux, uy, _ = place["U102"]
    place["J16"] = (ux - 8.0, uy, 0)
    missing = sorted(set(r for r in comps if not r.startswith("#")) - set(place))
    if missing:
        sys.exit("置き場所が決まっていない部品: " + " ".join(missing))
    return place


# ======== 空いた所へ置く（表と裏を分けて見る） ========
GRID = 0.1           # 占有の升目 [mm]
GAP = 0.05           # 枠どうしの最小の隙間（courtyard は元から逃げを含む）


def margin_of(npads):
    """部品の周りに空ける幅。足の多い IC は線を引き出す余白が要る。
    🔴 2026-09-15、全部 0.05 で詰めたら XU316 の 16〜25 番ピンが引き出せず、Freerouting が
       246 本中 18 本しか通せなかった（ユーザーが画面で「右下が開いている」と気づいた）。"""
    return 0.6 if npads >= 16 else 0.3 if npads >= 6 else 0.1


def legalize(boxes, side, fixed, keep, margins=None):
    """重なりの無い置き方にする。

    🔴 押し離し（relax）は、元の板の並びを区画へ縮めた塊を解けなかった（2026-09-15・79 組残った）。
    ⇒ 固定の物と立入禁止を先に升目へ塗り、動かせる部品を**大きい順**に、置きたい位置から
      渦巻きに外へ探して、最初に空いていた所へ置く。重なりは原理的に 0。IC が先に場所を取り、
      パスコンはその周りの空きに入る。
    """
    import numpy as np
    L, W, M = G.BOARD_L, G.BOARD_W, 0.4
    nx, ny = int(math.ceil(L / GRID)), int(math.ceil(W / GRID))
    occ = {"F": np.zeros((ny, nx), bool), "B": np.zeros((ny, nx), bool)}

    def cells(b, pad=GAP):
        return (max(0, int((b[0] - pad) / GRID)), max(0, int((b[1] - pad) / GRID)),
                min(nx, int(math.ceil((b[2] + pad) / GRID))), min(ny, int(math.ceil((b[3] + pad) / GRID))))

    def paint(b, s):
        x0, y0, x1, y1 = cells(b)
        occ[s][y0:y1, x0:x1] = True

    for r in fixed:
        paint(boxes[r], side[r])
    blocked_for = {}
    for k in keep:
        if k[5]:
            blocked_for.setdefault(k[5], []).append(k)
            continue
        paint(k, k[4])
    moved = {}
    order = sorted((r for r in boxes if r not in fixed),
                   key=lambda r: -(boxes[r][2] - boxes[r][0]) * (boxes[r][3] - boxes[r][1]))
    for r in order:
        b = boxes[r]
        w, h = b[2] - b[0], b[3] - b[1]
        s = side[r]
        mg = (margins or {}).get(r, GAP)
        own = np.zeros_like(occ[s])
        for k in keep:                           # 自分に向けた立入禁止（つまみの軸は AS5600 以外）
            if k[5] and k[5] != r and k[4] == s:
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


# ======== 押し離し（表と裏を分けて見る・今は使っていない） ========
def relax(boxes, side, movable, keep, rounds=4000):
    """boxes: ref → [x0, y0, x1, y1]（板の座標）。keep: 動かない四角 [(x0, y0, x1, y1, 面, 除外する ref)]。"""
    L, W, M = G.BOARD_L, G.BOARD_W, 0.4

    def shift(r, dx, dy):
        b = boxes[r]
        dx = max(M - b[0], min(L - M - b[2], dx))
        dy = max(M - b[1], min(W - M - b[3], dy))
        boxes[r] = [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]

    refs = list(boxes)
    for n in range(rounds):
        moved = False
        order = sorted(refs, key=lambda r: boxes[r][0])
        for i, ra in enumerate(order):
            a = boxes[ra]
            for rb in order[i + 1:]:
                b = boxes[rb]
                if b[0] >= a[2]:
                    break
                if side[ra] != side[rb]:
                    continue
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox <= 0 or oy <= 0:
                    continue
                free = [r for r in (ra, rb) if r in movable]
                if not free:
                    continue
                push = (min(ox, oy) + 0.12) / len(free)
                for r in free:
                    o = rb if r == ra else ra
                    ca = (boxes[r][0] + boxes[r][2]) / 2, (boxes[r][1] + boxes[r][3]) / 2
                    cb = (boxes[o][0] + boxes[o][2]) / 2, (boxes[o][1] + boxes[o][3]) / 2
                    if ox <= oy:
                        shift(r, push if ca[0] >= cb[0] else -push, 0)
                    else:
                        shift(r, 0, push if ca[1] >= cb[1] else -push)
                a = boxes[ra]
                moved = True
        for r in refs:
            if r not in movable:
                continue
            for k in keep:
                if k[4] != side[r] or k[5] == r:
                    continue
                b = boxes[r]
                ox = min(b[2], k[2]) - max(b[0], k[0])
                oy = min(b[3], k[3]) - max(b[1], k[1])
                if ox > 0 and oy > 0:
                    cb = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
                    ck = ((k[0] + k[2]) / 2, (k[1] + k[3]) / 2)
                    if ox <= oy:
                        shift(r, (ox + 0.15) * (1 if cb[0] >= ck[0] else -1), 0)
                    else:
                        shift(r, 0, (oy + 0.15) * (1 if cb[1] >= ck[1] else -1))
                    moved = True
        if not moved:
            return n
    return None


def full_box(fp, X, Y, ang):
    """足形の枠（図面の座標）。courtyard に**パッドの外形**と**丸の本当の半径**を足した物。

    🔴 2026-09-15、gen_pcb.courtyard だけで置いたら、パッドどうしが 25 か所で触れた:
       ・Voice PE の足形の一部（TSSOP・DGN8・SOT-23-5）は courtyard がパッドの外まで囲っていない
       ・丸の courtyard（テストパッド）を中心と円周上の 1 点で測っていて、半分の大きさに見ていた
    """
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
        # パッドの長方形を、パッドの向き（足形の中での向き）で回した実寸。
        # ⚠ 外接円で見ると 0402 まで一回り太り、XU316 の周りに入りきらなくなった（2026-09-15）
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
    """パッド 1 つ → 自動配線に渡す形。多角形のパッドと斜めのパッドは、**実物を囲う長方形**にして渡す。

    🔴 2026-09-15、マイクの LDO（U118・X2SON4）の足元で、線がパッドに 0.044 まで寄った。
       このパッドは多角形（custom）で、`size` は基準の小さな四角（0.228 × 0.235）しか持っていない。
       中央のパッドは 45° 回した 0.45 角。どちらも DSN では実物より小さく渡していた。
    """
    d = G.fp_pad(p)
    at = find1(p, "at")
    pa = float(at[3]) if len(at) > 3 else 0.0
    pts = []
    hx, hy = d["size"][0] / 2, d["size"][1] / 2
    pts += [(-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)]
    prim = find1(p, "primitives")
    if prim:
        for gp in find(prim, "gr_poly"):
            for xy in find(find1(gp, "pts"), "xy"):
                pts.append((float(xy[1]), float(xy[2])))
    if prim or pa % 90:
        a = math.radians(pa)
        if prim:
            # 多角形はそのまま多角形で渡す（長方形に丸めると隣のパッドに重なる。U118 の足で 0.534 まで膨らんだ）
            poly = [(float(xy[1]), float(xy[2])) for gp in find(prim, "gr_poly") for xy in find(find1(gp, "pts"), "xy")]
            if not poly:
                poly = pts[:4]
        else:
            poly = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        # 足形の座標（パッドの向きを入れた後）の多角形。多角形が複数あるパッド（X2SON4 は 2 つ）もあるので、
        # 全部の点の凸包 1 つにする（点を並べてつなぐと形がねじれる）
        d["poly"] = convex_hull([(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))
                                 for x, y in poly + pts[:4]])
        d["rot"] = 0.0
    return d


def board_box(fp, x, y, ang):
    """足形の枠を板の座標（Y 上向き）で。x, y は板の座標の原点。"""
    X, Y = G.bx(x, y)
    b = full_box(fp, X, Y, ang)
    return [b[0] - G.ORG[0], G.BOARD_W - (b[3] - G.ORG[1]), b[2] - G.ORG[0], G.BOARD_W - (b[1] - G.ORG[1])]


def keepouts():
    k = []
    for nx0, nx1, ny in G.NOTCHES:                       # 後ろの隅の欠き
        k += [(nx0, ny, nx1, G.BOARD_W, s, None) for s in "FB"]
    for mx, my in G.MOUNT:                              # 取付穴とナット
        r = G.NUT_R
        k += [(mx - r, my - r, mx + r, my + r, s, None) for s in "FB"]
    sx, sy, sw, sh = VB.SHAFT                          # つまみの軸（AS5600 だけ入ってよい）
    k.append((sx, sy, sx + sw, sy + sh, "F", "U4"))
    # 裏は電池の上に置けない（隙間 2.0）。帯の外を全部ふさぐ
    bat = G.BATTERY
    k.append((bat[0], bat[1], bat[2], G.BOARD_W, "B", None))
    for x0, y0, w, h in VB.BACK_BANDS:
        k.append((x0, 0.0, x0 + w, y0, "B", None))
    return k


def plug_keep(place_boxes, fps):
    """横挿しの口の前（相手の胴 3.1）に部品を置かせない。"""
    out = []
    for r, (side_dir, need) in G.CONN.items():
        if r not in place_boxes or r == "J4":
            continue
        b = place_boxes[r]
        f, x, y, a = fps[r]
        X, Y = G.bx(x, y)
        dx, dy = G.open_dir(f, X, Y, a)
        band = G.plug_band(tuple(b), (dx, dy), G.PLUG_BODY)
        out.append((min(band[0], band[2]), min(band[1], band[3]), max(band[0], band[2]), max(band[1], band[3]),
                    "B" if r in BACK_SIDE else "F", r))
    return out


def build():
    comps, pads, nets = G.netlist()
    G.NETNUM.clear()
    G.NETNUM.update(nets)
    place = build_place(comps)
    # 枠を測る
    boxes, side, raw = {}, {}, {}
    for r, (x, y, a) in place.items():
        f = load_fp(G.FP_OVERRIDE.get(r, comps[r]["fp"]))
        if r in BACK_SIDE:
            f = G.mirror_y(f)
        raw[r] = (f, x, y, a)
        boxes[r] = board_box(f, x, y, a)
        side[r] = "B" if r in BACK_SIDE else "F"
    keep = keepouts() + plug_keep(boxes, raw)
    # 🔴 裏の部品の**貫通の足**は表にも出る（2026-09-15、電池の口 J10 の足の上に R16 を置いていた）
    for r in BACK_SIDE & set(place):
        f, x, y, a = raw[r]
        X, Y = G.bx(x, y)
        for p in find(f, "pad"):
            if str(p[2]) not in ("thru_hole", "np_thru_hole"):
                continue
            q = find1(p, "at")
            dx, dy = G.rot_xy(float(q[1]), float(q[2]), a)
            rr = max(float(v) for v in find1(p, "size")[1:3]) / 2 + 0.3
            cx, cy = X + dx - G.ORG[0], G.BOARD_W - (Y + dy - G.ORG[1])
            keep.append((cx - rr, cy - rr, cx + rr, cy + rr, "F", None))
    movable = set(place) - FIXED
    margins = {r: margin_of(len([p for p in find(raw[r][0], "pad") if str(p[1])])) for r in place}
    moved = legalize(boxes, side, FIXED & set(place), keep, margins)
    far = sorted(moved.items(), key=lambda kv: -kv[1])[:8]
    print("  空いた所へ置いた。狙いから遠くへ行った物: " + "・".join(f"{r} {d:.1f}" for r, d in far))
    # 押し離した量だけ原点を動かす
    for r in movable:
        f, x, y, a = raw[r]
        b0 = board_box(f, x, y, a)
        dx, dy = boxes[r][0] - b0[0], boxes[r][1] - b0[1]
        place[r] = (x + dx, y + dy, a)
    # 検査
    bad = []
    rs = sorted(boxes)
    for i, ra in enumerate(rs):
        for rb in rs[i + 1:]:
            a, b = boxes[ra], boxes[rb]
            if side[ra] == side[rb] and a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                bad.append((ra, rb, round(min(a[2], b[2]) - max(a[0], b[0]), 2), round(min(a[3], b[3]) - max(a[1], b[1]), 2)))
    for ra, rb, w, h in bad[:40]:
        print(f"  重なり {ra} ↔ {rb}: {w} × {h}")
    hit = []
    for r in movable:
        b = boxes[r]
        for k in keep:
            if k[4] == side[r] and k[5] != r and b[0] < k[2] - 1e-6 and k[0] < b[2] - 1e-6 and b[1] < k[3] - 1e-6 and k[1] < b[3] - 1e-6:
                hit.append((r, k[5] or "穴・欠き・軸・電池"))
    for r, what in hit[:40]:
        print(f"  立入禁止に入っている {r}: {what}")
    area = {"F": 0.0, "B": 0.0}
    for r, b in boxes.items():
        area[side[r]] += (b[2] - b[0]) * (b[3] - b[1])
    print(f"  枠の合計 表 {area['F']:.0f} mm²・裏 {area['B']:.0f} mm²")

    # ---- 板を書く ----
    G.PLACE.clear()
    G.PLACE.update(place)
    placed, insts = [], []
    for r, (x, y, a) in place.items():
        X, Y = G.bx(x, y)
        back = r in BACK_SIDE
        node, f = G.place_footprint(r, comps[r], X, Y, a, pads, back=back)
        placed.append(node)
        pl = []
        for p in find(f, "pad"):
            if not str(p[1]) or str(p[2]) == "np_thru_hole":
                continue
            d = dsn_pad(p)
            d["side"] = "B.Cu" if back else "F.Cu"
            pl.append(d)
        insts.append(dict(ref=r, fp=comps[r]["fp"], x=X, y=Y, ang=a, pads=pl))
    doc = ["kicad_pcb", ["version", "20241229"], ["generator", Str("katanori/gen_pcb_voice.py")],
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
            # 積層は Voice PE と同じ（プリプレグ 0.1 ＋ コア 1.24 ＋ プリプレグ 0.1）
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
    zones = []
    pts = G.outline_pts()
    poly = ["polygon", ["pts"] + [["xy", f"{G.bx(*q)[0]:.3f}", f"{G.bx(*q)[1]:.3f}"] for q in pts]]
    for lay in COPPER:
        zones.append(["zone", ["net", str(nets["GND"])], ["net_name", Str("GND")], ["layer", Str(lay)],
                      ["uuid", Str(G.uid())], ["name", Str("GND")], ["hatch", "edge", "0.5"],
                      ["connect_pads", "yes", ["clearance", "0.2"]], ["min_thickness", "0.2"],
                      ["filled_areas_thickness", "no"],
                      ["fill", "yes", ["thermal_gap", "0.2"], ["thermal_bridge_width", "0.4"]], poly])
    doc += G.outline() + G.mounting_holes() + placed + zones + G.vbus_zone()
    (G.OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(doc) + "\n", encoding="utf-8")
    # 設計規則（Voice PE に寄せる）
    pro = G.OUT / f"{NAME}.kicad_pro"
    d = json.loads(pro.read_text(encoding="utf-8"))
    d["board"]["design_settings"]["rules"].update(
        # 最小線幅 0.09: Freerouting は細いピッチのパッドの手前で線を 0.112・0.09 へ細くする（ネックダウン）。
        #   JLCPCB の 4 層は 0.09mm（3.5mil）まで作れるので、規則をそこに合わせる（2026-09-15・237 本）
        {"min_clearance": PAD_PAD_MIN, "min_track_width": 0.15, "min_via_diameter": VIA[0],
         "min_through_hole_diameter": VIA[1], "min_via_annular_width": 0.1, "min_hole_clearance": 0.2,
         "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3})
    d["net_settings"]["classes"][0].update({"clearance": CLEAR, "track_width": TRACK,
                                            "via_diameter": VIA[0], "via_drill": VIA[1]})
    pro.write_text(json.dumps(d, indent=2), encoding="utf-8")
    # 規則: 板の下限は PAD_PAD_MIN（パッドどうしのため）。それ以外（線・穴・ベタ）は CLEAR を守らせる
    NL = chr(10)
    (G.OUT / f"{NAME}.kicad_dru").write_text(NL.join([
        "(version 1)",
        f'(rule "track_zone_{CLEAR}"',
        f"  (constraint clearance (min {CLEAR}mm))",
        "  (condition \"A.Type != 'Pad' || B.Type != 'Pad'\"))", ""]), encoding="utf-8")
    print(f"{len(placed)} 部品・ネット {len(nets)} 本 → {G.OUT / (NAME + '.kicad_pcb')}")
    # DSN
    bnd = [G.bx(*q) for q in G.outline_pts()]
    ko = []
    for mx, my in G.MOUNT:
        X, Y = G.bx(mx, my)
        r = G.MOUNT_D / 2 + G.MOUNT_KEEP
        ko.append((X - r, Y - r, X + r, Y + r))
    # 🔴 金属化していない穴（USB-C の位置決めの足など）も配線を入れない。v6.1 の gen_pcb.py は入れていたが、
    #    ここで入れ忘れて、VBUS のビアが J13 の穴の上に 25 か所打たれた（2026-09-15・hole_clearance）
    for it in insts:
        f = raw[it["ref"]][0]
        for q in find(f, "pad"):
            if str(q[2]) != "np_thru_hole":
                continue
            d = G.fp_pad(q)
            dx, dy = G.rot_xy(d["at"][0], d["at"][1], it["ang"])
            rr = max(d["size"]) / 2 + 0.35
            ko.append((it["x"] + dx - rr, it["y"] + dy - rr, it["x"] + dx + rr, it["y"] + dy + rr))
    netpins = {}
    for (ref, pin), net in pads.items():
        netpins.setdefault(net, []).append((ref, pin))
    # 🔴 内層を GND の面（DSN の plane）として渡すと、Freerouting 2.x が
    #    NullPointerException（"drillShapes" is null）で配線の段を途中で止めた（2026-09-15）。
    #    ⇒ 4 層とも配線の層として渡し、GND も自動配線に引かせる（v6.1 と同じ）。
    #    GND のベタは 4 層すべてに敷くので、In1.Cu は配線の少ない所がそのまま面になる
    np_, nn = dsn.write_dsn(G.OUT / f"{NAME}.dsn", NAME, insts, netpins, bnd, ko, copper=COPPER,
                           via=VIA, track_um=round(TRACK * 10000), clear_um=round(CLEAR * 10000))
    print(f"自動配線へ: {np_} 部品・{nn} ネット → {G.OUT / (NAME + '.dsn')}")
    if bad or hit:
        sys.exit(f"重なり {len(bad)} 組・立入禁止 {len(hit)} 件")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
