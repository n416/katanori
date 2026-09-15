# -*- coding: utf-8 -*-
"""Home Assistant Voice PE（hardware/ref/voice_pe/・CERN-OHL-P v2）を読む。

  python voicepe.py            → 3 シート（XMOS・DAC・Power）が外とつながる信号の一覧
  python voicepe.py <ネット名>  → そのネットの部品とピン

つながりは kicad-cli で書き出したネットリストを読む（回路図の座標を自分で辿らない）。
記号は回路図の lib_symbols、足形は .kicad_pcb に埋め込まれているものをそのまま使う。
"""

import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import kisym  # noqa: E402
from kisym import Str, find, find1  # noqa: E402
from kicad_paths import CLI  # noqa: E402

SRC = HERE.parents[0] / "ref" / "voice_pe" / "KiCad"
SCH = SRC / "Home Assistant Voice PE.kicad_sch"
PCB = SRC / "Home Assistant Voice PE.kicad_pcb"
CACHE = HERE / "build" / "voicepe.xml"
SHEETS = ("XMOS", "DAC", "Power")     # 写す 3 シート（ESP32・LED & Connector は写さない）


def _netlist():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    if not CACHE.exists() or CACHE.stat().st_mtime < SCH.stat().st_mtime:
        # kicad-cli は開いた回路図の隣の .kicad_prl（表示の設定）を書き換える。参照の写しは汚さない
        prl = SCH.with_suffix(".kicad_prl")
        keep = prl.read_bytes() if prl.exists() else None
        try:
            subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(CACHE), str(SCH)],
                           check=True, capture_output=True)
        finally:
            if keep is not None:
                prl.write_bytes(keep)
    return ET.parse(CACHE).getroot()


def _clean(s):
    return (s or "").replace("​", "").strip()


class VoicePE:
    def __init__(self):
        root = _netlist()
        self.comps = {}
        for c in root.iter("comp"):
            ref = c.get("ref")
            fields = {f.get("name"): _clean(f.text) for f in c.iter("field")}
            lib = c.find("libsource")
            sp = c.find("sheetpath")
            sheet = sp.get("names").strip("/").split("/")[0] if sp is not None else ""
            props = {p.get("name"): p.get("value") for p in c.iter("property")}
            self.comps[ref] = dict(
                ref=ref, value=_clean(c.findtext("value")), footprint=_clean(c.findtext("footprint")),
                lib=f"{lib.get('lib')}:{lib.get('part')}" if lib is not None else "",
                sheet=sheet, mpn=fields.get("MPN", ""), fields=fields,
                dnp="dnp" in props, exclude_bom="exclude_from_bom" in props)
        self.nets = {}                   # ネット名 → [(ref, pin, pinfunction)]
        self.pin_net = {}                # (ref, pin) → ネット名
        for n in root.iter("net"):
            name = n.get("name")
            nodes = [(x.get("ref"), x.get("pin"), x.get("pinfunction") or "") for x in n.iter("node")]
            self.nets[name] = nodes
            for ref, pin, _ in nodes:
                self.pin_net[(ref, pin)] = name

    def in_sheets(self, ref, sheets=SHEETS):
        return self.comps[ref]["sheet"] in sheets

    def interface(self, sheets=SHEETS):
        """3 シートの部品と、それ以外のシートの部品の両方が乗っているネット。"""
        out = {}
        for name, nodes in self.nets.items():
            inside = [x for x in nodes if self.in_sheets(x[0], sheets)]
            outside = [x for x in nodes if not self.in_sheets(x[0], sheets)]
            if inside and outside:
                out[name] = (inside, outside)
        return out


# ---- 記号（回路図の lib_symbols から） ----
_sym = {}


def symbols():
    """lib_id → 記号の S 式。全シートの lib_symbols を集める。"""
    if not _sym:
        for f in SRC.glob("*.kicad_sch"):
            tree = kisym.parse(f.read_text(encoding="utf-8"))[0]
            ls = find1(tree, "lib_symbols")
            for s in find(ls, "symbol") if ls else []:
                _sym.setdefault(str(s[1]), s)
    return _sym


# ---- 足形（.kicad_pcb に置かれた実物から） ----
_fp = {}


def footprints():
    """部品番号 → 足形の S 式（板の上の位置と回転を含んだまま）。"""
    if not _fp:
        tree = kisym.parse(PCB.read_text(encoding="utf-8"))[0]
        for fp in find(tree, "footprint"):
            ref = next((str(p[2]) for p in find(fp, "property") if p[1] == "Reference"), None)
            if ref:
                _fp[ref] = fp
    return _fp


PRETTY = HERE / "voicepe.pretty"
_KEEP = ("fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc", "pad")
_DROP_IN_PAD = ("uuid", "net", "pinfunction", "pintype")


def _mirror_y(node):
    """局所 Y と向きの符号を反転する（gen_pcb.mirror_y と同じ規則。裏面の足形はこの形で保存されている）。"""
    if not isinstance(node, list):
        return node
    if node and str(node[0]) in ("at", "start", "end", "center", "mid", "xy"):
        out = list(node)
        if len(out) > 2:
            out[2] = f"{(-float(out[2])) + 0.0:g}"      # + 0.0 で -0 を 0 にする
        if str(node[0]) == "at" and len(out) > 3:
            out[3] = f"{(-float(out[3])) % 360 + 0.0:g}"
        return out
    return [_mirror_y(e) for e in node]


def _flip(s):
    s = str(s)
    return Str("B." + s[2:]) if s.startswith("F.") else Str("F." + s[2:]) if s.startswith("B.") else Str(s)


def _pad_angle(pad):
    at = find1(pad, "at")
    return float(at[3]) if len(at) > 3 else 0.0


def _set_pad_angle(pad, a):
    at = find1(pad, "at")
    new = list(at[:3])
    a %= 360
    if abs(a) > 1e-6 and abs(a - 360) > 1e-6:
        new.append(f"{a:g}")
    pad[pad.index(at)] = new


def to_library(fp):
    """板の上に置かれた足形 → 表向き・回転 0 のライブラリの足形。

    板のファイルでは、図形とパッドの位置は足形の局所座標で、**パッドの向きだけは板の上での向き**
    （足形の回転を足した値）で入っている（gen_pcb.place_footprint の注記と同じ）。
    裏面の足形は局所 Y と向きが反転し、層が B.* になっている。⇒ 反転を戻し、足形の回転を引く。
    """
    back = str(find1(fp, "layer")[1]) == "B.Cu"
    at = find1(fp, "at")
    ang = float(at[3]) if len(at) > 3 else 0.0
    name = str(fp[1]).split(":")[-1]
    out = ["footprint", Str(name), ["version", "20241229"], ["generator", Str("katanori/voicepe.py")],
           ["layer", Str("F.Cu")],
           ["descr", Str("Home Assistant Voice PE（CERN-OHL-P v2・© Nabu Casa）の板から写した足形")]]
    attr = find1(fp, "attr")
    if attr:
        out.append(list(attr))
    for e in fp[2:]:
        if not isinstance(e, list) or e[0] not in _KEEP:
            continue
        lay = find1(e, "layer")
        if e[0] == "fp_circle" and lay and "CrtYd" in str(lay[1]):
            # 🔴 XU316 の足形は外形（courtyard）の線に 1 番ピンの印の丸が混ざっていて、
            #    KiCad の DRC が malformed_courtyard を 18 件出した（2026-09-15）。印は外形ではないので落とす
            continue
        body = [x for x in e if not (isinstance(x, list) and x[0] in _DROP_IN_PAD)]
        if back:
            a_board = _pad_angle(body) if e[0] == "pad" else 0.0
            body = _mirror_y(body)
            for k in ("layer", "layers"):
                lay = find1(body, k)
                if lay:
                    body[body.index(lay)] = [k] + [_flip(s) for s in lay[1:]]
            if e[0] == "pad":
                # 置くとき（gen_pcb）は「反転 → 向きに足形の回転を足す」なので、その逆
                _set_pad_angle(body, ang - a_board)
        elif e[0] == "pad":
            _set_pad_angle(body, _pad_angle(body) - ang)
        out.append(body)
    _clean_courtyard(out)
    return out, back, ang


def _clean_courtyard(fp):
    """外形（courtyard）の線が 1 周の閉じた形になっていなければ、線の範囲を囲う長方形 1 つに替える。

    🔴 XU316 の足形は外形の線に長さ 0 の線が 9 本と、内側に余計な線が 1 本混ざっていて、
       KiCad の DRC が malformed_courtyard を 19 件出した（2026-09-15・Voice PE の元の足形のまま）。
    """
    idx = [i for i, e in enumerate(fp) if isinstance(e, list) and e[0] == "fp_line"
           and find1(e, "layer") and "CrtYd" in str(find1(e, "layer")[1])]
    if not idx:
        return
    segs, deg = [], {}
    for i in idx:
        s, e = find1(fp[i], "start"), find1(fp[i], "end")
        a = (round(float(s[1]), 4), round(float(s[2]), 4))
        b = (round(float(e[1]), 4), round(float(e[2]), 4))
        if a == b:
            continue
        segs.append((a, b))
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    if segs and all(d == 2 for d in deg.values()) and len(segs) == len(deg):
        if len(segs) != len(idx):                      # 長さ 0 の線だけ落とす
            keep = [i for i in idx if (lambda s, e: (s[1], s[2]) != (e[1], e[2]))(find1(fp[i], "start"), find1(fp[i], "end"))]
            for i in sorted(set(idx) - set(keep), reverse=True):
                del fp[i]
        return
    xs = [p[0] for s in segs for p in s]
    ys = [p[1] for s in segs for p in s]
    lay = find1(fp[idx[0]], "layer")
    for i in sorted(idx, reverse=True):
        del fp[i]
    fp.append(["fp_rect", ["start", f"{min(xs):g}", f"{min(ys):g}"], ["end", f"{max(xs):g}", f"{max(ys):g}"],
               ["stroke", ["width", "0.05"], ["type", "solid"]], ["fill", "no"], list(lay)])


_fpname = {}


def fp_names(refs):
    """部品番号 → voicepe.pretty の足形の名前。

    🔴 Voice PE の中で**同じ名前なのにパッドが違う足形**がある（C0603・R0603 に 0.889 角と 0.7×0.9 の
    2 種類。2026-09-15）。名前だけで 1 つにまとめると片方のパッドが変わるので、形ごとに名前を分ける
    （2 つ目は「名前_v2」）。
    """
    if not all(r in _fpname for r in refs):
        fps = footprints()
        sigs = {}
        for ref in sorted(refs, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))):
            lib, _, _ = to_library(fps[ref])
            base = str(lib[1])
            sig = _pads_sig(lib)
            names = sigs.setdefault(base, [])
            if sig not in names:
                names.append(sig)
            k = names.index(sig)
            _fpname[ref] = base if k == 0 else f"{base}_v{k + 1}"
    return {r: _fpname[r] for r in refs}


def export_pretty(refs):
    """refs の部品が使う足形を voicepe.pretty に書き出す。戻り値は 部品番号 → 足形の名前。"""
    PRETTY.mkdir(exist_ok=True)
    fps = footprints()
    names = fp_names(refs)
    written = set()
    # 同じ名前の足形は、部品番号の若い順で最初の物を書く（呼ぶ側の並びで中身が揺れないように）
    for ref in sorted(refs, key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))):
        name = names[ref]
        if name in written:
            continue
        lib, _, _ = to_library(fps[ref])
        lib[1] = Str(name)
        (PRETTY / f"{name}.kicad_mod").write_text(kisym.dump(lib) + "\n", encoding="utf-8")
        written.add(name)
    return names


def _pads_sig(fp):
    return sorted((str(p[1]), tuple(f"{float(v):g}" for v in find1(p, "at")[1:3]),
                   tuple(f"{float(v):g}" for v in find1(p, "size")[1:3]), str(p[3]), _pad_angle(p) % 180)
                  for p in find(fp, "pad"))


def roundtrip(ref):
    """ライブラリの足形を、元と同じ面・同じ回転で置き直したとき、全パッドが元と一致するか。"""
    orig = footprints()[ref]
    lib, back, ang = to_library(orig)
    if back:
        lib = _mirror_y(lib)
    bad = []
    got = {str(p[1]): p for p in find(lib, "pad")}
    for p in find(orig, "pad"):
        q = got[str(p[1])]
        pa, qa = find1(p, "at"), find1(q, "at")
        a_orig = _pad_angle(p) % 360
        a_new = (_pad_angle(q) + ang) % 360
        same_pos = all(abs(float(pa[i]) - float(qa[i])) < 1e-4 for i in (1, 2))
        sx, sy = (float(v) for v in find1(p, "size")[1:3])
        d = (a_orig - a_new) % 360
        same_rot = min(d, 360 - d) < 1e-3 or (abs(sx - sy) < 1e-6 and min(d % 90, 90 - d % 90) < 1e-3) \
            or min(abs(d - 180), abs(d + 180)) < 1e-3
        lp = [str(s) for s in find1(p, "layers")[1:]]
        lq = [str(s) for s in find1(q, "layers")[1:]]
        lq = [str(_flip(s)) for s in lq] if back else lq
        if not (same_pos and same_rot and lp == lq):
            bad.append((str(p[1]), pa[1:], qa[1:], a_orig, a_new, lp, lq))
    return bad


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    v = VoicePE()
    if len(sys.argv) > 1:
        for name in sys.argv[1:]:
            for n, nodes in v.nets.items():
                if n.split("/")[-1] == name or n == name:
                    print(n)
                    for ref, pin, fn in nodes:
                        c = v.comps[ref]
                        print(f"   {c['sheet']:16s} {ref:6s} {pin:>4s} {fn:22s} {c['value']}")
        sys.exit()
    for name, (inside, outside) in sorted(v.interface().items()):
        o = " ".join(f"{r}.{p}" for r, p, _ in outside)
        i = " ".join(f"{r}.{p}" for r, p, _ in inside)
        print(f"{name:22s} 外: {o}\n{'':22s} 内: {i}")
