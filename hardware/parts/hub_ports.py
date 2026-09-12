# -*- coding: utf-8 -*-
"""ハブ基板の「口」を、ピン 1 本ずつ・箱の中の向きで取り出す。

出どころは hardware/relay_board.html の initialLayout() ただ 1 つで、
このファイルは穴名を座標に直して並べ替えるだけである。数字は書かない。

  from hub_ports import ports
  for p in ports():
      p.bundle, p.place, [(fn, net) for ... in p.pins]

🔒 **OLED と つまみ（AS5600）の口は役割が入れ替わっている**（下の SWAP）。
   relay_board.html のラベルは計画のままなので、ここで実配線に直す。
   **「ラベルと座標が食い違う」と見て戻さないこと。** 戻すと事故が再発する。
"""

import pathlib
import re

SRC = pathlib.Path(__file__).with_name("relay_board.html")

BOARD_L, BOARD_W, BOARD_T = 74.0, 52.0, 1.6   # 📄 外形 52 × 74・板厚 1.6
COLS, ROWS = 27, 19                            # 📄 27列 × 19行
PITCH = 2.54
MARGIN_X = (BOARD_L - (COLS - 1) * PITCH) / 2  # 3.98
MARGIN_Y = (BOARD_W - (ROWS - 1) * PITCH) / 2  # 3.14
MOUNT = (68.0, 46.0)                           # 📄 4-φ3.2・中心間隔

# 🔒 板は筐体へ 180度 回して載る（2026-08-19 ユーザー指示）。
#    ここが true のとき、下の座標は **箱に載った向き**である。
ROT180 = True

# 箱の中の向き（ROT180 のときの意味）。POWER.md 4章が `BTN2` を「箱の中では左（X 6.5）」、
# 組み立てマニュアル手順 3 が「後ろに並んでいる 4 本＝電流計・トグル・リード・電源」と
# 書いていて、どちらもこの向きで一致する。
#   X 小 = 左（イヤホンジャック側） / X 大 = 右（XIAO の USB-C 側）
#   Y 小 = 前（OLED 側）           / Y 大 = 後ろ（ハッチ側）

# 🔒 2026-08-24（ユーザー）。左が relay_board.html の id、右が **実際に挿す相手**。
#    鏡事故の補正で、OLED 用に計画したヘッダを つまみ に充ててある。
#    両方とも GND・3V3・SCL・SDA の 4 本で電気的に同じなので、入れ替えても回路は変わらない。
#    ⚠ **並び順は物理のヘッダに付いて残る**ので、線の順は口ごとに違う。
SWAP = {"OLED": "AS5600", "AS5600": "OLED"}

# 口の id → マニュアルでの束の呼び名（10 束）
BUNDLE = {
    "XIAO": "XIAO", "PHIN": "スピーカー IN", "OLED": "OLED", "AS5600": "つまみ",
    "BTN2": "会話ボタン", "REED": "リード", "PHOUT": "スピーカー OUT",
    "PWR": "電源", "INA": "電流計", "TOGGLE": "トグル",
}


def hole_xy(name):
    """'K5' → 箱に載った向きでの (x, y) [mm]。行 A が Y 大・列 1 が X 小（HTML 忠実）。"""
    m = re.fullmatch(r"([A-Z])(\d+)", name)
    row, col = ord(m.group(1)) - ord("A"), int(m.group(2)) - 1
    x = MARGIN_X + col * PITCH
    y = MARGIN_Y + (ROWS - 1 - row) * PITCH
    return (BOARD_L - x, BOARD_W - y) if ROT180 else (x, y)


class Port:
    def __init__(self, pid, label, exit_, pins):
        self.id = pid                      # 実配線での役割（SWAP 適用後）
        self.label = label
        self.exit = exit_
        self.pins = pins                   # [(hole, fn, net, x, y)] 並べ替え済み
        self.bundle = BUNDLE.get(pid, pid)

    @property
    def n(self):
        return len(self.pins)

    @property
    def along(self):
        """'x' なら口は左右に並ぶ、'y' なら前後に並ぶ。"""
        xs = [p[3] for p in self.pins]
        ys = [p[4] for p in self.pins]
        return "x" if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else "y"

    @property
    def start(self):
        """1 本目がどちら端か（数え始める目印）。"""
        return "左（イヤホンジャック側）" if self.along == "x" else "前（OLED 側）"

    @property
    def place(self):
        """板のどこに立っているか。目印で言う（実物に行列の刻印は無い）。"""
        cx = sum(p[3] for p in self.pins) / self.n
        cy = sum(p[4] for p in self.pins) / self.n
        if cy < 8:
            return "前の縁（OLED 側）"
        if cy > 45:
            return "後ろの縁（ハッチ側）"
        if cx < 12:
            return "左の縁（イヤホンジャック側）"
        if cx > 62:
            return "右の縁（XIAO の USB-C 側）"
        return "板の中ほど"


def _holes(chunk):
    return re.findall(r"(?:hole|a|b|B|C|E):\s*'([A-S]\d{1,2})'", chunk)


def ports():
    """10 口を、箱の中の並び順（口ごとに左→右 か 前→後ろ）で返す。"""
    txt = SRC.read_text(encoding="utf-8")
    body = txt[txt.index("function initialLayout()"):txt.index("JUMPERS:")]
    out = []

    def build(pid, label, exit_, pins):
        rows = [(h, fn, net, *hole_xy(h)) for h, fn, net in pins]
        key = 3 if (max(r[3] for r in rows) - min(r[3] for r in rows)) >= \
                   (max(r[4] for r in rows) - min(r[4] for r in rows)) else 4
        rows.sort(key=lambda r: r[key])
        out.append(Port(SWAP.get(pid, pid), label, exit_, rows))

    for m in re.finditer(r"\{ id:'(PH\w+)',\s*name:'([^']+)',\s*body:\{[^}]*\},\s*"
                         r"exit:'(\w+)',\s*pins:\[(.*?)\]", body, re.S):
        pid, name, exit_, pins = m.groups()
        build(pid, name, exit_, _pin_rows(pins))

    for m in re.finditer(r"\{ id:'(\w+)',\s*label:'([^']+)',\s*exit:'(\w+)',\s*"
                         r"pins:\[(.*?)\]\s*\}", body, re.S):
        pid, label, exit_, pins = m.groups()
        build(pid, label, exit_, _pin_rows(pins))
    return out


def _pin_rows(chunk):
    """pins:[...] の中を 1 ピンずつ (穴, 機能, ネット) に割る。"""
    rows = []
    for m in re.finditer(r"\{\s*hole:'([A-S]\d{1,2})',\s*fn:'([^']*)',\s*"
                         r"net:\s*(?:'([^']*)'|null)", chunk):
        rows.append((m.group(1), m.group(2), m.group(3)))
    return rows


# ---- 図（板を上から見た地図）----
# 🔴 実物のユニバーサル基板には行・列の刻印が無い。数えさせる指示には必ず図を添える。
#    向きは **OLED を手前**（外から見た向き）。X 小が左、Y 小が下。
PAL = dict(board="#dfe7d8", edge="#8a9a7e", ink="#22201d", sub="#6f6a63",
           pin="#ffffff", pin1="#c62828", lead="#8a9a7e",
           gnd="#37474f", v5="#c62828", v33="#ef6c00", i2c="#1565c0", oth="#6f6a63")
NETCOL = {"GND": "gnd", "V5": "v5", "V33": "v33", "SDA": "i2c", "SCL": "i2c"}
# シルクの綴りは口ごとにばらばら（3V3 / VDD）。読む側が揃うようネット名に寄せる。
CANON = {"V5": "5V", "GND": "GND", "V33": "3V3", "SDA": "SDA", "SCL": "SCL"}


def disp(fn, net):
    """図と表に出す信号名。電源と I2C はネット名で揃え、それ以外はシルクのまま。"""
    return CANON.get(net or "", fn)


# 名札をどちらの外へ逃がすか。自動で近い縁を選ぶと XIAO と つまみ が重なるので手で決める。
LABEL_SIDE = {"XIAO": "S", "AS5600": "W", "OLED": "W", "BTN2": "W",
              "INA": "N", "TOGGLE": "N", "REED": "N", "PWR": "N",
              "PHIN": "E", "PHOUT": "E"}


def board_svg(scale=9.0, padx=160.0, pady=92.0, oled_top=False):
    """板を上から見て、10 口とピン番号を描いた SVG を返す。

    oled_top=False: OLED（前）を下に（外から OLED を見る向き。v4 のマニュアル）
    oled_top=True : OLED（前）を上に（箱の後ろ・ハッチ側から覗いた向き。v5 のマニュアル・2026-09-06 ユーザー「上が OLED であってほしい」）
    どちらも上から見た図で、後者は前者を紙の上で 180° 回しただけ（鏡ではない）。左右の名札は板と一緒に回る。
    """
    W, H = BOARD_L * scale + padx * 2, BOARD_W * scale + pady * 2

    def sx(x):
        return padx + ((BOARD_L - x) if oled_top else x) * scale

    def sy(y):
        return pady + (y if oled_top else (BOARD_W - y)) * scale   # 既定は Y 小（前・OLED 側）を下に

    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.0f %.0f" '
         'width="%.0f" height="%.0f" preserveAspectRatio="xMidYMid meet" '
         'font-family="system-ui, sans-serif">' % (W, H, W, H)]
    o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" fill="%s" '
             'stroke="%s" stroke-width="1.6"/>'
             % (min(sx(0), sx(BOARD_L)), min(sy(0), sy(BOARD_W)), BOARD_L * scale, BOARD_W * scale,
                PAL["board"], PAL["edge"]))
    for mx in (-MOUNT[0] / 2, MOUNT[0] / 2):
        for my in (-MOUNT[1] / 2, MOUNT[1] / 2):
            o.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
                     'stroke-width="1.2"/>'
                     % (sx(BOARD_L / 2 + mx), sy(BOARD_W / 2 + my), 1.6 * scale, PAL["edge"]))
    # 箱の中での方角
    if oled_top:
        dirs = ((W / 2, 24, "前（OLED はこちら）", "middle"),
                (W / 2, H - 16, "後ろ（ハッチ・見ている側）", "middle"),
                (14, H / 2, "右（USB-C の壁）", "start"),
                (W - 14, H / 2, "左（ジャックの壁）", "end"))
    else:
        dirs = ((W / 2, H - 16, "前（OLED はこちら）", "middle"),
                (W / 2, 24, "後ろ（ハッチ）", "middle"),
                (14, H / 2, "左", "start"),
                (W - 14, H / 2, "右", "end"))
    for px, py, lab, anc in dirs:
        o.append('<text x="%.1f" y="%.1f" font-size="15" font-weight="700" fill="%s" '
                 'text-anchor="%s">%s</text>' % (px, py, PAL["edge"], anc, lab))

    for p in ports():
        xs = [q[3] for q in p.pins]
        ys = [q[4] for q in p.pins]
        cx, cy = sum(xs) / p.n, sum(ys) / p.n
        d = LABEL_SIDE[p.id]
        for i, (h, fn, net, x, y) in enumerate(p.pins, 1):
            col = PAL[NETCOL.get(net or "", "oth")]
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" '
                     'fill="%s" stroke="%s" stroke-width="1.4"/>'
                     % (sx(x) - .95 * scale, sy(y) - .95 * scale,
                        1.9 * scale, 1.9 * scale, PAL["pin"], col))
            o.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="%s" '
                     'text-anchor="middle">%d</text>' % (sx(x), sy(y) + 4.5, col, i))
        lx, ly = {"S": (cx, -3.4), "N": (cx, BOARD_W + 3.4),
                  "W": (-2.6, cy), "E": (BOARD_L + 2.6, cy)}[d]      # 板の座標で名札の位置
        scr = {"S": "N", "N": "S", "W": "E", "E": "W"}[d] if oled_top else d   # 紙の上でどちら側に出るか
        anc, dy1, dy2 = {"S": ("middle", 0, 15), "N": ("middle", 0, 15),
                         "W": ("end", -3, 12), "E": ("start", -3, 12)}[scr]
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="1.2" stroke-dasharray="3 3"/>'
                 % (sx(cx), sy(cy), sx(lx), sy(ly), PAL["lead"]))
        o.append('<text x="%.1f" y="%.1f" font-size="15" font-weight="700" fill="%s" '
                 'text-anchor="%s">%s <tspan font-size="12" fill="%s">%d本</tspan></text>'
                 % (sx(lx), sy(ly) + dy1, PAL["ink"], anc, p.bundle, PAL["sub"], p.n))
        o.append('<text x="%.1f" y="%.1f" font-size="11.5" fill="%s" text-anchor="%s">'
                 '%s</text>' % (sx(lx), sy(ly) + dy2, PAL["sub"], anc,
                                " / ".join(disp(q[1], q[2]) for q in p.pins)))
    o.append('</svg>')
    return "".join(o)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in sorted(ports(), key=lambda p: (p.pins[0][4], p.pins[0][3])):
        print(f"{p.bundle:12s} {p.n}本  {p.place:22s} {p.start}から")
        for i, (h, fn, net, x, y) in enumerate(p.pins, 1):
            print(f"    {i}本目  {disp(fn, net):5s} ({net})  [{h}]  x{x:6.2f} y{y:6.2f}")
