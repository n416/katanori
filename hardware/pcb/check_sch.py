# -*- coding: utf-8 -*-
"""katanori61.kicad_sch のつながりを、写した元と突き合わせる。

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
sys.path.insert(0, str(HERE.parents[0] / "parts"))
import hub_ports  # noqa: E402
from gen_sch import PORT_FLIP  # noqa: E402   # 並びを逆にした口（2 か所に書かない）

sys.path.insert(0, str(HERE))
from kicad_paths import CLI  # noqa: E402
SCH = HERE / "katanori61" / "katanori61.kicad_sch"
EAGLE = HERE.parents[0] / "ref" / "powerboost_1000c" / "Adafruit PowerBoost 1000C Rev B.sch"
RELAY_HTML = HERE.parents[0] / "parts" / "relay_board.html"


def kicad_nets():
    out = HERE / "katanori61" / "_check.xml"
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
REF = {"THERM": "R15", "CN4": "J13", "B1": "J10"}   # micro USB → 板に載せた USB-C（2026-09-12）
DROPPED = {"CN1", "R9", "R10", "R11", "R12", "X1", "JP2"}   # 5V を板の外へ出す物（gen_sch.py の冒頭）
# 🔒 2026-09-19 ユーザー「LED は本来不要」: 表示灯 4 つと、それだけに要る抵抗 4 本・T1（gen_sch.py の U1 の下）
DROPPED |= {"LED1", "R20", "T1", "LED2", "R5", "DONE", "R14", "CHRG/LBO", "R8"}
# ピン名 → ピン番号（2 端子の受動部品は向きを問わないので別に扱う）
PINS = {
    "U1": {"VOUT": ["1", "15", "16"], "SW": ["3", "4"], "PGND": ["5", "6", "7"], "GND": ["13", "17"],
           "VBAT": ["8"], "LBI": ["9"], "SYNC": ["10"], "EN": ["11"], "LBO": ["12"], "FB": ["14"]},
    "U2": {"VOUT1": ["1"], "VOUT2": ["20"], "VPCC": ["2"], "SEL": ["3"], "PROG2": ["4"], "THERM": ["5"],
           "STAT2": ["7"], "STAT1/LBO": ["8"], "/TE": ["9"], "VSS1": ["10"], "VSS2": ["11"],
           "THERMAL": ["21"], "PROG3": ["12"], "PROG1": ["13"], "VBAT1": ["14"], "VBAT2": ["15"],
           "VBATSENS": ["16"], "CE": ["17"], "VIN1": ["18"], "VIN2": ["19"]},
    "J13": {"VBUS": ["A4", "A9", "B4", "B9"], "GND": ["A1", "B1", "A12", "B12"]},
    "J10": {"-": ["1"], "+": ["2"]},
}
LED_PINS = {"A": ["2"], "C": ["1"]}
# 写すときに意図して変えたつながり: (EAGLE の部品, ピン) → 理由
CHANGED = {("J10", "+"): "電池の + と VLIPO のあいだに、逆接保護の P-ch（Q2）と INA226 のシャント（R41）を入れた"}


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
# 🔒 2026-09-13: AS5600（J3）とトグル（J7）は板の上の部品になって口が消え、XIAO は
#    hub_ports の 1 列 7 本から直挿しの 2 列 14 本になった（下の check_xiao で別に見る）。
# 🔒 2026-09-13 ユーザー「別に線が二股になるのは構わない」: リード（J6）と会話ボタン（J8）を
#    1 つの 4 ピン PH にまとめたので、この 2 つも hub_ports からは引かない（下の KNOB で見る）
PORT_REF = {"OLED": "J2", "PHIN": "J4", "PHOUT": "J5"}


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
# 🔒 2026-09-13: 板が 1 枚になったので、電源板側の別名（V33P・GNDP …）は無くなった
INA = {("U3", "1"): "V33", ("U3", "2"): "GND", ("U3", "6"): "V33", ("U3", "7"): "GND",
       ("U3", "4"): "SDA", ("U3", "5"): "SCL", ("U3", "10"): "BATP", ("U3", "9"): "VLIPO",
       ("U3", "8"): "VLIPO", ("R41", "1"): "BATP", ("R41", "2"): "VLIPO",
       # ⭐ 2026-09-16 夕: 逆接保護の P-ch（Q2）を J10 と シャントのあいだに入れたので、
       #    J10 の 2 番は BATP ではなく **BATRAW**（保護の手前）になった。
       #    🔴 向きを検算する: ドレイン（3 番）が電池側 BATRAW・ソース（2 番）が負荷側 BATP。
       #       ここが入れ替わると、逆接のときボディダイオードが順方向になって保護にならない。
       ("J10", "1"): "GND", ("J10", "2"): "BATRAW",
       ("Q2", "3"): "BATRAW", ("Q2", "2"): "BATP", ("Q2", "1"): "BATG",
       ("R46", "1"): "BATG", ("R46", "2"): "GND"}


def check_ina(k):
    bad = 0
    for (ref, pin), net in INA.items():
        if k.get((ref, pin)) != net:
            print(f"  ❌ {ref}.{pin}: {net} のはずが {k.get((ref, pin))}")
            bad += 1
    a1, a0 = k.get(("U3", "1")), k.get(("U3", "2"))
    addr = 0x40 + {("GND", "GND"): 0, ("GND", "V33"): 1, ("V33", "GND"): 4,
                   ("V33", "V33"): 5}[(a1, a0)]
    print(f"  INA226 のアドレス 0x{addr:02X}（A1={a1}・A0={a0}）")
    if addr != 0x44:
        bad += 1
    return bad


# v6.1（2026-09-14）: XIAO はライザーの板を挟むので、この板から見えるのは 1x07 の 7 本だけ。
# 並びは配線の都合で決めてよい（ライザーの上で入れ替わる）ので、鏡像の心配はこの板には無い。
# 🔴 ただし **7 本の顔ぶれ**（XIAO が実際に使うピン）は hub_ports.py の XIAO の口と同じでなければならない。
def check_xiao(k):
    bad = 0
    want = {"V5", "GND", "V33", "SDA", "SCL", "BTN", "IN"}
    got = {k.get(("J1", str(i))) for i in range(1, 8)}
    got = {g for g in got if g and not g.startswith("unconnected-")}
    src = {net for (_h, _fn, net, _x, _y) in
           [p for p in hub_ports.ports() if p.id == "XIAO"][0].pins if net}
    if got != want:
        print(f"  ❌ J1 の 7 本: {sorted(want)} のはずが {sorted(got)}")
        bad += 1
    elif src != want:
        print(f"  ❌ hub_ports の XIAO の口とちがう: {sorted(src)}")
        bad += 1
    else:
        print("  7 本とも hub_ports の XIAO の口と同じ顔ぶれ（ライザーを挟むので並びは自由）")
    return bad


# ---- 5. つまみ（AS5600）と、リード・電源の押しボタン・会話ボタンの口 ----
# 📄 AS5600 データシート 9 ページ Figure 13: 3.3V 動作は VDD5V(1) と VDD3V3(2) をつなぐ。
#    DIR(8)=GND で時計回りに増える。OUT(3) と PGO(5) は繋がない（🔴 PGO は OTP）。
KNOB = {("U4", "1"): "V33", ("U4", "2"): "V33", ("U4", "4"): "GND", ("U4", "8"): "GND",
        ("U4", "6"): "SDA", ("U4", "7"): "SCL", ("U4", "3"): None, ("U4", "5"): None,
        # ⭐ 2026-09-19: ハッチのトグルをやめ、板の押しボタン SW2 へ。J7 はリードだけの 2 ピン
        ("J7", "1"): "EN", ("J7", "2"): "GND",
        # SW2 の 1–3 番（離して閉）が GND・EN（1 GND・3 EN）。2・4・5・6 番は使わない
        ("SW2", "1"): "GND", ("SW2", "3"): "EN", ("SW2", "2"): None, ("SW2", "4"): None, ("SW2", "5"): None, ("SW2", "6"): None,
        # 会話ボタンは 2 ピンの口（板は口だけ持つ。押しボタンは天板）
        ("J6", "1"): "GND", ("J6", "2"): "BTN"}


def check_knob(k):
    bad = 0
    for (ref, pin), net in KNOB.items():
        got = k.get((ref, pin))
        if got and got.startswith("unconnected-"):
            got = None
        if got != net:
            print(f"  ❌ {ref}.{pin}: {net} のはずが {got}")
            bad += 1
    if not bad:
        print(f"  AS5600 8 本・リード 2 本・電源の押しボタン 6 本・会話ボタン 2 本の計 {len(KNOB)} 本が想定どおり")
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
    print("4. XIAO の口（ライザーの 1x07）")
    b3 += check_xiao(k)
    print("5. つまみ（AS5600）・リードの口・電源の押しボタン・会話ボタンの口")
    b3 += check_knob(k)
    total = b1 + b2 + b3
    print(f"結果: ❌ {total} 件" if total else "結果: 合わない所は 0 件")
    sys.exit(1 if total else 0)
