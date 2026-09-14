# -*- coding: utf-8 -*-
"""v6.1 の板に Voice PE の音声部を統合した回路図を作る（docs/VOICE-BOARD.md）。

  python gen_sch_voice.py  → hardware/pcb/katanori61_voice/katanori61_voice.kicad_sch（主の板）
                              hardware/pcb/katanori61_mic/katanori61_mic.kicad_sch（前のマイクのライザー）

出どころは 2 つで、ここで新しく設計した回路はわずか（ESP32 モジュールの周りと口だけ）。
  v6.1 の板 : gen_sch.py の PARTS（リレーまわり・XIAO の受け・SPK IN を外す）
  音声部    : Home Assistant Voice PE（hardware/ref/voice_pe/・CERN-OHL-P v2・© Nabu Casa）の
              XMOS・DAC・Power シートと、ESP32 シートの I2S の直列抵抗と I2C の引き上げ

Voice PE の部品は、部品番号に 100 を足して写す（R36 → R136）。v6.1 の番号とぶつからない。
どの部品を写し、どのネットを付け替えたかは check_sch_voice.py が Voice PE のネットリストと突き合わせる。
"""

import copy
import pathlib
import re
import sys
import uuid

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_sch as gs  # noqa: E402   # 読み込むと v6.1 の PARTS ができる
import kisym  # noqa: E402
import voicepe  # noqa: E402

V = voicepe.VoicePE()
REF_OFS = 100


def clean(s):
    return str(s).replace("​", "")


def clean_tree(x):
    """S 式の中の文字列から幅ゼロの空白を除く。XU316 の記号は名前に U+200B が混ざっていて、
    親の名前だけ直すと子の記号（名前_0_1）と食い違い、KiCad が回路図を読めなくなる（2026-09-15）。"""
    if isinstance(x, list):
        return [clean_tree(e) for e in x]
    if isinstance(x, kisym.Str):
        return kisym.Str(clean(x))
    return x


kisym.EXTRA.update({clean(k): clean_tree(s) for k, s in voicepe.symbols().items()})


def vref(r):
    m = re.match(r"([A-Za-z]+)(\d+)$", r)
    return f"{m.group(1)}{int(m.group(2)) + REF_OFS}"


# 部品番号 → lib_id（回路図の実体から。ネットリストの libsource は名前が崩れることがある）
LIB_OF = {}
for f in voicepe.SRC.glob("*.kicad_sch"):
    t = kisym.parse(f.read_text(encoding="utf-8"))[0]
    for s in kisym.find(t, "symbol"):
        lid = kisym.find1(s, "lib_id")
        ref = next((p[2] for p in kisym.find(s, "property") if p[1] == "Reference"), None)
        if lid and ref and not ref.startswith("#"):
            LIB_OF[str(ref)] = clean(lid[1])

# ======== 写す部品（Voice PE の部品番号） ========
# 🔒 仕分けは docs/VOICE-BOARD.md 8 章。ここに無い部品は写さない（DNP・テストポイントも写さない。J5 だけ例外）
COPY = {
    # Power: 0.9V（TPS62065）・3.3V（TPS62827）・1.8V（ME6211）。5V は v6.1 の昇圧（V5）からもらう。
    #   写さない: USB1・U17（USB の切替）・U13（VBUS→5V のスイッチ）・SW3・D8・D14・D22・FB12・R42・R43・
    #             R49・R50・R64・C80・C81・C155・R147（どれも 2 つ目の USB-C と、そこから 5V を作る道のもの）
    "Power": "U10 L1 C63 C73 C83 C65 C66 C90 R44 R46 R47 C64 R108 R77 "
             "U12 L2 R54 R55 C74 C71 C72 R14 R45 "
             "U11 R78 R48 C68 C69 C70 "
             "D6 D7 R56 R57",                      # USB の ESD と 22Ω は残し、v6.1 の USB-C から ESP32 へ通す
    # DAC: コーデック・アンプ・SHUTDOWN の引き下げ（爆音対策の要）。
    #   写さない: J1（3.5mm ジャック）とその道（FB2・FB3・C15〜C18・D2・D3・R18・R19）・
    #             ヘッドホン検出（D9・Q2・R26）・J2（スピーカーの口。v6.1 の J5 を使う）
    "DAC": "U8 C13 C14 C87 C33 C34 C37 C38 C35 C36 C39 C40 C117 C123 C144 C88 C89 C119 "
           "R15 R16 R17 R23 R24 FB8 R75 R82 "
           "U9 C22 C23 C24 C27 C28 FB4 FB5 R20 R21 R22 C19 C20 C21 R99 R100 R39 "
           "R25 R35 C29 R36",
    # XMOS: XU316 一式・リセット・マイクの電源とバッファ。
    #   写さない: SW1・R10・R66・C9・U14（ミュートスイッチ）／D13・D20・R52・R98・R138・R139（ミュートの検出）／
    #             Q10・R58（USB の VBUS 検出）／R142・R143（ESP32 との予備線）／
    #             🔒 J5（XSYS2 の 20 ピン）と R32・R33（xLink の 22Ω）: JTAG は XU316 のそばのテストパッド J16 にする
    #             （ユーザー 2026-09-15。20 ピンは裏の右の帯にしか置けず、XU316 から 45mm 離れて配線が 4 本残った。
    #              xLink は xSCOPE のデバッグ用で、書き込み xflash には要らない）
    "XMOS": "U2 U3 X1 C2 C3 R3 R4 R1 "
            "C1 C6 C55 C56 C57 C60 C143 C43 C44 C45 C46 C47 C48 C49 C50 C51 C52 C53 C54 C142 C58 C41 "
            "FB6 FB7 FB9 Q3 R29 R63 R31 C92 R59 "
            "R2 R8 R7 C4 C5 C12 C110 R11 U6 U18 R28 Q4 R12 R114 "
            "R41 R60 R70 R71 R72 R73 R103 R104 R105",
    # ESP32 シートから、XU316 とのあいだの直列抵抗（0Ω）と I2C の引き上げだけ
    "ESP32": "R92 R93 R94 R95 R96 R97 R101 R102 R9 R146 R123 R128",
}
# 前のライザーに載る物（マイク 2 個・ESD・直列抵抗）
RISER = "U4 U5 D1 D4 D10 D12 D18 D19 R5 R109 R6 R112 R30 R110"
FP_NAME = voicepe.fp_names([r for refs in COPY.values() for r in refs.split()] + RISER.split())

# ======== ネットの付け替え（Voice PE の名前 → この板の名前） ========
RENAME = {
    "+5V": "V5", "+3V3": "V33", "ESP_3V3": "V33", "+1V8": "V18", "0.9V": "V09", "+3.3VA": "V33A",
    "I2C_SDA": "SDA", "I2C_SCL": "SCL",
    "SPK+": "SPKO", "SKP-": "SPKM",           # v6.1 の SPK OUT（J5）は 1 − SPKM・2 + SPKO
    "USB_D_P": "USB_DP", "USB_D_N": "USB_DN", "USB_IN_D_P": "ESP_USB_DP", "USB_IN_D_N": "ESP_USB_DN",
}
# Voice PE の ESP32 のピンのネット → この板の ESP32 のピンのネット
for pin in ("GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GPIO14"):
    RENAME[f"Net-(U1-{pin})"] = pin
RENAME["Net-(U1-XTAL_32K_P)"] = "GPIO15"
# ピンごとの付け替え（Voice PE と違うつなぎ方にした所）
OVERRIDE = {
    # ミュートスイッチ（SW1 と 1kΩ の引き上げ）の代わりに ESP32 の GPIO2 で握る。既定は下の R48 で引き下げ＝マイク有効
    ("R114", "1"): "MIC_MUTE",
}


def net_name(vnet):
    short = vnet.split("/")[-1]
    if short.startswith("unconnected-"):
        return None
    if short in RENAME:
        return RENAME[short]
    m = re.match(r"Net-\((\w+)-(.+)\)$", short)
    if m:
        ref, pin = m.groups()
        name = f"N_{vref(ref)}_{pin}"
    else:
        name = short
    return re.sub(r"[^A-Za-z0-9_+]", "_", name)


def vpart(r, grp):
    c = V.comps[r]
    lib = LIB_OF[r]
    pins = kisym.pins(lib)
    nets = {}
    for num in pins:
        vnet = V.pin_net.get((r, num))
        nets[num] = OVERRIDE.get((r, num), net_name(vnet) if vnet else None)
    # 足形は Voice PE の板から写した voicepe.pretty（同じ名前で形の違う物は _v2 に分けてある）
    fp = FP_NAME[r]
    return dict(ref=vref(r), lib=lib, value=clean(c["value"]), x=0.0, y=0.0, nets=nets,
                fp=f"voicepe:{fp}", lcsc="", dnp=c["dnp"], grp=grp,
                note=f"Voice PE {r}（{c['sheet']}）", src=r)


def part(ref, lib, value, nets, fp="", lcsc="", note="", grp="", dnp=False):
    return dict(ref=ref, lib=lib, value=value, x=0.0, y=0.0, nets=nets, fp=fp, lcsc=lcsc,
                note=note, dnp=dnp, grp=grp, src=None)


# ======== 主の板 ========
DROP_V61 = {"K31", "Q31", "D31", "R31", "R32", "C31",   # ミュートリレー（アンプの SHUTDOWN が代わる）
            "J4",                                        # SPK IN（アンプが板に載る）
            "J1"}                                        # XIAO の受け（ESP32 が板に載る）
MAIN = [copy.deepcopy(P) for P in gs.PARTS if P["ref"] not in DROP_V61]
# 🔒 ユーザー 2026-09-15（「ごっちゃごちゃ。簡単にショートしそう」）: v6.1 の電源部の受動部品を小さくして、
#    空いた面積を配線の余裕（すきま 0.15・線 0.2）に回す。0805 は v6.1 が手はんだを前提にしていた名残。
#    10µF・2.2µF は 5V・VBUS に付くので、0402 では耐圧が足りない ⇒ 0603。47µF と 10mΩ（1206）はそのまま。
#    ⚠ 大きさを変えた部品の LCSC 番号は 0805 の物なので消す（発注の前に在庫と一緒に引き直す・fab.py が止める）
SHRINK = {"Resistor_SMD:R_0805_2012Metric": "Resistor_SMD:R_0402_1005Metric",
          "LED_SMD:LED_0805_2012Metric": "LED_SMD:LED_0603_1608Metric"}
for P in MAIN:
    P.setdefault("src", None)
    old = P["fp"]
    if old == "Capacitor_SMD:C_0805_2012Metric":
        big = P["value"] in ("10uF", "2.2uF")
        P["fp"] = "Capacitor_SMD:C_0603_1608Metric" if big else "Capacitor_SMD:C_0402_1005Metric"
    elif old in SHRINK:
        P["fp"] = SHRINK[old]
    if P["fp"] != old:
        P["lcsc"] = ""
        P["note"] = (P["note"] + "・" if P["note"] else "") + f"統合基板で {old.split(':')[1].split('_')[1]} → {P['fp'].split(':')[1].split('_')[1]}（LCSC 番号は引き直し）"
    if P["ref"] == "J13":
        # 🔒 ユーザー 2026-09-15: USB-C を 1 つにして充電と書き込みを兼ねる
        P["nets"].update({"A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN"})
        P["note"] = "充電と書き込みの口（D+/D− は ESD と 22Ω を通って ESP32 の USB へ）"
    if P["ref"] == "J2":
        # 🔒 ユーザー 2026-09-15: 画面の口は後から SPI に替えられる 1x07。1〜4 番は今の OLED の並び
        P["lib"] = "Connector_Generic:Conn_01x07"
        P["value"] = "OLED"
        P["nets"] = {"1": "GND", "2": "V33", "3": "OLED_SCL", "4": "OLED_SDA",
                     "5": "OLED_RES", "6": "OLED_DC", "7": "OLED_CS"}
        P["fp"] = "Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical"
        P["note"] = "1 GND・2 3V3・3 SCL/SCK・4 SDA/MOSI・5 RES・6 DC・7 CS。今の I2C の OLED は 1〜4 だけ挿す"
    if P["ref"] in ("R42", "R43"):
        # 画面は専用の I2C（GPIO16/17）に移ったので、v6.1 の引き上げはそちらへ回す
        P["nets"] = {"1": "V33", "2": "OLED_SDA" if P["ref"] == "R42" else "OLED_SCL"}
        P["note"] = "画面の I2C の引き上げ"

for sheet, refs in COPY.items():
    grp = {"Power": "vpower", "DAC": "codec", "XMOS": "xmos", "ESP32": "esp"}[sheet]
    MAIN += [vpart(r, grp) for r in refs.split()]

# ---- ESP32-S3-WROOM-1U（新しく足した物）----
ESP_PINS = {
    "EN": "ESP_EN", "IO0": "ESP_BOOT", "TXD0": "ESP_TXD", "RXD0": "ESP_RXD",
    "USB_D-": "ESP_USB_DN", "USB_D+": "ESP_USB_DP",
    "IO4": "XU316_RST", "IO5": "SDA", "IO6": "SCL",
    "IO7": "GPIO7", "IO8": "GPIO8", "IO9": "GPIO9", "IO10": "GPIO10", "IO11": "GPIO11",
    "IO12": "GPIO12", "IO13": "GPIO13", "IO14": "GPIO14", "IO15": "GPIO15",
    "IO16": "OLED_SCL", "IO17": "OLED_SDA", "IO18": "OLED_RES", "IO21": "OLED_DC", "IO48": "OLED_CS",
    "IO47": "AUDIO_PA_EN", "IO2": "MIC_MUTE", "IO40": "BTN",
    "3V3": "V33", "GND": "GND",
}
esp_nets = {num: ESP_PINS.get(nm) for num, (nm, *_rest) in kisym.pins("RF_Module:ESP32-S3-WROOM-1").items()}
MAIN += [
    part("U5", "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1U-N16R8", esp_nets,
         "RF_Module:ESP32-S3-WROOM-1U", "C3013946", grp="esp",
         note="外付けアンテナ（u.FL）。IO35〜37 は Octal PSRAM で使えない。ピンは docs/VOICE-BOARD.md 5 章"),
    part("R46", "Device:R_Small", "10K", {"1": "V33", "2": "ESP_EN"}, gs.FP_R, grp="esp", note="EN の引き上げ"),
    part("C43", "Device:C_Small", "1uF", {"1": "ESP_EN", "2": "GND"}, gs.FP_C, grp="esp", note="EN の遅延"),
    part("R47", "Device:R_Small", "10K", {"1": "V33", "2": "ESP_BOOT"}, gs.FP_R, grp="esp", note="IO0 の引き上げ"),
    part("C44", "Device:C_Small", "10uF", {"1": "V33", "2": "GND"}, gs.FP_C, grp="esp", note="ESP32 のパスコン"),
    part("C45", "Device:C_Small", "0.1uF", {"1": "V33", "2": "GND"}, gs.FP_C, grp="esp", note="ESP32 のパスコン"),
    part("R48", "Device:R_Small", "10K", {"1": "MUTE_ON", "2": "GND"}, gs.FP_R, grp="esp",
         note="マイクのミュートの引き下げ。ESP32 がリセット中でもマイクは有効"),
    part("TP1", "Connector:TestPoint", "TXD0", {"1": "ESP_TXD"}, "TestPoint:TestPoint_Pad_D1.0mm", grp="esp",
         note="🔒 UART0 はテストパッドだけ（I2S に使わない・ROM ログを読む最後の経路）"),
    part("TP2", "Connector:TestPoint", "RXD0", {"1": "ESP_RXD"}, "TestPoint:TestPoint_Pad_D1.0mm", grp="esp"),
    part("TP3", "Connector:TestPoint", "IO0", {"1": "ESP_BOOT"}, "TestPoint:TestPoint_Pad_D1.0mm", grp="esp",
         note="GND に当てながら電源を入れるとダウンロードモード"),
    part("TP4", "Connector:TestPoint", "EN", {"1": "ESP_EN"}, "TestPoint:TestPoint_Pad_D1.0mm", grp="esp"),
    # ERC 用の電源の印。フェライトビーズ（FB106・FB107・FB109）と、記号のピンが passive の LDO（U111）の
    #   先は KiCad から「電源が来ていない」に見える（回路の誤りではない）。Q1 の B の警告は v6.1 から同じ
    *[part(f"#FLG{i:02d}", "power:PWR_FLAG", "PWR_FLAG", {"1": n}, grp="flags")
      for i, n in enumerate(["VDD", "VDDIO", "V18", "N_U102_PLL_AVDD"], 5)],
    # XU316 の JTAG はテストパッド（2 列 × 4・2.54mm）。ポゴピンの治具を当てて XTAG4 から最初の 1 回だけ書く。
    #   1 番の V18 は XTAG4 が相手の電圧を知る基準（Voice PE の J5 の 1 番と同じ）。8 番は空き（治具の向きの目印）
    part("J16", "Connector_Generic:Conn_02x04_Odd_Even", "XU316 JTAG",
         {"1": "V18", "2": "TMS", "3": "TCK", "4": "TDI", "5": "TDO", "6": "RST_N", "7": "GND", "8": None},
         "katanori:JTAG_TP_2x4_P2.54mm", grp="xmos", dnp=True,
         note="部品は付けない（パッドだけ）。1 V18・2 TMS・3 TCK・4 TDI・5 TDO・6 RST_N・7 GND・8 空き"),
    part("J15", "Connector_Generic:Conn_01x05", "MIC RISER",
         {"1": "GND", "2": "MIC_CLK_M", "3": "GND", "4": "MIC_DATA_M", "5": "VDD_MIC"},
         "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical", grp="esp",
         note="前のマイクのライザー。PDM のクロックの隣を GND にした"),
]

# ---- JLCPCB（LCSC）の部品番号（2026-09-15 に JLCPCB の部品 API で取った） ----
# 受動部品は ⬜ まだ。fab.py が「番号が無い」で止まるので、書き出す前に埋める
LCSC_V = {
    "U102": ("XU316-1024-QF60B-C32", "C7397517"),   # 🔴 Voice PE の C24 は在庫 0。C32 もここは 12 個 ⇒ DigiKey から持ち込む
    "U103": ("W25Q32JVSSIQ", "C179173"),            # Voice PE は ZB25VQ32DSJG（取り扱いなし）
    "X101": ("24MHz 12pF", "C5265838"),             # Voice PE は Y2400FE001（見つからず）。ESR 45Ω
    "U108": ("TLV320AIC3204IRHBR", "C24109"), "U109": ("TPA6211A1DGNR", "C7718"),
    "U110": ("TPS62827DMQR", "C2071448"), "U112": ("TPS62065DSGR", "C398352"),
    "U111": ("ME6211C18M5G-N", "C236671"), "U118": ("SGM2036S-3.3XXDH4G/TR", "C5152997"),
    "U106": ("SN74LVC125APWR", "C7813"), "Q103": ("LBSS138WT1G", "C383201"), "Q104": ("S9013W", "C2919788"),
    "L101": ("0.47uH", "C97014"), "L102": ("1uH", "C395545"),
    "D106": ("SLESDPSA0402V05", "C7496591"), "D107": ("SLESDPSA0402V05", "C7496591"),
}
for P in MAIN:
    if P["ref"] in LCSC_V:
        P["value"], P["lcsc"] = LCSC_V[P["ref"]]

# ======== 前のマイクのライザー ========
MIC = [vpart(r, "mic") for r in RISER.split()]
for P in MIC:
    if P["ref"] in ("U104", "U105"):
        P["lcsc"] = "C22390138"
    if P["ref"].startswith("D1"):
        P["value"], P["lcsc"] = "SLESDPSA0402V05", "C7496591"
MIC += [
    part("J1", "Connector_Generic:Conn_01x05", "MIC RISER",
         {"1": "GND", "2": "MIC_CLK_M", "3": "GND", "4": "MIC_DATA_M", "5": "VDD_MIC"},
         "Connector_PinSocket_2.54mm:PinSocket_1x05_P2.54mm_Horizontal", grp="mic",
         note="主の板の J15 に挿さる（L 字のメス）"),
    # Voice PE は 100Ω だけでマイクの足元にコンデンサが無い（板の上で近いから）。線を挟むので RC にする
    part("C1", "Device:C_Small", "100nF", {"1": net_name("/XMOS/Net-(U4-L/R)"), "2": "GND"},
         "Capacitor_SMD:C_0402_1005Metric", grp="mic", note="U104 の電源の足元（R210 100Ω と RC）。私が足した"),
    part("C2", "Device:C_Small", "100nF", {"1": net_name("/XMOS/Net-(U5-VDD)"), "2": "GND"},
         "Capacitor_SMD:C_0402_1005Metric", grp="mic", note="U105 の電源の足元（R130 100Ω と RC）。私が足した"),
]


def prune(parts):
    """板の上で 1 か所にしか出てこないネット（写さなかった部品の向こう側）は未接続にする。"""
    count = {}
    for P in parts:
        for n in set(P["nets"].values()):
            if n:
                count[n] = count.get(n, 0) + 1
    lonely = sorted({n for n, k in count.items() if k == 1})
    for P in parts:
        pins_at = {}
        for num, n in P["nets"].items():
            pins_at.setdefault(n, []).append(num)
        for n, nums in pins_at.items():
            if n in lonely and len(nums) == 1:
                P["nets"][nums[0]] = None
    return lonely


def run(name, parts, groups, title, heads, comments, paper):
    gs.NAME = name
    gs.OUT = HERE / name
    gs.ROOT = str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/{name}"))
    gs._n[0] = 0
    gs.PARTS[:] = parts
    gs.GROUPS.clear()
    gs.GROUPS.update(groups)
    gs.SHEET.update(paper=paper, title=title, comments=comments, heads=heads)
    gs.build()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    lonely = prune(MAIN)
    print("未接続にしたネット（写さなかった部品の向こう側）:", " ".join(lonely))
    groups = dict(gs.GROUPS)
    groups.pop("xiao")
    groups.update({"xmos": (15, 300, 400), "codec": (440, 30, 390), "vpower": (440, 250, 390),
                   "esp": (440, 420, 390)})
    lic = "音声部は Home Assistant Voice PE（CERN-OHL-P v2・© Nabu Casa）の写し"
    run("katanori61_voice", MAIN, groups, "katanori 主の板（v6.1 ＋ 音声部）",
        gs.SHEET["heads"][:3] + [
            ("口 — v6.1 の口（SPK IN・XIAO の受けを外し、OLED を 1x07 に）", "ports"),
            ("XU316 — Voice PE の XMOS シートの写し（CERN-OHL-P v2）", "xmos"),
            ("コーデックとアンプ — Voice PE の DAC シートの写し", "codec"),
            ("電源 0.9V・1.8V・3.3V — Voice PE の Power シートの写し", "vpower"),
            ("ESP32-S3-WROOM-1U とその周り", "esp")],
        ["電源は Adafruit PowerBoost 1000C Rev B（CC BY-SA 3.0）の写し", lic,
         "gen_sch_voice.py が生成（docs/VOICE-BOARD.md）"], "A1")
    lonely_mic = prune(MIC)
    run("katanori61_mic", MIC, {"mic": (15, 30, 250)}, "katanori 前のマイクのライザー",
        [("マイク 2 個（71.0mm）— Voice PE の XMOS シートの写し（CERN-OHL-P v2）", "mic")],
        [lic, "gen_sch_voice.py が生成（docs/VOICE-BOARD.md）"], "A4")
