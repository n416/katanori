# -*- coding: utf-8 -*-
"""hub_power.kicad_sch のつながりを、写した元と突き合わせる。

  python check_sch.py

1. 電源の部分 — Adafruit PowerBoost 1000C Rev B の EAGLE 回路図（hardware/ref/powerboost_1000c/）の
   ネットごとに、写した先のピンが全部同じ 1 本のネットに入っているか。逆に、写した先の 1 本の
   ネットに元の 2 本が混ざっていないか。
2. ハブの部分 — relay_board.html の部品（PARTS / RELAY / BUTTON）と hub_ports.py の口の
   ピンごとのネットが、写した先で同じネットか。

KiCad の回路図は kicad-cli でネットリストに書き出してから読む（自分の書いた座標を信じない）。
"""

import collections
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "parts"))
import hub_ports  # noqa: E402
from gen_sch import PORT_FLIP  # noqa: E402   # 並びを逆にした口（2 か所に書かない）

CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SCH = HERE / "hub_power" / "hub_power.kicad_sch"
EAGLE = HERE.parent / "ref" / "powerboost_1000c" / "Adafruit PowerBoost 1000C Rev B.sch"
RELAY_HTML = HERE.parent / "parts" / "relay_board.html"


def kicad_nets():
    out = HERE / "hub_power" / "_check.xml"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out), str(SCH)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ネットリストを書き出せない:\n" + r.stdout + r.stderr)
    root = ET.parse(out).getroot()
    out.unlink()
    pin2net = {}
    for net in root.iter("net"):
        for node in net.iter("node"):
            pin2net[(node.get("ref"), node.get("pin"))] = net.get("name").lstrip("/")
    return pin2net


# ---- 1. PowerBoost ----
# EAGLE の部品 → 写した先の部品
REF = {"DONE": "LED3", "CHRG/LBO": "LED4", "THERM": "R15", "T1": "Q1", "CN4": "J13", "B1": "J10"}   # micro USB → 板に載せた USB-C（2026-09-12）
DROPPED = {"CN1", "R9", "R10", "R11", "R12", "X1", "JP2"}   # 5V を板の外へ出す物（gen_sch.py の冒頭）
# ピン名 → ピン番号（2 端子の受動部品は向きを問わないので別に扱う）
PINS = {
    "U1": {"VOUT": ["1", "15", "16"], "SW": ["3", "4"], "PGND": ["5", "6", "7"], "GND": ["13", "17"],
           "VBAT": ["8"], "LBI": ["9"], "SYNC": ["10"], "EN": ["11"], "LBO": ["12"], "FB": ["14"]},
    "U2": {"VOUT1": ["1"], "VOUT2": ["20"], "VPCC": ["2"], "SEL": ["3"], "PROG2": ["4"], "THERM": ["5"],
           "STAT2": ["7"], "STAT1/LBO": ["8"], "/TE": ["9"], "VSS1": ["10"], "VSS2": ["11"],
           "THERMAL": ["21"], "PROG3": ["12"], "PROG1": ["13"], "VBAT1": ["14"], "VBAT2": ["15"],
           "VBATSENS": ["16"], "CE": ["17"], "VIN1": ["18"], "VIN2": ["19"]},
    "Q1": {"B": ["1"], "E": ["2"], "C": ["3"]},
    "J13": {"VBUS": ["A4", "A9", "B4", "B9"], "GND": ["A1", "B1", "A12", "B12"]},
    "J10": {"-": ["1"], "+": ["2"]},
}
LED_PINS = {"A": ["2"], "C": ["1"]}
# 写すときに意図して変えたつながり: (EAGLE の部品, ピン) → 理由
CHANGED = {("J10", "+"): "電池の + と VLIPO のあいだに INA226 のシャント（R41）を入れた"}


def eagle_nets():
    root = ET.parse(EAGLE).getroot()
    parts = {p.get("name"): p for p in root.iter("part")}
    supplies = {"GND", "5.0V", "VBAT", "VBUS", "VLIPO"}
    nets = {}
    for net in root.iter("net"):
        pins = set()
        for pr in net.iter("pinref"):
            ref = pr.get("part")
            if ref.startswith("U$") or ref.startswith("GND") and parts[ref].get("deviceset") in supplies:
                continue
            if parts[ref].get("deviceset") in supplies:
                continue
            pins.add((ref, pr.get("pin")))
        nets[net.get("name")] = pins
    return nets


def check_powerboost(k):
    bad = 0
    e2k = {}
    seen = collections.defaultdict(set)
    for ename, pins in sorted(eagle_nets().items()):
        dest = set()
        for ref, pin in sorted(pins):
            if ref in DROPPED:
                continue
            nref = REF.get(ref, ref)
            if (nref, pin) in CHANGED:
                print(f"  変えた  {ename:7s} {ref}.{pin} … {CHANGED[(nref, pin)]}"
                      f"（写した先は {k.get((nref, PINS[nref][pin][0]))}）")
                continue
            if nref in PINS:
                nums = PINS[nref][pin]
            elif nref.startswith("LED"):
                nums = LED_PINS[pin]
            else:
                nums = None   # 2 端子の受動部品は下でまとめて見る
            if nums is None:
                continue
            for n in nums:
                net = k.get((nref, n))
                if net is None:
                    print(f"  ❌ {ename}: {nref}.{n} が写した先のどのネットにも無い")
                    bad += 1
                dest.add(net)
                seen[net].add(ename)
        # 2 端子の受動部品: EAGLE でその部品がつながる 2 本のネットの組と、写した先の組を比べる
        dest.discard(None)
        if len(dest) > 1:
            print(f"  ❌ {ename}: 写した先で {sorted(dest)} に割れている")
            bad += 1
        if dest:
            e2k[ename] = dest.pop()
    for net, enames in seen.items():
        if len(enames) > 1:
            print(f"  ❌ 写した先の {net} に元の {sorted(enames)} が混ざっている")
            bad += 1
    # 受動部品（R・C・L・LED 以外の 2 端子）
    en = eagle_nets()
    byref = collections.defaultdict(set)
    for ename, pins in en.items():
        for ref, pin in pins:
            byref[ref].add(ename)
    for ref, enames in sorted(byref.items()):
        nref = REF.get(ref, ref)
        if ref in DROPPED or nref in PINS or nref.startswith("LED"):
            continue
        want = sorted(e2k.get(e, "?" + e) for e in enames)
        got = sorted({k.get((nref, "1")), k.get((nref, "2"))})
        if want != got:
            print(f"  ❌ {ref}→{nref}: 元は {sorted(enames)}＝{want}、写した先は {got}")
            bad += 1
    print("  ネットの読み替え: " + "・".join(f"{a}→{b}" for a, b in sorted(e2k.items()) if a != b))
    return bad


# ---- 2. ハブ ----
HUB_REF = {"R1": "R31", "R2": "R32", "D1": "D31", "C1": "C31", "C2": "C32", "Q1": "Q31",
           "RELAY": "K31"}
# 🔒 2026-09-12 ユーザー: 板の上の直挿しの会話ボタン（relay_board の BUTTON）は載せない
HUB_PIN = {"Q31": {"B": "1", "C": "3", "E": "2"},   # SOT-23（2026-09-12 に 2SC1815 から替えた） "D31": {"cath": "1", "anode": "2"},
           # 🔒 2026-09-12 リレーを表面実装の Omron G6S-2F へ替えた。ピン番号は Omron の
           #    データシート（en-g6s.pdf 5 ページ・Top View）と KiCad の記号の両方で確かめた
           "K31": {"COM": "4", "コイル+": "1", "コイル-": "12", "NO": "5", "NC": "3"},
           "SW31": {"C": "2", "NO": "1", "NC": "3"}}
PORT_REF = {"XIAO": "J1", "OLED": "J2", "AS5600": "J3", "PHIN": "J4", "PHOUT": "J5",
            "REED": "J6", "TOGGLE": "J7", "BTN2": "J8"}


def check_hub(k):
    txt = RELAY_HTML.read_text(encoding="utf-8")
    body = txt[txt.index("PARTS: ["):txt.index("JUMPERS:")]
    want = []   # (ref, pin, net)
    for m in re.finditer(r"\{ id:'(\w+)', name:'[^']*',\s*kind:'(\w+)',\s*(?:a:'\w+',\s*b:'\w+'|pins:\{[^}]*\})"
                         r"(?:,\s*cath:'(\w)')?,?\s*nets:\{([^}]*)\}", body, re.S):
        pid, kind, cath, nets = m.groups()
        nets = dict(re.findall(r"(\w+):'(\w+)'", nets))
        ref = HUB_REF[pid]
        if kind == "tr":
            for t, n in nets.items():
                want.append((ref, HUB_PIN[ref][t], n))
        elif kind == "diode":
            ca = cath or "a"
            an = "b" if ca == "a" else "a"
            want += [(ref, "1", nets[ca]), (ref, "2", nets[an])]
        else:   # 抵抗・コンデンサは向きを問わない
            want.append((ref, "*", tuple(sorted(nets.values()))))
    relay = re.search(r"RELAY: \{.*?pins:\[(.*?)\]", body, re.S).group(1)
    coil = []
    for fn, net in re.findall(r"fn:'([^']+)',\s*net:\s*(?:'(\w+)'|null)", relay):
        if fn == "コイル":
            coil.append(net)
            continue
        want.append(("K31", HUB_PIN["K31"][fn], net or None))
    want += [("K31", "*coil", tuple(sorted(coil)))]
    for p in hub_ports.ports():
        if p.id in PORT_REF:
            pins = list(reversed(p.pins)) if p.id in PORT_FLIP else p.pins
            for i, (h, fn, net, x, y) in enumerate(pins, 1):
                want.append((PORT_REF[p.id], str(i), net))
    bad = 0
    for ref, pin, net in want:
        if pin == "*":
            got = tuple(sorted({k.get((ref, "1")), k.get((ref, "2"))}))
        elif pin == "*coil":
            got = tuple(sorted({k.get((ref, HUB_PIN[ref]["コイル+"])),
                                k.get((ref, HUB_PIN[ref]["コイル-"]))}))
        else:
            got = k.get((ref, pin))
            if got and got.startswith("unconnected-"):
                got = None
        if got != net:
            print(f"  ❌ {ref}.{pin}: 元は {net}、写した先は {got}")
            bad += 1
    print(f"  {len(want)} 本を突き合わせた")
    return bad


# ---- 3. 電流計 ----
# 電源板側のネットは名前を分けてある（gen_sch.py の PW）
INA = {("U3", "1"): "V33P", ("U3", "2"): "GNDP", ("U3", "6"): "V33P", ("U3", "7"): "GNDP",
       ("U3", "4"): "SDAP", ("U3", "5"): "SCLP", ("U3", "10"): "BATP", ("U3", "9"): "VLIPO",
       ("U3", "8"): "VLIPO", ("R41", "1"): "BATP", ("R41", "2"): "VLIPO",
       ("J10", "1"): "GNDP", ("J10", "2"): "BATP"}


def check_ina(k):
    bad = 0
    for (ref, pin), net in INA.items():
        if k.get((ref, pin)) != net:
            print(f"  ❌ {ref}.{pin}: {net} のはずが {k.get((ref, pin))}")
            bad += 1
    a1, a0 = k.get(("U3", "1")), k.get(("U3", "2"))
    addr = 0x40 + {("GNDP", "GNDP"): 0, ("GNDP", "V33P"): 1, ("V33P", "GNDP"): 4,
                   ("V33P", "V33P"): 5}[(a1, a0)]
    print(f"  INA226 のアドレス 0x{addr:02X}（A1={a1}・A0={a0}）")
    if addr != 0x44:
        bad += 1
    return bad


def check_cross(k):
    """板をまたぐ口 J11（ハブ）と J12（電源）が 1 対 1 で同じネットか。"""
    bad = 0
    want = [("V5", "V5P"), (None, None), ("GND", "GNDP"), ("V33", "V33P"),
            ("SDA", "SDAP"), ("SCL", "SCLP"), ("EN", "ENP")]
    for i, (wa, wb) in enumerate(want, 1):
        a, b = k.get(("J11", str(i))), k.get(("J12", str(i)))
        a = None if a and a.startswith("unconnected-") else a
        b = None if b and b.startswith("unconnected-") else b
        if (a, b) != (wa, wb):
            print(f"  ❌ {i} 本目: ハブ側 {a}（{wa} のはず）・電源側 {b}（{wb} のはず）")
            bad += 1
    print("  7 本とも相手が合っている（2 本目は空き・板ごとに名前を分けてある）" if not bad else "")
    return bad


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    k = kicad_nets()
    print("1. 電源（PowerBoost 1000C Rev B と突き合わせ）")
    b1 = check_powerboost(k)
    print("2. ハブ（relay_board.html と hub_ports.py と突き合わせ）")
    b2 = check_hub(k)
    print("3. 電流計")
    b3 = check_ina(k)
    print("4. 板をまたぐ口")
    b3 += check_cross(k)
    total = b1 + b2 + b3
    print(f"結果: ❌ {total} 件" if total else "結果: 合わない所は 0 件")
    sys.exit(1 if total else 0)
