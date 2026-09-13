# -*- coding: utf-8 -*-
"""ハブ＋電源の板の回路図（hub_power.kicad_sch）を作る。

  python gen_sch.py        → hardware/pcb/hub_power/hub_power.kicad_sch と .kicad_pro

回路は 3 つの出どころの写しで、ここで新しく設計した回路は無い。
  電源   : Adafruit PowerBoost 1000C Rev B（hardware/ref/powerboost_1000c/・CC BY-SA 3.0）
  電流計 : 今の INA226 モジュールの役目（シャント 10mΩ・アドレス 0x44）を INA226 のチップで
  ハブ   : hardware/parts/relay_board.html の PARTS / RELAY / BUTTON と hub_ports.py の口

どのピンにも短い線とネット名を付ける形で描く（線で部品どうしを結ばない）。
つながりは check_sch.py が PowerBoost の EAGLE の回路図と突き合わせる。
"""

import json
import math
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "parts"))
import kisym  # noqa: E402
from kisym import Str  # noqa: E402
import hub_ports  # noqa: E402

OUT = pathlib.Path(__file__).parent / "hub_power"
NAME = "hub_power"
ROOT = str(uuid.uuid5(uuid.NAMESPACE_URL, "katanori/hub_power"))
_n = [0]


def uid():
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/hub_power/{_n[0]}"))


G = 2.54
FP_R = "Resistor_SMD:R_0805_2012Metric"
FP_C = "Capacitor_SMD:C_0805_2012Metric"
FP_LED = "LED_SMD:LED_0805_2012Metric"

# ---- 部品 ----
# (ref, lib_id, value, gx, gy, {ピン番号: ネット}, 足形, LCSC, 注記)
# ネット None は「どこにも繋がない」（× を付ける）
# 置き場所は pack() が組（GROUPS）ごとに書いた順で詰める。gx, gy は使っていない（書いた順の目安）
PARTS = []
CUR = ["boost"]
# 組 → (左上 x, 左上 y, 幅) [mm]。A3 横（420 × 297）
GROUPS = {"boost": (15, 30, 190), "charge": (15, 120, 190), "ina": (220, 30, 185),
          "hub": (220, 120, 185), "ports": (15, 240, 250), "flags": (330, 240, 70),
          "knob": (330, 155, 70), "xiao": (220, 190, 185)}


def group(name):
    CUR[0] = name


def part(ref, lib, value, gx, gy, nets, fp="", lcsc="", note="", dnp=False, grp=None):
    PARTS.append(dict(ref=ref, lib=lib, value=value, x=0.0, y=0.0, nets=nets,
                      fp=fp, lcsc=lcsc, note=note, dnp=dnp, grp=grp or CUR[0]))


def r(ref, value, gx, gy, a, b, fp=FP_R, **kw):
    part(ref, "Device:R_Small", value, gx, gy, {"1": a, "2": b}, fp, **kw)


def c(ref, value, gx, gy, a, b, fp=FP_C, **kw):
    part(ref, "Device:C_Small", value, gx, gy, {"1": a, "2": b}, fp, **kw)


def led(ref, value, gx, gy, k, a):
    part(ref, "Device:LED_Small", value, gx, gy, {"1": k, "2": a}, FP_LED)


# ======== 電源: PowerBoost 1000C Rev B の写し ========
# 名前の読み替え（EAGLE → ここ）:
#   ネット  VBAT → VSYS（充電 IC が出す「負荷側」の電圧。電池そのものではない）
#           5.0V → V5（ハブの +5V と同じネット）  ENABLE → EN（ハブの EN と同じネット）
#           VLIPO・VBUS・GND・LBO はそのまま。N$n は役目の名前に付け替え
#   部品    DONE → LED3、CHRG/LBO → LED4、THERM → R15、T1 → Q1、B1 → J10（電池）、CN4 → J9（USB の入口）
# 写さなかった物: CN1（USB-A の出口）・R9〜R12（USB-A の D+/D- の分圧）・X1（端子台）・
#                 JP2（8 本のヘッダ）・FID1〜3・取付穴。どれも 5V を板の外へ出すための物で、
#                 この板では 5V は板の中でハブへ渡る。
X0, Y0 = 10, 12
part("U1", "Regulator_Switching:TPS61090", "TPS61090RSAR", X0 + 30, Y0 + 8,
     {"1": "V5", "15": "V5", "16": "V5", "2": None, "3": "SW", "4": "SW",
      "5": "GND", "6": "GND", "7": "GND", "13": "GND", "17": "GND",
      "8": "VSYS", "9": "LBI", "10": "GND", "11": "EN", "12": "LBO", "14": "FB"},
     "Package_DFN_QFN:Texas_RSA_VQFN-16-1EP_4x4mm_P0.65mm_EP2.7x2.7mm",
     lcsc="C206167", note="昇圧（PowerBoost U1）")
part("U2", "Battery_Management:MCP73871-2CC", "MCP73871-2CCI/ML", X0 + 8, Y0 + 32,
     {"1": "VSYS", "20": "VSYS", "2": "VPCC", "3": "VBUS", "4": "VBUS", "5": "THERM",
      "6": None, "7": "STAT2", "8": "STAT1", "9": "VBUS", "10": "GND", "11": "GND",
      "21": "GND", "12": "PROG3", "13": "PROG1", "14": "VLIPO", "15": "VLIPO",
      "16": "VLIPO", "17": "VBUS", "18": "VBUS", "19": "VBUS"},
     "Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
     lcsc="C5121473", note="充電・ロードシェア（PowerBoost U2）", grp="charge")
part("L1", "Device:L_Small", "6.8uH", X0 + 18, Y0 + 4, {"1": "VSYS", "2": "SW"},
     "Inductor_SMD:L_Changjiang_FNR4018S",
     note="PowerBoost は TDK VLC5045（5×5mm）。JLCPCB の在庫に合わせて FNR4018S6R8MT（4×4mm・2A）にした")
c("C1", "10uF", X0 + 22, Y0 + 4, "VSYS", "GND")
c("C4", "0.1uF", X0 + 25, Y0 + 4, "VSYS", "GND")
c("C2", "2.2uF", X0 + 44, Y0 + 4, "V5", "GND")
# 🔒 2026-09-12 ユーザー: Extended を減らすため 100µF 10V 1210（Extended）を
#    47µF 10V 1206（Basic・C96123）2 個に分けた。耐圧 10V は変えていない。
c("C6", "47uF", X0 + 47, Y0 + 4, "V5", "GND", fp="Capacitor_SMD:C_1206_3216Metric",
  note="PowerBoost C6（100µF 1210）の片割れ")
c("C9", "47uF", X0 + 50, Y0 + 4, "V5", "GND", fp="Capacitor_SMD:C_1206_3216Metric",
  note="PowerBoost C6 の片割れ・私が足した（2026-09-12）")
r("R3", "1.87M", X0 + 44, Y0 + 12, "V5", "FB")
r("R4", "200K", X0 + 47, Y0 + 12, "FB", "GND")
r("R1", "1.87M", X0 + 16, Y0 + 12, "VSYS", "LBI")
r("R2", "330K", X0 + 19, Y0 + 12, "LBI", "GND",
  note="PowerBoost は 340kΩ（E96・Extended）。LBO の閾値 0.5×(1+R1/R2) が 3.25V → 3.33V")
r("R13", "200K", X0 + 22, Y0 + 12, "VSYS", "EN")
# 電池の残りが少ないときの赤: LBO が下がると Q1 が導通して LED1 が点く
part("Q1", "Transistor_BJT:Q_PNP_BRT_BEC", "MMUN2133LT1G", X0 + 52, Y0 + 12,
     {"1": "LBO", "2": "VSYS", "3": "N_Q1C"}, "Package_TO_SOT_SMD:SOT-23",
     note="PowerBoost T1（SC-59）")
r("R20", "1K", X0 + 56, Y0 + 12, "N_Q1C", "N_LED1")
led("LED1", "RED", X0 + 59, Y0 + 12, "GND", "N_LED1")
# 5V が出ている印の青
r("R5", "1K", X0 + 52, Y0 + 4, "V5", "N_LED2")
led("LED2", "WHITE", X0 + 55, Y0 + 4, "GND", "N_LED2")
# 充電側
group("charge")
c("C8", "10uF", X0 + 26, Y0 + 26, "VBUS", "GND")
c("C7", "10uF", X0 + 29, Y0 + 26, "VLIPO", "GND")
r("R6", "220K", X0 + 32, Y0 + 26, "VBUS", "VPCC",
  note="PowerBoost は 270kΩ（E96・Extended）。R7 と組で比を保つ")
r("R7", "82K", X0 + 35, Y0 + 26, "VPCC", "GND",
  note="PowerBoost は 100kΩ。R6 と組で 100/370=0.2703 → 82/302=0.2715（差 0.45%）")
r("R16", "1.0K", X0 + 26, Y0 + 34, "GND", "PROG1")
r("R17", "100K", X0 + 29, Y0 + 34, "GND", "PROG3")
r("R15", "15K", X0 + 32, Y0 + 34, "GND", "THERM", note="PowerBoost THERM")
led("LED3", "GREEN", X0 + 38, Y0 + 30, "N_LED3", "VBUS")   # 充電が済んだ（PowerBoost DONE）
r("R14", "1K", X0 + 41, Y0 + 30, "N_LED3", "STAT2")
led("LED4", "YELLOW", X0 + 38, Y0 + 36, "N_LED4", "VBUS")  # 充電中（PowerBoost CHRG）
r("R8", "1K", X0 + 41, Y0 + 36, "N_LED4", "STAT1")

# ======== 電流計: INA226 ========
# 今のモジュールと同じく、電池の + と充電 IC の VBAT のあいだに 10mΩ を入れる。
# A1 = VS・A0 = GND でアドレス 0x44（今の実機と同じ・ファームを変えずに済む）。
XI, YI = 82, 12
group("ina")
part("U3", "Sensor_Energy:INA226", "INA226AIDGSR", XI, YI + 8,
     {"1": "V33", "2": "GND", "3": None, "4": "SDA", "5": "SCL", "6": "V33",
      "7": "GND", "8": "VLIPO", "9": "VLIPO", "10": "BATP"},
     "Package_SO:TSSOP-10_3x3mm_P0.5mm", lcsc="C49851", note="A1=VS・A0=GND → 0x44")
r("R41", "10m", XI - 12, YI + 8, "BATP", "VLIPO", fp="Resistor_SMD:R_1206_3216Metric",
  note="シャント 10mΩ（今のモジュールと同じ値）")
c("C41", "0.1uF", XI + 8, YI + 1, "V33", "GND")
r("R42", "10K", XI + 12, YI + 1, "V33", "SDA", note="I2C の引き上げ")
r("R43", "10K", XI + 15, YI + 1, "V33", "SCL", note="I2C の引き上げ")
part("J10", "Connector_Generic:Conn_01x02", "BAT (JST-PH)", XI - 20, YI + 8,
     {"1": "GND", "2": "BATP"}, "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
     note="🔴 1 番が −・2 番が +（PowerBoost B1 の並び）")
# 🔒 2026-09-12 ユーザー「2 だね」: 充電の USB-C の受け口を電源板に載せる（秋月の Type-C 基板と
#    線 2 本と手付けの CC 抵抗が消える）。JLCPCB は SMT の流れで付ける（Assembly Type: SMT Assembly）。
#    ⚠ 板の縁を壁へ持っていくのは筐体 v6 側の仕事。
part("J13", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", XI - 20, YI + 18,
     {"A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
      "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
      "A5": "CC1", "B5": "CC2",
      "A6": None, "B6": None, "A7": None, "B7": None, "A8": None, "B8": None},
     "katanori:USB_C_HRO_TYPE-C-31-M-12_NoFrontLegs", lcsc="C165948",
     note="充電の口。D+/D− と SBU は使わない")
r("R44", "5.1k", XI - 16, YI + 22, "CC1", "GND", note="CC1 の引き下げ（充電器に 5V を出させる）")
r("R45", "5.1k", XI - 13, YI + 22, "CC2", "GND", note="CC2 の引き下げ")

# ======== ハブ: relay_board.html の写し ========
XH, YH = 10, 62
group("hub")
# ミュートリレー（POWER.md 3 章）。部品番号は板の上の id に 30 を足した
r("R31", "1k", XH + 4, YH + 4, "IN", "BASE", note="relay_board R1")
r("R32", "10k", XH + 8, YH + 4, "BASE", "GND", note="relay_board R2・🔴 安全の要")
# 🔴 2026-09-12 ユーザー「トランジスタとダイオードは付けてよ」: 実装に載せるため表面実装へ。
#    SS8050 は hFE 200〜350（2SC1815-GR は 200〜400）・Ic 1.5A で、コイルの 30mA に対しては
#    2SC1815 と同じく深く飽和する。ベース 1kΩ・プルダウン 10kΩ・つなぎ方は変えていない。
part("Q31", "Transistor_BJT:MMBT3904", "SS8050", XH + 13, YH + 4,
     {"1": "BASE", "2": "GND", "3": "COL"}, "Package_TO_SOT_SMD:SOT-23",
     note="relay_board Q1（2SC1815-GR の表面実装の代わり・SOT-23 は 1=B・2=E・3=C）")
part("D31", "Diode:1N4148W", "1N4148W", XH + 20, YH + 4, {"1": "V5", "2": "COL"},
     "Diode_SMD:D_SOD-123", note="relay_board D1・カソードが +5V（表面実装の 1N4148W）")
# 🔒 2026-09-12 ユーザー「リレーに準じる物であればなんでもいい」: スルーホールの Y14H-1C-5DS から
#    表面実装の Omron G6S-2F DC5（C16707）へ。スルーホールだったのは手元の実物がそうだったからで、
#    理由は無かった。替えると機械が載せるので手はんだが消え、足形も KiCad の標準（Omron が引いた
#    land pattern）になる。コイルは 167Ω 30mA → 178Ω 28mA。接点は 2A@30VDC。
#    ピン番号は Omron のデータシート（en-g6s.pdf 5 ページ・Top View）と KiCad の記号の両方で確かめた:
#      1 = コイル ＋ ／ 12 = コイル −／ 4 = COM・3 = NC・5 = NO（もう 1 回路は 9 = COM・10 = NC・8 = NO）
part("K31", "Relay:G6S-2", "G6S-2F DC5", XH + 28, YH + 4,
     {"1": "V5", "12": "COL", "4": "SPKP", "5": "SPKO", "3": None,
      "9": None, "10": None, "8": None},
     "Relay_SMD:Relay_DPDT_Omron_G6S-2F",
     note="COM–NO を使う・NC は空き。2 回路のうち使うのは 1 回路だけ（もう 1 回路は未接続）")
c("C31", "0.1uF", XH + 36, YH + 4, "V5", "GND", note="relay_board C1")
c("C32", "0.1uF", XH + 40, YH + 4, "EN", "GND", note="relay_board C2・リードの跳ね止め")
# 🔒 2026-09-12 ユーザー「要らないね」: 板の上の直挿しの会話ボタン（relay_board の BUTTON）は載せない。
#    会話ボタンは天板のもの 1 つだけになり、口 J8（BTN2）で受ける。

# ======== つまみ: AS5600 をチップで載せる（2026-09-13） ========
# 🔒 ユーザー 2026-09-13「歯車 3 枚」。読み取りの芯が板 X 36.2・Y 7 に決まり、AS5600 は
#    外付けモジュール（口 J3）ではなく板の上のチップになった。線 4 本が消える。
# 📄 3.3V 動作の回路は AS5600 データシート 9 ページ Figure 13（hardware/ref/as5600/AS5600_v1-01.pdf）:
#    「In 3.3V operation, the VDD5V and VDD3V3 pins must be tied together.」＋ 100nF を GND へ。
#    1µF は 5V 動作の LDO 用・10µF は OTP を焼くときだけなので、どちらも要らない。
# 結線はいまのモジュールの使い方と同じ（docs/KNOB-ENCODER.md 配線章）:
#    VDD=3V3 ／ DIR=GND（時計回りで値が増える）／ SCL・SDA ／ OUT は繋がない
#    🔴 PGO には何も繋がない（OTP・焼くと戻せない）
XA, YA = 82, 62
group("knob")
part("U4", "katanori:AS5600-ASOM", "AS5600-ASOM", XA, YA,
     {"1": "V33", "2": "V33", "4": "GND", "8": "GND",
      "6": "SDA", "7": "SCL", "3": None, "5": None},
     "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", lcsc="C79815",
     note="つまみの角度。磁石は真上・板 X 36.2 Y 7。🔴 PGO(5) と OUT(3) は繋がない")
c("C42", "0.1uF", XA + 12, YA + 8, "V33", "GND", note="AS5600 のパスコン（📄 9 ページ Figure 13）")

# ======== マスタートグル: 板に実装するスライドスイッチ（2026-09-13） ========
# 🔒 筐体側 2026-09-13。口 J7（トグルへ 2 本）が消えて板の上の部品になる。
#    SHOU HAN MST-12D18G3（C49023766）・9.1 × 3.5 × 6.5・SMD の横出し・板 X 21.95〜31.05 の上の縁。
#    1 回路 2 接点のうち片側だけ使う（もう片方は未接続）。リードスイッチと並列で EN⇔GND。
#    ⚠ この部品の JLCPCB の区分（Basic か Extended か）は未確認（2026-09-13）。
part("SW1", "Switch:SW_SPDT", "MST-12D18G3", XA, YA + 20,
     {"2": "EN", "1": "GND", "3": None}, "katanori:SW_Slide_MST-12D18G3",
     lcsc="C49023766", note="マスタートグル。2=COM を EN へ・1 を GND へ・3 は空き", grp="hub")

# 口（hub_ports.py の並びのまま = 今の線がそのまま挿さる）
# 🔒 2026-09-13 で口は 7 つになった: XIAO・OLED・スピーカー IN・スピーカー OUT・リード・
#    会話ボタン・電池。AS5600（J3）とトグル（J7）は板の上の部品になって消えた。
# 🔒 2026-09-12 ユーザー: OLED を HS154L03W2C01（1.54"・SSD1309・I2C・`C7465999`）に替える前提で、
#    **J2 だけピンの並びを逆にする**。穴の位置は動かさない（同じ 4 穴のまま、載る信号が逆順になる）。
#      いまのユニバーサル基板の J2 : 1 SDA・2 SCL・3 3V3・4 GND
#      HS154L03W2C01 のパネル      : 1 GND・2 VCC・3 SCL・4 SDA（📄 データシート 1.5 Pin Definition）
#    ⇒ 逆にすると 1 GND・2 3V3・3 SCL・4 SDA で、パネルの並びと 1 対 1 で合う。
#    🔒 2026-09-13 に口そのものを JST PH の 4 ピン横型へ替えたが、**この並びは維持する**。
PORT_FLIP = {"OLED"}
NETMAP = {"V5": "V5", "V33": "V33", "GND": "GND", "SDA": "SDA", "SCL": "SCL", "EN": "EN",
          "BTN": "BTN", "IN": "IN", "SPKP": "SPKP", "SPKM": "SPKM", "SPKO": "SPKO"}
# 🔒 2026-09-13 ユーザー「別に線が二股になるのは構わない」: リード（REED）と会話ボタン（BTN2）は
#    hub_ports から引かず、下で 1 つの 4 ピン PH（J6）にまとめる
PORT_REF = {"OLED": "J2", "PHIN": "J4", "PHOUT": "J5"}
PORT_NAME = {"OLED": "OLED", "PHIN": "SPK IN", "PHOUT": "SPK OUT"}
# 🔒 2026-09-13 筐体側: 口は全部「線が板の面と平行に抜ける」形にする（外向きだと壁に当たる）。
#    2 本の口は 2.54 の L 字ソケット・スピーカーと電池と OLED は JST PH の横型。
FP_PORT = {
    "OLED": "Connector_JST:JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal",
    "PHIN": "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
    "PHOUT": "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
}
group("ports")
gx = XH + 4
for p in hub_ports.ports():
    if p.id not in PORT_REF:      # PWR・INA・XIAO・AS5600・TOGGLE は板の中の配線か別の部品になった
        continue
    pins = list(reversed(p.pins)) if p.id in PORT_FLIP else p.pins
    nets = {str(i): (NETMAP[net] if net else None) for i, (h, fn, net, x, y) in enumerate(pins, 1)}
    n = len(p.pins)
    part(PORT_REF[p.id], f"Connector_Generic:Conn_01x{n:02d}", PORT_NAME[p.id], gx, YH + 24, nets,
         FP_PORT[p.id], note=p.label)
    gx += 12

# ======== リードと会話ボタンを 1 つの口にまとめる（🔒 ユーザー 2026-09-13）========
# 口 6 つに対して、プラグの通り道まで取れる場所が板に 5 か所しか無かった（gen_pcb.py の CONN）。
# ユーザー「別に線が二股になるのは構わないと思います」。
# 🔴 3 ピン（EN・BTN・GND）ではなく **4 ピン**にする。GND を 2 本にすれば、1 つの端子へ線を
#    2 本入れる（圧着できない）ことも、線を割って継ぐこともせずに済む。
#    並びは **隣り合う 2 本ずつで分かれる**ように: 1 EN・2 GND がリードへ、3 GND・4 BTN が会話ボタンへ。
#    どちらも無極性のスイッチなので、組の中での順は効かない。
part("J6", "Connector_Generic:Conn_01x04", "REED+BTN2", 0, 0,
     {"1": "EN", "2": "GND", "3": "GND", "4": "BTN"},
     "Connector_JST:JST_PH_S4B-PH-K_1x04_P2.00mm_Horizontal",
     note="1 EN・2 GND → リード ／ 3 GND・4 BTN → 会話ボタン（線は口の所で二股）", grp="ports")

# ======== XIAO の口 — 2 列 14 本の直挿し（2026-09-13） ========
# 🔒 筐体側 2026-09-13。ReSpeaker の上に立っている 2×7 のピンヘッダ（XIAO 面から 10 出る）が、
#    この板のメスソケット 2 本へ真上から挿さる。線が 7 本消える。
# 🔴 **どちらの列がどちらか**は鏡像事故の温床なので、出どころを 3 つ揃えてから書いた:
#    ① 筐体側の 3 次元の変換（回転だけ・利き手は変わらない）で 📄 パッド「下から 9.397 と 24.627」が
#       板の X 9.40 と 24.63 に写る。下の列（9.397）が D0〜D6 側
#    ② XIAO の標準の上面図は「USB を上」で左列が D0…D6。ここでは USB-C が ReSpeaker の左を向くので
#       上面図を反時計 90° 回した形になり、左列（D0〜D6）が下へ来る
#    ③ docs/RESPEAKER-LITE.md 3 章: 外部パッド1 `Mute D3 D2 Usr ⏚ 3V3` が **下辺**・
#       外部電源パッド（GND・5V）が **上の長辺**。①② と同じ割り当てになる
# 🔴 板の +Z の面（部品が生える面・ReSpeaker を向いている面）から見た座標である。
#    KiCad の表面がこの面なので、そのまま入れて合う。
XX, YX = 15, 200
group("xiao")
# 列 X 9.40（D0〜D6 側）／ 列 X 24.63（5V・GND・3V3・D10〜D7 側）。どちらも 1 本目が Y 2.90 側
XIAO_ROWS = [
    ("J1", "XIAO D0-D6", 9.40,
     [(None, "D0"), (None, "D1"), ("BTN", "D2"), ("IN", "D3"),
      ("SDA", "D4"), ("SCL", "D5"), (None, "D6")]),
    ("J14", "XIAO PWR", 24.63,
     [("V5", "5V"), ("GND", "GND"), ("V33", "3V3"), (None, "D10"),
      (None, "D9"), (None, "D8"), (None, "D7")]),
]
for ref, nm, col_x, rows in XIAO_ROWS:
    part(ref, "Connector_Generic:Conn_01x07", nm, XX, YX,
         {str(i): net for i, (net, _) in enumerate(rows, 1)},
         "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical",
         note=f"列 X {col_x}・1 本目が Y 2.90 側: " + " / ".join(lbl for _, lbl in rows))
    XX += 60

# ---- JLCPCB（LCSC）の部品番号（2026-09-12 に JLCPCB の部品検索で取った） ----
# 「基」= Basic（種類ごとの取り付け料 $0 ）・「拡」= Extended（種類ごとに $3.07）
LCSC = {
    "U1": "C206167", "U2": "C5121473", "U3": "C49851",          # 拡: 昇圧・充電・電流計
    "Q1": "C21714196",                                          # 拡: MMUN2133（SOT-23）
    "L1": "C167807",                                            # 拡: FNR4018S6R8MT 6.8µH 2A（4×4mm）
    "R41": "C105362",                                           # 拡: 10mΩ 1% 1W 合金 1206
    "R1": "C482988", "R3": "C482988",                           # 拡: 1.87MΩ 1%
    "R4": "C17539", "R13": "C17539",                            # 基: 200kΩ
    "R17": "C149504",                                           # 基: 100kΩ
    "R2": "C23137",                                             # 基: 330kΩ 0603（元は 340kΩ C17636・Extended）
    "R6": "C22961",                                             # 基: 220kΩ 0603（元は 270kΩ C17589・Extended）
    "R7": "C23254",                                             # 基: 82kΩ 0603（元は 100kΩ。R6 と比を保つため）
    "C6": "C96123", "C9": "C96123",                             # 基: 47µF 10V 1206（元は 100µF 1210 C23742・Extended）
    "R15": "C17475",                                            # 基: 15kΩ
    "R32": "C17414", "R42": "C17414", "R43": "C17414",          # 基: 10kΩ
    "R5": "C17513", "R8": "C17513", "R14": "C17513",
    "R16": "C17513", "R20": "C17513", "R31": "C17513",          # 基: 1kΩ
    "C1": "C15850", "C7": "C15850", "C8": "C15850",             # 基: 10µF 25V
    "C4": "C49678", "C41": "C49678", "C31": "C49678", "C32": "C49678",   # 基: 0.1µF 50V
    "C2": "C377773",                                            # 基: 2.2µF 50V
    "LED1": "C84256", "LED2": "C34499", "LED3": "C2297", "LED4": "C2296",
    "Q31": "C2150", "D31": "C81598", "R44": "C27834", "R45": "C27834",                            # 基: SS8050（SOT-23）・1N4148W（SOD-123）
    "K31": "C16707",                                            # 拡: Omron G6S-2F DC5（表面実装のリレー）
    "U4": "C79815",                                             # 拡: AS5600-ASOM（SOIC-8・つまみの角度）
    "SW1": "C49023766",                                         # ⬜ 区分未確認: MST-12D18G3（横出しのスライドスイッチ）
}
# 🔴 LED の色は私が替えた（2026-09-12）。PowerBoost は 青（電源）と 橙（充電中）だが、
#    JLCPCB の無料枠に 0805 の青と橙が無く、拡張枠のものは在庫 0 だった。
#    ⇒ 青 → 白（C34499）、橙 → 黄（C2296）。色を戻すなら種類ごとに $3.07 と在庫待ちが要る。
for P in PARTS:
    if P["ref"] in LCSC:
        P["lcsc"] = LCSC[P["ref"]]

# 🔒 2026-09-13 ユーザー: 電源基板を中継基板へ統合して **板は 1 枚**になった。
# 板をまたぐ口（J11 ↔ J12・7 本）とミシン目のタブは消え、板ごとにネット名を変える処理
# （V5P・GNDP・V33P …）も要らなくなった。USB-C の周りに残っていた GNDP も GND に戻す。

# ERC 用の電源の印（コネクタから入ってくる電源）
group("flags")
for i, net in enumerate(["GND", "VBUS", "V33", "BATP"]):
    part(f"#FLG0{i + 1}", "power:PWR_FLAG", "PWR_FLAG", 120 + i * 6, 10, {"1": net})


# ---- 書き出し ----
def prop(name, val, x, y, hide=False, just=None, ang=0):
    eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
    if just:
        eff.append(["justify", just])
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Str(name), Str(val), ["at", f"{x:.2f}", f"{y:.2f}", str(ang)], eff]


def label(net, x, y, ang):
    just = {0: ["left", "bottom"], 90: ["left", "bottom"], 180: ["right", "bottom"], 270: ["right", "bottom"]}[ang]
    return ["label", Str(net), ["at", f"{x:.2f}", f"{y:.2f}", str(ang)],
            ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", *just]], ["uuid", Str(uid())]]


def wire(x1, y1, x2, y2):
    return ["wire", ["pts", ["xy", f"{x1:.2f}", f"{y1:.2f}"], ["xy", f"{x2:.2f}", f"{y2:.2f}"]],
            ["stroke", ["width", "0"], ["type", "default"]], ["uuid", Str(uid())]]


def text_pos(P):
    """部品番号と値を置く場所。ネット名の文字と重ならない側に逃がす。
    戻り値: ((ref の x, y, 寄せ), (値の x, y, 寄せ))"""
    pins = kisym.pins(P["lib"])
    X, Y = P["x"], P["y"]
    angs = {int(a) % 360 for (_, _, _, a, _) in pins.values()}
    pxs = [px for (_, px, _, _, _) in pins.values()]
    pys = [py for (_, _, py, _, _) in pins.values()]
    if 180 not in angs:           # 右へ出るネット名が無い（縦の R・C・L・コネクタ・トランジスタ・リレー）: 右に並べる
        x = X + max(0.0, max(pxs)) + (1.8 if len(pins) == 2 and angs <= {90, 270} else 3.0)
        return (x, Y - 0.6, "left"), (x, Y + 1.6, "left")
    if not angs & {90, 270}:      # 上下へ出るネット名が無い（横の LED・ダイオード・スイッチ）: 上下
        return (X, Y - max(pys) - 2.2, None), (X, Y - min(pys) + 3.2, None)

    def lab(sel):
        return max([G + 1.0 + 1.0 * len(P["nets"][n] or "") for n, (_, _, _, a, _) in pins.items()
                    if int(a) % 360 == sel] or [0.0])
    top = Y - max(pys) - lab(270) - 2.0
    bot = Y - min(pys) + lab(90) + 3.0
    return (X, top, None), (X, bot, None)


def extents(P):
    """部品の占める箱（ピン・短い線・ネット名の文字まで）。回路図の座標で (x0, y0, x1, y1)。"""
    pins = kisym.pins(P["lib"])
    X, Y = P["x"], P["y"]
    xs, ys = [], []
    for num, (nm, px, py, ang, typ) in pins.items():
        sx, sy = X + px, Y - py
        xs.append(sx)
        ys.append(sy)
        net = P["nets"][num] or ""
        L = G + 1.0 + 1.0 * len(net)
        dx, dy = {0: (-L, 0), 180: (L, 0), 90: (0, L), 270: (0, -L)}[int(ang) % 360]
        xs.append(sx + dx)
        ys.append(sy + dy)
    for (tx, ty, just), s in zip(text_pos(P), (P["ref"], P["value"])):
        w = 1.1 * len(s)
        xs += [tx, tx + w] if just == "left" else [tx - w / 2, tx + w / 2]
        ys += [ty - 1.3, ty + 0.6]
    return min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5


def check_layout():
    """部品の箱が重なっていないか。重なると別のネットがつながる（2026-09-12 に GND と VSYS がつながった）。"""
    bad = []
    boxes = [(P["ref"], extents(P)) for P in PARTS]
    for i, (ra, a) in enumerate(boxes):
        for rb, b in boxes[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                bad.append((ra, rb))
    return bad


def pack():
    """組ごとに、書いた順で左から右へ詰め、幅を超えたら次の段へ送る。原点はグリッドに乗せる。"""
    for gname, (gx0, gy0, gw) in GROUPS.items():
        cx, cy, rowh = gx0, gy0, 0.0
        for P in [P for P in PARTS if P["grp"] == gname]:
            P["x"] = P["y"] = 0.0
            x0, y0, x1, y1 = extents(P)
            w, h = x1 - x0, y1 - y0
            if cx + w > gx0 + gw and cx > gx0:
                cx, cy, rowh = gx0, cy + rowh + G, 0.0
            P["x"] = math.ceil((cx - x0) / G) * G
            P["y"] = math.ceil((cy - y0) / G) * G
            bx0, by0, bx1, by1 = extents(P)
            cx = bx1 + G
            rowh = max(rowh, by1 - cy)
    xs = [extents(P) for P in PARTS]
    print("図の範囲 x %.0f〜%.0f / y %.0f〜%.0f mm（A3 は 420 × 297）"
          % (min(b[0] for b in xs), max(b[2] for b in xs), min(b[1] for b in xs), max(b[3] for b in xs)))


def build():
    pack()
    bad = check_layout()
    if bad:
        for ra, rb in bad:
            print("重なり:", ra, rb, [round(v, 1) for v in extents(next(P for P in PARTS if P["ref"] == ra))],
                  [round(v, 1) for v in extents(next(P for P in PARTS if P["ref"] == rb))])
        sys.exit(f"部品の箱が {len(bad)} 組重なっている。置き場所を直す")
    libs = {}
    items = []
    for P in PARTS:
        libs.setdefault(P["lib"], kisym.symbol(P["lib"]))
        pins = kisym.pins(P["lib"])
        missing = set(pins) - set(P["nets"])
        extra = set(P["nets"]) - set(pins)
        assert not missing and not extra, (P["ref"], "ピンの割り当て漏れ", sorted(missing), sorted(extra))
        X, Y = P["x"], P["y"]
        ys = [py for (_, _, py, _, _) in pins.values()]
        top, bot = Y - max(ys), Y - min(ys)
        two = len(pins) == 2 and P["lib"].startswith("Device:")
        is_flag = P["ref"].startswith("#")
        sym = ["symbol", ["lib_id", Str(P["lib"])], ["at", f"{X:.2f}", f"{Y:.2f}", "0"], ["unit", "1"],
               ["exclude_from_sim", "no"], ["in_bom", "no" if is_flag else "yes"],
               ["on_board", "no" if is_flag else "yes"], ["dnp", "yes" if P["dnp"] else "no"],
               ["uuid", Str(uid())]]
        (rx, ry, rj), (vx, vy, vj) = text_pos(P)
        sym.append(prop("Reference", P["ref"], rx, ry, hide=is_flag, just=rj))
        sym.append(prop("Value", P["value"], vx, vy, hide=is_flag, just=vj))
        sym.append(prop("Footprint", P["fp"], X, Y, hide=True))
        sym.append(prop("Datasheet", "", X, Y, hide=True))
        if P["lcsc"]:
            sym.append(prop("LCSC", P["lcsc"], X, Y, hide=True))
        if P["note"]:
            sym.append(prop("Note", P["note"], X, Y, hide=True))
        for num in pins:
            sym.append(["pin", Str(num), ["uuid", Str(uid())]])
        sym.append(["instances", ["project", Str(NAME), ["path", Str("/" + ROOT),
                                                       ["reference", Str(P["ref"])], ["unit", "1"]]]])
        items.append(sym)
        # ピンごとに短い線とネット名（同じ位置に重なるピンは 1 回だけ）
        done = set()
        for num, (nm, px, py, ang, typ) in pins.items():
            sx, sy = round(X + px, 2), round(Y - py, 2)
            if (sx, sy) in done:
                continue
            done.add((sx, sy))
            net = P["nets"][num]
            if net is None:
                items.append(["no_connect", ["at", f"{sx:.2f}", f"{sy:.2f}"], ["uuid", Str(uid())]])
                continue
            if is_flag:
                items.append(label(net, sx, sy, 0))
                continue
            dx, dy, la = {0: (-G, 0, 180), 180: (G, 0, 0), 90: (0, G, 270), 270: (0, -G, 90)}[int(ang) % 360]
            items.append(wire(sx, sy, sx + dx, sy + dy))
            items.append(label(net, sx + dx, sy + dy, la))

    heads = [("昇圧 — Adafruit PowerBoost 1000C Rev B の写し（CC BY-SA 3.0・Limor Fried / Adafruit）", "boost"),
             ("充電 — 同じく PowerBoost 1000C Rev B の写し", "charge"),
             ("電流計 — INA226（シャント 10mΩ・0x44）・電池と USB の口", "ina"),
             ("ハブ — relay_board.html のミュートリレー・会話ボタン", "hub"),
             ("口 — hub_ports.py の並びのまま（今の線がそのまま挿さる）", "ports")]
    for t, gname in heads:
        gxx, gyy, _ = GROUPS[gname]
        items.append(["text", Str(t), ["exclude_from_sim", "no"], ["at", f"{gxx:.2f}", f"{gyy - 3:.2f}", "0"],
                      ["effects", ["font", ["size", "2", "2"], ["bold", "yes"]], ["justify", "left", "bottom"]],
                      ["uuid", Str(uid())]])

    doc = ["kicad_sch", ["version", "20250114"], ["generator", Str("eeschema")],
           ["generator_version", Str("9.0")], ["uuid", Str(ROOT)], ["paper", Str("A3")],
           ["title_block", ["title", Str("katanori ハブ＋電源")], ["rev", Str("0.1")],
            ["comment", "1", Str("電源は Adafruit PowerBoost 1000C Rev B（CC BY-SA 3.0）の写し")],
            ["comment", "2", Str("ハブは hardware/parts/relay_board.html の写し・gen_sch.py が生成")]],
           ["lib_symbols", *libs.values()], *items,
           ["sheet_instances", ["path", Str("/"), ["page", Str("1")]]], ["embedded_fonts", "no"]]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NAME}.kicad_sch").write_text(kisym.dump(doc) + "\n", encoding="utf-8")
    pro = OUT / f"{NAME}.kicad_pro"
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": f"{NAME}.kicad_pro", "version": 1}}, indent=2),
                       encoding="utf-8")
    print(f"{len(PARTS)} 部品 → {OUT / (NAME + '.kicad_sch')}")


if __name__ == "__main__":
    build()
