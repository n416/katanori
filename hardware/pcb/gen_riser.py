# -*- coding: utf-8 -*-
"""ライザーの板 2 枚（XIAO 用・OLED 用）の .kicad_pcb を作り、DRC とガーバーまで出す（⭐ 2026-09-19）。

  python gen_riser.py            → riser_xiao/・riser_oled/ に .kicad_pcb・.kicad_pro・drc.json・fab/gerber と zip

🔒 ユーザー 2026-09-19「まだ設計してなかったんかい。やってください」。それまでライザーは筐体の模型
   （case_v6_1.scad の riser61()・oriser61()）にしか無かった。

寸法は**全部筐体の模型から読む**（OpenSCAD に echo させる。ここに数字を写さない）。
  座標: 板の表（F.Cu）＝ 前面（XIAO・OLED の側）。前から見ると世界 +X が右・+Z が上なので鏡は無い。
        板の x ＝ 世界 X − 板の左の縁、板の y ＝ 板の上の縁の Z − 世界 Z（KiCad は y が下向き）。
  足形はこのファイルで直に書く（ライブラリの足形を回して裏へ返すと鏡の取り違えが起きるので、
  パッドは板の座標で置き、足形の回転は 0 のまま）。

XIAO のライザー（2 層・板厚 1.2）
  表: 表面実装のメス 2 個（SHOU HAN PM2.54-1x3PLT-H8.5-R C55218894 / 1x4 C55218895）。
      パッド 1.02 × 3.00 が列の芯から上下へ互い違い（📄 図面の PCB LAYOUT）。向きは模型の XSOCK_S0。
  裏: L 字のメス 1x07（SHOU HAN PM2.54-1x7PWZ-H8.5 C54876736）。足は口から 10.03 の列で板を貫く。
      胴の下にはがき 2 枚（0.4）を挟んで手はんだ（模型の LSOCK_SHIM）。
  ネット（ハブの J1 と同じ並び・gen_sch.py）: 1 5V・2 GND・3 3V3・4 SDA・5 SCL・6 D2(BTN)・7 D3(IN)
  XIAO の列（USB-C の側から数えた番号・マニュアル手順 4）: 信号の列 2 D2・3 D3・4 SDA・5 SCL／電源の列 0 5V・1 GND・2 3V3
OLED のライザー（2 層・板厚 1.6）
  表: 縦のメス 1x04（スルーホール C54876726）・裏: L 字のメス 1x04（C54876733）。
  ハブの J2（1 GND・2 3V3・3 SCL・4 SDA）と OLED のピンは同じ X で 1 対 1（gen_sch.py の PORT_FLIP）⇒ 同じ X どうしを縦に結ぶ。
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from kicad_paths import CLI  # noqa: E402

CASE = HERE.parent / "case_v6_1.scad"
OPENSCAD = r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe"
TMP = HERE.parent / "_tmp_riser"
OX, OY = 50.0, 50.0       # 図面の上の置き場所（板の左上の角）

# ---- 模型から読む ----
ECHO = """include <%s>
echo("RISER", x0 = riser_pin_x()[0] - 1.27, x1 = HUB_AT[0] + RISER_SOCK_CY, zt = max(riser_zs()) + 1.27 + RISER_TOP_CL, zp = riser_plate_z0(),
              zrow = riser_z0() + LSOCK_H, pins = riser_pin_x(), sig = xsock_pins(0), pwr = xsock_pins(1), zs = riser_zs(),
              s0 = XSOCK_S0, pad = XSOCK_PAD, t = XRISER_T);
echo("ORISER", x0 = oriser_xs()[0] - 1.27, x1 = oriser_xs()[1] + 1.27, zt = oriser_z() + 1.27 + 1.0, zb = riser_z0(),
               zrow = riser_z0() + LSOCK_H, pins = oriser_pin_x(), zf = oriser_z(), t = RISER_T);
"""


def model():
    TMP.mkdir(exist_ok=True)
    src = TMP / "echo.scad"
    src.write_text(ECHO % str(CASE).replace("\\", "/"), encoding="utf-8")
    r = subprocess.run([OPENSCAD, "-o", str(TMP / "echo.echo"), "-D", 'part="none"', "-D", 'MAT="nylon"', str(src)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (TMP / "echo.echo").read_text(encoding="utf-8") if (TMP / "echo.echo").exists() else ""
    res = {}
    for key in ("RISER", "ORISER"):
        m = re.search(r'ECHO: "%s", (.*)$' % key, out, re.M)
        if not m:
            sys.exit("模型の echo が取れない: " + key + "\n" + r.stderr[-1500:])
        body = m.group(1)
        d = {}
        for k, v in re.findall(r"(\w+) = (\[[^\]]*\]|[-0-9.e]+)", body):
            d[k] = json.loads(v) if v.startswith("[") else float(v)
        res[key] = d
    return res


# ---- 書き出しの部品 ----
def U(*k):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "katanori-riser/" + "/".join(map(str, k))))


def f3(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


class Board:
    def __init__(self, name, w, h, t, nets):
        self.name, self.w, self.h, self.t = name, w, h, t
        self.nets = ["", *nets]
        self.items = []

    def n(self, net):
        return '(net %d "%s")' % (self.nets.index(net), net)

    def ni(self, net):   # 線と穴は番号だけ（名前を付けると KiCad が読めない）
        return '(net %d)' % self.nets.index(net)

    def P(self, x, y):
        return "%s %s" % (f3(OX + x), f3(OY + y))

    def seg(self, net, layer, w, pts):
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            self.items.append('(segment (start %s) (end %s) (width %s) (layer "%s") %s (uuid "%s"))'
                              % (self.P(*a), self.P(*b), f3(w), layer, self.ni(net), U(self.name, "seg", net, layer, i, a, b)))

    def via(self, net, x, y):
        self.items.append('(via (at %s) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") %s (uuid "%s"))'
                          % (self.P(x, y), self.ni(net), U(self.name, "via", net, x, y)))

    def text(self, s, x, y, layer="F.SilkS", size=0.8, rot=0):
        mir = " (justify mirror)" if layer.startswith("B.") else ""
        self.items.append('(gr_text "%s" (at %s %s) (layer "%s") (uuid "%s") (effects (font (size %s %s) (thickness 0.15))%s))'
                          % (s, self.P(x, y), f3(rot), layer, U(self.name, "txt", s), f3(size), f3(size), mir))

    def fp(self, ref, value, lcsc, side, pads, body, tht):
        """pads: [(番号, ネット, x, y, 形)]。形 = ("smd", w, h) か ("tht", 径, 穴)。body: 胴の枠 (x0, y0, x1, y1)（板の座標）"""
        lay = "F" if side == "F" else "B"
        out = ['(footprint "katanori_riser:%s" (layer "%s.Cu") (uuid "%s") (at %s 0)' % (ref + "_" + value, lay, U(self.name, ref), self.P(0, 0))]
        for k, v, dy in (("Reference", ref, -1.0), ("Value", value, 1.0), ("LCSC", lcsc, 2.0)):
            out.append('(property "%s" "%s" (at %s 0) (layer "%s.Fab") (hide yes) (uuid "%s") (effects (font (size 0.8 0.8) (thickness 0.12))))'
                       % (k, v, "%s %s" % (f3(body[0]), f3(body[1] + dy)), lay, U(self.name, ref, k)))
        out.append("(attr %s)" % ("through_hole" if tht else "smd"))
        x0, y0, x1, y1 = body
        # 胴の枠は Fab だけ（シルクに描くとパッドと板の縁で切れる。部品はどれも左右対称で向きの印は要らない）
        out.append('(fp_rect (start %s %s) (end %s %s) (stroke (width 0.1) (type solid)) (fill no) (layer "%s.Fab") (uuid "%s"))'
                   % (f3(x0), f3(y0), f3(x1), f3(y1), lay, U(self.name, ref, "Fab")))
        out.append('(fp_rect (start %s %s) (end %s %s) (stroke (width 0.05) (type solid)) (fill no) (layer "%s.CrtYd") (uuid "%s"))'
                   % (f3(x0 - 0.25), f3(y0 - 0.25), f3(x1 + 0.25), f3(y1 + 0.25), lay, U(self.name, ref, "crt")))
        for num, net, x, y, shp in pads:
            if shp[0] == "smd":
                out.append('(pad "%s" smd rect (at %s %s) (size %s %s) (layers "F.Cu" "F.Paste" "F.Mask") %s (uuid "%s"))'
                           % (num, f3(x), f3(y), f3(shp[1]), f3(shp[2]), self.n(net), U(self.name, ref, num)))
            else:
                sh = "rect" if num == "1" else "circle"
                out.append('(pad "%s" thru_hole %s (at %s %s) (size %s %s) (drill %s) (layers "*.Cu" "*.Mask") %s (uuid "%s"))'
                           % (num, sh, f3(x), f3(y), f3(shp[1]), f3(shp[1]), f3(shp[2]), self.n(net), U(self.name, ref, num)))
        out.append(")")
        # 足形の原点は板の角（OX, OY）・回転 0。パッドは板の座標そのまま
        self.items.append("\n\t".join(out))

    def write(self, outdir):
        outdir.mkdir(parents=True, exist_ok=True)
        head = ['(kicad_pcb (version 20241229) (generator "katanori/gen_riser.py") (generator_version "9.0")',
                '(general (thickness %s) (legacy_teardrops no))' % f3(self.t), '(paper "A4")',
                '(layers (0 "F.Cu" signal) (2 "B.Cu" signal) (13 "F.Paste" user) (15 "B.Paste" user) (5 "F.SilkS" user "F.Silkscreen") '
                '(7 "B.SilkS" user "B.Silkscreen") (1 "F.Mask" user) (3 "B.Mask" user) (25 "Edge.Cuts" user) (31 "F.CrtYd" user "F.Courtyard") '
                '(29 "B.CrtYd" user "B.Courtyard") (35 "F.Fab" user) (33 "B.Fab" user))',
                '(setup (stackup (layer "F.Cu" (type "copper") (thickness 0.035)) (layer "dielectric 1" (type "core") (thickness %s) (material "FR4")) '
                '(layer "B.Cu" (type "copper") (thickness 0.035)) (copper_finish "None") (dielectric_constraints no)) (pad_to_mask_clearance 0))'
                % f3(self.t - 0.07)]
        head += ['(net %d "%s")' % (i, s) for i, s in enumerate(self.nets)]
        edge = '(gr_rect (start %s) (end %s) (stroke (width 0.1) (type default)) (fill no) (layer "Edge.Cuts") (uuid "%s"))' % (
            self.P(0, 0), self.P(self.w, self.h), U(self.name, "edge"))
        (outdir / (self.name + ".kicad_pcb")).write_text("\n\t".join(head + self.items + [edge]) + "\n)\n", encoding="utf-8")
        rules = {"min_clearance": 0.15, "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.25,
                 "min_hole_to_hole": 0.5, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_resolved_spokes": 1,
                 "min_silk_clearance": 0.0, "min_through_hole_diameter": 0.3, "min_track_width": 0.1,
                 "min_via_annular_width": 0.13, "min_via_diameter": 0.45}   # gen_sch.py の katanori61 と同じ（JLCPCB 6/6mil 相当）
        net_default = {"bus_width": 12.0, "clearance": 0.15, "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "line_style": 0,
                       "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": "Default", "pcb_color": "rgba(0, 0, 0, 0.000)",
                       "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 0.2, "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6.0}
        (outdir / (self.name + ".kicad_pro")).write_text(json.dumps({
            "board": {"design_settings": {"rules": rules}}, "meta": {"filename": self.name + ".kicad_pro", "version": 3},
            "net_settings": {"classes": [net_default], "meta": {"version": 4}}, "sheets": [], "text_variables": {}}, indent=2), encoding="utf-8")


PAD_THT = ("tht", 1.7, 1.0)     # 2.54 のピンの足の穴（KiCad の PinSocket の足形と同じ）
LSOCK_FULL = 10.03              # L 字の胴＋足の曲がり（口から足の列まで）＝模型の LSOCK_H と同じ数（胴の枠を描くためだけ）


def xiao(m):
    x0, zt, zp = m["x0"], m["zt"], m["zp"]
    X = lambda X_: X_ - x0
    Y = lambda Z_: zt - Z_
    w, h = m["x1"] - x0, zt - zp
    sig, pwr = m["sig"], m["pwr"]
    zsig, zpow = m["zs"]
    pw, pl = m["pad"]
    # 🔴 並びの前提（ここが崩れたら配線を引き直す）: 信号の列 4 本・電源の列 3 本・L 字 7 本、どれも左から右へ
    assert len(sig) == 4 and len(pwr) == 3 and len(m["pins"]) == 7
    assert m["s0"] == [-1, 1], "XSOCK_S0 が配線の前提（信号の列の 1 本目が下・電源の列の 1 本目が上）と違う"
    NETS = ["V5", "GND", "V33", "SDA", "SCL", "BTN", "IN"]           # L 字の 1〜7 番 ＝ ハブの J1 の 1〜7 番
    SIGN = ["BTN", "IN", "SDA", "SCL"]                             # 信号の列（XIAO の 2〜5 番: D2・D3・SDA・SCL）
    PWRN = ["V5", "GND", "V33"]                                    # 電源の列（XIAO の 0〜2 番: 5V・GND・3V3）
    b = Board("riser_xiao", w, h, m["t"], NETS)
    hx = [X(p) for p in m["pins"]]
    hy = Y(m["zrow"])
    sy, py = Y(zsig), Y(zpow)

    def smd_pads(xs, y, s0, nets):
        out = []
        for k, (xx, nt) in enumerate(zip(xs, nets)):
            up = (s0 if k % 2 == 0 else -s0) > 0                 # 上 ＝ 世界 +Z ＝ 板の y が小さい側
            out.append((str(k + 1), nt, X(xx), y - pl / 2 if up else y + pl / 2, ("smd", pw, pl)))
        return out

    def body(xs, y, n):
        L = n * 2.54 + 0.5
        c = (X(xs[0]) + X(xs[-1])) / 2
        return (c - L / 2, y - 1.25, c + L / 2, y + 1.25)

    b.fp("J2", "XIAO_SIG_1x4", "C55218895", "F", smd_pads(sig, sy, -1, SIGN), body(sig, sy, 4), False)
    b.fp("J3", "XIAO_PWR_1x3", "C55218894", "F", smd_pads(pwr, py, 1, PWRN), body(pwr, py, 3), False)
    # L 字の胴は裏。口（板の下の縁の側）から足の列まで LSOCK_FULL、胴の長さは SHOU HAN の図面の 7 × 2.54 + 0.5（板の左右の縁から 0.25 出る）
    b.fp("J1", "L_SOCKET_1x7", "C54876736", "B", [(str(i + 1), NETS[i], hx[i], hy, PAD_THT) for i in range(7)],
         (hx[0] - 1.52, hy - 1.27, hx[6] + 1.52, hy + LSOCK_FULL - 1.27), True)

    # ---- 線（F: 表・B: 裏）。信号 0.3・3V3 0.4・5V と GND 0.6 ----
    sx = [X(v) for v in sig]
    px = [X(v) for v in pwr]
    y0 = sy + 2.43            # D3 のビア（D3 のパッドは上向き。下のすきまへ下りる手前）
    y1 = sy + pl + 0.53       # SDA の横の線（下向きのパッドの端の 0.53 下）
    y2 = y1 + 1.1             # SCL の横の線と D2 のビア
    assert y2 + 0.15 < hy - 0.85 - 0.3, "信号のすきまが L 字の足の穴に届いた"
    b.seg("IN", "F.Cu", 0.3, [(sx[1], sy), (sx[1], y0)]); b.via("IN", sx[1], y0)
    b.seg("IN", "B.Cu", 0.3, [(sx[1], y0), (hx[6], y0), (hx[6], hy)])
    b.seg("BTN", "F.Cu", 0.3, [(sx[0], sy + pl / 2), (sx[0], y2)]); b.via("BTN", sx[0], y2)
    b.seg("BTN", "B.Cu", 0.3, [(sx[0], y2), (hx[5], y2), (hx[5], hy)])
    b.seg("SDA", "F.Cu", 0.3, [(sx[2], sy + pl / 2), (sx[2], y1), (hx[3], y1), (hx[3], hy)])
    b.seg("SCL", "F.Cu", 0.3, [(sx[3], sy - pl / 2), (sx[3], y2), (hx[4], y2), (hx[4], hy)])
    yk = hy + 1.6             # 電源の 3 本が L 字の足へ斜めに寄る所
    b.seg("V5", "F.Cu", 0.6, [(px[0], py - pl / 2), (px[0], yk), (hx[0], hy)])
    b.seg("GND", "F.Cu", 0.6, [(px[1], py + pl / 2), (px[1], yk), (hx[1], hy)])
    b.seg("V33", "F.Cu", 0.4, [(px[2], py - pl / 2), (px[2], yk), (hx[2], hy)])

    b.text("XIAO RISER t1.2", w - 3.2, (py + hy) / 2 + 1.0, size=0.8, rot=90)
    b.text("<USB-C", 3.2, 2.0, size=0.8)   # XIAO の USB-C の側（左）。挿す位置を 1 本ずらさないための目印（マニュアル手順 4）
    return b


def oled(m):
    x0, zt, zb = m["x0"], m["zt"], m["zb"]
    X = lambda X_: X_ - x0
    Y = lambda Z_: zt - Z_
    w, h = m["x1"] - x0, zt - zb
    NETS = ["GND", "V33", "SCL", "SDA"]          # ハブの J2 の 1〜4 番（gen_sch.py）
    assert len(m["pins"]) == 4
    b = Board("riser_oled", w, h, m["t"], NETS)
    hx = [X(p) for p in m["pins"]]
    hy, fy = Y(m["zrow"]), Y(m["zf"])
    b.fp("J1", "L_SOCKET_1x4", "C54876733", "B", [(str(i + 1), NETS[i], hx[i], hy, PAD_THT) for i in range(4)],
         (hx[0] - 1.52, hy - 1.27, hx[3] + 1.52, hy + LSOCK_FULL - 1.27), True)
    b.fp("J2", "OLED_SOCKET_1x4", "C54876726", "F", [(str(i + 1), NETS[i], hx[i], fy, PAD_THT) for i in range(4)],
         (hx[0] - 1.27, fy - 1.25, hx[3] + 1.27, fy + 1.25), True)
    for i in range(4):
        b.seg(NETS[i], "F.Cu", 0.4, [(hx[i], fy), (hx[i], hy)])
    b.text("OLED RISER t1.6", w / 2, (fy + hy) / 2, layer="B.SilkS", size=0.8, rot=90)
    for i in range(4):   # ピンの名前（縦書き・線の上）
        b.text(NETS[i].replace("V33", "3V3"), hx[i], fy + 3.6, size=0.8, rot=90)
    return b


def run(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit("失敗: " + " ".join(args) + "\n" + r.stdout + r.stderr)
    return r


def fab(b):
    out = HERE / b.name
    b.write(out)
    pcb = str(out / (b.name + ".kicad_pcb"))
    run("pcb", "drc", "--format", "json", "--severity-all", "-o", str(out / "drc.json"), pcb)
    d = json.loads((out / "drc.json").read_text(encoding="utf-8"))
    # lib_footprint_issues は数えない: 足形はこのファイルで直に書くのでライブラリに無い（わざと）
    viol = [v for v in d.get("violations", []) if v["severity"] in ("error", "warning") and v["type"] != "lib_footprint_issues"]
    un = d.get("unconnected_items", [])
    gerb = out / "fab" / "gerber"
    if gerb.exists():
        shutil.rmtree(gerb)
    gerb.mkdir(parents=True)
    run("pcb", "export", "gerbers", "-o", str(gerb) + "\\", "--no-protel-ext",
        "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts", pcb)
    run("pcb", "export", "drill", "-o", str(gerb) + "\\", "--format", "excellon", "--drill-origin", "absolute",
        "--excellon-units", "mm", "--excellon-separate-th", pcb)
    with zipfile.ZipFile(out / (b.name + "_gerber.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gerb.iterdir()):
            z.write(f, f.name)
    print("%-11s %.2f × %.2f mm・板厚 %.1f・DRC 違反 %d・未接続 %d → %s"
          % (b.name, b.w, b.h, b.t, len(viol), len(un), out / (b.name + "_gerber.zip")))
    for v in viol:
        print("   ", v["severity"], v["type"], v["description"], [i.get("description", "")[:60] for i in v.get("items", [])])


def main():
    m = model()
    fab(xiao(m["RISER"]))
    fab(oled(m["ORISER"]))


if __name__ == "__main__":
    main()
