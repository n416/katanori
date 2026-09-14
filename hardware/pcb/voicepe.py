# -*- coding: utf-8 -*-
"""Home Assistant Voice PE（hardware/ref/voice_pe/・CERN-OHL-P v2）を読む。

  python voicepe.py            → 3 シート（XMOS・DAC・Power）が外とつながる信号の一覧
  python voicepe.py <ネット名>  → そのネットの部品とピン

つながりは kicad-cli で書き出したネットリストを読む（回路図の座標を自分で辿らない）。
記号は回路図の lib_symbols、足形は .kicad_pcb に埋め込まれているものをそのまま使う。
"""

import pathlib
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
