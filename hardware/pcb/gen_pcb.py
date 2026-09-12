# -*- coding: utf-8 -*-
"""hub_power.kicad_pcb（部品を置いただけの板・配線はまだ）を作る。

  python gen_pcb.py

つながりは回路図から kicad-cli が書き出したネットリストを読む（手で写さない）。
ハブ側の部品と口は、今のユニバーサル基板の穴の座標（hub_ports.py / relay_board.html）に置くので、
筐体の側の線の道は変えなくてよい。電源側は私が並べた（下の PLACE）。

パネル（1 枚で発注して割る）:
    ハブ  74 × 52   … 左上 (0, 0)
    電源  36 × 28   … 左下 (0, 54)。間は 2mm 空け、ミシン目のタブ 2 本でつなぐ
"""

import math
import pathlib
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "parts"))
import kisym  # noqa: E402
from kisym import Str, find, find1  # noqa: E402
import hub_ports  # noqa: E402
import dsn  # noqa: E402

CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
FPDIR = pathlib.Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
OUT = HERE / "hub_power"
NAME = "hub_power"
_n = [0]


def uid():
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/pcb/{_n[0]}"))


# ---- パネルの寸法 ----
HUB_L, HUB_W = hub_ports.BOARD_L, hub_ports.BOARD_W      # 74 × 52
PWR_L, PWR_W = 40.0, 32.0                                # 電源板（2026-09-12 の当たり検査: 後ろへ伸ばす向きで 40 × 32 まで 0・44 × 32 は当たり 102mm3）
GAP = 2.0                                                # 板と板のあいだ（JLCPCB の分割）
PWR_Y0 = HUB_W + GAP                                     # 54
PWR_X0 = 5.0     # 電源板をパネルの中で右へ寄せる量。USB-C が板の縁から前へ出る分（2.2）が
                 # パネルの外へはみ出さないようにするため（実装のとき邪魔になる）
ORG = (60.0, 40.0)                                       # 図面の上でのパネルの左上
TAB_W = 4.0                                              # ミシン目のタブの幅
TABS = [10.0, 28.0]                                      # タブの中心 x


def hx(x, y):
    """ハブ基板の座標（hub_ports・Y 上向き）→ 図面の座標（Y 下向き）。"""
    return (ORG[0] + x, ORG[1] + (HUB_W - y))


def px(x, y):
    """電源板の座標（左上原点・Y 下向き）→ 図面の座標。"""
    return (ORG[0] + PWR_X0 + x, ORG[1] + PWR_Y0 + y)


def hole(name):
    return hx(*hub_ports.hole_xy(name))


# ---- 足形の差し替え（KiCad の標準に無い物は katanori.pretty に作る） ----
LOCAL = HERE / "katanori.pretty"
FP_OVERRIDE = {
    # 🔒 2026-09-12 リレーは表面実装の Omron G6S-2F へ替えたので、自作の足形は要らなくなった
    #    （KiCad 標準の Relay_SMD:Relay_DPDT_Omron_G6S-2F を使う）。
    # 🔴 2026-09-12 ユーザー「別に両方の足が出なくてもいいんじゃないの？」＋ CASE-V4-OPEN.md 119 行
    #    （口が外面の 0.8 裏だとプラグが奥で止まる・ベベルでは逃げられない）。
    #    前寄りのシェルの足 2 本を省いて、本体を板の縁から 3.0mm 出す
    "J13": "katanori:USB_C_HRO_TYPE-C-31-M-12_NoFrontLegs",
}


# ---- 置き場所 ----
# ハブ側: 今の基板の穴から。口はピン 1 番の穴に置き、向きは 1 番 → 2 番の向きから決める
PORT_REF = {"XIAO": "J1", "OLED": "J2", "AS5600": "J3", "PHIN": "J4", "PHOUT": "J5",
            "REED": "J6", "TOGGLE": "J7", "BTN2": "J8"}
# ハブの部品: (ref, 置く穴たち)。2 端子は 2 穴の中点・向きは穴の並び
HUB_PARTS = [("R31", ["C8", "C4"]), ("R32", ["D4", "D8"]), ("D31", ["I4", "I6"]),
             ("C31", ["F13", "G13"]), ("C32", ["O13", "N13"]), ("Q31", ["G5", "G6", "G7"]),
             # リレーは表面実装になって穴に縛られないので、**今の基板でリレーが座っていた 6 穴の
             # 真ん中**に本体の中心を置く（角度は長辺が縦になる 0 で固定）。K5 に原点を合わせると
             # 本体が下へはみ出して D31 と重なる。
             ("K31", ["K5", "K7", "O5", "O7"], 0)]   # SW31（板の上の会話ボタン）は 2026-09-12 に外した

# 電源板: (ref, x, y, 回転)。板の左上が原点・x は右・y は下
PLACE_PWR = {
    # 充電（左上）
    # USB-C の受け口。🔴 この足形はピン（パッド）が後ろ側（局所 −y）に出る形で、**口は +y 側**。
    # 口を板の左の縁へ向けるので回転 270。本体の前面（局所 y ＋3.65）を縁 x=0 に合わせて x = 3.65。
    # 本体の前面（局所 y ＋3.65）を板の縁より 3.0mm 前へ出す（原点は縁から 0.65mm 内側）。
    # 壁 2.0 ＋ 板と壁の逃げ 0.2 に対して、口は外面より 0.8mm 前に出る
    "J13": (0.65, 10.0, 270),
    "R44": (20.0, 1.7, 0), "R45": (24.0, 1.7, 0),   # CC の 5.1kΩ
    "C8":  (12.0, 4.0, 0), "C7": (16.0, 4.0, 0),
    "U2":  (12.0, 9.5, 0),       # MCP73871
    "R6":  (4.0, 17.0, 90), "R7": (4.0, 20.0, 90),   # USB-C の下（左の縁）
    "R16": (9.0, 18.0, 0), "R17": (12.5, 18.0, 0), "R15": (16.0, 18.0, 0),
    "LED4": (12.5, 24.0, 0), "R8": (16.0, 24.0, 0),      # 充電中（橙）
    "LED3": (19.5, 24.0, 0), "R14": (23.0, 24.0, 0),     # 充電が済んだ（緑）
    # 電池と電流計（下の帯）
    "J10": (6.0, 27.0, 0),       # 電池の JST-PH
    "R41": (13.0, 28.5, 0),      # シャント 10mΩ
    "U3":  (20.0, 28.5, 0),      # INA226
    "C41": (26.0, 28.5, 0), "R42": (30.0, 28.5, 0), "R43": (33.5, 28.5, 0),
    # 板をまたぐ口（電源側）: 右の縁に沿って 7 本
    "J12": (33.5, 3.5, 0),
    # 昇圧（右上）
    "U1":  (28.0, 7.0, 0),       # TPS61090
    "L1":  (21.0, 6.0, 0),
    "C1":  (19.5, 11.5, 0), "C4": (23.0, 11.5, 0),
    "C2":  (26.5, 12.0, 90), "C6": (33.5, 13.0, 90),
    "R3":  (30.5, 13.0, 90), "R4": (30.5, 17.0, 90),
    "R1":  (19.5, 15.5, 0), "R2": (23.2, 15.5, 0), "R13": (33.0, 6.0, 90),
    "Q1":  (22.0, 20.0, 0), "R20": (26.0, 20.0, 0), "LED1": (29.5, 20.0, 0),
    "R5":  (26.0, 16.5, 0), "LED2": (29.5, 16.5, 0),
}


def netlist():
    out = OUT / "_pcb.xml"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                        str(OUT / f"{NAME}.kicad_sch")], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ネットリストを書き出せない:\n" + r.stdout + r.stderr)
    root = ET.parse(out).getroot()
    out.unlink()
    comps = {}
    for c in root.iter("comp"):
        ref = c.get("ref")
        fp = c.findtext("footprint") or ""
        flds = {f.get("name"): (f.text or "") for f in c.iter("field")}
        comps[ref] = dict(fp=FP_OVERRIDE.get(ref, fp), value=c.findtext("value") or "",
                          lcsc=flds.get("LCSC", ""))
    pads, nets = {}, {}
    for net in root.iter("net"):
        nm = net.get("name").lstrip("/")
        nets.setdefault(nm, len(nets) + 1)
        for node in net.iter("node"):
            pads[(node.get("ref"), node.get("pin"))] = nm
    return comps, pads, nets


def load_fp(fp_id):
    lib, name = fp_id.split(":")
    p = (LOCAL if lib == "katanori" else FPDIR / f"{lib}.pretty") / f"{name}.kicad_mod"
    if not p.exists():
        sys.exit(f"足形が無い: {fp_id}")
    return kisym.parse(p.read_text(encoding="utf-8"))[0]


def rot_xy(x, y, ang):
    a = math.radians(ang)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def courtyard(fp, x, y, ang):
    xs, ys = [], []

    def walk(n):
        if isinstance(n, list):
            if n and n[0] in ("fp_line", "fp_poly", "fp_rect", "fp_circle"):
                lay = find1(n, "layer")
                if lay and "CrtYd" in str(lay[1]):
                    for k in ("start", "end", "center", "mid"):
                        for e in find(n, k):
                            xs.append(float(e[1]))
                            ys.append(float(e[2]))
                    for pts in find(n, "pts"):
                        for e in find(pts, "xy"):
                            xs.append(float(e[1]))
                            ys.append(float(e[2]))
            for e in n:
                if isinstance(e, list):
                    walk(e)
    walk(fp)
    if not xs:   # CrtYd の無い足形（自作）はパッドの範囲で代用
        for p in find(fp, "pad"):
            at = find1(p, "at")
            sz = find1(p, "size")
            for sx in (-1, 1):
                xs.append(float(at[1]) + sx * float(sz[1]) / 2)
                ys.append(float(at[2]) + sx * float(sz[2]) / 2)
    pts = [rot_xy(a, b, ang) for a in (min(xs), max(xs)) for b in (min(ys), max(ys))]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts),
            x + max(p[0] for p in pts), y + max(p[1] for p in pts))


def place_footprint(ref, comp, x, y, ang, pads):
    fp = load_fp(comp["fp"])
    out = ["footprint", Str(comp["fp"]), ["layer", Str("F.Cu")], ["uuid", Str(uid())],
           ["at", f"{x:.3f}", f"{y:.3f}"] + ([f"{ang:.0f}"] if ang else []),
           ["property", Str("Reference"), Str(ref), ["at", "0", "-2.5", "0"], ["layer", Str("F.SilkS")],
            ["uuid", Str(uid())], ["effects", ["font", ["size", "0.8", "0.8"], ["thickness", "0.12"]]]],
           ["property", Str("Value"), Str(comp["value"]), ["at", "0", "2.5", "0"], ["layer", Str("F.Fab")],
            ["hide", "yes"], ["uuid", Str(uid())],
            ["effects", ["font", ["size", "0.8", "0.8"], ["thickness", "0.12"]]]],
           ["property", Str("LCSC"), Str(comp.get("lcsc", "")), ["at", "0", "3.5", "0"],
            ["layer", Str("F.Fab")], ["hide", "yes"], ["uuid", Str(uid())],
            ["effects", ["font", ["size", "0.8", "0.8"], ["thickness", "0.12"]]]],
           ["attr", "through_hole" if find1(fp, "attr") and "through_hole" in str(find1(fp, "attr")[1:])
            else "smd"]]
    for e in fp[2:]:
        if not isinstance(e, list) or e[0] in ("version", "generator", "generator_version", "layer",
                                               "descr", "tags", "attr", "property", "uuid", "embedded_fonts"):
            continue
        if e[0] == "pad":
            pad = [x for x in e if not (isinstance(x, list) and x[0] == "uuid")]
            # 🔴 パッドの at の 3 つ目は「板の上での向き」。部品を回したとき、位置は KiCad が回すが
            #    形は回らない（2026-09-12 に F.Cu の SVG を測って確認）。ここで足しておく
            if ang:
                # ⚠ 浅い複製なので at の中身はライブラリと共有している。作り直してから書く
                #    （共有したまま足すと、DSN に渡す向きにも二重に足さる）
                pa = list(find1(pad, "at"))
                pad[pad.index(find1(pad, "at"))] = pa
                a2 = ((float(pa[3]) if len(pa) > 3 else 0.0) + ang) % 360
                del pa[3:]
                if a2:
                    pa.append(f"{a2:.0f}")
            num = str(pad[1])
            net = pads.get((ref, num))
            if net is not None:
                pad = pad + [["net", str(NETNUM[net]), Str(net)]]
            pad = pad + [["uuid", Str(uid())]]
            out.append(pad)
        elif e[0] == "model" and ref in MODEL_VIS:
            path, off = MODEL_VIS[ref]
            out.append(["model", Str(path),
                        ["offset", ["xyz", f"{off[0]}", f"{off[1]}", f"{off[2]}"]],
                        ["scale", ["xyz", "1", "1", "1"]], ["rotate", ["xyz", "0", "0", "0"]]])
        else:
            body = [x for x in e if not (isinstance(x, list) and x[0] == "uuid")]
            # uuid を持てるのは図形・文字・ゾーンだけ（他に足すと KiCad が読めない）
            if e[0].startswith("fp_") or e[0] == "zone":
                body = body + [["uuid", Str(uid())]]
            out.append(body)
    return out, fp


def seg(x1, y1, x2, y2, layer="Edge.Cuts", width=0.1):
    return ["gr_line", ["start", f"{x1:.3f}", f"{y1:.3f}"], ["end", f"{x2:.3f}", f"{y2:.3f}"],
            ["stroke", ["width", str(width)], ["type", "default"]], ["layer", Str(layer)],
            ["uuid", Str(uid())]]


def outline():
    """2 枚の外形と、そのあいだのミシン目のタブ。タブの中に φ0.6 の穴を並べる。"""
    o = []
    x0, y0 = ORG
    hub = [(0, 0), (HUB_L, 0), (HUB_L, HUB_W), (0, HUB_W)]
    # ハブ: 下の辺はタブのところで切れる
    for i in range(4):
        a, b = hub[i], hub[(i + 1) % 4]
        if i != 2:
            o.append(seg(x0 + a[0], y0 + a[1], x0 + b[0], y0 + b[1]))
    cuts = sorted([(t - TAB_W / 2, t + TAB_W / 2) for t in TABS])
    xs = [0.0] + [v for c in cuts for v in c] + [HUB_L]
    for i in range(0, len(xs) - 1, 2):
        o.append(seg(x0 + xs[i], y0 + HUB_W, x0 + xs[i + 1], y0 + HUB_W))
    # 電源板: 上の辺も同じところで切れる
    pw = [(PWR_X0, PWR_Y0), (PWR_X0 + PWR_L, PWR_Y0), (PWR_X0 + PWR_L, PWR_Y0 + PWR_W),
          (PWR_X0, PWR_Y0 + PWR_W)]
    for i in range(4):
        a, b = pw[i], pw[(i + 1) % 4]
        if i != 0:
            o.append(seg(x0 + a[0], y0 + a[1], x0 + b[0], y0 + b[1]))
    xs2 = [PWR_X0] + [v for c in cuts if PWR_X0 <= c[0] and c[1] <= PWR_X0 + PWR_L for v in c]         + [PWR_X0 + PWR_L]
    for i in range(0, len(xs2) - 1, 2):
        o.append(seg(x0 + xs2[i], y0 + PWR_Y0, x0 + xs2[i + 1], y0 + PWR_Y0))
    # タブの横の辺（2mm の隙間を渡る）とミシン目の穴
    for t in TABS:
        if not (PWR_X0 <= t - TAB_W / 2 and t + TAB_W / 2 <= PWR_X0 + PWR_L):
            continue
        for sx in (-1, 1):
            o.append(seg(x0 + t + sx * TAB_W / 2, y0 + HUB_W, x0 + t + sx * TAB_W / 2, y0 + PWR_Y0))
        for k in range(5):
            cx = x0 + t - TAB_W / 2 + 0.5 + k * 0.75
            o.append(["gr_circle", ["center", f"{cx:.3f}", f"{y0 + HUB_W + GAP / 2:.3f}"],
                      ["end", f"{cx + 0.3:.3f}", f"{y0 + HUB_W + GAP / 2:.3f}"],
                      ["stroke", ["width", "0.1"], ["type", "default"]], ["fill", "no"],
                      ["layer", Str("Edge.Cuts")], ["uuid", Str(uid())]])
    return o


def mounting_holes():
    """ハブの 4 隅の φ3.2（今の基板と同じ 68 × 46 間隔）。"""
    o = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = hx(HUB_L / 2 + sx * hub_ports.MOUNT[0] / 2, HUB_W / 2 + sy * hub_ports.MOUNT[1] / 2)
            o.append(["footprint", Str("MountingHole:MountingHole_3.2mm_M3"), ["layer", Str("F.Cu")],
                      ["uuid", Str(uid())], ["at", f"{x:.3f}", f"{y:.3f}"], ["attr", "exclude_from_bom"],
                      ["pad", Str(""), "np_thru_hole", "circle", ["at", "0", "0"],
                       ["size", "3.2", "3.2"], ["drill", "3.2"],
                       ["layers", Str("F&B.Cu"), Str("*.Mask")], ["uuid", Str(uid())]]])
    return o


NETNUM = {}
INSTS = []
NPTH = []      # 金属化していない穴のまわり（銅を置かせない四角）
# ⚠ 絵のためだけの 3D モデルの差し替え。KiCad 10 は TYPE-C-31-M-12 のモデルを同梱していないので、
#    ピン数と向きが同じ別の USB-C（GCT USB4105・16P 横挿し）を見た目の確認用に割り当てる。
#    **実際に載る部品は C165948（TYPE-C-31-M-12）のままで、足形も変えていない。**
MODEL_VIS = {"J13": ("${KICAD10_3DMODEL_DIR}/Connector_USB.3dshapes/"
                     "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step", (0.0, 0.365, 0.0))}
FIXED = {"J13"}   # 押し離しても動かさない部品（USB-C は板の縁に口を合わせてあるので動かすと引っ込む）
MARGIN = 0.5      # 板の縁から部品の枠まで


def fp_pad(p):
    """足形のパッド 1 つ → dsn.py に渡す形。"""
    at = find1(p, "at")
    sz = find1(p, "size")
    return dict(num=str(p[1]), type=str(p[2]), shape=str(p[3]),
                size=(float(sz[1]), float(sz[2])),
                at=(float(at[1]), float(at[2])),
                rot=float(at[3]) if len(at) > 3 else 0.0)


def relax(placed, boxes, rounds=400):
    """電源板の部品だけを少しずつ押し離して、枠の重なりを無くす（ハブ側は今の基板の座標なので動かさない）。
    置いた位置の狙い（下の PLACE_PWR）は残したいので、動かすのは重なっている分だけにする。"""
    idx = {b[0]: i for i, b in enumerate(boxes)}
    movable = set(PLACE_PWR) - FIXED
    lo = (ORG[0] + PWR_X0 + MARGIN, ORG[1] + PWR_Y0 + MARGIN)
    hi = (ORG[0] + PWR_X0 + PWR_L - MARGIN, ORG[1] + PWR_Y0 + PWR_W - MARGIN)

    def shift(ref, dx, dy):
        i = idx[ref]
        r, (x0, y0, x1, y1) = boxes[i]
        dx = max(lo[0] - x0, min(hi[0] - x1, dx))
        dy = max(lo[1] - y0, min(hi[1] - y1, dy))
        boxes[i] = (r, (x0 + dx, y0 + dy, x1 + dx, y1 + dy))
        at = find1(placed[i], "at")
        at[1] = f"{float(at[1]) + dx:.3f}"
        at[2] = f"{float(at[2]) + dy:.3f}"
        for it in INSTS:      # 自動配線へ渡す座標も一緒に動かす（別々に持つと片方だけ動く）
            if it["ref"] == ref:
                it["x"] += dx
                it["y"] += dy
        return dx, dy

    for ref in movable:      # まず板の中へ入れる（置いた座標が縁を越えていることがある）
        x0, y0, x1, y1 = boxes[idx[ref]][1]
        shift(ref, 0.0, 0.0)
    for _ in range(rounds):
        moved = False
        for i, (ra, a) in enumerate(boxes):
            for j in range(i + 1, len(boxes)):
                rb, b = boxes[j]
                ov_x = min(a[2], b[2]) - max(a[0], b[0])
                ov_y = min(a[3], b[3]) - max(a[1], b[1])
                if ov_x <= 0 or ov_y <= 0:
                    continue
                free = [r for r in (ra, rb) if r in movable]
                if not free:
                    continue
                push = (min(ov_x, ov_y) + 0.15) / len(free)
                ax = (a[0] + a[2]) / 2 < (b[0] + b[2]) / 2
                ay = (a[1] + a[3]) / 2 < (b[1] + b[3]) / 2
                for r in free:
                    s = (1 if (r == rb) == ax else -1)
                    if ov_x <= ov_y:
                        shift(r, s * push, 0)
                    else:
                        s = (1 if (r == rb) == ay else -1)
                        shift(r, 0, s * push)
                a = boxes[i][1]
                moved = True
        if not moved:
            return
    print("  ⚠ 押し離しが収束しなかった")


def build():
    comps, pads, nets = netlist()
    NETNUM.update(nets)
    placed, boxes = [], []

    def add(ref, x, y, ang):
        fpnode, raw = place_footprint(ref, comps[ref], x, y, ang, pads)
        placed.append(fpnode)
        boxes.append((ref, courtyard(raw, x, y, ang)))
        INSTS.append(dict(ref=ref, fp=comps[ref]["fp"], x=x, y=y, ang=ang,
                          pads=[fp_pad(p) for p in find(raw, "pad")
                                if str(p[1]) and str(p[2]) != "np_thru_hole"]))
        # 🔴 金属化していない穴（位置決めの穴）も銅を置かせない。伝え忘れると配線が穴すれすれを通る
        #    （2026-09-12・USB-C の受け口で 0.015mm まで寄った）
        for q in find(raw, "pad"):
            if str(q[2]) != "np_thru_hole":
                continue
            d = fp_pad(q)
            dx, dy = rot_xy(d["at"][0], d["at"][1], ang)
            NPTH.append((ref, dx, dy, max(d["size"]) / 2 + 0.3))

    # 口（ピン 1 番の穴・向きは 1 番 → 2 番）
    for p in hub_ports.ports():
        if p.id not in PORT_REF:
            continue
        (x1, y1) = hole(p.pins[0][0])
        (x2, y2) = hole(p.pins[1][0])
        ang = {(1, 0): 90, (-1, 0): 270, (0, 1): 0, (0, -1): 180}[
            (round((x2 - x1) / 2.54), round((y2 - y1) / 2.54))]
        add(PORT_REF[p.id], x1, y1, ang)
    # 板をまたぐ口（ハブ側）: 無くなった電流計の口の跡から後ろの縁に沿って 7 本
    x1, y1 = hx(21.76, 48.86)   # 電流計の口の跡（24.3〜31.92）から 1 本ぶん左。右端はトグルの口の 5.08 手前
    add("J11", x1, y1, 90)
    # ハブの部品
    for ent in HUB_PARTS:
        ref, holes = ent[0], ent[1]
        fixed_ang = ent[2] if len(ent) > 2 else None       # 3 つ目があれば角度を指定
        pts = [hole(h) for h in holes]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        if len(pts) == 1:
            add(ref, pts[0][0], pts[0][1], fixed_ang or 0)
        else:
            dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
            ang = fixed_ang if fixed_ang is not None else (0 if abs(dx) >= abs(dy) else 90)
            add(ref, cx, cy, ang)
    # 電源板
    for ref, (x, y, ang) in PLACE_PWR.items():
        X, Y = px(x, y)
        add(ref, X, Y, ang)

    relax(placed, boxes)
    out_of_board = []
    for ref, b in boxes:
        if ref in FIXED:      # USB-C はプラグの通り道が板の外へ出るのが正しい
            continue
        if ref in PLACE_PWR:
            lim = (ORG[0] + PWR_X0, ORG[1] + PWR_Y0, ORG[0] + PWR_X0 + PWR_L,
                   ORG[1] + PWR_Y0 + PWR_W)
        else:
            lim = (ORG[0], ORG[1], ORG[0] + HUB_L, ORG[1] + HUB_W)
        d = max(lim[0] - b[0], lim[1] - b[1], b[2] - lim[2], b[3] - lim[3])
        if d > 1e-6:
            out_of_board.append((ref, round(d, 2)))
    for ref, d in out_of_board:
        print(f"  板からはみ出し {ref}: {d} mm")
    missing = sorted(set(comps) - {b[0] for b in boxes} - {r for r in comps if r.startswith("#")})
    if missing:
        sys.exit("置き場所が決まっていない部品: " + ", ".join(missing))
    bad = []
    for i, (ra, a) in enumerate(boxes):
        for rb, b in boxes[i + 1:]:
            if a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                bad.append((ra, rb, round(min(a[2], b[2]) - max(a[0], b[0]), 2),
                            round(min(a[3], b[3]) - max(a[1], b[1]), 2)))
    for ra, rb, w, h in bad:
        print(f"  重なり {ra} ↔ {rb}: {w} × {h} mm")
    doc = ["kicad_pcb", ["version", "20241229"], ["generator", Str("katanori/gen_pcb.py")],
           ["generator_version", Str("9.0")],
           ["general", ["thickness", "1.6"], ["legacy_teardrops", "no"]],
           ["paper", Str("A3")],
           ["layers",
            ["0", Str("F.Cu"), "signal"], ["2", Str("B.Cu"), "signal"],
            ["9", Str("F.Adhes"), "user", Str("F.Adhesive")], ["11", Str("B.Adhes"), "user", Str("B.Adhesive")],
            ["13", Str("F.Paste"), "user"], ["15", Str("B.Paste"), "user"],
            ["5", Str("F.SilkS"), "user", Str("F.Silkscreen")], ["7", Str("B.SilkS"), "user", Str("B.Silkscreen")],
            ["1", Str("F.Mask"), "user"], ["3", Str("B.Mask"), "user"],
            ["17", Str("Dwgs.User"), "user", Str("User.Drawings")],
            ["19", Str("Cmts.User"), "user", Str("User.Comments")],
            ["21", Str("Eco1.User"), "user", Str("User.Eco1")], ["23", Str("Eco2.User"), "user", Str("User.Eco2")],
            ["25", Str("Edge.Cuts"), "user"], ["27", Str("Margin"), "user"],
            ["31", Str("F.CrtYd"), "user", Str("F.Courtyard")], ["29", Str("B.CrtYd"), "user", Str("B.Courtyard")],
            ["35", Str("F.Fab"), "user"], ["33", Str("B.Fab"), "user"]],
           ["setup", ["pad_to_mask_clearance", "0"],
            ["pcbplotparams", ["layerselection", "0x00000000_00000000_55555555_5755f5ff"],
             ["disableapertmacros", "no"], ["usegerberextensions", "no"], ["usegerberattributes", "yes"],
             ["usegerberadvancedattributes", "yes"], ["creategerberjobfile", "yes"],
             ["dashed_line_dash_ratio", "12.000000"], ["dashed_line_gap_ratio", "3.000000"],
             ["svgprecision", "4"], ["plotframeref", "no"], ["mode", "1"], ["useauxorigin", "no"],
             ["dxfpolygonmode", "yes"], ["dxfimperialunits", "yes"], ["dxfusepcbnewfont", "yes"],
             ["psnegative", "no"], ["psa4output", "no"], ["plot_black_and_white", "yes"],
             ["sketchpadsonfab", "no"], ["plotpadnumbers", "no"], ["hidednponfab", "no"],
             ["sketchdnponfab", "yes"], ["crossoutdnponfab", "yes"], ["subtractmaskfromsilk", "no"],
             ["outputformat", "1"], ["mirror", "no"], ["drillshape", "1"], ["scaleselection", "1"],
             ["outputdirectory", Str("")]]],
           ["net", "0", Str("")]]
    for nm, num in sorted(nets.items(), key=lambda kv: kv[1]):
        doc.append(["net", str(num), Str(nm)])
    doc += outline() + mounting_holes() + placed
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(doc) + "\n", encoding="utf-8")
    print(f"{len(placed)} 部品・ネット {len(nets)} 本 → {OUT / (NAME + '.kicad_pcb')}")
    # 自動配線に渡す DSN。パネルの外形を囲い、板と板のあいだ・空いている所は銅を置かせない
    x0, y0 = ORG
    bnd = [(x0, y0), (x0 + HUB_L, y0), (x0 + HUB_L, y0 + PWR_Y0 + PWR_W), (x0, y0 + PWR_Y0 + PWR_W)]
    ko = [(x0, y0 + HUB_W, x0 + HUB_L, y0 + PWR_Y0),                      # 割るところ
          (x0 + PWR_X0 + PWR_L, y0 + PWR_Y0, x0 + HUB_L, y0 + PWR_Y0 + PWR_W),   # 電源板の右の空き
          (x0, y0 + PWR_Y0, x0 + PWR_X0, y0 + PWR_Y0 + PWR_W)]                   # 左の空き
    pos = {it["ref"]: (it["x"], it["y"]) for it in INSTS}   # 押し離したあとの位置
    for ref, dx, dy, rr in NPTH:
        cx, cy = pos[ref]
        ko.append((cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mx, my = hx(HUB_L / 2 + sx * hub_ports.MOUNT[0] / 2, HUB_W / 2 + sy * hub_ports.MOUNT[1] / 2)
            ko.append((mx - 2.3, my - 2.3, mx + 2.3, my + 2.3))           # 取付穴（φ3.2 ＋ 逃げ）
    netpins = {}
    for (ref, pin), net in pads.items():
        netpins.setdefault(net, []).append((ref, pin))
    n_part, n_net = dsn.write_dsn(OUT / f"{NAME}.dsn", NAME, INSTS, netpins, bnd, ko)
    print(f"自動配線へ: {n_part} 部品・{n_net} ネット → {OUT / (NAME + '.dsn')}")
    if bad:
        sys.exit(f"部品が {len(bad)} 組重なっている")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
