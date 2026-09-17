# -*- coding: utf-8 -*-
"""gen_sch_voice.py が作った回路図を、元の 2 つ（Voice PE と v6.1）と突き合わせる。

  python check_sch_voice.py

回路図は kicad-cli でネットリストに書き出してから読む（生成側の座標や辞書を信じない）。
音声の板とハブは、ライザー（音声の板の J21 の k 番 ↔ ハブの J1 の 2k−1 番、J22 の k 番 ↔ J1 の 2k 番）を
1 本の線とみなしてつなぐ。

1. Voice PE から写した部品 — Voice PE で同じネットだったピンは同じネットに、違うネットだったピンは
   違うネットにいるか。例外は OVERRIDE（つなぎ方を変えた所）と MERGE（名前をまとめた電源）だけ。
2. ESP32 のピン — Voice PE の ESP32（U1）の GPIOn が乗っていたネットに、この板の U5 の IOn が乗っているか。
   写さなかった物のためのピン（NOT_COPIED_GPIO）と、つなぎ方を変えたピン（ESP_CHANGED）は別に確かめる。
3. 爆音の穴 — アンプの SHUTDOWN に乗っているのが決めた部品だけか。UART0 がテストパッドだけか。
4. v6.1 から残した部品 — v6.1 の回路図と同じ組み合わせでつながっているか（変えた口は除く）。
"""

import collections
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from kicad_paths import CLI  # noqa: E402
import voicepe  # noqa: E402
import gen_sch_voice as gv  # noqa: E402   # 写した部品の一覧と、変えた所の一覧だけを使う

BUILD = HERE / "build"
errors = []


def err(msg):
    errors.append(msg)
    print("  ❌", msg)


def netlist(sch):
    BUILD.mkdir(exist_ok=True)
    out = BUILD / (sch.stem + ".xml")
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out), str(sch)],
                   check=True, capture_output=True)
    root = ET.parse(out).getroot()
    # ⭐ 2026-09-17: 読んだら消す（check_sch.py と同じ作り）。
    #   残していたせいで build/ に 9/15 の網表が残り、別のセッションが
    #   それを読んで「Q2・R46 が居ない」と報告してきた。読むのはこの関数だけ。
    out.unlink()
    pin_net = {}
    names = {}
    for n in root.iter("net"):
        name = n.get("name")
        nodes = [(x.get("ref"), x.get("pin"), x.get("pinfunction") or "") for x in n.iter("node")]
        for ref, pin, fn in nodes:
            # KiCad は未接続のピンを 1 ピンだけの "unconnected-(...)" ネットにする
            pin_net[(ref, pin)] = None if name.startswith("unconnected-") else name
            names[(ref, pin)] = fn
    return pin_net, names


V = voicepe.VoicePE()
audio, audio_fn = netlist(HERE / "katanori61_audio" / "katanori61_audio.kicad_sch")
hub, hub_fn = netlist(HERE / "katanori61_hub" / "katanori61_hub.kicad_sch")
v61, _ = netlist(HERE / "katanori61" / "katanori61.kicad_sch")

# ---- 2 枚を 1 つのネットの集まりにする（ライザーの口でつなぐ） ----
parent = {}


def find(a):
    parent.setdefault(a, a)
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(a, b):
    parent[find(a)] = find(b)


NODE = {}      # (板, ref, pin) → ネットの代表（未接続なら None）
for board, pn in (("audio", audio), ("hub", hub)):
    for (ref, pin), net in pn.items():
        NODE[(board, ref, pin)] = find((board, net)) if net else None
for k in range(1, 8):
    for jref, hp in (("J21", 2 * k - 1), ("J22", 2 * k)):
        a, b = audio.get((jref, str(k))), hub.get(("J1", str(hp)))
        if a and b:
            union(("audio", a), ("hub", b))
        else:
            err(f"ライザー: 音声の板の {jref}.{k} ↔ ハブの J1.{hp} が片側で未接続")


def net_of(board, ref, pin):
    n = NODE.get((board, ref, pin), "missing")
    return n if n in (None, "missing") else find(n)


def label(rep):
    return f"{rep[1]}" if rep else "未接続"


COPIED = {r for refs in gv.COPY.values() for r in refs.split()}


def where(r):
    return "audio"


# ======== 1. Voice PE から写した部品 ========
print("1. Voice PE から写した部品")
missing = [r for r in COPIED if net_of(where(r), gv.vref(r), next(p for (rr, p) in V.pin_net if rr == r)) == "missing"]
for r in sorted(missing):
    err(f"{r}（→ {gv.vref(r)}）が回路図に無い")
OVERRIDE = {(r, p) for (r, p) in gv.OVERRIDE}
# 名前をまとめてよい Voice PE のネット（どれも同じ電源）
MERGE = [{"+3V3", "ESP_3V3"}]
vnet_to_new = collections.defaultdict(set)
new_to_vnet = collections.defaultdict(set)
checked = 0
for vnet, nodes in V.nets.items():
    short = vnet.split("/")[-1]
    got = collections.defaultdict(list)
    for r, p, _ in nodes:
        if r not in COPIED or (r, p) in OVERRIDE:
            continue
        rep = net_of(where(r), gv.vref(r), p)
        if rep == "missing":
            continue
        got[rep].append(f"{gv.vref(r)}.{p}")
        checked += 1
    if len(got) > 1:
        err(f"Voice PE の {short} が {len(got)} つに割れた: " +
            " / ".join(f"{label(k)}: {' '.join(v[:4])}" for k, v in got.items()))
    for rep in got:
        if rep:
            vnet_to_new[short].add(rep)
            new_to_vnet[rep].add(short)
    if None in got and sum(len(v) for v in got.values()) > 1 and len(got) == 1:
        err(f"Voice PE の {short}（{' '.join(got[None])}）が全部未接続になった")
for rep, vs in new_to_vnet.items():
    if len(vs) > 1 and not any(vs <= m for m in MERGE):
        err(f"Voice PE の違うネットが {label(rep)} で 1 つになった: {sorted(vs)}")
print(f"  写した部品 {len(COPIED)} 個・ピン {checked} 本を Voice PE のネットと照合")

# ======== 2. ESP32 のピン ========
print("2. ESP32 のピン（Voice PE の U1 の GPIOn ↔ この板の U5 の IOn）")
NOT_COPIED_GPIO = {3: "ミュートスイッチの検出", 23: "ヘッドホンの検出（GPIO17 の位置のピン名は下で確かめる）",
                   38: "2 本目の I2C", 39: "2 本目の I2C", 40: "XU316 との予備線", 41: "XU316 との予備線"}
# KiCad のネットリストのピン名は「名前_番号」（IO4_4・GPIO4_9）なので、末尾の番号を落として比べる
def pinname(fn, pin):
    return fn[: -len(pin) - 1] if fn.endswith("_" + pin) else fn


esp_pin = {pinname(fn, pin): (ref, pin) for (ref, pin), fn in audio_fn.items() if ref == "U5"}
seen = 0
for (r, p), vnet in V.pin_net.items():
    if r != "U1":
        continue
    fn = V.nets[vnet]
    fname = pinname(next((f for rr, pp, f in fn if rr == "U1" and pp == p), ""), p)
    m = re.match(r"GPIO(\d+)|MTDI|MTCK|MTDO|MTMS|U0TXD|U0RXD|XTAL_32K_P|SPICLK_P|SPICLK_N", fname)
    if not m:
        continue
    gpio = {"MTCK": 39, "MTDO": 40, "MTDI": 41, "MTMS": 42, "U0TXD": 43, "U0RXD": 44, "XTAL_32K_P": 15,
            "SPICLK_P": 47, "SPICLK_N": 48}.get(fname, int(m.group(1)) if m.group(1) else -1)
    # この Voice PE のネットに乗っている、写した部品のピンの行き先
    targets = {net_of(where(rr), gv.vref(rr), pp) for rr, pp, _ in V.nets[vnet] if rr in COPIED}
    targets.discard(None)
    targets.discard("missing")
    if not targets:
        continue
    seen += 1
    if gpio in NOT_COPIED_GPIO:
        err(f"GPIO{gpio} は写さない約束（{NOT_COPIED_GPIO[gpio]}）なのに、写した部品が乗っている")
        continue
    ref, pin = esp_pin.get(f"IO{gpio}", (None, None))
    got = net_of("audio", "U5", pin) if pin else "missing"
    if got not in targets:
        err(f"GPIO{gpio}: Voice PE では {sorted(label(t) for t in targets)} につながっていたが、U5 の IO{gpio} は {label(got) if got != 'missing' else '無い'}")
print(f"  Voice PE の ESP32 から写した相手があるピン {seen} 本")
# つなぎ方を変えたピン（Voice PE とは違う）: 名前 → 同じネットに居るべき相手（板・部品・ピン）
ESP_CHANGED = {
    "USB_D+": ("audio", "R157", "2", "USB の 22Ω の ESP32 側（Voice PE は USB の切替 U17 を挟んでいた）"),
    "USB_D-": ("audio", "R156", "2", "同上"),
    "IO2": ("audio", "R214", "1", "マイクのミュート（Voice PE はスライドスイッチ SW1）"),
    "IO40": ("hub", "J6", "2", "会話ボタン（ハブの J6・ライザー越し）"),
    "IO16": ("hub", "J2", "3", "画面の SCL（ハブの J2・ライザー越し）"), "IO17": ("hub", "J2", "4", "画面の SDA"),
    "IO18": ("hub", "J2", "5", "画面の RES"), "IO21": ("hub", "J2", "6", "画面の DC"), "IO48": ("hub", "J2", "7", "画面の CS"),
    "IO5": ("hub", "U3", "4", "共用の I2C の SDA（ハブの INA226・ライザー越し）"),
    "IO6": ("hub", "U3", "5", "共用の I2C の SCL"),
    "TXD0": ("audio", "TP1", "1", "UART0 はテストパッドだけ"), "RXD0": ("audio", "TP2", "1", "同上"),
    "IO0": ("audio", "TP3", "1", "書き込みモード"), "EN": ("audio", "TP4", "1", "リセット"),
}
for fn, (board, ref, pin, why) in ESP_CHANGED.items():
    a = net_of("audio", "U5", esp_pin[fn][1])
    b = net_of(board, ref, pin)
    if a is None or a != b:
        err(f"U5 の {fn} が {ref}.{pin} と同じネットにいない（{why}）")
print(f"  変えたピン {len(ESP_CHANGED)} 本を確かめた")
# ライザーを越える電源と USB（名前が同じでも、ライザーの番号がずれていれば別のネットになる）
ACROSS = [(("hub", "J13", "A6"), "USB_DP"), (("hub", "J13", "A7"), "USB_DN"), (("hub", "U1", "1"), "V5"),
          (("hub", "U3", "1"), "V33"), (("hub", "U3", "2"), "GND")]
audio_names = set(audio.values())
for (board, ref, pin), anet in ACROSS:
    full = next((n for n in ("/" + anet, anet) if n in audio_names), None)   # ラベルのネットは "/名前"・電源の記号は "名前"
    if full is None or net_of(board, ref, pin) != find(("audio", full)):
        err(f"ハブの {ref}.{pin} が音声の板の {anet} とつながっていない（ライザーの並び）")
print(f"  ライザーを越える電源と USB {len(ACROSS)} 本を確かめた")
# XU316 の JTAG はテストパッド J16（Voice PE の J5 の代わり）。XU316 のピンの名前で突き合わせる
JTAG = {"2": "TMS", "3": "TCK", "4": "TDI", "5": "TDO", "6": "RST_N", "1": "VDDIOB18", "7": "GND"}
u2_pin = {pinname(fn, pin): pin for (ref, pin), fn in audio_fn.items() if ref == "U102"}
for jp, sig in JTAG.items():
    a = net_of("audio", "J16", jp)
    b = net_of("audio", "U102", u2_pin.get(sig, "?"))
    if a is None or a != b:
        err(f"JTAG のパッド J16.{jp} が XU316 の {sig} と同じネットにいない")
if net_of("audio", "J16", "8") not in (None, "missing"):
    err("JTAG のパッド J16.8 は空きのはず")
print(f"  JTAG のテストパッド {len(JTAG)} 個を XU316 のピンと確かめた")

# ======== 3. 爆音の穴 ========
print("3. 爆音の穴")
shut = net_of("audio", "U109", "1")
on_shut = sorted(f"{r}.{p}" for (b, r, p), n in NODE.items() if b == "audio" and n and find(n) == shut)
want = ["C129.1", "R125.1", "R135.2", "U109.1"]
if on_shut != want:
    err(f"アンプの SHUTDOWN に乗っている物が違う: {on_shut}（あるべき: {want}）")
else:
    print("  SHUTDOWN: 470kΩ（R135）で引き下げ・4.7kΩ（R125）の向こうは ESP32 だけ・ヘッドホン検出の Q が居ない")
if net_of("audio", "R135", "1") != net_of("audio", "U5", "1"):
    err("R135（470kΩ）の反対側が GND ではない")
en_side = net_of("audio", "R125", "2")
on_en = sorted(f"{r}.{p}" for (b, r, p), n in NODE.items() if b == "audio" and n and find(n) == en_side)
if on_en != ["R125.2", "R136.2"]:
    err(f"R125 の向こう側に余計な物がいる: {on_en}")
pa = net_of("audio", "R136", "1")
on_pa = sorted(f"{r}.{p}" for (b, r, p), n in NODE.items() if b == "audio" and n and find(n) == pa)
if on_pa != ["R136.1", f"U5.{esp_pin['IO47'][1]}"]:
    err(f"アンプの EN（R136 の手前）に ESP32 の IO47 以外が乗っている: {on_pa}（XU316 に握らせない）")
for fn in ("TXD0", "RXD0"):
    n = net_of("audio", "U5", esp_pin[fn][1])
    on = sorted(f"{r}.{p}" for (b, r, p), nn in NODE.items() if b == "audio" and nn and find(nn) == n)
    if len(on) != 2 or not any(x.startswith("TP") for x in on):
        err(f"{fn}（GPIO43/44）にテストパッド以外が乗っている: {on}")
print("  UART0 はテストパッドだけ")

# ======== 4. v6.1 から残した部品 ========
print("4. v6.1 から残した部品")
CHANGED_V61 = {("J13", "A6"), ("J13", "B6"), ("J13", "A7"), ("J13", "B7"), ("R42", "2"), ("R43", "2")}
CHANGED_V61 |= {("J2", str(i)) for i in range(1, 8)} | {("J1", str(i)) for i in range(1, 15)}   # 画面の口・ライザー
kept = {(r, p) for (r, p) in v61 if (r, p) in hub and (r, p) not in CHANGED_V61 and not r.startswith("#")}
by_old = collections.defaultdict(set)
by_new = collections.defaultdict(set)
for r, p in kept:
    by_old[v61[(r, p)]].add(net_of("hub", r, p))
    by_new[net_of("hub", r, p)].add(v61[(r, p)])
for old, news in by_old.items():
    if len(news) > 1:
        err(f"v6.1 の {old} が割れた: {sorted(map(label, news))}")
for new, olds in by_new.items():
    olds.discard(None)
    if new and len(olds) > 1:
        err(f"v6.1 の違うネット {sorted(olds)} が {label(new)} で 1 つになった")
gone = sorted({r for (r, p) in v61 if (r, p) not in hub and not r.startswith("#")})
print(f"  残したピン {len(kept)} 本を照合。外した部品: {' '.join(gone)}")

print(f"結果: 合わない所は {len(errors)} 件")
sys.exit(1 if errors else 0)
