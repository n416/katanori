# PowerBoost の 5 本の L 字ピンと JST の行き先の図（docs/manual/_manual_img_v5/pb_pins.png）。
# マニュアル手順 12 の 2 枚目。ピンの名前と並びは hardware/parts/parts.scad の PB_PIN_*（micro-USB に近い端が USB・遠い端が 5Vo）、
# 行き先は _asm_manual_v5.py の手順 0 の表と同じ。python _pb_pins_fig.py で作り直す。
import os
from PIL import Image, ImageDraw, ImageFont
W, H = 1500, 1150
im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/" + ("meiryob.ttc" if b else "meiryo.ttc"), s)
f16, f18, f20, f22b, f26b = F(16), F(18), F(20), F(22, True), F(26, True)
BR, BK, OR = "#8b5a2b", "#222", "#e8871e"   # 茶・黒・橙（マニュアルの線の色）

d.text((30, 20), "PowerBoost の 5 本の L 字ピンと JST は、それぞれどこへ行くか", font=f26b, fill="#111")
d.text((30, 60), "部品面を見て micro-USB を左にした向き。8 ピン列は下辺（箱では後ろ・ハッチ側）、JST は上辺（前・OLED 側）。ピンは名前で呼ぶ。", font=f18, fill="#444")

# --- 電池 ---
jx = 700
d.rounded_rectangle([jx - 200, 110, jx + 220, 170], 10, fill="#f5f5f5", outline="#333", width=2)
d.text((jx - 188, 122), "電池（電流計の OUT ± から来る JST のプラグ）", font=f20, fill="#111")
d.line([jx, 170, jx, 260], fill="#c0392b", width=5); d.line([jx + 14, 170, jx + 14, 260], fill=BK, width=5)
d.text((jx + 30, 200), "＋ 赤 ／ − 黒", font=f16, fill="#333")

# --- PowerBoost ---
bx0, by0, bx1, by1 = 330, 300, 1170, 610
d.rounded_rectangle([bx0, by0, bx1, by1], 14, fill="#1e3a8a", outline="#0f1f4d", width=3)
d.text((bx0 + 20, by0 + 18), "PowerBoost 1000C（部品面）", font=f22b, fill="white")
d.rectangle([jx - 45, by0 - 40, jx + 45, by0 + 20], fill="#eee", outline="#333", width=2)
d.text((jx - 38, by0 - 34), "JST-PH", font=f18, fill="#111")
# micro-USB
d.rectangle([bx0 - 30, 410, bx0 + 60, 500], fill="#9aa5b1", outline="#333", width=2)
d.text((bx0 - 26, 424), "micro\nUSB", font=f18, fill="#111")
d.text((bx0 - 250, 410), "使わない\n（箱の中に隠れたまま。\n　線も挿さない）", font=f18, fill="#555")
# USB-A の足跡
d.rectangle([bx0 + 100, by0 + 60, bx0 + 100, by0 + 60])
ax0 = bx1 - 160
d.rectangle([ax0, 350, bx1 - 30, 508], outline="#f1c40f", width=3)
for cy in (372, 492): d.ellipse([ax0 + 20, cy - 9, ax0 + 38, cy + 9], fill="white")
d.text((ax0 + 50, 362), "USB-A の\n足跡", font=f18, fill="#f1c40f")
d.text((ax0 + 8, 404), "ジャック無し\nピンも立てない", font=f16, fill="#f1c40f")
d.text((ax0 + 8, 444), "（5V 出力は\n　5Vo のピンから）", font=f16, fill="#f1c40f")

# --- 8 ピン列 ---
names = ["USB", "LiPo", "Vs", "EN", "GND", "LBO", "GND", "5Vo"]
px0, pitch, py = 420, 90, by1 - 40
pin_x = {}
dest = {  # ピン: (色, ラベル行, 段)
    0: (BR, ["充電（茶）", "→ Type-C 基板の", "　L 字 1 本目 VBUS"], 0),
    3: (OR, ["電源（橙）", "→ ハブ PWR の口の", "　1 本目 EN"], 1),
    4: (BK, ["電源（黒）", "→ ハブ PWR の口の", "　2 本目 GND"], 2),
    6: (BK, ["充電（黒）", "→ Type-C 基板の", "　L 字 2 本目 GND"], 0),
    7: (BR, ["電源（茶）", "→ ハブ PWR の口の", "　4 本目 5V"], 1),
}
for i, n in enumerate(names):
    x = px0 + i * pitch; pin_x[i] = x
    d.rectangle([x - 22, py - 22, x + 22, py + 22], fill="#d4af37" if i in dest else "#7f8c8d", outline="#222", width=2)
    d.text((x - 26, py - 62), n, font=f18, fill="white")
    if i in dest:
        d.rectangle([x - 16, by1 - 6, x + 16, by1 + 30], fill="#222")                                  # 樹脂
        d.rectangle([x - 5, by1 + 30, x + 5, by1 + 90], fill="#bbb", outline="#555")                   # ピン（後ろへ 6）
        d.rectangle([x - 18, by1 + 90, x + 18, by1 + 180], fill="#63b3ed", outline="#2b6cb0", width=2)  # DuPont
    else:
        d.text((x - 24, by1 + 8), "空き", font=f16, fill="#777")
yb = by1 + 180
d.text((30, yb - 60), "L 字ピン 5 本。樹脂は板の上、ピンは縁から\n後ろへ水平、ハウジング（水色）も水平に寝る。\n線はその先で下（床の方）へ曲がる。", font=f16, fill="#333")

# 行き先のラベル（段違いで重ならないように）
for i, (col, lines, lv) in dest.items():
    x = pin_x[i]; ly = yb + 40 + lv * 95
    d.line([x, yb, x, ly], fill=col, width=6)
    d.ellipse([x - 7, ly - 7, x + 7, ly + 7], fill=col)
    tx = x - 120
    d.rounded_rectangle([tx - 8, ly + 10, tx + 232, ly + 82], 6, fill="white", outline=col, width=2)
    d.text((tx, ly + 12), lines[0], font=f18, fill=col)
    d.text((tx, ly + 34), lines[1], font=f16, fill="#222")
    d.text((tx, ly + 56), lines[2], font=f16, fill="#222")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "docs", "manual", "_manual_img_v5", "pb_pins.png")
im.save(os.path.normpath(OUT))
print(os.path.normpath(OUT))
