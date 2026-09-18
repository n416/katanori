# -*- coding: utf-8 -*-
"""音声の板（ReSpeaker Lite の場所・82.024 × 34.007・4 層・両面に部品）に部品を置き、電源と GND を先に引いて、
.kicad_pcb と DSN を書く。

  python gen_sch_voice.py && python check_sch_voice.py   → 回路図（katanori61_audio/）
  python gen_pcb_audio.py                                 → katanori61_audio/katanori61_audio.kicad_pcb と .dsn
  python gen_pcb_audio.py --route                         → Freerouting（信号だけ）→ 取り込み → GND の縫い → DRC
  python gen_pcb_audio.py --route --keep                  → 🔴 今の板の自動配線（locked でない線と穴）を残したまま、
                                                            手の線（hand_wiring・flash_wiring・jtag_wiring）を作り直して DRC。
                                                            2026-09-16 以降の板はこれで作る（Freerouting は回さない。
                                                            自動配線は 7 回とも XU316 の周りで同じ所を残したので、
                                                            残りは全部手で引いた。DROP のネットは古い線を捨てて手で引く）

座標（docs/VOICE-BOARD.md 11 章）: **ReSpeaker Lite と同じ「XIAO 面から見て 左から x ／ 下から b」**。
  KiCad の上から見た面（F.Cu）＝ XIAO 面（後ろ・背の高い物）、B.Cu ＝ マイク面（前・低い物だけ）。
  図面の座標へは gen_pcb.bx(x, b)（Y を反転）。筐体の世界座標は X ＝ 2.000 + x、Z ＝ 41.507 − b
  （⇒ b の小さい辺が天井側、大きい辺が床とハブの側）。

🔴 2026-09-15 の 1 回目（Voice PE の並びを区画へ縮めて空きへ詰め、GND も電源も自動配線に渡した）は、
   パス 2 で未接続 40 本が残った。原因は 3 つ:
   1. **GND（108 ピン）を 4 層とも「信号層」のまま自動配線に線で引かせていた**。渡した 536 ピンの 2 割が GND で、
      画面の線の大半が GND と電源だった。
   2. Voice PE の並びを 0.45 倍に縮めたので、XU316 の周りの部品の隙間が 0.25〜0.65 で、線 0.2＋隙間 0.15 × 2 が通らない。
   3. 区画が部品の流れを無視していた（Flash が XU316 から 15mm、0.9V/1.8V のレギュレータが 35〜45mm。
      芯の電源を 0.2 の線で 40mm 引く形＝細く長い電源線）。
   ⇒ この版の方針:
   ・GND と GNDA は自動配線に渡さない。In1 を GND の面（自動配線に見せない）、F/B にも GND ベタ、GND のパッドの
     そばには生成時に貫通穴を打つ。GNDA はコーデック・アンプの下だけの島（Voice PE と同じ・F と In1）。
   ・電源（V5・V33・V18・V09・VDD・VDDIO・V33A・PA_5V）は生成時に太い線（0.4〜0.6）で引いて固定（DSN では protect）。
   ・置き方は手で決める。Voice PE の固まり（XU316 と真裏のパスコン・水晶・PLL・各レギュレータ・コーデックとアンプ）は
     1.0 倍のまま鏡に写し、Flash と JTAG は XU316 の隣、0.9V/1.8V は XU316 のそば、コーデック・アンプはスピーカーの口の隣、
     3.3V の電源は V5 の入口（J21 の 1 番）の近くでマイクとコーデックから離す。

面の割り当て: Voice PE の板を**裏から見た鏡像**で写す（X を鏡、向きは 180 − a、層は F↔B・In1↔In2）。
  Voice PE の裏（XU316・コーデック・電源）→ この板の F.Cu（XIAO 面）
  Voice PE の表（マイク・XU316 の真裏のパスコン）→ この板の B.Cu（マイク面）
"""

import json
import subprocess
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_pcb as G  # noqa: E402
import gen_sch_voice as GV  # noqa: E402
import kisym  # noqa: E402
import voicepe  # noqa: E402
import dsn  # noqa: E402
from kisym import Str, find, find1  # noqa: E402

NAME = "katanori61_audio"
G.OUT = HERE / NAME
G.NAME = NAME
COPPER = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
ROUTE_COPPER = ["F.Cu", "In2.Cu", "B.Cu"]      # 自動配線に見せる層（In1 は GND の面なので見せない）

# ======== 板の形（ReSpeaker Lite の公式 CAD・docs/RESPEAKER-LITE.md 5.6） ========
G.BOARD_L, G.BOARD_W = 82.024, 34.007
CORNER_R = 1.27
G.NOTCHES = [(0.0, 0.0, G.BOARD_W + 1), (G.BOARD_L, G.BOARD_L, G.BOARD_W + 1)]   # 欠きは無い（幅 0 の欠き）
G.BOARD_CR = 0.0   # 2026-09-18: 角の丸めはハブの板（katanori61）だけ。音声の板は角の立った長方形のまま
G.MOUNT = []     # 🔒 ユーザー 2026-09-16「XIAO の固定穴位置まで揃えなくてもいい」: 筐体 v6.1 にダボは無い。ReSpeaker Lite の穴は写さない
G.MOUNT_D = 2.20
G.POSTS = []
HOLE_KEEP_R = 2.1                                  # 穴の周りに部品を置かない半径（M2 のねじの頭 φ3.8 の半分 ＋ 0.2）

# ======== 規則（docs/VOICE-BOARD.md 10 章） ========
# ⚠ パッドどうしは足形そのものが狭い（XU316 0.146・U118 0.123）ので、ネットクラスは 0.12、線・穴・ベタは kicad_dru で 0.15
TRACK, CLEAR, VIA = 0.2, 0.15, (0.45, 0.2)
PAD_PAD_MIN = 0.12
EDGE = 0.4           # 板の縁から部品の枠まで

_load = G.load_fp


def load_fp(fp_id):
    lib, name = fp_id.split(":", 1)
    if lib == "voicepe":
        return kisym.parse((voicepe.PRETTY / f"{name}.kicad_mod").read_text(encoding="utf-8"))[0]
    return _load(fp_id)


G.load_fp = load_fp

# ======== 筐体が決める物（docs/VOICE-BOARD.md 11 章） ========
MIC_AT = {"U104": (5.487, 17.002), "U105": (76.487, 17.002)}   # ReSpeaker Lite の U4・U5 の中心（前板の穴がここを向く）
RISER_B = {"J21": 24.627, "J22": 9.397}                        # XIAO のピンの 2 列（1 番は x 2.932）
RISER_X0 = 2.932
SPK_BOX = (73.94, 0.6, 80.94, 8.55)                            # 右下の角（裏のマイク U105 の足と重ならない所。上から挿す）


def keepouts():
    """[(x0, b0, x1, b1, 面, 入ってよい部品)]。面は "F"（XIAO 面）か "B"（マイク面）。"""
    L, W = G.BOARD_L, G.BOARD_W
    k = []
    for mx, my in G.MOUNT:
        k += [(mx - HOLE_KEEP_R, my - HOLE_KEEP_R, mx + HOLE_KEEP_R, my + HOLE_KEEP_R, s, None) for s in "FB"]
    # XIAO 面: 左右の壁のリブ・ハブの板の前の縁（背 2.9 まで ⇒ 背の高い物を入れない）
    k += [(0, 0, 1.7, W, "F", None), (80.35, 0, L, W, "F", None)]
    k.append((0, 31.9, L, W, "F", frozenset(r for r in GV_REFS if r not in TALL)))
    # ライザーのメスの口（ピン以外は背 3.4 まで ⇒ 背の高い物を入れない）
    k += [(1.66, 8.1, 16.9, 10.7, "F", frozenset(r for r in GV_REFS if r not in TALL)),
          (1.66, 23.4, 16.9, 25.9, "F", frozenset(r for r in GV_REFS if r not in TALL))]
    # マイク面: 床の座の唇（0.2）・OLED の L 足（0.185）・OLED のフィルム（0.185〜接触）・押さえ（上の縁を 0.3 押す）
    k += [(6.0, 31.0, 74.35, W, "B", None),
          (5.2, 0, 11.2, 0.9, "B", None), (70.9, 0, 76.9, 0.9, "B", None),
          (34.8, 15.71, 47.3, 19.21, "B", None)]
    k += [(30.5 - 0.5, 0, 35.8 + 0.5, 0.8, s, None) for s in "FB"] + [(48.0 - 0.5, 0, 50.4 + 0.5, 0.8, s, None) for s in "FB"]
    # マイク面の FPC のコネクタ（背 1.2 まで）: マイクと 1.2 を超える物を入れない（0402 だけ入れてよい）
    k.append((32.05, 15.71, 50.05, 19.21, "B", frozenset(r for r in GV_REFS if r.startswith(("C", "R", "D")))))
    return k


# 背の高い物（ハブの縁の帯 b ≥ 31.9 とライザーの口の上に入れない）。ESP32 モジュール 3.2・コネクタ・インダクタ
TALL = {"U5", "J21", "J22", "J23", "L101", "L102"}
GV_REFS = set()     # build() で回路図の部品を入れる
GV_SRC = {}         # この板の部品番号 → Voice PE の部品番号


# ======== 置き場所（板の座標・手で決める） ========
def mirror_block(src_ic, anchor, refs, rot=0.0, skip=(), ang_fix=None):
    """Voice PE の部品の固まりを、裏から見た鏡像（1.0 倍）で anchor（src_ic の中心を置く所）へ写す。
    rot: 固まり全体を回す角度（反時計回り・度）。返す: {ref: (x, b, 角度, 裏か)}。
    Voice PE で裏（B.Cu）の物はこの板の表（F）、表の物は裏（B）へ。"""
    vfp = voicepe.footprints()
    f0 = vfp[src_ic]
    cx, cy = float(find1(f0, "at")[1]), float(find1(f0, "at")[2])
    th = math.radians(rot)
    out = {}
    for vr in refs.split():
        r = GV.vref(vr)
        if vr in skip or r not in GV_REFS:
            continue
        f = vfp[vr]
        at = find1(f, "at")
        a = float(at[3]) if len(at) > 3 else 0.0
        dx, db = -(float(at[1]) - cx), -(float(at[2]) - cy)
        ex, eb = dx * math.cos(th) - db * math.sin(th), dx * math.sin(th) + db * math.cos(th)
        back = str(find1(f, "layer")[1]) == "F.Cu"
        ang = (180 - a + rot) % 360
        if ang_fix and r in ang_fix:
            ang = ang_fix[r]
        out[r] = (anchor[0] + ex, anchor[1] + eb, round(ang) % 360, back)
    return out


# 固まりの基準（Voice PE の IC の中心をここに置く）
U102_AT = (54.0, 17.8)      # XU316（表）。真裏のパスコンが裏（マイク面）の x 48.5〜55.5 に来る（フィルムの帯 x < 47.3 を避ける）
U110_AT = (9.5, 28.8)       # 3.3V の降圧。V5 の入口（J21 の 1 番 x 2.93, b 24.63）のそば、マイク（b 17）から 11mm
U112_AT = (54.5, 29.8)      # 0.9V の降圧。XU316 の真上（芯の電源を短く）
U111_AT = (59.0, 7.0)       # 1.8V の LDO。XU316 の下（V18 のピン 17・26・31 と JTAG のそば）
U108_AT = (67.0, 23.0)      # コーデック。固まりを −90° 回して、アンプがスピーカーの口（J23）の左に来る
U106_AT = (67.5, 4.2)       # マイクのバッファ。右下の空き（XU316 の右側の逃げ道を空ける）
U118_AT = (34.0, 29.5)      # マイクの LDO。ESP32 の上（背 1 以下の物だけ。MIC_MUTE は ESP32 の 38 番のそば）
ESP_AT = (30.3, 16.6)       # ESP32 の枠の中心。左の列がライザー（USB・I2C・画面）を向く。アンテナの端は b 26.5 側
J16_AT = (51.5, 4.5)        # JTAG のパッド（2x4）。XU316 の下の JTAG のピン（18〜24 番）の真下


def build_place(comps):
    """{ref: (x, b, 角度)} と 裏に置く部品の集合。"""
    place, back = {}, set()

    def put(d):
        for r, (x, b, a, bk) in d.items():
            place[r] = (x, b, a)
            if bk:
                back.add(r)

    # --- 筐体が決める物 ---
    for r, b in RISER_B.items():
        place[r] = (RISER_X0, b, 90)          # 90°: 足が +x へ並ぶ（1 番が x 2.932）
    place["J23"] = (*box_origin(comps["J23"]["fp"], 0, (SPK_BOX[0] + SPK_BOX[2]) / 2, (SPK_BOX[1] + SPK_BOX[3]) / 2), 0)
    vfp = voicepe.footprints()
    for r, (x, b) in MIC_AT.items():
        f = vfp[GV_SRC[r]]
        a = float(find1(f, "at")[3]) if len(find1(f, "at")) > 3 else 0.0
        place[r] = (*box_origin(comps[r]["fp"], (180 - a) % 360, x, b, back=True), round(180 - a) % 360)
        back.add(r)
    # --- マイクの足元（Voice PE の近い方のマイクからのずれを鏡にして写す・全部マイク面） ---
    put(mirror_block("U4", place["U104"][:2], "D1 D4 D10 R109 R6 R110"))
    put(mirror_block("U5", place["U105"][:2], "D12 D18 D19 R112 R5 R30 C5"))
    place["C301"] = (3.0, 14.6, 90)         # マイクの足元の 100nF（新しく足した物）
    place["C302"] = (79.3, 20.2, 90)
    back |= {"C301", "C302"}
    # --- ESP32 と、その周り ---
    place["U5"] = (*box_origin(comps["U5"]["fp"], 0, *ESP_AT), 0)
    place.update({"C44": (22.8, 28.0, 0), "C45": (25.5, 28.0, 0),          # V33 のパスコン（2 番ピンの上）
                  "R46": (19.6, 21.6, 0), "C43": (19.6, 20.4, 0),          # EN の引き上げと 1uF（3 番ピンの左）
                  "R47": (41.0, 10.5, 0)})                                 # BOOT の引き上げ（27 番ピンの右）
    # ライザーのそば（b 6.3 の列・J22 の口の手前）: USB の ESD と 22Ω、I2C の引き上げ
    for i, r in enumerate(["D106", "D107", "R156", "R157", "R223", "R228"]):
        place[r] = (4.5 + 2.0 * i, 6.3, 90)
    # I2S の直列 0Ω（ESP32 の下の列 GPIO9〜14 の真下・縦置き）と、左の列の 3 本（GPIO7・8・15）
    for r, px in (("R195", 25.85), ("R196", 27.13), ("R197", 28.39), ("R109", 29.66), ("R192", 30.94), ("R201", 32.2)):
        place[r] = (px, 4.6, 90)
    place.update({"R202": (21.5, 4.6, 90), "R193": (23.0, 4.6, 90), "R194": (24.5, 4.6, 90), "R246": (28.4, 2.4, 0)})
    # テストパッド（裏）: 🔴 Flash の真下に 4 つ並べたら、その穴と裏の線で Flash と XU316 の間の道が塞がった（2026-09-16）。
    #    ESP32 のピンのすぐ隣に置き、ピン → 穴 → 裏のパッド（穴はパッドの中）の 1 本で済ませる
    place.update({"TP1": (38.1, 22.1, 0), "TP2": (40.18, 20.3, 0),      # TXD・RXD（右の列の隣）
                  "TP3": (42.18, 10.5, 0), "TP4": (22.7, 23.7, 0)})       # BOOT（R47 の穴の上）・EN（左の列の穴の上）
    back |= {"TP1", "TP2", "TP3", "TP4"}
    # --- XU316 の固まり（Voice PE の並びのまま。真裏のパスコンはマイク面） ---
    # （Voice PE の C53/C54 は XU316 の下 5mm。ここでは空き道の外（6.5mm）へ下げる）
    put(mirror_block("U2", U102_AT,
                     "U2 X1 C2 C3 R3 R4 C41 FB6 FB9 C43 C45 C46 C47 C48 C49 C50 C51 C55 C56 C57 C52 C53 C54 C58 "
                     "Q3 R29 R63 R31 C92 R60 R70 R71 R72 R103 R104 R105 R62"))
    place.update({"R173": (53.0, 24.6, 90), "R141": (51.5, 24.6, 90),     # X1D34→I2S_DIN_ESP・XOD32→RST_DAC（上の空き道の外）
                  # XU316 の左のピン（7・9・10・11・13・14 番）の相手を、ピンと同じ順に上から並べる（線が交差しない）
                  "R203": (46.8, 18.9, 180), "R160": (46.8, 17.9, 180), "R170": (46.8, 16.9, 180),
                  "R159": (46.8, 15.9, 180), "R171": (46.8, 14.9, 180), "R172": (46.8, 13.9, 180),
                  "R204": (60.4, 20.4, 270), "R205": (60.8, 12.5, 90),    # I2S2 の 0Ω（右下の空き道の外）
                  "C242": (56.4, 9.4, 90), "C243": (44.0, 21.2, 0),        # V18・VDDIO の 100nF（C243 はマイク面）
                  "C160": (71.0, 6.0, 90), "C106": (71.0, 8.0, 0)})       # VDDIO の 100nF（U106 の 14 番のそば）
    # Flash（XU316 の左）: 🔴 列を横にして置くと、上の列（D0・CLK・D3）が XU316 の反対を向き、どう引いても 2 本が交差した
    #    （自動配線が 7 回とも同じ所で諦めた・2026-09-16）。90° 回して右の列（CS・D1・D2・GND）を XU316 のピンと同じ順に
    #    向き合わせる。CLK は Flash の下を回って左の列へ、D3 は Flash の腹の下（パッドの間）を通す。全部が表の面で交差しない
    #    CS の引き上げ R101 と VDDIO の 100nF（C101・C243）はマイク面（Flash の裏）
    place.update({"U103": (45.2, 22.2, 90), "R101": (49.35, 18.6, 270), "C101": (44.0, 20.0, 0)})
    back |= {"R101", "C101", "C243", "R123"}
    place["J16"] = (*J16_AT, 90)
    place["C153"] = (55.2, 11.3, 270)
    place["C154"] = (51.5, 11.3, 270)
    place.update({"X101": (46.94, 11.5, 180), "C102": (46.94, 10.2, 0), "C103": (48.72, 11.5, 270),
                  "R103": (47.95, 12.8, 0), "R104": (46.08, 12.8, 180),
                  "Q103": (47.9, 8.5, 180), "R129": (45.97, 8.5, 90), "R163": (45.0, 8.5, 270),
                  "R131": (49.7, 8.0, 90), "C192": (50.6, 8.0, 270)})
    # --- 電源（Voice PE の固まりのまま） ---
    # 3.3V の降圧（手で並べる: J21 の口の枠 b 26.4 と取付穴の枠 x 4.6 の外・上の縁の帯の中）
    place.update({"U110": (9.0, 28.2, 0), "L101": (11.8, 28.2, 0),          # LX はピン 5（右）→ L101 の 1 番へ
                  "C173": (6.6, 28.2, 90), "C183": (6.6, 30.6, 90), "C163": (9.0, 30.4, 0),   # V5 の入力
                  "C165": (14.8, 28.2, 90), "C166": (16.7, 28.2, 90), "C190": (18.2, 28.2, 90),  # V33 の出力
                  "R147": (8.0, 32.4, 90), "R146": (9.2, 32.4, 90), "C164": (10.4, 32.4, 90), "R144": (11.6, 32.4, 90),  # FB
                  "R208": (13.4, 31.6, 90), "R177": (14.6, 31.6, 90)})        # EN・PG の引き上げ
    put(mirror_block("U12", U112_AT, "U12 L2 R54 R55 C74 C71 C72 R14 R45 FB7 C44"))
    put(mirror_block("U11", U111_AT, "U11 R78 R48 C68 C69 C70"))
    # --- コーデックとアンプ（Voice PE の固まりを −90° 回す: アンプが右、スピーカーの口へ向く） ---
    put(mirror_block("U8", U108_AT,
                     "U8 C13 C14 C87 C33 C34 C37 C38 C35 C36 C39 C40 C117 C88 C89 C119 R15 R16 R17 "
                     "U9 C22 C23 C24 C27 C28 FB4 FB5 R20 R21 R22 C19 C20 C21 R99 R100 R39", rot=-90))
    place.update({"U109": (74.4, 19.9, 270), "R139": (72.6, 9.6, 0),
                  "FB108": (64.5, 16.5, 90), "C223": (65.7, 16.5, 90), "C244": (66.9, 16.5, 90),   # V33 → V33A
                  "R123": (63.8, 23.4, 90), "R124": (62.5, 15.7, 0),     # LDO_SELECT（マイク面・30 番の裏）・RST_DAC の引き上げ
                  "C128": (73.6, 11.7, 0), "C123": (75.7, 12.3, 0),     # SPKM の 10nF・PA_5V の 100nF（C124 の隣）
                  "R125": (62.5, 10.5, 0), "R135": (64.4, 10.5, 0), "C129": (66.3, 10.5, 0), "R136": (68.2, 10.5, 0),  # SHUTDOWN
                  "R175": (62.9, 32.3, 0), "R182": (78.5, 10.5, 90)})    # GND–GNDA の 0Ω（島の縁をまたぐ）
    # --- マイクのバッファと LDO ---
    place.update({"U106": (*U106_AT, 0), "R102": (61.0, 18.0, 90), "R108": (65.8, 12.5, 90), "R107": (64.6, 12.5, 90)})
    put(mirror_block("U18", U118_AT, "U18 C12 C110 R11 R28 Q4 R12"))
    place.update({"C104": (41.0, 32.0, 90), "R214": (42.3, 32.0, 90), "R48": (43.6, 32.0, 90)})
    missing = sorted(set(r for r in comps if not r.startswith("#")) - set(place))
    if missing:
        sys.exit("置き場所が決まっていない部品: " + " ".join(missing))
    return place, back


FIXED = {"J21", "J22", "J23", "U104", "U105", "U5"}


def box_origin(fp_id, ang, cx, cy, back=False):
    """枠の中心が (cx, cy)（板の座標）に来る原点。"""
    f = load_fp(fp_id)
    if back:
        f = G.mirror_y(f)
    b = full_box(f, 0.0, 0.0, ang)
    return cx - (b[0] + b[2]) / 2, cy + (b[1] + b[3]) / 2


def full_box(fp, X, Y, ang):
    """足形の枠（図面の座標）。courtyard に**パッドの外形**と**丸の本当の半径**を足した物。"""
    xs, ys = [], []
    b = G.courtyard(fp, 0.0, 0.0, 0.0)
    xs += [b[0], b[2]]
    ys += [b[1], b[3]]

    def walk(n):
        if isinstance(n, list):
            if n and n[0] == "fp_circle":
                lay = find1(n, "layer")
                if lay and "CrtYd" in str(lay[1]):
                    c, e = find1(n, "center"), find1(n, "end")
                    rr = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
                    xs.extend([float(c[1]) - rr, float(c[1]) + rr])
                    ys.extend([float(c[2]) - rr, float(c[2]) + rr])
            for e in n:
                if isinstance(e, list):
                    walk(e)
    walk(fp)
    for p in find(fp, "pad"):
        at, sz = find1(p, "at"), find1(p, "size")
        pa = math.radians(float(at[3]) if len(at) > 3 else 0.0)
        hx, hy = float(sz[1]) / 2 + 0.05, float(sz[2]) / 2 + 0.05
        for sx, sy in ((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)):
            xs.append(float(at[1]) + sx * math.cos(pa) + sy * math.sin(pa))
            ys.append(float(at[2]) - sx * math.sin(pa) + sy * math.cos(pa))
    pts = [G.rot_xy(a, c, ang) for a in (min(xs), max(xs)) for c in (min(ys), max(ys))]
    return (X + min(p[0] for p in pts), Y + min(p[1] for p in pts),
            X + max(p[0] for p in pts), Y + max(p[1] for p in pts))


def board_box(fp, x, b, ang):
    """足形の枠を板の座標（Y 上向き）で。"""
    X, Y = G.bx(x, b)
    bb = full_box(fp, X, Y, ang)
    return [bb[0] - G.ORG[0], G.BOARD_W - (bb[3] - G.ORG[1]), bb[2] - G.ORG[0], G.BOARD_W - (bb[1] - G.ORG[1])]


def convex_hull(points):
    """凸包（反時計回り・Andrew の方法）。"""
    pts = sorted(set((round(x, 5), round(y, 5)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def dsn_pad(p):
    """パッド 1 つ → 自動配線に渡す形。多角形のパッドと斜めのパッドは、実物を囲う凸包の多角形にして渡す。"""
    d = G.fp_pad(p)
    at = find1(p, "at")
    pa = float(at[3]) if len(at) > 3 else 0.0
    hx, hy = d["size"][0] / 2, d["size"][1] / 2
    rect = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    prim = find1(p, "primitives")
    if prim or pa % 90:
        a = math.radians(pa)
        poly = [(float(xy[1]), float(xy[2])) for gp in find(prim, "gr_poly") for xy in find(find1(gp, "pts"), "xy")] \
            if prim else []
        d["poly"] = convex_hull([(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))
                                 for x, y in (poly or rect) + rect])
        d["rot"] = 0.0
    return d


def outline():
    """角 R1.27 の長方形（ReSpeaker Lite の公式 CAD と同じ）。"""
    L, W, R = G.BOARD_L, G.BOARD_W, CORNER_R
    o = [G.seg(*G.bx(R, 0), *G.bx(L - R, 0)), G.seg(*G.bx(L, R), *G.bx(L, W - R)),
         G.seg(*G.bx(L - R, W), *G.bx(R, W)), G.seg(*G.bx(0, W - R), *G.bx(0, R))]
    for cx, cb, a0 in ((R, R, 180), (L - R, R, 270), (L - R, W - R, 0), (R, W - R, 90)):
        pts = [G.bx(cx + R * math.cos(math.radians(a0 + t)), cb + R * math.sin(math.radians(a0 + t))) for t in (0, 45, 90)]
        o.append(["gr_arc", ["start", f"{pts[0][0]:.3f}", f"{pts[0][1]:.3f}"], ["mid", f"{pts[1][0]:.3f}", f"{pts[1][1]:.3f}"],
                  ["end", f"{pts[2][0]:.3f}", f"{pts[2][1]:.3f}"], ["stroke", ["width", "0.1"], ["type", "default"]],
                  ["layer", Str("Edge.Cuts")], ["uuid", Str(G.uid())]])
    return o


def outline_poly():
    """ベタと DSN の外形（角の丸は 8 分割の折れ線で近似・内側に寄る向き）。"""
    L, W, R = G.BOARD_L, G.BOARD_W, CORNER_R
    pts = []
    for cx, cb, a0 in ((L - R, R, 270), (L - R, W - R, 0), (R, W - R, 90), (R, R, 180)):
        pts += [(cx + R * math.cos(math.radians(a0 + t)), cb + R * math.sin(math.radians(a0 + t))) for t in range(0, 91, 15)]
    return pts


# ======== 置いた後のパッドの位置（板の座標） ========
PADS = {}      # (ref, 番号) → dict(x, b, side, size, shape, net, kind)
CENTER = {}    # ref → (x, b)


def collect_pads(node, ref):
    at = find1(node, "at")
    X, Y = float(at[1]), float(at[2])
    A = math.radians(float(at[3]) if len(at) > 3 else 0.0)
    CENTER[ref] = (X - G.ORG[0], G.BOARD_W - (Y - G.ORG[1]))
    for p in find(node, "pad"):
        pa, sz = find1(p, "at"), find1(p, "size")
        px, py = float(pa[1]), float(pa[2])
        rx = px * math.cos(A) + py * math.sin(A)
        ry = -px * math.sin(A) + py * math.cos(A)
        gx, gy = X + rx - G.ORG[0], G.BOARD_W - (Y + ry - G.ORG[1])
        net = find1(p, "net")
        lay = [str(s) for s in find1(p, "layers")[1:]]
        pang = (float(pa[3]) if len(pa) > 3 else 0.0) % 180
        w, h = float(sz[1]), float(sz[2])
        if abs(pang - 90) < 1e-6:
            w, h = h, w
        PADS[(ref, str(p[1]))] = dict(x=gx, b=gy, size=(w, h), shape=str(p[3]), kind=str(p[2]),
                                      net=str(net[2]) if net else None,
                                      side="*" if str(p[2]) in ("thru_hole", "np_thru_hole") else lay[0][0])


def pad(ref, num):
    d = PADS[(ref, str(num))]
    return (d["x"], d["b"])


# ======== 先に引く線と穴（電源・GND） ========
# 板の座標の折れ線。KiCad には locked を付けて書き、自動配線（DSN）には protect で渡す
TRACKS = []    # (net, layer, width, [(x, b), ...])
VIAS = []      # (net, x, b)
OLD_SEGS = []  # --keep で戻す自動配線の線 (x0, b0, x1, b1, w)（板の座標）: GND の穴がこれを避けるため
OLD_VIAS = []  # 同じく穴 (x, b)
LAYER_MAP = {"F.Cu": "B.Cu", "B.Cu": "F.Cu", "In1.Cu": "In2.Cu", "In2.Cu": "In1.Cu"}


def track(net, layer, w, pts):
    TRACKS.append((net, layer, w, [tuple(p) for p in pts]))


def via(net, x, b):
    VIAS.append((net, x, b))


_VPE = {}


def voicepe_wiring():
    """Voice PE の板の線と貫通穴（ネット名つき・図面座標）。"""
    if not _VPE:
        tree = kisym.parse(voicepe.PCB.read_text(encoding="utf-8"))[0]
        names = {str(n[1]): str(n[2]) for n in find(tree, "net")}
        segs, vias = [], []
        for s in find(tree, "segment"):
            a, b = find1(s, "start"), find1(s, "end")
            segs.append((names[str(find1(s, "net")[1])], str(find1(s, "layer")[1]), float(find1(s, "width")[1]),
                         (float(a[1]), float(a[2])), (float(b[1]), float(b[2]))))
        for v in find(tree, "via"):
            at = find1(v, "at")
            vias.append((names[str(find1(v, "net")[1])], float(at[1]), float(at[2])))
        _VPE["segs"], _VPE["vias"] = segs, vias
    return _VPE["segs"], _VPE["vias"]


def copy_wiring(src_ic, anchor, nets_src, radius, rot=0.0, nets_ok=(), min_w=0.2, layers=("F.Cu", "B.Cu")):
    """Voice PE の src_ic の周り（半径 radius・図面 mm）にある、nets_src のネットの線と穴を鏡に写して TRACKS/VIAS へ。
    層は F↔B・In1↔In2。ネット名はこの板の名前に替える（無いネットは飛ばす）。線幅は min_w 未満なら min_w にする。"""
    vfp = voicepe.footprints()
    f0 = vfp[src_ic]
    cx, cy = float(find1(f0, "at")[1]), float(find1(f0, "at")[2])
    th = math.radians(rot)

    def T(x, y):
        dx, db = -(x - cx), -(y - cy)
        return (anchor[0] + dx * math.cos(th) - db * math.sin(th), anchor[1] + dx * math.sin(th) + db * math.cos(th))

    segs, vias = voicepe_wiring()
    n = 0
    for net, lay, w, a, b in segs:
        if net not in nets_src or lay not in layers or                 math.hypot(a[0] - cx, a[1] - cy) > radius or math.hypot(b[0] - cx, b[1] - cy) > radius:
            continue
        nn = GV.net_name(net)
        if nn not in nets_ok:
            continue
        ww = max(w, min_w)
        if ww < 0.3:
            ww = min(ww, 0.2)
        track(nn, LAYER_MAP[lay], ww, [T(*a), T(*b)])
        n += 1
    for net, x, y in vias:
        if net in nets_src and math.hypot(x - cx, y - cy) <= radius:
            nn = GV.net_name(net)
            if nn in nets_ok:
                via(nn, *T(x, y))
    return n


def _touch(pt, net, layer, own_idx):
    """点 pt（板の座標）が、同じネットのパッド・貫通穴・他の線に触れているか。"""
    x, b = pt
    for (ref, num), d in PADS.items():
        if d["net"] != net or (d["side"] not in ("*", layer[0])):
            continue
        w, h = d["size"]
        if abs(x - d["x"]) <= w / 2 + 0.05 and abs(b - d["b"]) <= h / 2 + 0.05:
            return True
    for vn, vx, vb in VIAS:
        if vn == net and math.hypot(x - vx, b - vb) <= VIA[0] / 2 + 0.05:
            return True
    for i, (tn, tl, tw, pts) in enumerate(TRACKS):
        if i == own_idx or tn != net or tl != layer:
            continue
        for a, c in zip(pts, pts[1:]):
            # 線分 a–c への距離
            ax, ab = a; cx, cb = c
            L2 = (cx - ax) ** 2 + (cb - ab) ** 2
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * (cx - ax) + (b - ab) * (cb - ab)) / L2))
            if math.hypot(x - (ax + t * (cx - ax)), b - (ab + t * (cb - ab))) <= tw / 2 + 0.05:
                return True
    return False


def prune_dangling():
    """写した線のうち、どちらかの端が何にも触れていない物を落とす（触れる相手が消えて新たに浮く物も、繰り返して落とす）。
    🔴 2026-09-16 ユーザー「この緑で囲んだ所のガッタガタは大丈夫なんです？」: Voice PE の線を半径で切って写すと、
       写す範囲の外へ続いていた線が行き先の無い切れ端として残った（VDDIO の 1mm の束など）。"""
    removed = 0
    while True:
        keep = []
        drop = 0
        for i, (net, lay, w, pts) in enumerate(TRACKS):
            if _touch(pts[0], net, lay, i) and _touch(pts[-1], net, lay, i):
                keep.append((net, lay, w, pts))
            else:
                drop += 1
        removed += drop
        TRACKS[:] = keep
        if not drop:
            break
    return removed


def move_via(net, old, new, tol=0.15):
    """写した貫通穴 1 つを new へ動かし、その穴で終わっていた線の端も一緒に動かす。"""
    for i, (n, vx, vb) in enumerate(VIAS):
        if n == net and math.hypot(vx - old[0], vb - old[1]) < tol:
            VIAS[i] = (net, new[0], new[1])
            for j, (tn, tl, tw, pts) in enumerate(TRACKS):
                if tn == net:
                    TRACKS[j] = (tn, tl, tw, [new if math.hypot(q[0] - vx, q[1] - vb) < 1e-6 else q for q in pts])
            return True
    return False


def nudge_vias_off_pins(ref):
    """🔴 Voice PE から写した貫通穴（隙間 0.125 の設計）が、ピンの列の 0.1mm 横にあって隣のピンの出口を塞いだ
    （2026-09-16・21・23・53 番が未接続）。ピンのパッドに 0.15 より近い穴は、部品の中心から外へ 0.1 ずつ動かす。"""
    cx, cb = CENTER[ref]
    pads = [(d["x"], d["b"], d["size"], d["net"]) for (r, n), d in PADS.items() if r == ref and d["net"]]
    moved = 0
    for i, (net, vx, vb) in enumerate(VIAS):
        if math.hypot(vx - cx, vb - cb) > 6.0:
            continue
        ox, ob = vx, vb
        ux, ub = vx - cx, vb - cb
        n = math.hypot(ux, ub) or 1.0
        ux, ub = ux / n, ub / n
        for _ in range(8):
            bad = False
            for px, pb, (w, h), pnet in pads:
                if pnet == net:
                    continue
                if _rect_gap(vx, vb, VIA[0] / 2, (px - w / 2, pb - h / 2, px + w / 2, pb + h / 2)) < CLEAR + 0.01:
                    bad = True
                    break
            if not bad:
                break
            vx, vb = vx + ux * 0.1, vb + ub * 0.1
        if (vx, vb) != (ox, ob):
            VIAS[i] = (net, vx, vb)
            for j, (tn, tl, tw, pts) in enumerate(TRACKS):
                if tn == net:
                    TRACKS[j] = (tn, tl, tw, [(vx, vb) if math.hypot(q[0] - ox, q[1] - ob) < 1e-6 else q for q in pts])
            moved += 1
    return moved


def hand_wiring():
    """自動配線に任せない短い線と穴。
    🔴 2026-09-16: XU316 の左のピンの列とその相手（0Ω の列）の間の道を、自動配線が南北の幹線に使ってしまい、
       ピン → 0Ω の 3mm の線が 6 本とも引けなかった。ピンのそばの短い線は先に決め打ちする。
       JTAG・QSPI・I2S_BCLK・LDO_SELECT は、目で確かめずに座標で引いたら交差だらけになった（13 か所）ので、
       ここでは引かず、他を固定した上で自動配線に引かせる（--partial）。"""
    W = 0.15
    # 写した VDDIO の穴（8・38・52 番の外側）: 8 番は手の線の通り道と重なるので自分で引き直す（flash_wiring）。52 番は少し外へ
    drop_copied_near("VDDIO", pad("U102", "8"), 2.6)
    move_via("VDDIO", (54.4, 21.93), (54.4, 22.15))
    flash_wiring()
    jtag_wiring()
    # 左の辺: ピン → 同じ高さの相手（ピンの並びと同じ順なので交差しない）。パッドの列から 0.5mm は真横に出てから曲がる
    for pin, ref in (("7", "R203"), ("9", "R160"), ("10", "R170"), ("11", "R159"), ("13", "R171"), ("14", "R172")):
        a, b = pad("U102", pin), pad(ref, "1")
        track(PADS[("U102", pin)]["net"], "F.Cu", W, [a, (a[0] - 0.5, a[1]), (b[0] + 0.65, b[1]), b])
    # 水晶: XOUT（15 番）→ R103.1 → R104.1、XIN（16 番）→ R103.2 → C103.1 → X101.1、R104.2 → X101.3 → C102.1
    p15, p16 = pad("U102", "15"), pad("U102", "16")
    r103a, r103b, r104a, r104b = pad("R103", "1"), pad("R103", "2"), pad("R104", "1"), pad("R104", "2")
    c103a, x1, x3, c102a = pad("C103", "1"), pad("X101", "1"), pad("X101", "3"), pad("C102", "1")
    track("N_U102_XOUT", "F.Cu", W, [p15, (50.0, p15[1]), (49.3, 14.05), (48.7, 13.45), (47.9, 13.45), (r103a[0], 13.05), r103a])
    track("N_U102_XOUT", "F.Cu", W, [r103a, r104a])
    track("N_U102_XIN", "F.Cu", W, [p16, (p16[0], 13.4), (49.6, 13.4), (r103b[0] + 0.3, 13.1), r103b])
    track("N_U102_XIN", "F.Cu", W, [r103b, (c103a[0], 12.4), c103a, (x1[0], c103a[1]), x1])
    track("N_C102_Pad1", "F.Cu", W, [r104b, (r104b[0], 11.7), x3, (x3[0], c102a[1]), c102a])
    # 上の辺 53 番 → R173（52 番の穴を避けて、まず 0.4 真上へ）
    p53, r173 = pad("U102", "53"), pad("R173", "1")
    track("N_U102_X1D34", "F.Cu", W, [p53, (p53[0], p53[1] + 0.4), (p53[0] - 0.45, p53[1] + 0.85), (r173[0], r173[1] - 1.0), r173])
    # 右の辺: 39 番 → R102（38 番の穴の下を通る）、41 番 → R204（上へ）
    p41, r204 = pad("U102", "41"), pad("R204", "1")
    track("N_U102_X0D35", "F.Cu", W, [p41, (p41[0] + 1.4, p41[1]), (59.8, r204[1] - 0.9), (r204[0] - 0.4, r204[1]), r204])
    # V33（30 番）→ 穴 → 裏を回って C158.1 と FB109.1（C158 の右を上がる）
    p30, c158, fb109 = pad("U102", "30"), pad("C158", "1"), pad("FB109", "1")
    track("V33", "F.Cu", 0.2, [p30, (p30[0], 12.6), (p30[0], 12.0)])
    via("V33", p30[0], 12.0)
    track("V33", "B.Cu", 0.3, [(p30[0], 12.0), (p30[0], 12.6), (58.6, 14.0), (58.94, 14.5), (58.94, fb109[1]), fb109])
    track("V33", "B.Cu", 0.3, [(58.94, fb109[1]), (58.94, c158[1]), c158])
    # V18: C154 → 17 番、C153 → 26 番（0.2: 隣のピンとの隙間 0.17）。31 番は裏の C152 から穴で
    c154, c153, c152 = pad("C154", "1"), pad("C153", "1"), pad("C152", "1")
    p17, p26, p31 = pad("U102", "17"), pad("U102", "26"), pad("U102", "31")
    track("V18", "F.Cu", 0.2, [c154, (p17[0], c154[1] + 0.2), p17])
    track("V18", "F.Cu", 0.2, [c153, p26])
    track("V18", "F.Cu", 0.2, [p31, (58.1, p31[1]), (58.1, 14.4)])
    via("V18", 58.1, 14.4)
    track("V18", "B.Cu", 0.2, [(58.1, 14.4), (c152[0], 15.3), c152])
    # GNDA の島（F と In1）をつなぐ穴（コーデックの 17 番の切り欠きにも 1 つ）
    for x, b in ((69.0, 25.4), (65.0, 30.5), (78.0, 31.0), (63.85, 27.15)):
        via("GNDA", x, b)
    # 🔴 マイク（MSM261）の信号のパッド（1〜4 番）は周りを GND のパッドに囲まれていて、隙間 0.15 では外へ線が出せない
    #    （Voice PE は隙間 0.125 で斜めに抜いていた・2026-09-16 に自動配線がマイクの GND の上を通って短絡）。
    #    ⇒ パッドの中に貫通穴を打って内層へ抜く（via-in-pad）。マイクの周り（マイク面）は自動配線に入らせない
    for ref in ("U104", "U105"):
        for num in ("1", "2", "3", "4"):
            d = PADS[(ref, num)]
            if d["net"] and d["net"] != "GND":
                via(d["net"], d["x"], d["b"])
    # 🔴 GND のベタの島に取り残されるパッド（DRC の unconnected・2026-09-16）:
    #    XU316 の裏の C150/C152/C158 の GND（表は XU316 の足元で穴が打てない）→ XU316 の GND パッドの端に穴を打って裏の線でつなぐ。
    #    R115（SPI_SELECT の引き下げ。Voice PE の位置のまま GNDA の島の中）の GND → 隣に穴（裏の GND のベタと D119 につながる）
    via("GND", 55.6, 17.4)
    track("GND", "B.Cu", 0.2, [padn("C150", "GND"), (56.4, 17.3), (56.0, 17.3), (55.79, 17.4), (55.6, 17.4)])
    via("GND", 72.4, 22.85)
    track("GND", "F.Cu", 0.2, [padn("R115", "GND"), (72.15, 23.0), (72.4, 22.85)])


def padn(ref, net):
    """ref のパッドのうち net の物（板の座標）。"""
    for (r, n), d in PADS.items():
        if r == ref and d["net"] == net:
            return (d["x"], d["b"])
    sys.exit(f"{ref} に {net} のパッドが無い")


def flash_wiring():
    """Flash（90° 回転）の QSPI 6 本・VDDIO の左側・テストパッド・I2S_LRCK の裏の線・R101。全部を目で確かめた座標で引く。"""
    W = 0.15
    p1, p2, p3, p5, p59, p60 = (pad("U102", n) for n in ("1", "2", "3", "5", "59", "60"))
    f = {n: pad("U103", n) for n in "12345678"}
    # 右の列（CS・D1・D2）: XU316 のピンと同じ順なので、まっすぐ寄せるだけ
    track("QSPI_CS_N", "F.Cu", W, [p3, (49.45, p3[1]), (49.3, f["1"][1] - 0.31), f["1"]])
    track("QSPI_D1", "F.Cu", W, [p1, (50.4, p1[1]), (50.4, 21.1), (49.9, f["2"][1]), f["2"]])
    track("QSPI_D2", "F.Cu", W, [p60, (p60[0], 21.85), (50.15, 21.85), (49.5, f["3"][1]), f["3"]])
    # D3: 右の列の 1・2 番の間から Flash の腹の下を通り、左の列の 8・7 番の間へ出て 7 番へ
    mid = (f["1"][1] + f["2"][1]) / 2
    track("QSPI_D3", "F.Cu", W, [p2, (49.75, p2[1]), (49.75, mid), (42.4, mid), (42.0, f["7"][1] - 0.2), f["7"]])
    # D0: 上の列 59 番 → 上へ → Flash の上（GND の 4 番の上）を左へ → 5 番へ
    top = f["4"][1] + 0.64
    track("QSPI_D0", "F.Cu", W, [p59, (p59[0], 22.4), (50.4, 22.4), (50.2, 22.6), (50.2, top - 0.2), (50.0, top),
                                 (41.8, top), f["5"]])
    # CLK: 5 番 → Flash の下（0Ω の列 R203 の上）を左へ → 左の列の外側を上がって 6 番へ
    lo = f["1"][1] - 0.59
    track("QSPI_CLK", "F.Cu", W, [p5, (49.3, p5[1]), (48.6, lo), (40.65, lo), (40.65, f["6"][1]), f["6"]])
    # VDDIO: 8 番 → 7・9 番の線の間を通って穴 → 内層 2 → Flash の 8 番（パッドの中の穴）。途中に C101（裏）へ穴、C243 は C101 から
    p8 = pad("U102", "8")
    track("VDDIO", "F.Cu", W, [p8, (50.0, p8[1]), (49.0, 18.09), (48.2, 18.32), (47.9, 18.4)])
    via("VDDIO", 47.9, 18.4)
    track("VDDIO", "In2.Cu", 0.25, [(47.9, 18.4), (47.9, 19.0), (46.95, f["8"][1]), f["8"]])
    via("VDDIO", *f["8"])
    via("VDDIO", 43.0, f["8"][1])
    c101, c243 = padn("C101", "VDDIO"), padn("C243", "VDDIO")
    track("VDDIO", "B.Cu", 0.2, [(43.0, f["8"][1]), c101])
    track("VDDIO", "B.Cu", 0.2, [c101, c243])
    p52v = (54.4, 22.15)
    track("VDDIO", "F.Cu", 0.2, [p52v, (54.4, 25.6), (54.2, 25.8), (43.5, 25.8), (43.2, 25.5), (43.2, 25.35)])
    via("VDDIO", 43.2, 25.35)
    track("VDDIO", "B.Cu", 0.2, [(43.2, 25.35), (43.2, 21.5), c243])
    # R101（裏）: CS の線の上の穴 → 裏の R101 → VDDIO の穴
    via("QSPI_CS_N", 48.5, f["1"][1])          # Flash の 1 番のパッドの中（隣のピンの線の間には穴が入らない）
    r_cs, r_io = padn("R101", "QSPI_CS_N"), padn("R101", "VDDIO")
    track("QSPI_CS_N", "B.Cu", 0.2, [(48.5, f["1"][1]), (48.5, 19.5), (49.0, r_cs[1]), r_cs])
    track("VDDIO", "B.Cu", 0.2, [r_io, (48.4, r_io[1]), (47.9, 18.4)])
    # テストパッド: ESP32 のピン → 穴（裏のパッドの中）
    via("ESP_TXD", 40.18, 21.42)
    track("ESP_TXD", "F.Cu", W, [padn("U5", "ESP_TXD"), (40.18, 21.42)])
    track("ESP_TXD", "B.Cu", 0.2, [(40.18, 21.42), (39.3, 21.42), (38.6, 22.1), padn("TP1", "ESP_TXD")])
    via("ESP_RXD", 40.18, 20.15)
    track("ESP_RXD", "F.Cu", W, [padn("U5", "ESP_RXD"), (40.18, 20.15)])
    track("ESP_EN", "B.Cu", 0.2, [(22.7, 22.7), padn("TP4", "ESP_EN")])
    # I2S_LRCK の裏の線: XU316 の裏のパスコンの塊の上を回る（古い線は VDDIO の穴と重なった）
    via("I2S_LRCK", 45.69, 16.9)
    track("I2S_LRCK", "F.Cu", 0.2, [pad("R170", "2"), (45.69, 16.9)])
    track("I2S_LRCK", "In2.Cu", 0.2, [(36.39, 16.9), (45.69, 16.9)])
    track("I2S_LRCK", "B.Cu", 0.2, [(45.69, 16.9), (50.45, 16.9), (50.45, 21.5), (52.0, 21.5), (52.63, 22.13), (52.63, 22.79),
                                    (57.02, 22.79)])


def jtag_wiring():
    """XU316 の下（JTAG 5 本・RST_N・PLL_AVDD の穴・V18）と右（X0D36・SCL・X1D22）。
    🔴 下: V18 の内層 2 の線が XU316 の下で袋小路を作り、TDO が真ん中を縦に走り、PLL_AVDD の写した穴が 21・23 番の真ん中にあって
       自動配線が 7 回とも同じ所で諦めた（2026-09-16）。V18 は板の下端の表の線と裏の線に替え、TDO は内層で J16 の真下へ、
       TMS・TCK は表で J16 の 2 列の間を通す。ピンの並びは 0.4mm なので、穴は隣のピンの線が離れた所にしか置けない"""
    W = 0.15
    p20, p21, p22, p23, p24 = (pad("U102", n) for n in ("20", "21", "22", "23", "24"))
    # PLL_AVDD の写した穴を、21 番と 23 番の線がよけられる深さへ
    move_via("N_U102_PLL_AVDD", (53.59, 13.69), (53.6, 12.3))
    # TDO: 20 番 → 穴 → 内層 2 を真下へ → J16 の 5 番（RST_N の 6 番の真下）の下から入る
    track("TDO", "F.Cu", W, [p20, (p20[0], 13.6), (52.6, 13.35), (52.6, 12.9)])
    via("TDO", 52.6, 12.9)
    track("TDO", "In2.Cu", 0.2, [(52.6, 12.9), (52.75, 12.75), (52.75, 7.75), (53.75, 6.75), (53.75, 6.7)])
    via("TDO", 53.75, 6.7)
    track("TDO", "F.Cu", 0.2, [(53.75, 6.7), (53.75, 3.6), (53.38, 3.23), pad("J16", "5")])
    # RST_N: 21 番 → TDO の穴と PLL_AVDD の穴の間を下りて → リセットの固まり（C192・R131・Q103）と J16 の 6 番
    c192, r131, q103, j6 = pad("C192", "1"), pad("R131", "1"), pad("Q103", "3"), pad("J16", "6")
    track("RST_N", "F.Cu", W, [p21, (p21[0], 13.6), (53.1, 13.5), (53.1, 9.0), (52.55, c192[1]), c192])
    track("RST_N", "F.Cu", 0.2, [c192, (50.18, 8.03), (r131[0], r131[1] + 0.01), r131, (49.2, r131[1]), (48.81, 7.93), (q103[0], 7.93), q103])
    track("RST_N", "F.Cu", 0.2, [c192, (j6[0], 6.29), j6])
    # TMS: 23 番 → 右へ半歩ずれて下りる → J16 の 2 列の間（上の段）を左へ → 2 番の下から入る
    j2 = pad("J16", "2")
    track("TMS", "F.Cu", W, [p23, (p23[0], 13.45), (54.2, 13.25), (54.2, 2.55), (53.95, 2.3),
                             (49.2, 2.3), (48.96, 2.55), (48.96, 4.5), (j2[0] + 0.2, 4.5), j2])
    # TCK: 24 番 → もう半歩右へ → J16 の 2 列の間（下の段）を左へ → 3 番の上から入る
    j3 = pad("J16", "3")
    track("TCK", "F.Cu", W, [p24, (p24[0], 13.9), (54.65, 13.65), (54.65, 12.6)])
    via("TCK", 54.65, 12.6)
    track("TCK", "In2.Cu", 0.2, [(54.65, 12.6), (54.65, 5.2), (54.25, 4.8), (j3[0] + 0.4, 4.8), (j3[0], 4.6)])
    via("TCK", j3[0], 4.6)
    track("TCK", "F.Cu", 0.2, [(j3[0], 4.6), j3])
    # TDI: 内層の穴を J16 の 4 番のそばへ（TMS・TCK の道を空ける）
    j4 = pad("J16", "4")
    track("TDI", "In2.Cu", 0.2, [(52.22, 6.21), (51.6, 5.7), (51.4, 5.5)])
    via("TDI", 51.4, 5.5)
    track("TDI", "F.Cu", 0.2, [(51.4, 5.5), (50.95, j4[1]), j4])
    # V18: (a) J16 の 1 番は板の下端の表の線で、(b) C154・R131 の側は裏の線で、C242 のそばの穴から
    j1 = pad("J16", "1")
    track("V18", "F.Cu", 0.3, [(56.4, 6.4), (56.4, 1.9), (56.1, 1.6), (j1[0] + 0.3, 1.6), j1])
    # V18 の C154・R131 の枝（自動配線の形をそのまま手で戻す）
    via("V18", 50.21, 11.07)
    track("V18", "F.Cu", 0.4, [(50.21, 11.07), (50.9, 11.76), (51.5, 11.76)])
    track("V18", "F.Cu", 0.4, [(50.21, 11.07), (49.7, 10.56), (49.7, 8.46)])
    c242 = padn("C242", "V18")
    track("V18", "F.Cu", 0.3, [c242, (55.95, c242[1]), (55.7, c242[1] + 0.25), (55.7, 9.6)])
    via("V18", 55.7, 9.6)
    track("V18", "B.Cu", 0.3, [(55.7, 9.6), (51.4, 9.6), (50.9, 10.1), (50.9, 10.6), (50.21, 11.07)])
    # 右の列: X0D36（43 番）は穴 → 内層 2 で R205 へ（古い道の形）。SCL（44 番）は穴 → 内層 2 で上へ → 裏の SCL の線へ
    p39, p43, p44 = pad("U102", "39"), pad("U102", "43"), pad("U102", "44")
    r205 = pad("R205", "1")
    track("N_U102_X0D36", "F.Cu", W, [p43, (58.25, p43[1]), (58.35, 19.7)])
    via("N_U102_X0D36", 58.35, 19.7)
    track("N_U102_X0D36", "In2.Cu", 0.2, [(58.35, 19.7), (60.38, 19.7), (60.38, 16.58), (61.94, 15.02), (61.94, 12.53), (61.45, r205[1])])
    via("N_U102_X0D36", 61.45, r205[1])
    track("N_U102_X0D36", "F.Cu", 0.2, [(61.45, r205[1]), r205])
    track("SCL", "F.Cu", W, [p44, (58.6, p44[1]), (58.85, 20.25)])
    via("SCL", 58.85, 20.25)
    track("SCL", "In2.Cu", 0.2, [(58.85, 20.25), (58.85, 23.5), (59.2, 23.85), (59.2, 24.5)])
    via("SCL", 59.2, 24.5)
    track("SCL", "B.Cu", 0.2, [(59.2, 24.5), (59.2, 25.49)])
    # X1D22（39 番）→ R102: 38 番の VDDIO の写した穴を下へ動かして道を空ける
    move_via("VDDIO", (58.69, 18.34), (59.0, 16.85))
    drop_copied_near("VDDIO", (58.69, 18.34), 0.5)
    p38 = pad("U102", "38")
    track("VDDIO", "F.Cu", W, [p38, (58.3, p38[1]), (58.6, 17.5), (58.75, 17.1), (59.0, 16.85)])
    track("VDDIO", "B.Cu", 0.3, [(59.0, 16.85), (59.4, 16.99)])
    track("VDDIO", "B.Cu", 0.3, [(57.45, 18.35), (58.75, 18.35), (58.9, 18.2), (58.9, 17.6), (59.0, 16.85)])
    r102 = pad("R102", "1")
    track("N_U102_X1D22", "F.Cu", W, [p39, (58.5, p39[1]), (59.3, r102[1]), r102])
    # LDO_SELECT: コーデック 30 番のすぐ左に穴 → 裏の R123 → 裏の V33A の線へ。🔴 30 番は上下のピン（29 DVDD・31 RST_DAC）の線に
    #    挟まれていて表では入れない。DVDD の写した線は 30 番の高さを空ける形に引き直す
    p30 = pad("U108", "30")
    via("N_U108_LDO__SELECT", 63.8, p30[1])
    track("N_U108_LDO__SELECT", "F.Cu", W, [(63.8, p30[1]), p30])
    r_ld, r_va = padn("R123", "N_U108_LDO__SELECT"), padn("R123", "V33A")
    track("N_U108_LDO__SELECT", "B.Cu", 0.2, [(63.8, p30[1]), r_ld])
    track("V33A", "B.Cu", 0.2, [r_va, (63.3, r_va[1]), (62.68, 24.48)])
    p29, dv1 = pad("U108", "29"), (63.14, 22.14)
    drop_copied_near("N_U108_DVDD", dv1, 1.2)
    track("N_U108_DVDD", "F.Cu", 0.2, [p29, (63.7, p29[1]), (63.5, 22.95), (63.38, 23.2)])
    track("N_U108_DVDD", "F.Cu", 0.2, [(63.14, 22.92), (63.14, 22.39)])


def drop_copied_near(net, pt, r):
    """写した線と穴のうち、pt から r 以内に端がある net の物を捨てる。"""
    TRACKS[:] = [t for t in TRACKS if not (t[0] == net and any(math.hypot(q[0] - pt[0], q[1] - pt[1]) < r for q in t[3]))]
    VIAS[:] = [v for v in VIAS if not (v[0] == net and math.hypot(v[1] - pt[0], v[2] - pt[1]) < r)]


def prewire(nets):
    """電源と、Voice PE の固まりの中の線を先に引く。"""
    ok = set(nets)
    # --- XU316: VDD の環と貫通穴、PLL、水晶、真裏のパスコンへの線（Voice PE の U2 の周り 9mm） ---
    copy_wiring("U2", U102_AT, {"VDD", "VDDIO", "Net-(U2-PLL_AVDD)"}, 9.0, nets_ok=ok, min_w=0.15)
    # --- 0.9V の降圧（SW・FB・0.9V・VDD の環まで）と 1.8V の LDO、3.3V の降圧の周り ---
    # SW（スイッチ端子 → インダクタ）は Voice PE の扇形の束ではなく 1 本の直線で引く（ユーザー 2026-09-16「ガッタガタ」）
    copy_wiring("U12", U112_AT, {"Net-(U12-FB)", "Net-(U12-EN)", "Net-(U12-MODE)"}, 4.5, nets_ok=ok)
    p2, pl = pad("U112", "2"), pad("L102", "1")
    track("N_U112_SW", "F.Cu", 0.3, [p2, (p2[0] + 0.65, p2[1])])
    track("N_U112_SW", "F.Cu", 0.4, [(p2[0] + 0.65, p2[1]), pl])
    copy_wiring("U11", U111_AT, {"Net-(U11-IN)", "Net-(U11-EN)"}, 5.5, nets_ok=ok)
    # --- コーデックとアンプ（Voice PE の U8 の周り 13mm・固まりごと −90° 回す） ---
    copy_wiring("U8", U108_AT, {"Net-(U8-AVDD)", "Net-(U8-DVDD)", "Net-(U8-REF)", "+3.3VA", "Net-(U8-IN1_L)",
                                "Net-(U8-IN2_L)", "Net-(U8-IN3_L)",
                                "Net-(C19-Pad2)", "Net-(C20-Pad2)", "Net-(C21-Pad2)", "Net-(U8-SPI__SELECT)"},
                13.0, rot=-90, nets_ok=ok)


# 電源のネット（自動配線には線幅 0.4 の組として渡す。GND・GNDA は渡さない）
POWER_NETS = {"V5", "V33", "V18", "V09", "PA_5V", "SPKO", "SPKM", "N_U110_LX", "N_U112_SW"}
POWER_W = 0.4
POWER2_NETS = {"VDD", "VDDIO", "V33A", "VDD_MIC"}
POWER2_W = 0.3


def _rect_gap(cx, cb, r, box):
    """丸（中心・半径）と長方形（x0,b0,x1,b1）の隙間。"""
    dx = max(box[0] - cx, 0, cx - box[2])
    db = max(box[1] - cb, 0, cb - box[3])
    return math.hypot(dx, db) - r


def gnd_vias():
    """GND の SMD パッドのそば（部品の外側）に貫通穴を 1 つずつ打つ。QFN の裏のパッドには 3×3。
    GND は自動配線に渡さないので、F/B のベタと In1 の面をここでつなぐ（縫いのビアは route.stitch が足す）。"""
    boxes = []     # 他の銅（パッド）の枠（板の座標）
    for (ref, num), d in PADS.items():
        w, h = d["size"]
        boxes.append((d["x"] - w / 2, d["b"] - h / 2, d["x"] + w / 2, d["b"] + h / 2, d["net"], d["side"]))
    put = []
    r_via = VIA[0] / 2

    def free(x, b):
        if x < 1.0 or b < 1.0 or x > G.BOARD_L - 1.0 or b > G.BOARD_W - 1.0:
            return False
        for mx, my in G.MOUNT:
            if math.hypot(x - mx, b - my) < G.MOUNT_D / 2 + G.MOUNT_KEEP + r_via:
                return False
        for bx0, bb0, bx1, bb1, net, side in boxes:
            gap = _rect_gap(x, b, r_via, (bx0, bb0, bx1, bb1))
            if net == "GND" and gap > 0.05:
                continue
            if gap < CLEAR + 0.02:
                return False
        for _, vx, vb in put:
            if math.hypot(x - vx, b - vb) < VIA[0] + 0.3:
                return False
        for tn, tl, tw, pts in TRACKS:
            if tn == "GND":
                continue
            for a, c in zip(pts, pts[1:]):
                ax, ab = a
                cx2, cb2 = c
                L2 = (cx2 - ax) ** 2 + (cb2 - ab) ** 2
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * (cx2 - ax) + (b - ab) * (cb2 - ab)) / L2))
                if math.hypot(x - (ax + t * (cx2 - ax)), b - (ab + t * (cb2 - ab))) < tw / 2 + r_via + CLEAR + 0.02:
                    return False
        for tn, vx, vb in VIAS:
            if math.hypot(x - vx, b - vb) < VIA[0] + CLEAR + 0.05:
                return False
        for vx, vb in OLD_VIAS:
            if math.hypot(x - vx, b - vb) < VIA[0] + CLEAR + 0.05:
                return False
        for ax, ab, cx2, cb2, tw in OLD_SEGS:
            L2 = (cx2 - ax) ** 2 + (cb2 - ab) ** 2
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * (cx2 - ax) + (b - ab) * (cb2 - ab)) / L2))
            if math.hypot(x - (ax + t * (cx2 - ax)), b - (ab + t * (cb2 - ab))) < tw / 2 + r_via + CLEAR + 0.02:
                return False
        return True

    for (ref, num), d in PADS.items():
        if d["net"] != "GND" or d["kind"] != "smd":
            continue
        w, h = d["size"]
        if w > 3 and h > 3:                      # QFN の裏のパッド: 3×3（裏面のパスコンや線と重なる所は打たない）
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    x, b = d["x"] + i * 1.0, d["b"] + j * 1.0
                    if free(x, b):
                        put.append(("GND", x, b))
            continue
        cx, cb = CENTER[ref]
        vx, vb = d["x"] - cx, d["b"] - cb
        n = math.hypot(vx, vb) or 1.0
        ux, ub = vx / n, vb / n
        half = (abs(ux) * w + abs(ub) * h) / 2
        for k in (0.55, 0.75, 0.95, 1.2):
            x, b = d["x"] + ux * (half + k), d["b"] + ub * (half + k)
            if free(x, b):
                put.append(("GND", x, b))
                break
    for net, x, b in put:
        via(net, x, b)
    return len(put)


def gnda_island():
    """GNDA の島（F.Cu と In1.Cu・優先 1）。コーデック U108 の本体（EPAD は GND）は島の外に残す（Voice PE と同じ）。"""
    return [(63.4, 26.4), (63.4, 33.3), (80.0, 33.3), (80.0, 10.5), (70.4, 10.5), (70.4, 25.0), (68.4, 25.0), (68.4, 26.4)]


# ======== 書く ========
def build():
    comps, pads, nets = G.netlist()
    G.NETNUM.clear()
    G.NETNUM.update(nets)
    GV_REFS.update(r for r in comps if not r.startswith("#"))
    GV_SRC.update({p["ref"]: p["src"] for p in GV.AUDIO if p.get("src")})
    place, back = build_place(comps)
    boxes, side, raw = {}, {}, {}
    for r, (x, b, a) in place.items():
        f = load_fp(comps[r]["fp"])
        if r in back:
            f = G.mirror_y(f)
        raw[r] = (f, x, b, a)
        boxes[r] = board_box(f, x, b, a)
        side[r] = "B" if r in back else "F"
    keep = keepouts()
    # 貫通の足（ライザーのピン・スピーカーの口）は裏にも出る ⇒ 裏にも立入禁止
    for r in FIXED:
        f, x, b, a = raw[r]
        X, Y = G.bx(x, b)
        for p in find(f, "pad"):
            if str(p[2]) not in ("thru_hole", "np_thru_hole"):
                continue
            q = find1(p, "at")
            dx, dy = G.rot_xy(float(q[1]), float(q[2]), a)
            rr = max(float(v) for v in find1(p, "size")[1:3]) / 2 + 0.3
            cx, cy = X + dx - G.ORG[0], G.BOARD_W - (Y + dy - G.ORG[1])
            keep.append((cx - rr, cy - rr, cx + rr, cy + rr, "B" if side[r] == "F" else "F", None))
    # 検査: 同じ面の重なり・立入禁止・板の縁
    bad = []
    rs = sorted(boxes)
    for i, ra in enumerate(rs):
        for rb in rs[i + 1:]:
            p, q = boxes[ra], boxes[rb]
            if side[ra] == side[rb] and p[0] < q[2] - 1e-6 and q[0] < p[2] - 1e-6 and p[1] < q[3] - 1e-6 and q[1] < p[3] - 1e-6:
                bad.append((ra, rb))
    for ra, rb in bad[:60]:
        print(f"  重なり {ra} ↔ {rb}")
    hit = []
    for r in set(place) - FIXED:
        p = boxes[r]
        for k in keep:
            if k[4] == side[r] and not (k[5] is not None and r in k[5]) and \
                    p[0] < k[2] - 1e-6 and k[0] < p[2] - 1e-6 and p[1] < k[3] - 1e-6 and k[1] < p[3] - 1e-6:
                hit.append((r, tuple(round(v, 2) for v in k[:4]), k[4]))
        if p[0] < EDGE or p[1] < EDGE or p[2] > G.BOARD_L - EDGE or p[3] > G.BOARD_W - EDGE:
            hit.append((r, "板の縁", side[r]))
    for r, k, s in hit[:60]:
        print(f"  立入禁止に入っている {r}（{s}）: {k}")
    area = {"F": 0.0, "B": 0.0}
    for r, p in boxes.items():
        area[side[r]] += (p[2] - p[0]) * (p[3] - p[1])
    print(f"  枠の合計 XIAO 面（F）{area['F']:.0f} mm²・マイク面（B）{area['B']:.0f} mm²（板 {G.BOARD_L * G.BOARD_W:.0f}）")

    # ---- 部品を置く ----
    placed, insts = [], []
    PADS.clear()
    CENTER.clear()
    for r, (x, b, a) in place.items():
        X, Y = G.bx(x, b)
        node, f = G.place_footprint(r, comps[r], X, Y, a, pads, back=r in back)
        placed.append(node)
        collect_pads(node, r)
        pl = []
        for p in find(f, "pad"):
            if not str(p[1]) or str(p[2]) == "np_thru_hole":
                continue
            d = dsn_pad(p)
            d["side"] = "B.Cu" if r in back else "F.Cu"
            pl.append(d)
        insts.append(dict(ref=r, fp=comps[r]["fp"], x=X, y=Y, ang=a, pads=pl))
    # ---- 先に引く線と穴 ----
    TRACKS.clear()
    VIAS.clear()
    prewire(nets)
    n_mv = nudge_vias_off_pins("U102")
    n_drop = prune_dangling()
    hand_wiring()
    n_gnd = gnd_vias()
    print(f"  GND の貫通穴 {n_gnd} 個・浮いた切れ端を {n_drop} 本落とした・ピンに近い写した穴を {n_mv} 個ずらした")
    pre_nets = sorted({t[0] for t in TRACKS} | {v[0] for v in VIAS})
    wiring_items = []
    for net, lay, w, pts in TRACKS:
        for a, b in zip(pts, pts[1:]):
            (xa, ya), (xb, yb) = G.bx(*a), G.bx(*b)
            if f"{xa:.4f},{ya:.4f}" == f"{xb:.4f},{yb:.4f}":
                continue
            wiring_items.append(["segment", ["start", f"{xa:.4f}", f"{ya:.4f}"], ["end", f"{xb:.4f}", f"{yb:.4f}"],
                                 ["width", f"{w:.3f}"], ["locked", "yes"], ["layer", Str(lay)],
                                 ["net", str(nets[net])], ["uuid", Str(G.uid())]])
    for net, x, b in VIAS:
        X, Y = G.bx(x, b)
        wiring_items.append(["via", ["locked", "yes"], ["at", f"{X:.4f}", f"{Y:.4f}"], ["size", f"{VIA[0]}"],
                             ["drill", f"{VIA[1]}"], ["layers", Str("F.Cu"), Str("B.Cu")],
                             ["net", str(nets[net])], ["uuid", Str(G.uid())]])
    print(f"  先に引いた: 線 {len([i for i in wiring_items if i[0] == 'segment'])} 本・穴 {len(VIAS)} 個・ネット {len(pre_nets)} 本")

    doc = ["kicad_pcb", ["version", "20241229"], ["generator", Str("katanori/gen_pcb_audio.py")],
           ["generator_version", Str("9.0")],
           ["general", ["thickness", "1.6"], ["legacy_teardrops", "no"]],
           ["paper", Str("A3")],
           ["layers",
            ["0", Str("F.Cu"), "signal"], ["4", Str("In1.Cu"), "power"], ["6", Str("In2.Cu"), "signal"],
            ["2", Str("B.Cu"), "signal"],
            ["9", Str("F.Adhes"), "user", Str("F.Adhesive")], ["11", Str("B.Adhes"), "user", Str("B.Adhesive")],
            ["13", Str("F.Paste"), "user"], ["15", Str("B.Paste"), "user"],
            ["5", Str("F.SilkS"), "user", Str("F.Silkscreen")], ["7", Str("B.SilkS"), "user", Str("B.Silkscreen")],
            ["1", Str("F.Mask"), "user"], ["3", Str("B.Mask"), "user"],
            ["17", Str("Dwgs.User"), "user", Str("User.Drawings")],
            ["19", Str("Cmts.User"), "user", Str("User.Comments")],
            ["25", Str("Edge.Cuts"), "user"], ["27", Str("Margin"), "user"],
            ["31", Str("F.CrtYd"), "user", Str("F.Courtyard")], ["29", Str("B.CrtYd"), "user", Str("B.Courtyard")],
            ["35", Str("F.Fab"), "user"], ["33", Str("B.Fab"), "user"]],
           ["setup",
            # 積層は Voice PE と同じ（プリプレグ 0.1 ＋ コア 1.24 ＋ プリプレグ 0.1）・1.6mm（docs/VOICE-BOARD.md 6 章）
            ["stackup",
             ["layer", Str("F.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 1"), ["type", Str("prepreg")], ["thickness", "0.1"], ["material", Str("FR4")]],
             ["layer", Str("In1.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 2"), ["type", Str("core")], ["thickness", "1.24"], ["material", Str("FR4")]],
             ["layer", Str("In2.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 3"), ["type", Str("prepreg")], ["thickness", "0.1"], ["material", Str("FR4")]],
             ["layer", Str("B.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["copper_finish", Str("None")], ["dielectric_constraints", "no"]],
            ["pad_to_mask_clearance", "0"]],
           ["net", "0", Str("")]]
    for nm, num in sorted(nets.items(), key=lambda kv: kv[1]):
        doc.append(["net", str(num), Str(nm)])
    poly = ["polygon", ["pts"] + [["xy", f"{G.bx(*q)[0]:.3f}", f"{G.bx(*q)[1]:.3f}"] for q in outline_poly()]]
    zones = [["zone", ["net", str(nets["GND"])], ["net_name", Str("GND")], ["layer", Str(lay)],
              ["uuid", Str(G.uid())], ["name", Str("GND")], ["hatch", "edge", "0.5"],
              ["connect_pads", "yes", ["clearance", "0.2"]], ["min_thickness", "0.2"],
              ["filled_areas_thickness", "no"],
              ["fill", "yes", ["thermal_gap", "0.2"], ["thermal_bridge_width", "0.4"],
               ["island_removal_mode", "2"], ["island_area_min", "8"]], poly] for lay in ("F.Cu", "In1.Cu", "B.Cu")]
    # 🔴 内層 2 に GND のベタを敷くと、XU316 の下などで穴の打てない浮いた島が 8 つ残った（2026-09-16）。内層 2 はベタ無し。
    #    表と裏の 8mm² 未満の島（手の線の間の細長い銅）は消す（浮いた銅を残さない）
    isl = ["polygon", ["pts"] + [["xy", f"{G.bx(*q)[0]:.3f}", f"{G.bx(*q)[1]:.3f}"] for q in gnda_island()]]
    zones += [["zone", ["net", str(nets["GNDA"])], ["net_name", Str("GNDA")], ["layer", Str(lay)],
               ["uuid", Str(G.uid())], ["name", Str("GNDA")], ["hatch", "edge", "0.5"], ["priority", "1"],
               ["connect_pads", "yes", ["clearance", "0.2"]], ["min_thickness", "0.2"],
               ["filled_areas_thickness", "no"],
               ["fill", "yes", ["thermal_gap", "0.2"], ["thermal_bridge_width", "0.4"],
                ["island_removal_mode", "2"], ["island_area_min", "3"]], isl] for lay in ("F.Cu", "In1.Cu")]
    doc += outline() + G.mounting_holes() + placed + wiring_items + zones
    (G.OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(doc) + "\n", encoding="utf-8")
    pro = G.OUT / f"{NAME}.kicad_pro"
    d = json.loads(pro.read_text(encoding="utf-8"))
    d.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {}).update(
        {"min_clearance": PAD_PAD_MIN, "min_track_width": 0.15, "min_via_diameter": VIA[0],
         "min_through_hole_diameter": VIA[1], "min_via_annular_width": 0.1, "min_hole_clearance": 0.2,
         "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3, "solder_mask_min_width": 0.1})
    # ⚠ ネットクラスの間隔はパッドどうしにも効き、kicad_dru の条件付き規則が当たらない組ではこちらが使われる
    d.setdefault("net_settings", {}).setdefault("classes", [{"name": "Default"}])[0].update(
        {"clearance": PAD_PAD_MIN, "track_width": TRACK, "via_diameter": VIA[0], "via_drill": VIA[1]})
    pro.write_text(json.dumps(d, indent=2), encoding="utf-8")
    NL = chr(10)
    (G.OUT / f"{NAME}.kicad_dru").write_text(NL.join([
        "(version 1)",
        f'(rule "track_zone_{CLEAR}"',
        f"  (constraint clearance (min {CLEAR}mm))",
        "  (condition \"A.Type != 'Pad' || B.Type != 'Pad'\"))",
        # マイク面は Voice PE の線（隙間 0.125 の設計）を写しているので 0.125。JLCPCB の 4 層は 0.09 まで作れる
        '(rule "b_side_0.125"',
        "  (layer B.Cu)",
        "  (constraint clearance (min 0.125mm))",
        "  (condition \"A.Type != 'Pad' || B.Type != 'Pad'\"))", ""]), encoding="utf-8")
    print(f"{len(placed)} 部品・ネット {len(nets)} 本 → {G.OUT / (NAME + '.kicad_pcb')}")
    # ---- DSN（信号だけ。GND・GNDA は渡さない。In1 は見せない） ----
    bnd = [G.bx(*q) for q in outline_poly()]
    ko = []
    for mx, my in G.MOUNT:
        X, Y = G.bx(mx, my)
        rr = G.MOUNT_D / 2 + G.MOUNT_KEEP
        ko.append((X - rr, Y - rr, X + rr, Y + rr))
    for it in insts:
        f = raw[it["ref"]][0]
        for q in find(f, "pad"):
            if str(q[2]) != "np_thru_hole":
                continue
            dd = G.fp_pad(q)
            dx, dy = G.rot_xy(dd["at"][0], dd["at"][1], it["ang"])
            rr = max(dd["size"]) / 2 + 0.35
            ko.append((it["x"] + dx - rr, it["y"] + dy - rr, it["x"] + dx + rr, it["y"] + dy + rr))
    for net, x, b in VIAS:
        if net in ("GND", "GNDA"):
            X, Y = G.bx(x, b)
            rr = VIA[0] / 2 + CLEAR
            ko.append((X - rr, Y - rr, X + rr, Y + rr))
    netpins = {}
    for (ref, pin), net in pads.items():
        if net in ("GND", "GNDA"):
            continue
        netpins.setdefault(net, []).append((ref, pin))
    np_, nn = dsn.write_dsn(G.OUT / f"{NAME}.dsn", NAME, insts, netpins, bnd, ko, copper=ROUTE_COPPER,
                           via=VIA, track_um=round(TRACK * 10000), clear_um=round(CLEAR * 10000))
    # 先に引いた線と穴を protect（自動配線が動かさない）で渡す
    vianame = f"Via[0-{len(ROUTE_COPPER) - 1}]_{round(VIA[0] * 1000)}:{round(VIA[1] * 1000)}_um"
    rows = []
    for net, lay, w, pts in TRACKS:
        if net in ("GND", "GNDA") or lay not in ROUTE_COPPER:
            continue
        for a, b in zip(pts, pts[1:]):
            (xa, ya), (xb, yb) = G.bx(*a), G.bx(*b)
            rows.append(f'    (wire (path {lay} {round(w * dsn.SCALE)} {dsn._x(xa)} {dsn._y(ya)} {dsn._x(xb)} {dsn._y(yb)})'
                        f' (net "{net}") (type protect))')
    for net, x, b in VIAS:
        if net in ("GND", "GNDA"):
            continue
        X, Y = G.bx(x, b)
        rows.append(f'    (via {vianame} {dsn._x(X)} {dsn._y(Y)} (net "{net}") (type protect))')
    txt = (G.OUT / f"{NAME}.dsn").read_text(encoding="utf-8")
    txt = txt.replace("  (wiring\n  )", "  (wiring\n" + "\n".join(rows) + "\n  )")
    # 電源のネットは線幅 POWER_W の組にする（kicad_default から外して power の組に入れる）
    pw = sorted(n for n in netpins if n in POWER_NETS and len(netpins[n]) > 1)
    pw2 = sorted(n for n in netpins if n in POWER2_NETS and len(netpins[n]) > 1)
    i0 = txt.index('    (class kicad_default "" ')
    i1 = txt.index("\n", i0)
    line = txt[i0:i1]
    for n in pw + pw2:
        line = line.replace(f' "{n}"', "")
    txt = txt[:i0] + line + txt[i1:]
    cls = ""
    for name, ns, w in (("power", pw, POWER_W), ("power2", pw2, POWER2_W)):
        cls += (f'    (class {name} "" ' + " ".join(f'"{n}"' for n in ns) + "\n"
                f"      (circuit (use_via {vianame}))\n"
                f"      (rule (width {round(w * dsn.SCALE)}) (clearance {round(CLEAR * dsn.SCALE)}))\n    )\n")
    txt = txt.replace("  )\n  (wiring", cls + "  )\n  (wiring", 1)
    # XU316 の周り（ピンの列から 2mm）は、自動配線に穴を打たせない（🔴 2026-09-16 空けた道を穴で埋めて 7・9 番が出られなかった）
    ux, ub = CENTER["U102"]
    vk = ""
    for i, (x0, b0, x1, b1) in enumerate(((ux - 5.6, ub - 5.6, ux - 3.6, ub + 5.6), (ux + 3.6, ub - 5.6, ux + 5.6, ub + 5.6),
                                          (ux - 5.6, ub - 5.6, ux + 5.6, ub - 3.6), (ux - 5.6, ub + 3.6, ux + 5.6, ub + 5.6))):
        (X0, Y0), (X1, Y1) = G.bx(x0, b1), G.bx(x1, b0)
        vk += f'    (via_keepout "xu316_{i}" (rect F.Cu {dsn._x(X0)} {dsn._y(Y1)} {dsn._x(X1)} {dsn._y(Y0)}))\n'
    mk = ""
    for ref in ("U104", "U105"):
        mx, mb = CENTER[ref]
        (X0, Y0), (X1, Y1) = G.bx(mx - 2.2, mb + 2.6), G.bx(mx + 2.2, mb - 2.6)
        mk += f'    (keepout "mic_{ref}" (rect B.Cu {dsn._x(X0)} {dsn._y(Y1)} {dsn._x(X1)} {dsn._y(Y0)}))\n'
    txt = txt.replace("  )\n  (placement", mk + vk + "  )\n  (placement", 1)
    (G.OUT / f"{NAME}.dsn").write_text(txt, encoding="utf-8")
    print(f"自動配線へ: {np_} 部品・{nn} ネット（GND・GNDA を除く）・固定の線 {len(rows)} 本 → {G.OUT / (NAME + '.dsn')}")
    if bad or hit:
        sys.exit(f"重なり {len(bad)} 組・立入禁止 {len(hit)} 件")


def stitch_more():
    """route.stitch（3.2mm 格子）で残った GND のベタの島を減らすため、2.0mm 格子でも縫う（φ0.45/0.2）。"""
    import check_pcb
    pcb = kisym.parse((G.OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    allobj = check_pcb.shapes(pcb)
    nets = {str(e[2]): e[1] for e in find(pcb, "net")}
    import route as R
    put = []
    PITCH, CLR = 2.0, 0.45
    for i in range(int((G.BOARD_L - 2) / PITCH) + 1):
        for j in range(int((G.BOARD_W - 2) / PITCH) + 1):
            u, v = 1.0 + i * PITCH, 1.0 + j * PITCH
            X, Y = G.bx(u, v)
            me = ("circle", X, Y, VIA[0] / 2)
            if all(check_pcb.gap(me, g) > CLR for _, _, g in allobj):
                put.append((X, Y))
    body = list(pcb)
    for X, Y in put:
        body.append(["via", ["at", f"{X:.4f}", f"{Y:.4f}"], ["size", f"{VIA[0]}"], ["drill", f"{VIA[1]}"],
                     ["layers", Str("F.Cu"), Str("B.Cu")], ["net", nets["GND"]], ["uuid", Str(R.uid())]])
    (G.OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(body) + "\n", encoding="utf-8")
    print(f"  GND を縫うビアをさらに {len(put)} 個打った（格子 {PITCH}mm）")


# 手で引き直すため捨てる自動配線: (ネット, 箱 (x0,b0,x1,b1)) — 箱に端が入る線・穴を捨てる。箱が None なら全部
DROP = [("QSPI_CS_N", None), ("QSPI_D0", None), ("QSPI_D1", None), ("QSPI_D2", None), ("QSPI_D3", None), ("QSPI_CLK", None),
        ("ESP_TXD", None), ("ESP_RXD", None), ("ESP_EN", (23.0, 0, 90, 40)), ("ESP_BOOT", (42.5, 0, 90, 40)),
        ("VDDIO", (42.0, 17.0, 50.3, 29.0)), ("I2S_LRCK", (44.5, 16.5, 53.0, 23.5)),
        ("N_U102_X0D36", None), ("N_U108_LDO__SELECT", None), ("TMS", None), ("RST_N", None), ("TDO", None), ("TDI", (50.5, 4.0, 53.0, 6.0)),
        ("TCK", (51.0, 3.0, 55.0, 14.5)), ("V18", (48.0, 3.5, 54.2, 12.5)), ("V18", (53.0, 11.85, 57.8, 12.8)),
        ("N_U102_X1D22", None), ("VDDIO", (58.0, 17.5, 59.0, 18.6))]


def _dropped(net, e):
    for n, box in DROP:
        if n != net:
            continue
        if box is None:
            return True
        pts = [find1(e, "at")] if e[0] == "via" else [find1(e, "start"), find1(e, "end")]
        for q in pts:
            x, b = float(q[1]) - G.ORG[0], G.BOARD_W - (float(q[2]) - G.ORG[1])
            if box[0] <= x <= box[2] and box[1] <= b <= box[3]:
                return True
    return False


# KiCad の Python でベタを塗り、穴もパッドも無い島（浮いた銅）を集める（図面の座標の多角形）
KI_ISLANDS = r"""
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); pcbnew.ZONE_FILLER(b).Fill(b.Zones())
vias = [(t.GetPosition(), t.GetNetname()) for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
pads = [(q.GetPosition(), q.GetNetname(), q) for fp in b.GetFootprints() for q in fp.Pads()]
out = []
for z in b.Zones():
    net = z.GetNetname()
    for lay in z.GetLayerSet().Seq():
        poly = z.GetFilledPolysList(lay)
        for i in range(poly.OutlineCount()):
            o = poly.Outline(i)
            if any(n == net and o.PointInside(pos) for pos, n in vias):
                continue
            if any(n == net and q.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and o.PointInside(pos) for pos, n, q in pads):
                continue
            out.append({"net": net, "layer": b.GetLayerName(lay), "area": o.Area() / 1e12,
                        "pts": [[o.CPoint(k).x / 1e6, o.CPoint(k).y / 1e6] for k in range(o.PointCount())]})
json.dump(out, open(sys.argv[2], "w"))
"""


def _inside(x, y, pts):
    ok = False
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            ok = not ok
    return ok


def stitch_islands(rounds=2):
    """縫いの格子が入らなかった GND/GNDA のベタの島（穴もパッドも無い浮いた銅）に、島の中の空いた所へ穴を 1 つずつ打つ。
    🔴 2026-09-16: 格子 2.0mm でも、線に細かく切られた島（XU316 の周りなど）には穴が入らず、DRC の unconnected が 8 残った。"""
    import check_pcb
    import route as R
    kipy = pathlib.Path(R.CLI).parent / "python.exe"
    pcb_path = G.OUT / f"{NAME}.kicad_pcb"
    total = 0
    for _ in range(rounds):
        js = G.OUT / "islands.json"
        subprocess.run([str(kipy), "-c", KI_ISLANDS, str(pcb_path), str(js)], check=True, capture_output=True)
        islands = json.loads(js.read_text(encoding="utf-8"))
        js.unlink()
        if not islands:
            break
        pcb = kisym.parse(pcb_path.read_text(encoding="utf-8"))[0]
        allobj = check_pcb.shapes(pcb)
        nets = {str(e[2]): e[1] for e in find(pcb, "net")}
        vias = [(float(find1(v, "at")[1]), float(find1(v, "at")[2])) for v in find(pcb, "via")]
        body = list(pcb)
        put = 0
        for isl in islands:
            pts = [tuple(q) for q in isl["pts"]]
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            best = None
            x = min(xs)
            while x <= max(xs) and best is None:
                y = min(ys)
                while y <= max(ys):
                    if _inside(x, y, pts):
                        me = ("circle", x, y, VIA[0] / 2)
                        gap = min((check_pcb.gap(me, g) for nm, _, g in allobj if nm != isl["net"]), default=9)
                        dv = min((math.hypot(x - vx, y - vy) for vx, vy in vias), default=9)
                        if gap > 0.16 and dv > 0.6:
                            best = (x, y)
                            break
                    y += 0.25
                x += 0.25
            if best is None:
                print(f"  島に穴が打てない: {isl['net']} {isl['layer']} {isl['area']:.1f}mm² "
                      f"x {min(xs) - G.ORG[0]:.1f}-{max(xs) - G.ORG[0]:.1f} b {G.BOARD_W - (max(ys) - G.ORG[1]):.1f}-{G.BOARD_W - (min(ys) - G.ORG[1]):.1f}")
                continue
            X, Y = best
            body.append(["via", ["at", f"{X:.4f}", f"{Y:.4f}"], ["size", f"{VIA[0]}"], ["drill", f"{VIA[1]}"],
                         ["layers", Str("F.Cu"), Str("B.Cu")], ["net", nets[isl["net"]]], ["uuid", Str(R.uid())]])
            vias.append((X, Y))
            allobj.append((isl["net"], "F.Cu", ("circle", X, Y, VIA[0] / 2)))
            put += 1
        pcb_path.write_text(kisym.dump(body) + chr(10), encoding="utf-8")
        total += put
        print(f"  浮いた島 {len(islands)} 個に穴を {put} 個打った")
        if put == 0:
            break
    return total


def _old_wiring(targets):
    """今の板から、自動配線の線と穴（locked でない物）のうち、targets 以外のネットの物を集める（DROP の物は捨てる）。"""
    pcb = kisym.parse((G.OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    names = {str(e[1]): str(e[2]) for e in find(pcb, "net")}
    keep = []
    for e in pcb:
        if isinstance(e, list) and e[0] in ("segment", "via") and not find1(e, "locked"):
            net = names.get(str(find1(e, "net")[1]), "")
            if net and net not in targets and not (e[0] == "via" and (net == "GND" or float(find1(e, "size")[1]) >= 0.59)) and not _dropped(net, e):
                keep.append((net, e))
    return keep


def route():
    """Freerouting（信号だけ）→ SES を取り込む（locked の線と穴は残す）→ GND の縫い → DRC。
    --partial NET,NET,… : そのネットだけ引き直す。他の自動配線の結果は protect で渡して残す。"""
    if "--board" not in sys.argv:
        sys.argv += ["--board", NAME]
    import route as R
    targets = set()
    old = []
    if "--keep" in sys.argv:
        # 🔴 自動配線を回さない。今の板の自動配線（DROP 以外）を残し、手の線を足して DRC（2026-09-16 手で引く段階）
        old = _old_wiring(set())
        for net, e in old:
            if e[0] == "segment":
                a, b = find1(e, "start"), find1(e, "end")
                OLD_SEGS.append((float(a[1]) - G.ORG[0], G.BOARD_W - (float(a[2]) - G.ORG[1]),
                                 float(b[1]) - G.ORG[0], G.BOARD_W - (float(b[2]) - G.ORG[1]), float(find1(e, "width")[1])))
            else:
                at = find1(e, "at")
                OLD_VIAS.append((float(at[1]) - G.ORG[0], G.BOARD_W - (float(at[2]) - G.ORG[1])))
        build()
        pcb = kisym.parse((G.OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
        body = [e for e in pcb if not (isinstance(e, list) and e[0] in ("segment", "via") and not find1(e, "locked"))]
        for net, e in old:
            body.append([x for x in e if not (isinstance(x, list) and x[0] == "uuid")] + [["uuid", Str(R.uid())]])
        (G.OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(body) + chr(10), encoding="utf-8")
        print(f"  自動配線は回さず、残す自動配線 {len(old)} 個を戻した")
        R.stitch()
        stitch_more()
        stitch_islands()
        return R.drc()
    if "--partial" in sys.argv:
        targets = set(sys.argv[sys.argv.index("--partial") + 1].split(","))
        old = _old_wiring(targets)
        build()
        vianame = f"Via[0-{len(ROUTE_COPPER) - 1}]_{round(VIA[0] * 1000)}:{round(VIA[1] * 1000)}_um"
        rows = []
        for net, e in old:
            if e[0] == "segment":
                a, b = find1(e, "start"), find1(e, "end")
                lay = str(find1(e, "layer")[1])
                if lay not in ROUTE_COPPER:
                    continue
                w = float(find1(e, "width")[1])
                rows.append(f'    (wire (path {lay} {round(w * dsn.SCALE)} {dsn._x(float(a[1]))} {dsn._y(float(a[2]))} '
                            f'{dsn._x(float(b[1]))} {dsn._y(float(b[2]))}) (net "{net}") (type protect))')
            else:
                at = find1(e, "at")
                rows.append(f'    (via {vianame} {dsn._x(float(at[1]))} {dsn._y(float(at[2]))} (net "{net}") (type protect))')
        dpath = G.OUT / f"{NAME}.dsn"
        txt = dpath.read_text(encoding="utf-8")
        txt = txt.replace("\n  )\n)\n", "\n" + "\n".join(rows) + "\n  )\n)\n", 1)
        dpath.write_text(txt, encoding="utf-8")
        print(f"  引き直すネット {len(targets)} 本。残す自動配線 {len(old)} 個を protect で渡した")
    if "--ses" not in sys.argv:
        R.run_freerouting()
    # 🔴 Freerouting 2.4.1 は名前の無い (net の塊を 1 つ書くことがあり、dsn.read_ses が落ちる（2026-09-16）。
    #    名前の無い塊には仮の名前を付けて読み、その線は捨てる
    ses = G.OUT / f"{NAME}.ses"
    txt = re.sub(r"\(net\s+\(", '(net "__noname__" (', ses.read_text(encoding="utf-8"))
    # 🔴 Freerouting は protect で渡した線と穴を SES にそのまま返す。取り込むと、板に書いた手の線（locked）と二重になり、
    #    手の線を直した後は古い形が SES から戻ってくる（2026-09-16）。protect の物は捨てる
    txt = re.sub(r"\(wire\s*\(path[^()]*\)\s*\(type protect\)\s*\)", "", txt)
    txt = re.sub(r"\(via [^()]*\(type protect\)\s*\)", "", txt)
    ses.write_text(txt, encoding="utf-8")
    pcb = kisym.parse((G.OUT / f"{NAME}.kicad_pcb").read_text(encoding="utf-8"))[0]
    nets = {str(e[2]): e[1] for e in find(pcb, "net")}
    refs = {}
    for f in find(pcb, "footprint"):
        at = find1(f, "at")
        ref = [p for p in find(f, "property") if str(p[1]) == "Reference"]
        if ref:
            refs[str(ref[0][2])] = (float(at[1]), float(at[2]))
    wires, vias = dsn.read_ses(G.OUT / f"{NAME}.ses", refs)
    body = [e for e in pcb if not (isinstance(e, list) and e[0] in ("segment", "via") and not find1(e, "locked"))]
    n_seg = 0
    for net, layer, w, pts in wires:
        if net == "__noname__":
            continue
        if net not in nets:
            sys.exit(f"SES のネット '{net}' が基板に無い")
        for a, b in zip(pts, pts[1:]):
            sa, sb = (f"{a[0]:.4f}", f"{a[1]:.4f}"), (f"{b[0]:.4f}", f"{b[1]:.4f}")
            if sa == sb:
                continue
            body.append(["segment", ["start", sa[0], sa[1]], ["end", sb[0], sb[1]], ["width", f"{max(w, 0.15):.3f}"],
                         ["layer", Str(layer)], ["net", nets[net]], ["uuid", Str(R.uid())]])
            n_seg += 1
    for net, x, y in vias:
        if net == "__noname__":
            continue
        body.append(["via", ["at", f"{x:.4f}", f"{y:.4f}"], ["size", f"{VIA[0]}"], ["drill", f"{VIA[1]}"],
                     ["layers", Str("F.Cu"), Str("B.Cu")], ["net", nets[net]], ["uuid", Str(R.uid())]])
    for net, e in old:
        e2 = [x for x in e if not (isinstance(x, list) and x[0] == "uuid")] + [["uuid", Str(R.uid())]]
        body.append(e2)
    (G.OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(body) + "\n", encoding="utf-8")
    print(f"  自動配線から: 線 {n_seg} 本・穴 {len(vias)} 個を入れた（先に引いた物 {len(old)} 個と、固定の線は残した）")
    R.stitch()
    stitch_more()
    stitch_islands()
    return R.drc()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--route" in sys.argv:
        route()
    else:
        build()
