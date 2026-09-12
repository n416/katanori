# -*- coding: utf-8 -*-
"""KiCad の基板 ↔ 自動配線ソフト（Freerouting）のファイルを変換する。

KiCad のコマンドライン版には Specctra の DSN 書き出しも SES 取り込みも無い（画面にしか無い）ので、
ここで両方を書く。

  write_dsn(path, insts, nets, boundary, keepouts)  … 自動配線に渡す
  read_ses(path)                                    … 戻ってきた配線と貫通穴を読む

座標: KiCad は mm・Y が下向き、DSN は um・Y が上向き。ここで 1000 倍と符号反転をする。
"""

import math
import re

# 単位は KiCad の DSN 書き出しに合わせる: (resolution um 10) ＝ 0.1µm 刻み。
# 🔴 ここを µm にしていたら、戻ってきた座標が 10 倍になった（2026-09-12）
SCALE = 10000.0         # mm → DSN の単位（0.1µm）
TRACK_UM = 2000         # 既定の線幅 0.2mm
CLEAR_UM = 1500         # 既定の間隔 0.15mm
VIA_DIA = 8000          # 貫通穴の銅の直径 0.8mm
VIA = "Via[0-1]_800:400_um"


def _x(v):
    return round(v * SCALE, 1)


def _y(v):
    return round(-v * SCALE, 1)


def padstack_of(pad):
    """パッド 1 つ → (名前, DSN の shape の行たち)。丸・角丸・長丸は DSN の circle / rect で近似する。"""
    kind, shape = pad["type"], pad["shape"]
    sx, sy = pad["size"]
    layers = ["F.Cu", "B.Cu"] if kind != "smd" else ["F.Cu"]
    if shape == "circle":
        name = "Round[%s]Pad_%dum" % ("A" if kind != "smd" else "T", round(sx * SCALE))
        body = [f"(shape (circle {ly} {round(sx * SCALE)}))" for ly in layers]
    else:
        name = "Rect[%s]Pad_%dx%dum" % ("A" if kind != "smd" else "T",
                                        round(sx * SCALE), round(sy * SCALE))
        body = [f"(shape (rect {ly} {round(-sx / 2 * SCALE)} {round(-sy / 2 * SCALE)} "
                f"{round(sx / 2 * SCALE)} {round(sy / 2 * SCALE)}))" for ly in layers]
    return name, body


def write_dsn(path, name, insts, nets, boundary, keepouts=()):
    """insts: [{ref, fp, x, y, ang, pads:[{num,type,shape,size,at,rot}]}]
    nets: {ネット名: [(ref, パッド番号), ...]}
    boundary: [(x, y), ...]（閉じた多角形・mm）
    keepouts: [(x0, y0, x1, y1), ...]（銅を置かない四角・mm）"""
    # 🔴 部品 1 つにつき 1 つの image を作り、パッドの位置も形も**回した状態**で書く。
    #    Freerouting は placement の回転でパッドの形を回さない（2026-09-12・コンデンサだけが
    #    短絡として出た。1.15 × 2.7 のパッドを回さずに見ていた）。回転は 0 で渡す。
    padstacks, images = {}, {}
    for it in insts:
        img = images.setdefault(it["ref"], [])
        a = it["ang"] % 360
        for p in it["pads"]:
            q = dict(p)
            x, y = p["at"]
            if a == 90:          # KiCad と同じ向き（x' = x cos + y sin, y' = -x sin + y cos）
                q["at"] = (y, -x)
            elif a == 180:
                q["at"] = (-x, -y)
            elif a == 270:
                q["at"] = (-y, x)
            q["rot"] = (p.get("rot", 0) + a) % 360
            if q["rot"] % 180 == 90:      # 形の縦横を入れ替える（90°・270°）
                q["size"] = (p["size"][1], p["size"][0])
                q["rot"] = 0
            nm, body = padstack_of(q)
            padstacks[nm] = body
            rot = f" (rotate {q['rot']:.0f})" if q.get("rot") else ""
            img.append(f"      (pin {nm}{rot} {q['num']} {_x(q['at'][0])} {_y(q['at'][1])})")
    o = [f'(pcb {name}.dsn', '  (parser', '    (string_quote ")',
         "    (space_in_quoted_tokens on)", '    (host_cad "katanori/dsn.py")',
         '    (host_version "1")', "  )", "  (resolution um 10)", "  (unit um)", "  (structure",
         "    (layer F.Cu (type signal) (property (index 0)))",
         "    (layer B.Cu (type signal) (property (index 1)))",
         "    (boundary (path pcb 0 " + " ".join(f"{_x(a)} {_y(b)}" for a, b in boundary) + "))",
         f"    (via {VIA})",
         f"    (rule (width {TRACK_UM}) (clearance {CLEAR_UM}) (clearance {CLEAR_UM} (type default_smd))"
         f" (clearance {CLEAR_UM} (type smd_smd)))"]
    for i, (x0, y0, x1, y1) in enumerate(keepouts):
        o.append(f'    (keepout "ko{i}" (rect F.Cu {_x(x0)} {_y(y1)} {_x(x1)} {_y(y0)}))')
        o.append(f'    (keepout "ko{i}b" (rect B.Cu {_x(x0)} {_y(y1)} {_x(x1)} {_y(y0)}))')
    o.append("  )")
    o.append("  (placement")
    for it in insts:
        o.append(f"    (component {it['ref']}")
        o.append(f"      (place {it['ref']} {_x(it['x'])} {_y(it['y'])} front 0)")
        o.append("    )")
    o.append("  )")
    o.append("  (library")
    for fp, pins in images.items():
        o.append(f"    (image {fp}")
        o += pins
        o.append("    )")
    # 貫通穴（ビア）の定義。これが無いと層をまたげず、自動配線が片面で詰まる（2026-09-12）
    padstacks[VIA] = [f"(shape (circle F.Cu {VIA_DIA}))", f"(shape (circle B.Cu {VIA_DIA}))"]
    for nm, body in padstacks.items():
        o.append(f"    (padstack {nm}")
        o += ["      " + b for b in body]
        o.append("      (attach off)")
        o.append("    )")
    o.append("  )")
    o.append("  (network")
    for net, pins in sorted(nets.items()):
        if len(pins) < 2:
            continue
        o.append(f'    (net "{net}"')
        o.append("      (pins " + " ".join(f"{r}-{p}" for r, p in pins) + ")")
        o.append("    )")
    o.append('    (class kicad_default "" ' + " ".join(f'"{n}"' for n in sorted(nets) if len(nets[n]) > 1))
    o.append(f"      (circuit (use_via {VIA}))")
    o.append(f"      (rule (width {TRACK_UM}) (clearance {CLEAR_UM}))")
    o.append("    )")
    o.append("  )")
    o.append("  (wiring")
    o.append("  )")
    o.append(")")
    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")
    return len(insts), sum(1 for n in nets.values() if len(n) > 1)


# ---- 戻り（SES）----
_WIRE = re.compile(r"\(wire\s*\(path\s+(\S+)\s+([\d.]+)\s+([-\d.\s]+?)\)", re.S)
_NET = re.compile(r"\(net\s+([^\s()]+)", re.S)
_VIA = re.compile(r'\(via\s+"?([^"\s()]+)"?\s+([-\d.]+)\s+([-\d.]+)')


_PLACE = re.compile(r"\(place\s+(\S+)\s+([-\d.]+)\s+([-\d.]+)")


def ses_unit(txt, refs):
    """SES の 1mm あたりの単位数を、書いてある resolution ではなく**置いた部品の座標との比**で出す。
    🔴 Freerouting が返す座標は渡した単位の 10 倍だった（2026-09-12）。数えて決める。"""
    rs = []
    for m in _PLACE.finditer(txt):
        ref = m.group(1).strip('"')
        if ref in refs and abs(refs[ref][0]) > 1:
            rs.append(float(m.group(2)) / refs[ref][0])
    if not rs:
        raise SystemExit("SES に置いた部品が 1 つも無い（倍率を出せない）")
    unit = sorted(rs)[len(rs) // 2]
    if max(abs(r / unit - 1) for r in rs) > 0.005:
        raise SystemExit("SES の倍率が部品ごとにばらばら（%.4f〜%.4f）" % (min(rs), max(rs)))
    return unit


def read_ses(path, refs):
    """SES → (配線, 貫通穴)。配線 = [(ネット, 層, 幅mm, [(x,y)…])]、貫通穴 = [(ネット, x, y)]。
    refs: {部品名: (x, y)}（こちらが置いた座標 mm）。倍率の割り出しに使う。"""
    txt = open(path, encoding="utf-8").read()
    unit = ses_unit(txt, refs)
    wires, vias = [], []
    # net_out ごとに切って、その中の wire / via を拾う
    parts = re.split(r"\(net\s+", txt)[1:]
    for chunk in parts:
        net = re.match(r'"?([^\s"()]+)"?', chunk).group(1)
        for m in _WIRE.finditer(chunk):
            layer, w, coords = m.group(1), float(m.group(2)), m.group(3).split()
            pts = [(float(coords[i]) / unit, -float(coords[i + 1]) / unit)
                   for i in range(0, len(coords) - 1, 2)]
            wires.append((net, layer, w / unit, pts))
        for mv in _VIA.finditer(chunk):
            vias.append((net, float(mv.group(2)) / unit, -float(mv.group(3)) / unit))
    return wires, vias
