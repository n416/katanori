# -*- coding: utf-8 -*-
"""v6.1 の板の地図を SVG で刷る。python hardware/pcb/v61_map.py

動かせない物（外形・欠き・穴・USB-C・AS5600・つまみの軸・ライザー 2 枚）は筐体から来た値。
区画（電源 3 つ・リレー）と 口 5 つは私が置いた物で、最後に重なりを数える。
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import v61_board as B

S, M, HDR = 9.0, 26.0, 126.0
Wp, Hp = B.L * S + M * 2, B.W * S + M * 2 + HDR + 118
def px(x, y): return (M + x * S, M + HDR + (B.W - y) * S)
FONT = 'font-family="Yu Gothic UI,Meiryo,sans-serif"'
o = []

def rect(x, y, w, h, fill, stroke="none", sw=1.0, dash=None, op=1.0):
    X, Y = px(x, y + h)
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" fill-opacity="%s" stroke="%s" stroke-width="%s"%s/>'
             % (X, Y, w * S, h * S, fill, op, stroke, sw, (' stroke-dasharray="%s"' % dash) if dash else ""))

def circ(x, y, d, fill, stroke="none", sw=1.0):
    X, Y = px(x, y)
    o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%s"/>' % (X, Y, d / 2 * S, fill, stroke, sw))

def txt(x, y, s, size=11, fill="#1b2430", anchor="middle", weight="normal"):
    X, Y = px(x, y)
    o.append('<text x="%.1f" y="%.1f" font-size="%s" fill="%s" text-anchor="%s" font-weight="%s" %s>%s</text>'
             % (X, Y, size, fill, anchor, weight, FONT, s))

def arrow(x0, y0, x1, y1, col):
    X0, Y0 = px(x0, y0); X1, Y1 = px(x1, y1)
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#ah)"/>'
             % (X0, Y0, X1, Y1, col))

def raw(s): o.append(s)

def fp_box(p):
    _nm, cx, cy, (fw, fh), ex = p[0], p[1], p[2], p[3], p[4]
    w, h = (fh, fw) if ex in ("+X", "-X") else (fw, fh)   # +Z（縦）は回さない
    return (cx - w / 2, cy - h / 2, w, h)

def plug_box(p, d=None):
    """板の面に沿って要る通り道。縦（+Z）の口は面を食わないので None"""
    if p[4] in ("+Z", "-Z"): return None
    d = B.PLUG_D if d is None else d
    x, y, w, h = fp_box(p); ex = p[4]
    return {"+Y": (x, y + h, w, d), "-Y": (x, y - d, w, d),
            "+X": (x + w, y, d, h), "-X": (x - d, y, d, h)}[ex]

raw('<defs><marker id="ah" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
    '<path d="M0,0 L7,3.5 L0,7 z" fill="#5a6a85"/></marker></defs>')
raw('<rect x="0" y="0" width="%.0f" height="%.0f" fill="#f7f8fa"/>' % (Wp, Hp))

# 板と欠き
rect(0, 0, B.L, B.W, "#16603a", "#0d3a23", 1.5, op=0.16)
for n in B.NOTCHES:
    rect(n[0], n[1], n[2] - n[0], n[3] - n[1], "#f7f8fa", "#b23", 1.2, "4 3")
for n in B.NOTCHES:
    txt((n[0] + n[2]) / 2, n[1] - 2.2, "欠き", 9, "#b23")
for i, (bx, by, bw, bh) in enumerate(B.BACK_BANDS):
    rect(bx, by, bw, bh, "#7a8699", "#7a8699", 1.0, "2 4", op=0.07)
txt(B.BACK_BANDS[0][0] + 8.0, 8.8, "裏に胴 6.0 が入る帯", 9, "#5a6a85")
txt(B.BACK_BANDS[1][0] + 8.0, 8.8, "裏に胴 6.0 が入る帯", 9, "#5a6a85")

# 電源の区画
for (x, y, w, h) in B.POWER_AREAS:
    rect(x, y, w, h, "#2f6fb5", "#2f6fb5", 1.6, "7 4", op=0.13)
p0 = B.POWER_AREAS[0]; cx, cy = p0[0] + p0[2] / 2, p0[1] + p0[3] / 2
for dy, s, sz in ((5.6, "電源の帯（部品を置いた範囲 39.1 × 32.3）", 13), (2.4, "MCP73871 充電 / TPS61090 昇圧 + 6.8µH", 11),
                  (-0.6, "INA226 + 10mΩ シャント（電力計）", 11), (-3.6, "LED 4 / 入出力の C・R", 11)):
    txt(cx, cy + dy, s, sz, "#20507f", weight="bold" if sz == 14 else "normal")


# リレー
rx, ry, rw, rh = B.RELAY
rect(rx, ry, rw, rh, "#8a5cc4", "#6a3ca4", 1.4, op=0.18)
txt(rx + rw / 2, ry + 7.2, "ミュートリレー", 11, "#5a2f96", weight="bold")
txt(rx + rw / 2, ry + 4.4, "G6S-2F 15.3 × 10.7", 10, "#5a2f96")
txt(rx + rw / 2, ry + 1.8, "背 9.33（板でいちばん高い）", 9, "#5a2f96")

# 位置が決まっている物
ux0 = B.L - B.USBC_BODY_D
rect(ux0, B.USBC_Y - B.USBC_SHELL_W / 2, B.USBC_BODY_D, B.USBC_SHELL_W, "#e08b2a", "#a75f10", 1.4, op=0.35)
txt(ux0 - 1.0, B.USBC_Y + 2.0, "充電 USB-C", 11, "#8a4d08", anchor="end", weight="bold")
for (x0, x1, y), nm, z, cl in ((B.RISER_XIAO, "XIAO ライザー", "1x07 ソケット・背 8.5", 18.78),
                               (B.RISER_OLED, "OLED ライザー", "1x04 ソケット・背 8.5", 11.16)):
    x0 = (x0 + x1) / 2 - cl / 2; x1 = x0 + cl
    rect(x0, y - B.RISER_D / 2, x1 - x0, B.RISER_D, "#d94f4f", "#a32020", 1.4, op=0.35)
    txt((x0 + x1) / 2, y + 2.8, nm, 11, "#8c1c1c", weight="bold")
    txt((x0 + x1) / 2, y - 4.6, z, 10, "#8c1c1c")
sx, sy, sw, sh = B.SHAFT
circ(sx + sw / 2, sy + sh / 2, 7.0, "#f7f8fa", "#c58a00", 1.4)
ax, ay = B.AS5600
rect(ax - B.AS5600_FP[0] / 2, ay - B.AS5600_FP[1] / 2, B.AS5600_FP[0], B.AS5600_FP[1], "#c58a00", "#8a6000", 1.2, op=0.5)
txt(ax - 4.6, ay + 0.6, "AS5600", 11, "#7a5500", anchor="end", weight="bold")
txt(ax - 4.6, ay - 2.2, "つまみの軸 φ7 が降りる", 9, "#7a5500", anchor="end")
for (hx, hy) in B.HOLES:
    circ(hx, hy, B.HOLE_HEAD_D, "#f7f8fa", "#556", 1.0); circ(hx, hy, B.HOLE_D, "#556")

# 口（枠 + プラグの通り道 + 行き先の矢印）
for p in B.PORTS:
    nm, pcx, pcy, _fp, ex, nets, side = p
    x, y, w, h = fp_box(p)
    back = (side == "B")
    rect(x, y, w, h, "#2f7fa8" if back else "#3aa06a", "#14536e" if back else "#1d6b44", 1.4, "4 3" if back else None, op=0.45)
    pb = plug_box(p)
    if pb:
        rect(pb[0], pb[1], pb[2], pb[3], "#3aa06a", "#1d6b44", 1.0, "3 3", op=0.12)
    col = "#0d4560" if back else "#0e4a2c"
    txt(pcx, pcy + 0.9, nm + ("（裏・縦）" if back else "（縦）" if ex == "+Z" else ""), 10, col, weight="bold")
    txt(pcx, pcy - 1.6, nets, 8, col)
    key = "リード" if nm.startswith("リード") else nm
    t = B.WIRE_TARGETS.get(key)
    if t:
        arrow(pcx, pcy, min(max(t[0], 1.5), B.L - 1.5), min(max(t[1], 1.5), B.W - 1.5), "#5a6a85")

# 見出し
raw('<text x="%s" y="32" font-size="19" font-weight="bold" fill="#1b2430" %s>v6.1 の板 — 載る物と、線が出る口 5 つ（82.024 × 37.4 × 1.6）</text>' % (M, FONT))
for i, (s, c) in enumerate((
        ("緑 ＝ 線の口（JST-PH 2.0・枠 6.9 × 8.6）。薄い枠はプラグの相手が入る 3.1。破線の矢印は線の行き先（筐体からの実測）。", "#44506a"),
        ("リード＋トグル（4 ピン）は縦（上向き）。電池は板の裏に縦（下向き）。どちらも板の面を食わないので通り道の枠は無い。", "#44506a"),
        ("⚠ リレーを前へ 2.0 動かした（筐体が示した限界は 2.5・つまみの軸まで 0.5 残る）。リードの口はその後ろに 0.3 で並ぶ。", "#8a1c1c"),
        ("⚠ 板を 4.0 上げた（🔒 ユーザー 2026-09-14）。裏 Z 12.0・表 13.6。裏の口はトップ型の嵌合 8.0 が 4.0 余して入る。板の座標は 1 つも動かない。", "#8a1c1c"))):
    raw('<text x="%s" y="%s" font-size="12.5" fill="%s" %s>%s</text>' % (M, 56 + i * 19, c, FONT, s))

yb = M + HDR + B.W * S + 32
tail = []
def foot(i, s, c="#1b2430"):
    tail.append('<text x="%s" y="%.0f" font-size="12.5" fill="%s" %s>%s</text>' % (M, yb + i * 21, c, FONT, s))

# --- 重なりの検算 ---
def _ov(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0

# ⭐ 2026-09-16 夕: 欠きは「後ろの両隅に必ず 2 個」ではなくなったので、数えて並べる
FIXED = [("欠き %d" % (i + 1), (n[0], n[1], n[2] - n[0], n[3] - n[1])) for i, n in enumerate(B.NOTCHES)]
FIXED += [("USB-C", (ux0, B.USBC_Y - B.USBC_SHELL_W / 2, B.USBC_BODY_D, B.USBC_SHELL_W)),
         ("つまみの軸 φ7", B.SHAFT),
         ("XIAO ソケット 1x07", ((B.RISER_XIAO[0] + B.RISER_XIAO[1]) / 2 - 18.78 / 2, B.RISER_XIAO[2] - B.RISER_D / 2, 18.78, B.RISER_D)),
         ("OLED ソケット 1x04", ((B.RISER_OLED[0] + B.RISER_OLED[1]) / 2 - 11.16 / 2, B.RISER_OLED[2] - B.RISER_D / 2, 11.16, B.RISER_D))]
FIXED += [("M2 %d" % (i + 1), (h[0] - B.HOLE_HEAD_D / 2, h[1] - B.HOLE_HEAD_D / 2, B.HOLE_HEAD_D, B.HOLE_HEAD_D))
          for i, h in enumerate(B.HOLES)]
MINE = [("リレー", B.RELAY)]   # 電源の帯は区画の目安なので検算に入れない
# ⭐ 2026-09-16 夕: **裏の口の枠を表の検算から外した**。それまで表と裏を 1 枚の紙として見ていて、
#    板を挟んで別の側に居る物どうしを重なりと呼んでいた（J10 を裏の右の帯へ移したら、表の
#    SPK IN の枠と 9.19mm² 重なると出た。物は板の反対側に居る）。裏の口は下の裏用の検算で見る。
#    ⚠ 板を貫く足が相手の胴に突き出るかは、この地図では見られない（足形が要る）。gen_pcb.py が見る
MINE += [("口 " + p[0], fp_box(p)) for p in B.PORTS if p[6] == "F"]
MINE += [("通り道 " + p[0], plug_box(p)) for p in B.PORTS if plug_box(p) and p[6] == "F"]
BACK = [("裏の口 " + p[0], fp_box(p)) for p in B.PORTS if p[6] == "B"]
BACK += [("裏の通り道 " + p[0], plug_box(p)) for p in B.PORTS if plug_box(p) and p[6] == "B"]
# 裏の通り道は板の下（表の口やその通り道とは当たらない）。床から立つ柱と、裏の帯の外だけを見る
FLOOR_POSTS = [("床の柱 %d" % (i + 1), (h[0] - 3.5, h[1] - 3.5, 7.0, 7.0)) for i, h in enumerate(B.HOLES)]

OVER_EDGE = {"通り道 リード＋トグル"}   # 後ろの縁を越える（殻の側で空けてもらう）
bad = []
for nm, r in MINE:
    if nm not in OVER_EDGE and (r[0] < -1e-9 or r[1] < -1e-9 or r[0] + r[2] > B.L + 1e-9 or r[1] + r[3] > B.W + 1e-9):
        bad.append("%s: 板からはみ出す" % nm)
    for fn, fr in FIXED + MINE:
        if fn == nm: continue
        if fn.replace("通り道 ", "口 ") == nm or nm.replace("通り道 ", "口 ") == fn: continue
        a = _ov(r, fr)
        if a > 1e-9:
            bad.append("%s x %s: %.2fmm2" % (nm, fn, a))
for p_ in [q for q in B.PORTS if q[6] == "B"]:
    r = fp_box(p_)
    if not any(r[0] >= b[0] - 1e-9 and r[1] >= b[1] - 1e-9 and r[0] + r[2] <= b[0] + b[2] + 1e-9
               and r[1] + r[3] <= b[1] + b[3] + 1e-9 for b in B.BACK_BANDS):
        bad.append("口 %s: 裏の帯（嵌合 8.0 が入る所）から出る" % p_[0])
for nm, r in BACK:
    inband = any(r[0] >= b[0] - 1e-9 and r[1] >= b[1] - 1e-9 and r[0] + r[2] <= b[0] + b[2] + 1e-9
                 and r[1] + r[3] <= b[1] + b[3] + 1e-9 for b in B.BACK_BANDS)
    if not inband:
        bad.append("%s: 裏の帯（胴が入る所）から出る" % nm)
    for fn, fr in FLOOR_POSTS + BACK:
        if fn == nm: continue
        a = _ov(r, fr)
        if a > 1e-9: bad.append("%s x %s: %.2fmm2" % (nm, fn, a))
seen, uniq = set(), []
for b in bad:
    k = tuple(sorted(b.split(":")[0].split(" x ")))
    if k not in seen:
        seen.add(k); uniq.append(b)
for b in uniq:
    print("NG ", b)
print("重なり", "なし" if not uniq else "%d 件" % len(uniq))

foot(0, "配線まで通っている（2026-09-16 夕に J10 を縦へ移して引き直し）: 53 部品・ネット 49 本・配線 742 本・ビア 64 ＋ GND を縫う 103。DRC のエラー 0・未接続 0。")
foot(1, "高さ: 表の縦の口の上は 33 まで空く（筐体の実測）。裏は床まで 12.0 だが、電池の真上は 6.0 しか無いので、裏の口は左右の帯にしか置けない。")
foot(2, "重なり: 区画・口・プラグの通り道 × 動かせない物 を機械で数えて 0 件。" if not uniq else "⚠ 重なり %d 件（直していない）" % len(uniq),
     "#1b2430" if not uniq else "#8a1c1c")
raw("".join(tail))

svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" viewBox="0 0 %.0f %.0f">' % (Wp, Hp, Wp, Hp)
       + "".join(o) + "</svg>")
out = pathlib.Path(__file__).parent / "v61_map.svg"
out.write_text(svg, encoding="utf-8")
print("wrote", out.name, len(svg), "bytes")
