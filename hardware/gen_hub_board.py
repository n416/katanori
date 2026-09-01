#!/usr/bin/env python3
# ハブ基板 (DAISEN PU52X74) のモックを relay_board.html から生成する。
#
# 🔒 **手で転記しない。** 穴割りの正は relay_board.html の initialLayout() であって、
#    このファイルではない。穴割りを直したら、これを流し直す:
#
#      python hardware/gen_hub_board.py
#
# respeaker_lite_parts.scad と同じ方針（自動生成・212ボックスを手で写さない）。
#
# ⚠ 高さだけは relay_board.html に入っていない（あれは2Dの穴割り図なので）。
#    下の HEIGHTS で与える。**出どころと格付けを必ず添えること。**

import re, pathlib

SRC = pathlib.Path(__file__).with_name("relay_board.html")
DST = pathlib.Path(__file__).with_name("hub_board_parts.scad")

# ---- 基板そのもの（relay_board.html の説明文が正）----
BOARD_L, BOARD_W, BOARD_T = 74.0, 52.0, 1.6   # 📄 外形52×74・板厚1.6
COLS, ROWS = 27, 19                            # 📄 27列 × 19行
PITCH = 2.54
SPAN_X = (COLS - 1) * PITCH                    # 66.04
SPAN_Y = (ROWS - 1) * PITCH                    # 45.72
MARGIN_X = (BOARD_L - SPAN_X) / 2              # 3.98
MARGIN_Y = (BOARD_W - SPAN_Y) / 2              # 3.14
MOUNT = (68.0, 46.0)                           # 📄 4-φ3.2・中心間隔

# ---- 筐体の中での向き ----
# 🔒 **板は筐体へ 180度 回して載る**（2026-08-19 ユーザー指示「鏡面を直したなら
#    180度回転させて」）。鏡像を直しただけだと口が前後そっくり入れ替わり、
#    XIAO が背面・PWR が前面という筐体と噛み合わない並びになるため。
#    ⇒ 生成器は **載る向き**で出す。HTML 忠実な向きから 180度 回した座標になる。
# 🔒 これを変えたら hub_board.scad の hub_dir() も一緒に変わる（HUB_ROT180 を見ている）。
# ⚠ 鏡像の修正（行A を Y 大へ）と、この 180度 回転は**別の操作**。
#    2つ合わせた正味の差は、鏡像だった頃に対して**左右の反転**である。
ROT180 = True

# ---- 部品の高さ（板の上面から。relay_board.html には無い）----
#   📄 = データシート/カタログ  ✅ = ユーザー実測  ⚠ = 推定
HEIGHTS = {
    "res":    (2.5,  "⚠ 1/4W を寝かせた胴の直径"),
    "diode":  (2.0,  "⚠ 1N4148 を寝かせた胴の直径"),
    "cap":    (5.0,  "⚠ 0.1µF セラミックを立てた高さ"),
    "tr":     (5.2,  "⚠ TO-92 の胴の高さ"),
    "relay":  (10.0, "📄 Y14H-1C-5DS データシート（docs/DIMENSIONS.md 3章）"),
    # ✅ 2026-08-17 **6.0 → 11.0 に訂正。** 6.0 は胴だけの高さで、レバーの +5mm が
    #    入っていなかった。⚠ これは hub_board.scad が2回やった「裸のヘッダ 8.5mm で
    #    比べる」誤りと同じ形で、**胴だけ数えて、出っ張りを数えていない。**
    # 🔒 レバー式のまま残すことが決定（2026-08-17 ユーザー:「かなり使い易い。
    #    タクティカルスイッチにしたら不便過ぎる」）。テスト用に板へ残し、筐体の
    #    会話ボタン（BTN2・タクト）とは並列。
    # ⇒ これで **板の上でいちばん高いのはリレー(10.0)ではなくボタン(11.0)** になり、
    #    hub_stack_h(true) が 13.6 → 14.6 になる。筐体は BACK_Y から逆算しているので
    #    自動で追従する（case_v1.scad の HUB_D）。
    "button": (11.0, "✅ DAOKAI 本体6mm ＋ レバー5mm。**レバー込みの実高**（docs/DIMENSIONS.md 3章）"),
    "ph":     (6.0,  "⬜ PH2.0 トップ型の高さ未確定（サイド型なら約4）"),
    "header": (8.5, "📄 2.54mm ピンヘッダの標準的な全高（樹脂2.5＋ピン6）"),
}

txt = SRC.read_text(encoding="utf-8")
body = txt[txt.index("function initialLayout()"):txt.index("JUMPERS:")]


def hole_xy(name):
    """'K5' → (x, y) [mm]。列=1..27 が X（列1が X 小）、行=A..S が Y（**行A が Y 大**）。

    🔴 **2026-08-19 まで行Aを Y 小に置いていた。鏡像だった**（ユーザー指摘
       「中継基板のコネクタの位置が実際と違う。鏡面になってないか。ハンダ面に部品が
       乗ってる」）。relay_board.html は **部品面**を描いていて、SVG の y は下向きなので
       画面では **行A が上**。SCAD で部品面（+Z）から見下ろすと Y は画面の上へ伸びるから、
       行A を Y 小に置くと**同じ面を見ているのに上下だけが反転**する。列は両方とも
       左が列1なので、回転では戻らない鏡像になっていた。
    🔒 **HTML の画面の上 = SCAD の +Y。** ここを変えたら hub_board.scad の
       hub_dir() の up/down も一緒に入れ替える（口の向きは画面方向で書かれている）。
    """
    m = re.fullmatch(r"([A-Z])(\d+)", name)
    row, col = ord(m.group(1)) - ord("A"), int(m.group(2)) - 1
    x = MARGIN_X + col * PITCH               # HTML 忠実: 列1 が左
    y = MARGIN_Y + (ROWS - 1 - row) * PITCH  # HTML 忠実: 行A が上
    return (BOARD_L - x, BOARD_W - y) if ROT180 else (x, y)


def holes_in(chunk):
    # ⚠ 穴名だけを拾う。`hole:` を必ず付けること —— これが無いと fn:'D3' / fn:'D2'
    #    （XIAO のピン名）まで穴として数え、XIAO の口が7本ではなく9本になる。
    #    2026-08-15 に実際にそうなった。
    return re.findall(r"(?:hole|a|b|B|C|E):\s*'([A-S]\d{1,2})'", chunk)


def esc(s):
    """SCAD の文字列に入れられる形にする。⚠ ラベルに `"` が入る（OLED 2.42"）。"""
    return s.replace('"', "”")


out = []          # (id, name, kind, x0, y0, x1, y1, h, note)


def add(pid, name, kind, holes, w=None, l=None):
    """穴の並びから胴の bbox を作る。w/l が来たらそれを優先する。"""
    pts = [hole_xy(h) for h in holes]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    dx = (l if l else max(xs) - min(xs) + 2.0)
    dy = (w if w else max(ys) - min(ys) + 2.0)
    # 穴の並びが縦なら胴も縦（長辺を穴の伸びる向きに合わせる）
    if (max(ys) - min(ys)) > (max(xs) - min(xs)) and l and w and l > w:
        dx, dy = dy, dx
    h, note = HEIGHTS[kind]
    out.append((pid, name, kind, cx - dx / 2, cy - dy / 2,
                cx + dx / 2, cy + dy / 2, h, note))


# ---- PARTS（抵抗・ダイオード・コンデンサ・トランジスタ）----
for m in re.finditer(r"\{ id:'(\w+)',\s*name:'([^']+)',\s*kind:'(\w+)',(.*?)body:\{L:([\d.]+),\s*W:([\d.]+)\}", body, re.S):
    pid, name, kind, mid, L, W = m.groups()
    add(pid, name, kind, holes_in(mid), w=float(W), l=float(L))

# ---- リレー ----
m = re.search(r"RELAY:\s*\{.*?name:'([^']+)',\s*bodyL:([\d.]+),\s*bodyW:([\d.]+),\s*pins:\[(.*?)\]", body, re.S)
add("RELAY", m.group(1), "relay", holes_in(m.group(4)), w=float(m.group(3)), l=float(m.group(2)))

# ---- 会話ボタン ----
m = re.search(r"BUTTON:\s*\{.*?name:'([^']+)',\s*bodyW:([\d.]+),\s*bodyH:([\d.]+),\s*pins:\[(.*?)\]", body, re.S)
add("BUTTON", m.group(1), "button", holes_in(m.group(4)), w=float(m.group(3)), l=float(m.group(2)))

# ---- ピンヘッダ（口）----
# 🔒 headers は「板の外へ線が出る口」の一覧で、hub_corridors()（線が出て曲がるのに
#    要る 25mm の空間）がこれを見る。**線が出る口は全部ここに入れること。**
headers = []


def add_port(pid, label, exit_, holes):
    """口として登録する。⚠ add() だけして headers に入れないと、
    **その口の線は検査に現れない**（下の🔴）。"""
    pts = [hole_xy(h) for h in holes]
    headers.append((pid, label, exit_, len(holes),
                    min(p[0] for p in pts), min(p[1] for p in pts),
                    max(p[0] for p in pts), max(p[1] for p in pts)))


# ---- PH2.0 コネクタ ----
# 🔴 2026-08-17 まで、ここは exit: を**読んでいるのに捨てていた**（変数 exit_ が未使用）。
#    そのため PHIN/PHOUT が HUB_HEADERS に入らず、**スピーカーの IN/OUT 2口だけ
#    線の空間の検査から丸ごと抜けていた**（case_v1 の chk_wire_out が過少を出していた）。
#    ⇒ ピンヘッダと同じく口として登録する。
for m in re.finditer(r"\{ id:'(PH\w+)',\s*name:'([^']+)',\s*body:\{L:([\d.]+),\s*W:([\d.]+)\},\s*exit:'(\w+)',\s*pins:\[(.*?)\]", body, re.S):
    pid, name, L, W, exit_, pins = m.groups()
    hs = holes_in(pins)
    add(pid, name, "ph", hs, w=float(W), l=float(L))
    add_port(pid, name, exit_, hs)

# 🔒 2026-08-24（ユーザー）。**OLED と AS5600 の口は役割を入れ替えて使う。**
#    OLED 用に計画したヘッダを AS5600 に充て、つまみの線が OLED から見て右に出るように
#    した（鏡事故の補正）。両口とも GND・3V3・SCL・SDA で電気的に同一なので、名札だけが動く。
# 🔴 **relay_board.html の名札は計画のままなので、ここで実配線へ直す。**
#    これを外すと、流し直すたびに補正が消えて事故が再発する。「食い違い」と見て戻さないこと。
SWAP = {"OLED": "AS5600", "AS5600": "OLED"}
SWAP_NOTE = {
    "AS5600": "🔒 2026-08-24 実配線: 旧 OLED 計画のヘッダをユーザーが AS5600 に充てた"
              "（鏡事故の補正。つまみの線が OLED から見て右に出る＝このロボットの核心）",
    "OLED": "🔒 2026-08-24 実配線: 旧 AS5600 計画のヘッダ（上の入れ替えの相方）",
}
plan = {}   # 計画の id → (label, exit, 穴)。入れ替えは全部読んでから当てる

for m in re.finditer(r"\{ id:'(\w+)',\s*label:'([^']+)',\s*exit:'(\w+)',\s*pins:\[(.*?)\]\s*\}", body, re.S):
    pid, label, exit_, pins = m.groups()
    hs = holes_in(pins)
    add(pid, label, "header", hs)      # ⚠ 胴の名前は計画のまま（口だけ入れ替える）
    plan[pid] = (label, exit_, hs)

for pid, (label, exit_, hs) in plan.items():
    real = SWAP.get(pid, pid)          # この穴に実際に挿さる相手
    if real != pid:
        label = plan[real][0] + " " + SWAP_NOTE[real]
    add_port(real, label, exit_, hs)

with DST.open("w", encoding="utf-8") as f:
    f.write("// 🔴 自動生成。手で編集しない。\n")
    f.write("//    生成元: relay_board.html の initialLayout()\n")
    f.write("//    作り直す: python hardware/gen_hub_board.py\n\n")
    f.write(f"HUB_L = {BOARD_L}; HUB_W = {BOARD_W}; HUB_T = {BOARD_T};\n")
    f.write(f"HUB_PITCH = {PITCH}; HUB_MARGIN = [{MARGIN_X:.2f}, {MARGIN_Y:.2f}];\n")
    f.write(f"HUB_MOUNT = [{MOUNT[0]}, {MOUNT[1]}]; HUB_MOUNT_D = 3.2;\n")
    f.write("// 🔒 板が筐体へ載る向き。true なら HTML 忠実な向きから 180度 回してある。\n")
    f.write("//    hub_board.scad の hub_dir() がこれを見て口の向きを合わせる。\n")
    f.write(f"HUB_ROT180 = {'true' if ROT180 else 'false'};\n\n")
    f.write("// [ id, name, kind, x0, y0, x1, y1, 高さ ]\n")
    f.write("HUB_PARTS = [\n")
    for p in out:
        f.write(f'  ["{p[0]}", "{esc(p[1])}", "{p[2]}", {p[3]:.2f}, {p[4]:.2f}, '
                f'{p[5]:.2f}, {p[6]:.2f}, {p[7]}],   // {p[8]}\n')
    f.write("];\n\n")
    f.write("// [ id, label, 出る向き, 本数, x0, y0, x1, y1 ]\n")
    f.write("HUB_HEADERS = [\n")
    for h in headers:
        f.write(f'  ["{h[0]}", "{esc(h[1])}", "{h[2]}", {h[3]}, '
                f'{h[4]:.2f}, {h[5]:.2f}, {h[6]:.2f}, {h[7]:.2f}],\n')
    f.write("];\n")

import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

tallest = max(out, key=lambda p: p[7])
print(f"部品 {len(out)} 個 / 口 {len(headers)} 個 -> {DST.name}")
print(f"板の上でいちばん高いのは {tallest[1]} の {tallest[7]}mm  ({tallest[8]})")
for h in headers:
    print(f"  口 {h[0]:8s} {h[3]}本  出る向き={h[2]:6s} {h[1]}")
