# -*- coding: utf-8 -*-
"""katanori61.kicad_pcb（部品を置いただけの板・配線はまだ）を作る。

  python gen_pcb.py

つながりは回路図から kicad-cli が書き出したネットリストを読む（手で写さない）。
ハブ側の部品と口は、今のユニバーサル基板の穴の座標（hub_ports.py / relay_board.html）に置くので、
筐体の側の線の道は変えなくてよい。電源側は私が並べた（下の PLACE）。

パネル（1 枚で発注して割る）:
    ハブ  74 × 52   … 左上 (0, 0)
    電源  36 × 28   … 左下 (0, 54)。間は 2mm 空け、ミシン目のタブ 2 本でつなぐ
"""

import math
import pathlib
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "parts"))
import kisym  # noqa: E402
from kisym import Str, find, find1  # noqa: E402
import hub_ports  # noqa: E402
import dsn  # noqa: E402

from kicad_paths import CLI, FPDIR  # noqa: E402
OUT = HERE / "katanori61"
NAME = "katanori61"

# ---- 電源の道の線幅（2026-09-16）----
# ⭐ これを入れるまで、電池を流す線まで自動配線の既定 0.2mm のままだった。幅を決めた人がいなかった。
#   実測（docs/POWER.md 1886 行）: 放電 300〜325mA・2 秒の最大 355〜365mA／充電 505〜560mA。
#   充電の上限は PROG1 = R16 1.0kΩ で 1A。
#   0.2mm は 2.457mΩ/mm・IPC の許容 0.74A（外層 1oz・ΔT10℃）で、電池の道 88.4mm が 217mΩ になる。
#   0.8mm にすると 0.614mΩ/mm・許容 2.03A、同じ道が 54mΩ ＝ 最大放電で 20mV・充電で 30mV に収まる。
#   1.0mm との差は 6mV しかなく、2 層のこの密度で引けるほうを採った。
# ⚠ BATP と VLIPO は**シャントのセンス線と同じネット**なので、この幅はセンス線にも掛かる。
#   センス線は別に細い線で先に引いて protect で守る（ステップ 2）。
#
# 2 段に分ける。⭐ 最初 7 本を全部 0.8 にしたら未接続が 6 本出た（2026-09-16）。
#   VBUS・V5・VSYS は U2 の QFN-20（0.5mm ピッチ）・U1 の VQFN-16・J13 の USB-C という
#   細かいパッドに何本も降りる配り物で、太いまま通すと U3 まわりの SCL/SDA/V33 と
#   R16 の PROG1 を押し出した。**直列に電流が通る道だけ**を太くする。
#   BAT_NETS  … 電池 → 逆接保護 → シャント → 充電 IC の一本道。ここが 88.4mm ＝ 217mΩ の本体
#   POWER_NETS… 配り物。0.4mm で 1.229mΩ/mm・IPC 許容 1.23A（外層 1oz・ΔT10℃）あれば足りる
# ⭐ 2026-09-16: 並べ直して電池の道が 107mm → 12mm になったので、0.8 で押し通す必要が消えた。
#   0.6mm で 0.819mΩ/mm・IPC 許容 1.65A。道が 12mm なら 10mΩ ＝ 充電上限 1A でも 10mV。
#   0.8 のままだと U2（QFN-20・0.5mm ピッチ）の 14〜16 番から VLIPO が逃げられず未接続が出る。
# ---- 4 層（2026-09-17）----
# 2 層では U2（QFN-20・4×4）の 20 ピンが出入りできず、部品を動かすたびに別のネットが切れた
# （L1 の枠と U2 の枠の間が 0.4mm）。JLCPCB の見積もりで 82×38・5 枚が 2 層 $4.00 / 4 層 $7.00。
# In1 を GND の面にすると GND の 47 パッドが配線から消え、In2 が 3 枚目の配線層になる。
# ⚠ 内層を DSN の plane にすると Freerouting が落ちる（drillShapes is null・docs/VOICE-BOARD.md 10 章）。
#   ⇒ **plane は使わない。**自動配線には F.Cu / In2.Cu / B.Cu の 3 層だけ見せ、In1 は KiCad のベタで敷く。
COPPER = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
ROUTE_COPPER = ["F.Cu", "In2.Cu", "B.Cu"]   # In1 は GND の面なので自動配線に見せない
# 貫通穴は 2 層のときと同じ 0.6/0.3。統合基板の 0.45/0.2 は XU316 の細ピッチのために
# 落とした値で、この板には要らない。0.2 の穴はこの板の規則（min_through_hole_diameter 0.3・
# min_via_annular_width 0.13）に掛かり、DRC が 69 件ずつエラーを出した（2026-09-17）。
VIA4 = (0.6, 0.3)

BAT_NETS = {"BATRAW", "BATP", "VLIPO"}
BAT_W = 0.6
#   ⚠ VBUS はこの組に**入れない**。U2（QFN-20・0.5mm ピッチ）に VBUS のパッドが 6 本あり、
#     0.4mm では辺から逃がせず、試すたびに違うピンが浮いた（9 番 → 3 番と VPCC・2026-09-16）。
#     得も小さい: 幹（J13 → U2）は 0.2mm で 141mΩ ＝ 充電 560mA で 85mV。5V 側なので効かない。
POWER_NETS = {"VSYS", "SW", "V5"}
POWER_W = 0.4

# ---- 先に手で引く線（2026-09-16）----
# 自動配線に任せられない所だけを、こちらで引いて固定する。
#   板（.kicad_pcb）へは locked を付けて書き、DSN へは (type protect) で渡す。
#   自動配線はこの線を動かさず、避けて引く。SES で返ってくる protect の写しは route.py が捨てる。
# ⚠ 座標は **KiCad の板の座標そのまま**（bx() を通した後の値）。パッドの中心に端を合わせること。
PRE_TRACKS = []   # ケルビンは kelvin_tracks() が置いてある物から作る
_KELVIN = []      # build() が入れる
_n = [0]


def uid():
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/pcb/{_n[0]}"))


# ---- 板の寸法（v6.1・2026-09-14）----
# 座標は **板の左前が原点・X 右・Y 後ろ**。図面（KiCad）の座標へは bx() で移す。
# ⚠ ここは筐体側（別セッション）が決めた数字で、こちらでは動かさない。1 か所に置くため
#    v61_board.py（この板の「動かせない物」の一覧）から読む。
sys.path.insert(0, str(HERE))
import v61_board as VB

BOARD_L, BOARD_W = VB.L, VB.W                      # 82.024 × 37.4
# 後ろの縁の欠き。x0, x1, この y から後ろの縁まで。
# ⭐ 2026-09-16 夕: 数を 2 個に決め打ちしていたのをやめた（欠きが 1 個になったため）
NOTCHES = [(n[0], n[2], n[1]) for n in VB.NOTCHES]
MOUNT = list(VB.HOLES)            # M2 × 4（床から立つ柱 φ7 の上）
MOUNT_D = VB.HOLE_D               # φ2.2
MOUNT_KEEP = 0.5                  # 穴のまわりに **銅** を置かせない幅
# 🔒 2026-09-14 筐体側: ねじは板の上から M2×6・ナットは柱の中の横差し。板の上に出るのは頭だけ
NUT_R = 4.62 / 2 + 0.25
POSTS = []                        # v6.1 は板を貫く柱が無い（後ろの隅の 2 本は上の欠きになった）
POST_KEEP = 0.5
# 🔴 つまみの軸 φ7 が真上から降りる。ここに置いてよいのは AS5600（U4）だけ
KEEPOUT_MAGNET = (VB.SHAFT[0], VB.SHAFT[1], VB.SHAFT[0] + VB.SHAFT[2], VB.SHAFT[1] + VB.SHAFT[3])
# 電池は板の**下**（板の裏まで 6.0）。表の部品の背には効かない。裏に置けるのはこの外の帯だけ
BATTERY = (16.05, 0.0, 66.05, 31.4)
ORG = (40.0, 40.0)                # 図面の上での板の左上
# 筐体（箱）の座標と板の座標のずれ。**箱 = 板 + BOX**（2026-09-14 筐体側）
BOX = VB.ORG_W


def outline_pts():
    """外形の頂点（板の座標・反時計回り）。後ろの縁に欠きが 0 個以上ある。

    ⭐ 2026-09-16 夕に一般化した。それまで「後ろの両隅に必ず 2 個」と決め打ちで、
    欠きが 1 個になったら書き換えるしかなかった。右の縁から左へ回りながら、
    欠きを右から順に落としていく。
    """
    pts = [(0, 0), (BOARD_L, 0), (BOARD_L, BOARD_W)]
    left_open = False
    for x0, x1, yf in sorted(NOTCHES, key=lambda n: -n[1]):
        pts += [(x1, BOARD_W), (x1, yf), (x0, yf)]
        left_open = x0 <= 1e-9
        if not left_open:
            pts += [(x0, BOARD_W)]
    if not left_open:
        pts += [(0, BOARD_W)]
    return pts


def bx(x, y):
    """板の座標（左下が原点・Y 上向き）→ 図面の座標（Y 下向き）。"""
    return (ORG[0] + x, ORG[1] + (BOARD_W - y))


# ---- 足形の差し替え（KiCad の標準に無い物は katanori.pretty に作る） ----
LOCAL = HERE / "katanori.pretty"
FP_OVERRIDE = {
    # 🔒 2026-09-12 リレーは表面実装の Omron G6S-2F へ替えたので、自作の足形は要らなくなった
    #    （KiCad 標準の Relay_SMD:Relay_DPDT_Omron_G6S-2F を使う）。
    # ⭐ 2026-09-17 🔒 ユーザー「1.3 以下に戻してレジンのハッチは口の周りを掘るしかないね」:
    #   **素の足形（シェルの足 4 本）へ戻した**。前寄りの足はパッドの外縁が口の面から 1.800 後ろに
    #   あるので、胴の出が 1.800 を超えると板からはみ出す。v6 は 3.0 出していたので足 2 本を省いた
    #   自作版（katanori:…_NoFrontLegs）を使っていたが、v6.1 の出は 1.3 なのでパッドの外縁が
    #   板の縁の 0.470 内側に収まる。抜き挿しの力は 4 本で受ける。
    "J13": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
}


# ---- 置き場所（板の座標・(x, y, 角度)。角度は KiCad の回し方に合わせて後で検算する）----

def pwr(x, y, ang=0):
    """旧・電源板（40 × 32・左上原点・y は下向き）の並びを 90° 回して電池の影へ入れる。

    旧板で自動配線が通った相対の並びをそのまま持ち込むための写像で、ここで新しく並べ直してはいない。
      新 X = 1.0 + 旧 y × 1.13 （実際に使う 1.7〜28.5 → 2.9〜33.2）
      新 Y = 25.5 + 旧 x × 1.32 （実際に使う 4〜36.5 → 30.8〜73.7）

    🔴 2026-09-13 に X を詰めて Y へ伸ばした。板の右（X 25〜35）を **口のプラグの
    通り道の車線**として空けるため。OLED の柱が上の縁の枠を奪って、PH 4 ピンが右の帯へ
    回り、その通り道が電池の影を横切ることになった。

    🔴 倍率は 2026-09-13 に足した。旧板（40 × 32 ＝ 1280mm²）の詰め方のまま電池の影
    （35 × 50 ＝ 1750mm²）へ入れていて、余っている面積を使っていなかった。そのせいで
    自動配線が 2 本残った（STAT2 と EN）。部品の大きさは変わらないので、広げた分だけ隙間が増える。
    """
    return (1.0 + y * 1.13, 25.5 + x * 1.32, (ang + 90) % 360)


PLACE_V6 = {
    # ======== 電池の影（X 0〜35・Y 25〜75・天井 4.4）========
    # 電源・充電・電流計。いちばん背が高いのがインダクタの 1.8 なので 4.4 に楽に入る。
    # 🔴 USB-C（J13）・電池の PH（J10）はここへ入れない（背 3.16 と 4.8 で、口が板の外を向く）
    # 🔴 CC の引き下げ 2 本は **USB-C の足元**に置く。旧電源板の並びをそのまま写したら
    #    J13 から 40mm 離れて CC2 が 1 本つながらなかった（2026-09-13）
    "R44": (27.0, 71.0, 0), "R45": (23.5, 71.0, 0),
    "C8": pwr(12.0, 4.0), "C7": pwr(16.0, 4.0),
    "U2": pwr(12.0, 9.5),
    "R6": pwr(4.0, 17.0, 90), "R7": pwr(4.0, 20.0, 90),
    # 🔴 2026-09-14: R16 が 18.0 のままだと PROG1 が 1 本つながらない（自動配線が残す）
    "R16": pwr(9.0, 19.6),
    "R17": pwr(12.5, 18.0),
    "R15": pwr(16.0, 18.0),
    "LED4": (21.5, 42.5, 90), "R8": (17.5, 47.0, 90),
    "LED3": (13.5, 52.0, 90), "R14": (17.5, 52.0, 90),
    "R41": pwr(13.0, 28.5),
    # 🔴 この 6 つは pwr() のままだと J2 と J4 のプラグの通り道
    #    （X 24.9〜34.9・Y 43.5〜62.3）に落ちるので、左へ寄せて手で置く
    "U3": (9.0, 47.0, 90), "C41": (13.5, 47.0, 90),
    "R42": (9.0, 52.0, 90), "R43": pwr(33.5, 28.5),
    "U1": pwr(28.0, 7.0), "L1": pwr(21.0, 6.0),
    "C1": pwr(19.5, 11.5), "C4": pwr(23.0, 11.5),
    "C2": pwr(26.5, 12.0, 90), "C6": pwr(33.5, 13.0, 90), "C9": pwr(36.5, 13.0, 90),
    "R3": pwr(30.5, 13.0, 90), "R4": pwr(30.5, 17.0, 90),
    "R1": pwr(19.5, 15.5), "R2": pwr(23.2, 15.5),
    # R13（EN の引き上げ）は J2 のプラグの通り道（X 0.5〜11.4・Y 62〜73）に入るので外へ出す
    "R13": (20.0, 68.0, 90),
    "Q1": (21.0, 57.5, 90), "R20": pwr(26.0, 20.0), "LED1": pwr(29.5, 20.0),
    "R5": pwr(26.0, 16.5), "LED2": pwr(29.5, 16.5),
    # ミュートリレーの駆動（どれも 1.35 以下）。🔴 **リレーの隣に置く**。
    # 最初 Y 70.5（電池の影の上）に置いたらリレーまで 53mm 離れて COL がつながらなかった。
    # 2026-09-13 に柱の抜き (31.58, 2.46) φ4.0 が入って、J14 と柱のあいだが 2.88mm しか
    # 残らなくなったので、K31 の左上の帯（Y 20〜25・天井は電池の影の 4.4）へ移した
    # 🔴 2026-09-13、Y 22.5 のままだと SCL が J1 へ降りられない（自動配線が 1 本残す）。
    #    それまで通っていたのは、**向きを間違えた J5 の通り道**が C31 を上へ押していたからで、
    #    向きを直したら押されなくなり、車線が消えた。⇒ 車線を**わざと**空ける。
    #    Y 26.5 なら J1 の上端 19.91 との間に 5.6 空く（背はどれも 1.6 以下・電池の影の下）
    "C31": (6.0, 26.5, 0), "R32": (10.0, 26.5, 0), "R31": (14.0, 26.5, 0),
    "D31": (19.5, 22.5, 0), "Q31": (24.0, 22.5, 0),
    # C32 は EN の跳ね止め。リレーではなく EN の線（リード J6・トグル SW1）の側に置く
    # C32 は EN の跳ね止め。RC は位置に依らないので、配線が通る所へ置いてよい
    "C32": (16.0, 58.0, 0),

    # ======== 背の高い物（電池の影の外）========
    # 🔒 XIAO の口 2 列。列 X 9.40 が D0〜D6 側・1 本目が Y 2.90 側（gen_sch.py の XIAO_ROWS）
    "J1": (9.40, 2.90, "xiao"), "J14": (24.63, 2.90, "xiao"),
    # 🔒 つまみ。磁石と歯車の軸がこの真上に降りる（KEEPOUT_MAGNET）
    "U4": (36.2, 7.0, 0), "C42": (28.0, 10.8, 0),
    # ミュートリレー（背 9.33）。90 度回して寝かせる（電池の影 Y>25 に掛けない）。
    # 🔴 2026-09-13 機構担当: 立入禁止の φ10.2（芯 36.2, 7）に 0.10 食い込んでいたので上げた。
    #    ついでに AS5600 から離す（芯どうし 10.5 → 12.0mm）。電池の影の縁まで残り 0.8
    "K31": (34.65, 18.85, 90),
    # 🔒 マスタートグル。胴のレバー側を板の上端 Y 81.2 に揃える → 足形の原点は Y 76.2
    "SW1": (26.5, 76.2, 0),
    # 🔒 充電の USB-C。板 X 37.5・口が板の上端から 3.0 出る
    "J13": (37.5, 80.55, 180),
    # 口（線が板の面と平行に抜ける形）
    # 🔒 スピーカーは箱の左なので、スピーカーへ出る J5 を左の帯に置く。
    # J4（ReSpeaker から来る側）は右の帯へ回す
    "J5": (3.0, 13.5, 0),      # スピーカー OUT（左の帯・PH 横。取付穴のナットを避けて上げた）
    # 🔴 2026-09-13: OLED の柱 (3.30, 71.80) φ6.5 が上の縁の唯一の 4 ピンの枠を奪った。
    #    総当たりで探し直したら、PH 4 ピンが入るのは **谷** と **右の帯（口を −X へ向ける）** の
    #    2 つだけ。谷には J6 が居るので、OLED を右の帯へ回す。線は伸びるが、谷へ入れた場合の
    #    65mm より短い（芯どうし約 35mm）
    # 🔴 2026-09-13、口の向きを実測したら J2 と J4 が**逆を向いていた**（手書きの OPEN_DIR が
    #    180° ずれていた）。J2 は相手が板の右の縁を 2.6 越えて殻を貫き、J4 は相手が SW1 と J13 に
    #    ぶつかっていた。⇒ **どちらも 180° 回して、口を板の内側へ向けた。**
    #    枠は 180° 回しても同じ大きさなので、置き場所は動いていない
    # ⚠ 角度を 180° 回すと、枠は同じ大きさのまま**パッドの反対側へ移る**（2 ピンで (2.0, 4.9)・
    #    4 ピンは X 対称なので Y だけ）。⇒ 枠を元の場所に残すため、置き点も同じだけ動かしてある
    # 🔴 270° に回すとパッドが枠の反対の端（X 36.75 → 41.75）へ移り、柱 (40.70, 38.80) の
    #    抜き φ6.5（Y 35.55〜42.05）に SCL と SDA が乗った（copper_edge_clearance 0.000）。
    #    枠は柱を避けていたのにパッドは避けていない ⇒ **+3.3 上げて、いちばん下のパッドを 43.3 に**
    "J2": (41.75, 49.3, 270),  # OLED（右の帯・PH 横 4 ピン・口は板の内側 −X）
    "J4": (32.5, 72.9, 0),     # スピーカー IN（右の帯・PH 横・口は板の内側 −Y）
    "J10": (41.0, 25.65, 180),  # 電池の PH 横（右の帯・口は +Y ＝ 電池の側）
    # 🔒 2026-09-13: リードと会話ボタンは 1 つの 4 ピン PH（J6）にまとまった。
    # 4 ピンの PH は幅 10.90 あり、入るのは「谷」（幅 11.6）と「上の縁」（幅 12）の 2 か所だけ。
    # OLED は前の上へ行くので上の縁、リード＋会話ボタンは谷に置く
    # 🔴 2026-09-13、調停役が殻の実体に当てて「J6 の相手が壁を 0.85 貫く（44.472mm³）」と出した。
    #    板の上には何も無いので**板の検査も殻の検査も通る**。挿す相手をどちらも持っていなかった。
    #    ⇒ +2.0 上げて、**相手（枠の縁から 3.1）が板の縁の内側で終わる**ようにした。
    #      板の下の縁 Y 0 に対して相手の先端 Y 0.15・殻の内側の面（箱 Y 2.0）に対して 1.15。
    #      他の 4 口は元から板の上で終わっている（J6 だけが外へ出ていた）
    # 🔴 2026-09-13 調停役: 「線が壁へ向かって出ても、**曲げる場所が無い**」（φ1.0 の線の
    #    曲げ半径は 5 倍で 5mm 見当。壁までは 2.25 しかない）。⇒ **180° 回して口を +Y（谷）へ向け、
    #    Y も元へ戻した。**谷は指のぶん 10.0 まで空いていて、相手も線も板の上で完結する。
    #    ⇒ 殻を 0.85 彫る話も、+2.0 上げる話も、どちらも要らなくなった
    "J6": (20.0, 3.10, 180),   # リード＋会話ボタン（XIAO の下の谷・口は谷の側 +Y）
}

# ======== v6 の板（44 × 81.2・縦）から v6.1 の板（82.024 × 37.4・横）への写し ========
# 🔴 **鏡にしない。** 軸を入れ替えるだけの写し（X←y・Y←x）は行列式が −1 で鏡像になり、
#    足形のパッドの並びが裏返る。時計回りに 90° 回す形（(x, y) → (y, −x)）で写す。
#    v6 で自動配線が通った相対の並びをそのまま持ち込むための写像で、ここで並べ直してはいない。
# 倍率 0.75 / 0.80 は、v6 の電源の帯（x 1〜35・y 25.5〜75）を v6.1 の空き
#    （X 19〜56.1・Y 3.5〜35.8）へ収める値。
#    🔴 2026-09-14: 最初 0.75 / 0.80（Y は 30.7 まで）で回したら 9 本が未接続・違反 24 件だった。
#       v6 でも同じ症状を「面積が余っているのに詰めていた」で直しているので、後ろの縁まで伸ばした。
#       それでも STAT1 と VSYS の 2 本が残ったので、X も左へ広げた（19.0〜56.1 → 16.8〜55.9）。
SX, SY = 0.79, 0.95


def v61(x, y, ang=0):
    return (16.8 + (y - 25.5) * SX, 3.5 + (35.0 - x) * SY, (ang - 90) % 360)


def org_from_box(fp_id, ang, x0, y0, x1, y1, back=False, key="CrtYd"):
    """置きたい**枠**（板の座標）と角度から、足形の**原点**（板の座標）を逆算する。

    🔴 こちらが筐体と決めてきたのは「枠」で、PLACE の表は「原点」を書く。手で引き算すると
       回転のたびに向きを間違える（v6 で 3 回踏んだ）。⇒ 足形を読んで、その角度での枠を測って引く。
    🔴 裏面（back）は**局所 Y が反転した状態で保存される**（KiCad 自身の板で確かめた。
       cm5_minima の同じ足形が表 (-1, 0.43) / 裏 (-1, -0.43)）。⇒ 反転してから測る。
    ⚠ 出来上がりは build() の中で **置いたあとの枠を測って**突き合わせる（check_boxes）。
       ここの式だけを信じない。
    ⭐ 2026-09-17: key="Fab" にすると **胴**で位置を決める。壁から出す量のように
       「物がどこまで出るか」で決まる置き方は、枠で指定すると逃げのぶんずれる
       （USB-C を枠で 1.3 出したら胴は 0.8 しか出ず、奥まりが 0.8 のはずが 1.3 になった）。
    """
    fp = load_fp(fp_id)
    if back:
        fp = mirror_y(fp)
    cx0, cy0, cx1, cy1 = courtyard(fp, 0.0, 0.0, ang, key)
    return (x0 - cx0, y0 + cy1)


# 板の上で場所が決まっている物（v61_board.py と筐体からの実測）。写像は通さない。
# 角度は「足形の 0 度での向き」から決めた:
#   PH 横（S2B/S4B）… 0 度で口は −Y。90 度で +X・180 度で +Y・270 度で −X
#   PH 縦（B2B/B4B）… 口は上。パッドは +X へ並ぶ
#   ピンソケット 1x0n … 0 度でパッドが +Y へ並ぶ。270 度で +X へ並ぶ
#   USB-C … 0 度で口は +Y（パッドは −Y 側）。270 度で口が +X
# ---- 枠で置く物（v61_board.py の PORTS と同じ枠を使う）----
#   (角度, 枠 x0, y0, x1, y1)。枠は v61_board.py が持っている値から作る
def _fb(nm):
    q = [x for x in VB.PORTS if x[0] == nm][0]
    fw, fh = q[3]
    w, h = (fh, fw) if q[4] in ("+X", "-X") else (fw, fh)
    return (q[1] - w / 2, q[2] - h / 2, q[1] + w / 2, q[2] + h / 2)


# 板の**裏**に付く物（KiCad でも B.Cu に置く）。局所 Y が反転する
BACK_SIDE = {"J10"}
# ⭐ 2026-09-17: 枠ではなく **胴** で置く物。壁から出す量で位置が決まる口だけ。
#   枠（courtyard）は KiCad が付けた逃げで物の形ではない（USB-C は後ろへ 0.5 大きい）
BOX_BY_FAB = {"J13"}
PH_H2 = "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal"
PH_V2 = "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"
PH_V4 = "Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical"
SOCK7 = "Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical"   # 板の側はオス（2026-09-14）
SOCK4 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
BOX_PLACE = {
    # 口。角度は「足形の 0 度で口が −Y」から決めた（90 で +X・180 で +Y・270 で −X）
    # ⭐ 2026-09-16 夕 🔒 ユーザー「J4とJ6を縦にして」: 横出し → 縦。角度はパッドの並びだけを決める
    "J4": (PH_V2, 0) + _fb("SPK IN"),
    "J5": (PH_H2, 270) + _fb("SPK OUT"),
    "J6": (PH_V2, 0) + _fb("会話ボタン"),
    "J7": (PH_V4, 0) + _fb("リード＋トグル"),      # 縦 4 ピン（上から挿す）
    # ⭐ 2026-09-16 夕 🔒 ユーザー「ケーシング作ったから垂直のがいい。結局一番穴は小さくなる」:
    #    サイド型 S2B-PH-K（横出し・左の帯）→ **トップ型 B2B-PH-K を板の裏に下向き**、右の帯へ。
    #    角度 180 は「パッドを **X** へ並べる」ため（枠は PH2_V 6.9 × 5.5）。裏なので足形は鏡になるが、
    #    縦の口は口の向きが ±Z で鏡に関係しない。**効くのはパッドの並びだけ**なので CHECK_PADS で見る。
    #    ⚠ Y へ並べる（270）も試したが、はんだ足が J4 に挿さったプラグの下に入って置けなかった（v61_board.py の注）
    # ⭐⭐ 角度 270 でパッドが **Y** へ並ぶ（手前が 2 番 ＝ VBAT ＋・奥が 1 番 ＝ GND）。
    #     180（X 並び）にしていたのは J4 のプラグに塞がれていたため。J4 を縦にして戻した
    # 電池の口は **電池の外**に置く。電池は板の座標 X 16.05〜66.05 を占め、その上は
    # 板の裏まで 12.0 − 6.0 = 6.0 しか無い。縦の PH は挿して 8.0 要る（📄 ePH.pdf 1 ページ）。
    # 電池の外なら床まで 12.0。電池のタブも X 66.05 から出るので、その右が線としても短い。
    # 判定は v61_board.back_clear() が電池の箱から引き算して出す。
    "J10": (PH_V2, 270, 73.5, 12.5, 79.0, 19.4),     # 縦 2 ピン（板の裏・口は下 ＝ 電池の側）
    # ライザーの縦ソケット（パッドが板の +X へ 2.54 間隔で並ぶ向き）
    "J1": (SOCK7, 90, -0.01, VB.RISER_XIAO[2] - VB.RISER_D / 2, 18.79, VB.RISER_XIAO[2] + VB.RISER_D / 2),
    "J2": (SOCK4, 90, 35.47, VB.RISER_OLED[2] - VB.RISER_D / 2, 46.63, VB.RISER_OLED[2] + VB.RISER_D / 2),
    # 充電の USB-C（口が板の右の縁から 1.53 出る）
    # 🔴 2026-09-14: 270 度で置いたらパッドが板の外（板 X 82.8）へ出て、縁までの距離の違反が
    #    18 件出た。図面の Y は下向きなので、板の座標で見ると回る向きが逆になる。⇒ 90 度。
    # USB-C は **壁のある縁**にしか置けない（🔒 ユーザー 2026-09-16「壁であればどこでもいいですよ。
    # ハッチ側でもいいです」）。前の縁は壁ではなく ReSpeaker の板が立っていて、板の縁から
    # 背面まで 3.465・胴を 1.53 出すと残り 1.935 でプラグが入らない。
    # ⇒ **後ろの縁（ハッチ側）**。U2（板 X 33）に一番近い壁で、VBUS が短い。
    # 角度 180 で口が +Y（ハッチ）を向く。
    "J13": ("Connector_USB:USB_C_Receptacle_USB2.0_16P", 180,
            (BOARD_L - VB.USBC_SHELL_W) / 2, BOARD_W + VB.usbc_out() - VB.USBC_BODY_D,
            (BOARD_L + VB.USBC_SHELL_W) / 2, BOARD_W + VB.usbc_out()),   # 枠ではなく胴（BOX_BY_FAB）
    # ミュートリレー（背 9.33）
    "K31": ("Relay_SMD:Relay_DPDT_Omron_G6S-2F", 90) + VB.RELAY[:2]
           + (VB.RELAY[0] + VB.RELAY[2], VB.RELAY[1] + VB.RELAY[3]),
}
# ======== 電源部の配置（板の座標・2026-09-16）========
# ⭐ ここまでの電源部は **二重の写し**だった: 旧 PowerBoost 基板 → v6 の板（pwr()）→ v6.1 の板（v61()）。
#   gen_pcb.py の写しの注が「ここで並べ直してはいない」と書いているとおりで、v6.1 の板の上で
#   電源部を並べた人はいなかった。その結果:
#     ・電池の口 J10（X 76）から シャント R41（X 30）まで板を横断し、配線 107mm ＝ 0.2mm で 217mΩ
#     ・シャント R41 と 電流計 U3 が 23mm 離れ、ケルビンが取れず INA226 が 9.6 倍に読む
#     ・USB-C J13（X 80）から 充電 IC U2（X 28）まで 52mm
#     ・U2 の周りに全部が集まり、0.5mm ピッチの辺から 0.4mm の線が逃げられない
#   ⇒ **電流が流れる順に、左へ向かって一列**に並べ直す。
#      J10（電池）→ Q2（逆接保護）→ R41（シャント）→ U2（充電）→ L1・U1（昇圧）→ J1（XIAO・固定 X 0〜18.79）
#      U3（INA226）は R41 の真上に置く。J13（USB-C）は U2 のすぐ前の縁へ。
# 🔒 2026-09-16 ユーザー「この板が成立しなければ筐体は作り直し。ここが中枢」。
#    固定は **板の外形・取付穴・J1（XIAO のライザー）** の 3 つだけ。
#    v61_board.py の USBC_Y・電池のタブの位置は筐体側の都合なので縛らない。板の裏に何が入るかは
#    v61_board.py の back_clear()（電池の箱からの引き算）で毎回出す。
POWER_V61 = {
    # 並べ方: 小さい部品は **X 3.0 間隔・Y は 5.0 / 9.5 / 14.0 / 19.0 / 23.0 / 27.0 の列**に揃える。
    # 主の道だけ Y 14.0 の一直線（U2 は下の辺から 5 本逃がすので 1.5 上げてある）。
    # ---- 主の道（右から左へ流れる）----
    "U1":  (22.0, 14.0, 180),   # 昇圧 TPS61090（180°: SW と V5 を L1 の側＝右へ）
    "L1":  (27.5, 14.0, 180),   # インダクタ（180°: 2 番 SW を U1 の側＝左へ）
    "U2":  (33.5, 15.5, 0),     # 充電 MCP73871（下の辺 6〜10 番の逃げ道を空けるため 1.5 上）
    "R41": (39.5, 14.0, 180),   # シャント 10mΩ（180°: 1 番 BATP を Q2 の側＝右へ）
    "Q2":  (44.0, 14.0, 0),     # 逆接保護 P-ch（3 番 ドレインが +X ＝ J10 の側）
    "U3":  (39.5, 19.3, 270),   # INA226 — R41 の真上（ケルビン。X を R41 と揃える）
    # ---- 前の列 Y 5.0（U2 の下の辺 6〜10 番へ行く物と CC）----
    "R44": (20.0, 5.0, 0), "R45": (23.0, 5.0, 0),      # CC 5.1k
    "LED3": (26.0, 5.0, 0), "R14": (29.0, 5.0, 0),     # 充電済み（STAT2 = 7 番）
    "R15": (32.0, 5.0, 0),                              # THERM（5 番）
    "LED4": (35.0, 5.0, 0), "R8": (38.0, 5.0, 0),      # 充電中（STAT1 = 8 番）
    "R46": (44.0, 5.0, 0),                              # Q2 のゲート
    # ---- Y 9.5 / 11.0 ----
    # V5 の出力コンデンサは U1 の**下の辺**（15・16 番 板 Y 12.04）の真下に 3 本並べる。
    # ⭐ 2026-09-17: C6・C9 は Y 23.0 の列（U1 から銅で 33〜37mm・42〜48mΩ）に居た。
    #   600kHz では配線のインダクタンス（33mm で 30nH ≒ 120mΩ）が効いて、47µF が
    #   出力リプルに働いていなかった。1206 なので間隔は 3.5。
    "C2": (22.0, 9.5, 0), "C6": (25.5, 9.5, 0), "C9": (29.0, 9.5, 0),
    # ⚠ X 35.0 だと U2 の 9 番の逃げ道（escape_stub）が R16 の GND パッドに 0.01mm まで寄る
    "R16": (36.5, 11.0, 0), "R17": (39.5, 11.0, 0),    # PROG1 / PROG3（U2 の右の辺 11〜15 番）
    # ---- Y 19.0（パスコン）----
    "C1": (22.0, 19.0, 0), "C4": (25.0, 19.0, 0),       # VSYS
    "C7": (28.0, 19.0, 0), "C8": (31.0, 19.0, 0),       # VLIPO / VBUS
    "C41": (34.0, 19.0, 0),
    "R42": (44.0, 19.0, 0), "R43": (47.0, 19.0, 0),    # I2C の引き上げ
    # ---- Y 23.0（分圧と大きいコンデンサ）----
    "R1": (22.0, 23.0, 0), "R2": (25.0, 23.0, 0),       # LBI
    "R3": (28.0, 23.0, 0), "R4": (31.0, 23.0, 0),       # FB
    "R13": (34.0, 23.0, 0),                             # EN
    "R6": (37.0, 23.0, 0), "R7": (40.0, 23.0, 0),      # VPCC

    # ---- Y 27.0（印の LED）----
    "LED2": (22.0, 27.0, 0), "R5": (25.0, 27.0, 0),    # 5V が出ている
    "LED1": (28.0, 27.0, 0), "R20": (31.0, 27.0, 0), "Q1": (34.0, 27.0, 0),   # 電池残量
}
FIXED_V61 = {
    # つまみ（磁石と軸がこの真上に降りる）。AS5600 は芯で置く
    "U4": (65.700, 13.800, 0), "C42": (57.500, 13.800, 0),
}
FIXED_V61.update(POWER_V61)


def solve_fixed():
    """枠で指定した物の原点を足形から逆算して PLACE を仕上げる（load_fp が要るので実行時に呼ぶ）。"""
    for r, (fp, a, x0, y0, x1, y1) in BOX_PLACE.items():
        ox, oy = org_from_box(FP_OVERRIDE.get(r, fp), a, x0, y0, x1, y1, back=r in BACK_SIDE,
                              key="Fab" if r in BOX_BY_FAB else "CrtYd")
        FIXED_V61[r] = (ox, oy, a)
    PLACE.update(FIXED_V61)

# v6.1 に無い部品: SW1（板のトグル → ハッチへ）・J14（XIAO の 2 列目 → ライザーで 1 本に）・
GONE_V61 = {"SW1", "J14"}
PLACE = {r: v61(*v) for r, v in PLACE_V6.items()
         if r not in BOX_PLACE and r not in FIXED_V61 and r not in GONE_V61}
PLACE.update(FIXED_V61)


# 🔴 口は「枠が重なっていない」だけでは挿せない。**プラグの通り道**を別に見る。
#    2026-09-13 ユーザー「J4J5どうやって挿すんだ」。私は当たりの検査しか書いておらず、
#    J4・J6・J8 の 3 つで通り道が塞がっていた。[[clearance-is-not-assemblability]]
#    値: (足形の中でのプラグの向き, 通り道の長さ)
#      PH の横挿し   … 口は局所 −Y。プラグの胴 7.6 ＋ 指と曲がり 2.4 = 10.0
#      2.54 の L 字   … 口は局所 −X。DuPont のハウジング 14（hardware/parts/plug.scad）＋ 2 = 16.0
# v6.1: 板の面に沿ってプラグが入るのは 3 つだけ。J1・J2 はライザーのソケット（板が立つ）、
#       J7 と J10 は縦の PH（上・下から挿す）なので、板の面の通り道は要らない。
# ⭐ 2026-09-16 夕: J4 と J6 が縦になったので、板の面に沿ってプラグが入るのは **J5 だけ**になった
CONN = {
    "J5": ("-y", 10.0),
}
# ⛔⛔ **手書きの OPEN_DIR は捨てた**（2026-09-13）。全ての角度で 180° 逆で、
#    プラグの通り道の検査は 5 口とも **口の裏側**を見ていた。「5 口すべて空いている」は
#    「裏側が空いていた」という意味しかなかった。J2 は板の右の縁を 2.60 越えていて、
#    それを誰も捕まえられなかった（殻の側は「私が左と言ったので左を見た」）。
#    ⇒ **向きは表で持たない。置いてある足形から測る。**[[mirror-word-needs-proof]]
#
# 🔒 測り方: **口は必ずパッドと反対側に開く。**横挿しの口は、足が胴の後ろの端で板へ落ち、
#    胴がそこから前へ伸びて、その先が開いている（📄 ePH.pdf 3 ページの側面図。
#    足の (3.4) は胴の片方の端にしかない）。
#    ⇒ **パッドの重心から枠の中心へ向かう向き＝開いている向き。**
#      PH 2 ピン横で ±2.45 出る（枠 8.60 の中心とパッドのずれ）。X と Y のどちらが
#      大きいかで 4 方向に丸める。
# ⭐ 2026-09-16 夕に引き直した。🔴 **旧 3.1 は導出そのものが間違っていた。**
#   旧: 📄 2 ページ（SMT の図）の (9.6) − 6.0 − 逃げ 0.5 = 3.1。引いた 6.0 は**トップ型の背**で、
#       (9.6) が載っている**サイド型の奥行き 7.6** ではない。層の違う数どうしを引いていた。
#   正: 📄 1 ページ（Through-hole の組立図）  サイド型 (9.6) − 胴の奥行き 7.6 = **2.0**
#                                             トップ型 (8)   − 胴の背     6.0 = **2.0**
#   この表は courtyard の枠から測るので、逃げ 0.5 を引いて 1.5 を渡す（＝胴の縁から 2.0）。
PLUG_BODY = 1.5   # 相手のハウジングが **courtyard の縁**から出る量（胴の縁からは 2.0）
# ⚠ 押し離し（relax）だけは 3.1 のまま予約する。**検査の値ではなく置き方の手加減**である。
#    1.5 に詰めたら電源の区画の小物が流れ込み、D31 と Q31 が 2.3 × 1.29 重なって落ち着いた（2026-09-16 夕）。
#    口の前は指も取り付くので、置く段階では広めに空けておく方が結果が良い
PLUG_KEEP = 3.1


def plug_band(rect, d, n):
    """口の枠（**板の座標** x0, y0, x1, y1）の前へ、長さ n の帯を作る。

    🔴 向きの計算をここ 1 か所に閉じる。2026-09-13、同じ式を 3 か所に書いて
       2 か所で Y の符号を逆にした（gen_pcb の OPEN_DIR と parts_place の band）。
    """
    x0, y0, x1, y1 = rect
    dx, dy = d
    if dx:
        return (x1, y0, x1 + n, y1) if dx > 0 else (x0 - n, y0, x0, y1)
    return (x0, y1, x1, y1 + n) if dy > 0 else (x0, y0 - n, x1, y0)


def open_dir(fp, x, y, ang):
    """置いてある足形の「開いている向き」を測る。返すのは**板の座標**の単位ベクトル。"""
    a = math.radians(ang)
    px = py = 0.0
    n = 0
    for pd in find(fp, "pad"):
        q = find1(pd, "at")
        lx, ly = float(q[1]), float(q[2])
        px += x + lx * math.cos(a) + ly * math.sin(a)
        py += y - lx * math.sin(a) + ly * math.cos(a)
        n += 1
    px /= n
    py /= n
    b = courtyard(fp, x, y, ang)
    dx = (b[0] + b[2]) / 2 - px
    dy = -((b[1] + b[3]) / 2 - py)      # 図面の Y は下向き。板の Y へ直す
    return (1 if dx > 0 else -1, 0) if abs(dx) > abs(dy) else (0, 1 if dy > 0 else -1)

# ---- 板の面からの背の高さ [mm] ----
# 🔴 筐体側は板を「44 × 81.2 × 4.0 の塊」として持っていた（2026-09-13 に判明）。
#    実体に割るのに要るので、部品ごとの背をここに置く。**出どころを必ず付ける。**
#      📄 = データシート／図面で取った   ⚠ = 一般値（パッケージから推した・未確認）
HEIGHT = {
    "K31":  (9.33, "📄 en-g6s.pdf 5 ページ ＋ KiCad の STEP（Z 0〜9.330）"),
    # ⭐ 2026-09-16 夕に直した。2026-09-14 に「板の側は縦のメスソケット（背 8.5）」から
    #    **オスのピンヘッダ**（樹脂 2.5・ピンの先は板の面から 8.5）へ替えたのに、この表が 8.5 のままだった。
    #    ここで要るのは「板の上に立っている樹脂の塊」なので **2.5**。
    #    ピンの 6.0 はライザーの裏の L 字のメスが咥えるので、空間としては空いていない扱いでよい
    "J1":   (2.54, "🔒 2.54 ヘッダの規格の姿（樹脂 **2.54**・ピン 6.0・先は板の面から 8.54）。⭐ 2026-09-16 夕に 2.5 → 2.54（KiCad の 3D モデルの実測）"),
    "J2":   (2.54, "🔒 同上（1x04）"),   # 🔴 出どころの頭が 📄 か 🔒 でないと、gen_case_parts が 3D モデル（ピン込みの 8.65）で上書きする
    "J14":  (8.5,  "v6.1 に無い（XIAO の 2 列目・ライザーで 1 本になった）"),
    # 📄 ePH.pdf 3 ページ「Header（Through-hole type）・Side entry type」の側面図は
    #    **板が縦に描いてある**（足が横向きで (3.4) も横）。⇒ 4.8 が板からの高さ・7.6 が板の面の奥行き。
    #    courtyard 8.60 ＝ 7.6 ＋ 逃げ 0.5 × 2 で裏が取れる。
    #    挿した相手（PHR・厚み 4.5）は口の中に収まるので、**挿しても 4.8 を超えない**
    #    （📄 2 ページの SMT 型の組立図で、挿した外形の高さ (5.5) ＝ SMT の口自身の高さ 5.5）。
    # ⚠ 旧 "J2": (4.8, "📄 ePH.pdf 3 ページ Side entry") は、J2 が PH の横出しだった頃の残り。
    #    いまの J2 は OLED のライザーを受けるピンヘッダなので上へ移した（2026-09-16 夕）
    # 2026-09-16 夕に J4 と J6 を縦（Top entry）へ替えたので、背も 4.8 → 6.0。
    # J5 は口が板の左の縁を向いていて盤面を食わないので横出し（Side entry・4.8）のまま
    "J4":   (6.0,  "📄 ePH.pdf 3 ページ Top entry（B2B-PH-K の胴。嵌合は 8.0）"),
    "J5":   (4.8,  "📄 ePH.pdf 3 ページ Side entry"),
    "J6":   (6.0,  "📄 ePH.pdf 3 ページ Top entry（同上）"),
    # ⭐ 2026-09-16 夕にトップ型へ。📄 ePH.pdf 3 ページ Top entry の図で胴の背は 6.0、
    #    1 ページ「mounting height of 8 mm」で**嵌合した高さは 8.0**。板の裏が Z 12.0 なので床まで 4.0 余る
    "J7":   (6.0,  "📄 ePH.pdf 3 ページ Top entry（B4B-PH-K の胴。嵌合は 8.0）⭐ 2026-09-16 夕に追加。それまで既定の 1.45 で数えていた"),
    "J10":  (6.0,  "📄 ePH.pdf 3 ページ Top entry（嵌合は 8.0・1 ページ）"),
    "Q2":   (1.1,  "⚠ 一般値 SOT-23（逆接保護の P-ch）"),
    "SW1":  (4.0,  "📄 MST-12D18G3.pdf（胴 3.5 ＋ 浮き 0.5。レバーは Z 2.3〜3.8）"),
    "J13":  (3.16, "⚠ 二次資料（PCBWiki）・メーカー図は未取得"),
    # 🔒 2026-09-13、JLCPCB の部品ページ（C79815）の仕様欄 `Height 1.75mm` で裏が取れた。
    #    ⚠ ただしこの欄の名前は部品によって違い、**板からの高さなのは `Z-Height of the Board` だけ**。
    #    SW1（C49023766）の `Switch Height 6.5mm` は板の面の奥行きで、板からの高さではない
    "U4":   (1.75, "📄相当 JLCPCB C79815 の仕様欄 Height 1.75mm"),
    "L1":   (1.8,  "型番の「18」＝ 1.8mm（FNR4018S）"),
    "C6":   (1.6,  "⚠ 一般値 1206 MLCC"),
    "C9":   (1.6,  "⚠ 一般値 1206 MLCC"),
    "R41":  (0.65, "⚠ 一般値 1206 合金シャント"),
    "D31":  (1.35, "⚠ 一般値 SOD-123"),
    "Q1":   (1.3,  "⚠ 一般値 SOT-23"),
    "Q31":  (1.3,  "⚠ 一般値 SOT-23"),
    "U1":   (1.0,  "⚠ 一般値 VQFN-16"),
    "U2":   (0.9,  "⚠ 一般値 QFN-20"),
    "U3":   (1.1,  "⚠ 一般値 MSOP-10"),
}
HEIGHT_DEFAULT = (1.45, "⚠ 一般値・0805 の抵抗とコンデンサと LED はこれ以下")

# 角度を検算する所。板の座標で「このパッドはここに来るはず」を書いておく。
# 🔴 鏡像事故はここで止める（[[mirror-accident-ledger]]）。1 本目と 7 本目の Y が入れ替わったら落ちる
# 🔴 置いたあとのパッドの位置を板の座標で検算する（角度の取り違えはここで捕まる）。
#    v6.1: ライザーのソケットは 1 番が左・パッドが +X へ 2.54 間隔（筐体へ渡した座標）。
CHECK_PADS = {
    # 🔒 2026-09-14: ライザーが裏面の L 字のメスで受ける形になり、ピンの列が +2.87 後ろへ動いた
    ("J1", "1"): (1.770, 11.805), ("J1", "7"): (17.010, 11.805),
    ("J2", "1"): (37.240, 4.770), ("J2", "4"): (44.860, 4.770),
    # 🔴🔴 電池の極性。裏面なので足形が鏡になる。ここが入れ替わると逆接で煙が出る
    #    （2026-09-11 に実機で INA226 から煙・PowerBoost が発熱している）。
    #    **奥（Y 大）が GND ／ 手前（Y 小）が VBAT（＋）** — PowerBoost B1 と同じ言い方。
    #    🔴 1 番 GND が**奥**（Y 16.950）・2 番 VBAT ＋ が**手前**（Y 14.950）
    ("J10", "1"): (75.700, 16.950), ("J10", "2"): (75.700, 14.950),
    # ⭐ 2026-09-16 夕: 逆接保護の P-ch（Q2）の向き。ここが回ると保護にならないので位置で縛る。
    #    SOT-23 は 1 番（G）と 2 番（S）が片側・3 番（D）が反対側で、**3 番＝ドレイン＝電池側**である。
    #    角度 0 で 3 番が +X 側（44.940）・1/2 番が −X 側（43.060）に並ぶ。J10（X 75.7）は Q2 の
    #    +X 側なので、電池は 3 番（ドレイン）から入る。ネットの対応（3=BATRAW・2=BATP・1=BATG）は check_sch.py が見る
    ("Q2", "1"): (43.060, 14.950), ("Q2", "2"): (43.060, 13.050), ("Q2", "3"): (44.940, 14.000),
    # USB-C は「パッドの列が板の内側」だけが条件（A1 と B1 のどちらが上かは足形が決める）。
    # 2026-09-16: 右の縁 → 後ろの縁（ハッチ側）。板の縁は Y 37.4 で、パッドの列が
    #    Y 31.000 ＝ 板の内側（胴の出 1.3・足 4 本）。X は足形の並びに任せる
    ("J13", "A1"): (None, 31.000), ("J13", "B1"): (None, 31.000),
}


def netlist():
    out = OUT / "_pcb.xml"
    r = subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                        str(OUT / f"{NAME}.kicad_sch")], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ネットリストを書き出せない:\n" + r.stdout + r.stderr)
    root = ET.parse(out).getroot()
    out.unlink()
    comps = {}
    for c in root.iter("comp"):
        ref = c.get("ref")
        fp = c.findtext("footprint") or ""
        flds = {f.get("name"): (f.text or "") for f in c.iter("field")}
        comps[ref] = dict(fp=FP_OVERRIDE.get(ref, fp), value=c.findtext("value") or "",
                          lcsc=flds.get("LCSC", ""))
    pads, nets = {}, {}
    for net in root.iter("net"):
        nm = net.get("name").lstrip("/")
        nets.setdefault(nm, len(nets) + 1)
        for node in net.iter("node"):
            pads[(node.get("ref"), node.get("pin"))] = nm
    return comps, pads, nets


def load_fp(fp_id):
    lib, name = fp_id.split(":")
    p = (LOCAL if lib == "katanori" else FPDIR / f"{lib}.pretty") / f"{name}.kicad_mod"
    if not p.exists():
        sys.exit(f"足形が無い: {fp_id}")
    return kisym.parse(p.read_text(encoding="utf-8"))[0]


def rot_xy(x, y, ang):
    a = math.radians(ang)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def courtyard(fp, x, y, ang, key="CrtYd"):
    """置いた足形の外接枠。key="Fab" にすると **胴（F.Fab／B.Fab）**の枠になる。

    ⭐ 2026-09-16 夕に key を足した。courtyard は KiCad が周りに 0.3〜0.5 の逃げを付けた
    **置き場所の予約**で、物の形ではない。板を貫いた足が板の反対側の物に当たるかは
    逃げではなく胴で見る（J10 を裏へ回して、J4 の逃げに 0.00 で触れる置き方が出た）。
    """
    xs, ys = [], []

    def walk(n):
        if isinstance(n, list):
            if n and n[0] in ("fp_line", "fp_poly", "fp_rect", "fp_circle"):
                lay = find1(n, "layer")
                if lay and key in str(lay[1]):
                    for k in ("start", "end", "center", "mid"):
                        for e in find(n, k):
                            xs.append(float(e[1]))
                            ys.append(float(e[2]))
                    for pts in find(n, "pts"):
                        for e in find(pts, "xy"):
                            xs.append(float(e[1]))
                            ys.append(float(e[2]))
            for e in n:
                if isinstance(e, list):
                    walk(e)
    walk(fp)
    if not xs and key != "CrtYd":   # その層が無い足形は courtyard で代用（安全側）
        return courtyard(fp, x, y, ang)
    if not xs:   # CrtYd の無い足形（自作）はパッドの範囲で代用
        for p in find(fp, "pad"):
            at = find1(p, "at")
            sz = find1(p, "size")
            for sx in (-1, 1):
                xs.append(float(at[1]) + sx * float(sz[1]) / 2)
                ys.append(float(at[2]) + sx * float(sz[2]) / 2)
    pts = [rot_xy(a, b, ang) for a in (min(xs), max(xs)) for b in (min(ys), max(ys))]
    return (x + min(p[0] for p in pts), y + min(p[1] for p in pts),
            x + max(p[0] for p in pts), y + max(p[1] for p in pts))


# 🔴 裏面の足形の書き方は、KiCad 自身の実例で確かめた（2026-09-14）。
#    C:/Program Files/KiCad/10.0/share/kicad/demos/cm5_minima/CM5_MINIMA_3.kicad_pcb に
#    同じ足形が表と裏の両方に置いてあり、**局所 Y だけが符号反転**して層が F↔B になっていた
#    （パッド 1 が F: (-1, 0.43) → B: (-1, -0.43)）。推測ではなく写した。
def mirror_y(node):
    """図形・パッドの局所座標の Y を反転する（裏面へ回すとき）。"""
    if not isinstance(node, list):
        return node
    if node and str(node[0]) in ("at", "start", "end", "center", "mid", "xy"):
        out = list(node)
        if len(out) > 2:
            try:
                out[2] = f"{-float(out[2]):g}"
            except ValueError:
                pass
        if str(node[0]) == "at" and len(out) > 3:      # 向きも反転
            try:
                out[3] = f"{(-float(out[3])) % 360:g}"
            except ValueError:
                pass
        return out
    return [mirror_y(e) for e in node]


def flip_layer(name):
    """F.* ↔ B.* を入れ替える（裏面に付ける部品用）。"""
    s = str(name)
    if s.startswith("F."):
        return "B." + s[2:]
    if s.startswith("B."):
        return "F." + s[2:]
    return s


def place_footprint(ref, comp, x, y, ang, pads, back=False):
    fp = load_fp(comp["fp"])
    if back:
        # 🔴 裏面は**足形ごと**局所 Y を反転してから使う。ここで 1 回だけ反転すれば、
        #    パッドも図形も枠（courtyard）も同じ物を見る。返す fp も反転済みなので、
        #    呼び出し側の当たり判定が「反転前の枠」を見る事故が起きない（2026-09-14 に踏んだ）
        fp = mirror_y(fp)
    # 🔴 記号（R15・C42…）は**一つも印刷しない**（2026-09-16 夕・ユーザー
    #    「口の名前と極性を入れて、SMD の記号は消してください」）。
    #    足形が持つ記号は「原点から上へ 2.5」の決め打ちにしか置けず、この密度では
    #    隣の部品やパッドの上に乗ってシルクが読めなくなっていた（R5 と R33 が
    #    重なって「R5-3R3」に見えていた）。自分で挿す口の番号は捨てずに、
    #    silk() が「J5 SPK OUT」の形で**名前と一緒に**置き直す。
    #    記号そのものは Value と同じく F.Fab／B.Fab へ回して隠す（部品表と実装位置は
    #    property を読むので、層を変えても壊れない）。
    tht = bool(find1(fp, "attr")) and "through_hole" in str(find1(fp, "attr")[1:])
    fab_lay = "B.Fab" if back else "F.Fab"
    # ⚠ 裏の層に置く文字は、隠してあっても鏡にしておく（KiCad の DRC が
    #    nonmirrored_text_on_back_layer で拾う）
    mir = [["justify", "mirror"]] if back else []

    def hidden_prop(nm, val, dy):
        return ["property", Str(nm), Str(val), ["at", "0", f"{dy}", "0"],
                ["layer", Str(fab_lay)], ["hide", "yes"], ["uuid", Str(uid())],
                ["effects", ["font", ["size", "0.8", "0.8"], ["thickness", "0.12"]]] + mir]

    out = ["footprint", Str(comp["fp"]), ["layer", Str("B.Cu" if back else "F.Cu")], ["uuid", Str(uid())],
           ["at", f"{x:.3f}", f"{y:.3f}"] + ([f"{ang:.0f}"] if ang else []),
           hidden_prop("Reference", ref, -2.5),
           hidden_prop("Value", comp["value"], 2.5),
           hidden_prop("LCSC", comp.get("lcsc", ""), 3.5),
           ["attr", "through_hole" if tht else "smd"]]
    for e in fp[2:]:
        if not isinstance(e, list) or e[0] in ("version", "generator", "generator_version", "layer",
                                               "descr", "tags", "attr", "property", "uuid", "embedded_fonts"):
            continue
        if e[0] == "pad":
            pad = [x for x in e if not (isinstance(x, list) and x[0] == "uuid")]
            # 🔴 パッドの at の 3 つ目は「板の上での向き」。部品を回したとき、位置は KiCad が回すが
            #    形は回らない（2026-09-12 に F.Cu の SVG を測って確認）。ここで足しておく
            if ang:
                # ⚠ 浅い複製なので at の中身はライブラリと共有している。作り直してから書く
                #    （共有したまま足すと、DSN に渡す向きにも二重に足さる）
                pa = list(find1(pad, "at"))
                pad[pad.index(find1(pad, "at"))] = pa
                a2 = ((float(pa[3]) if len(pa) > 3 else 0.0) + ang) % 360
                del pa[3:]
                if a2:
                    pa.append(f"{a2:.0f}")
            if back:
                lay = find1(pad, "layers")
                if lay:
                    pad[pad.index(lay)] = ["layers"] + [Str(flip_layer(str(s))) for s in lay[1:]]
            num = str(pad[1])
            net = pads.get((ref, num))
            if net is not None:
                pad = pad + [["net", str(NETNUM[net]), Str(net)]]
            pad = pad + [["uuid", Str(uid())]]
            out.append(pad)
        elif e[0] == "model" and ref in MODEL_VIS:
            path, off = MODEL_VIS[ref]
            out.append(["model", Str(path),
                        ["offset", ["xyz", f"{off[0]}", f"{off[1]}", f"{off[2]}"]],
                        ["scale", ["xyz", "1", "1", "1"]], ["rotate", ["xyz", "0", "0", "0"]]])
        else:
            body = [x for x in e if not (isinstance(x, list) and x[0] == "uuid")]
            if back:
                lay = find1(body, "layer")
                if lay:
                    body[body.index(lay)] = ["layer", Str(flip_layer(str(lay[1])))]
                # ⚠ 足形が自分で持っている文字（JST の "${REFERENCE}" など）も、裏へ回したら
                #    鏡にする。付け忘れると DRC が nonmirrored_text_on_back_layer で拾う
                if e[0] == "fp_text":
                    eff = find1(body, "effects")
                    if eff is None:
                        eff = ["effects"]
                        body = body + [eff]
                    elif not find1(eff, "justify"):
                        eff = list(eff)
                        body[body.index(find1(body, "effects"))] = eff
                    if not find1(eff, "justify"):
                        eff.append(["justify", "mirror"])
                    elif "mirror" not in [str(t) for t in find1(eff, "justify")[1:]]:
                        j = list(find1(eff, "justify"))
                        eff[eff.index(find1(eff, "justify"))] = j + ["mirror"]
            # 🔴 シルクに出る線と字は、製造の下限（SILK_T = 0.15）まで太らせる。
            #    ⭐ 2026-09-16 夕。KiCad の標準ライブラリの枠線は 0.12 で、JLCPCB の
            #    capabilities（Rigid PCB）の "Minimum Line Width ≥ 0.15mm — Characters width
            #    less than 0.15mm will be unidentifiable" を下回っていた。
            #    表のシルクの**長さの 84%**（のべ 489.3mm / 313 本）がこれだった。
            #    ⚠ body は浅い複製で、中身はライブラリと**共有している**。中を書き換えると
            #       同じ足形を使う他の部品にも伝染するので、節ごと作り直して差し替える
            lay2 = find1(body, "layer")
            if lay2 and "SilkS" in str(lay2[1]):
                def _thicken(node, key):
                    w = find1(node, key)
                    if w is None or float(w[1]) >= SILK_T:
                        return node
                    return [c if not (isinstance(c, list) and c[0] == key) else [key, str(SILK_T)]
                            for c in node]
                st = find1(body, "stroke")
                if st is not None:
                    body[body.index(st)] = _thicken(st, "width")
                elif find1(body, "width") is not None:      # 古い書き方の足形
                    body = _thicken(body, "width")
                eff = find1(body, "effects")                # fp_text の字の太さ
                if eff is not None:
                    fnt = find1(eff, "font")
                    if fnt is not None and find1(fnt, "thickness") is not None:
                        eff2 = list(eff)
                        eff2[eff2.index(fnt)] = _thicken(fnt, "thickness")
                        body[body.index(eff)] = eff2
            # uuid を持てるのは図形・文字・ゾーンだけ（他に足すと KiCad が読めない）
            if e[0].startswith("fp_") or e[0] == "zone":
                body = body + [["uuid", Str(uid())]]
            out.append(body)
    return out, fp


def seg(x1, y1, x2, y2, layer="Edge.Cuts", width=0.1):
    return ["gr_line", ["start", f"{x1:.3f}", f"{y1:.3f}"], ["end", f"{x2:.3f}", f"{y2:.3f}"],
            ["stroke", ["width", str(width)], ["type", "default"]], ["layer", Str(layer)],
            ["uuid", Str(uid())]]


def outline():
    """板の外形（44 × 81.2）と、上の縁の切り欠き。"""
    o = []
    # 左下 →（右回り）。上の辺は切り欠きで 2 本に割れる
    pts = outline_pts()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        o.append(seg(*bx(*a), *bx(*b)))
    # 柱が通る抜き（丸）
    for px, py, d in POSTS:
        X, Y = bx(px, py)
        o.append(["gr_circle", ["center", f"{X:.3f}", f"{Y:.3f}"],
                  ["end", f"{X + d / 2:.3f}", f"{Y:.3f}"],
                  ["stroke", ["width", "0.1"], ["type", "default"]], ["fill", "no"],
                  ["layer", Str("Edge.Cuts")], ["uuid", Str(uid())]])
    return o


def mounting_holes():
    """M2（φ2.2）4 つ。板 X 3.5 と 40.5・Y 3.5 と 69.5（37 × 66 の格子・🔒 筐体側 2026-09-13）。

    ⚠ DRC の lib_footprint_mismatch がこの 4 つで出る（2026-09-16・fp-lib-table を置いて
      検査が動くようになってから見えた）。**既知の差で、工場に出る物は一致している。**
        穴       np_thru_hole・円・(size 2.2 2.2)・(drill 2.2)  ← 元と完全に同じ
        layers   ここは "F&B.Cu"、元は "*.Cu"。2 層なので同じ意味
        欠け     元にある fp_circle 2 つ（Cmts.User の目印・F.CrtYd の枠）と fp_text と
                 attr の exclude_from_pos_files。どれもガーバーにもドリルにも出ない
      exclude_from_pos_files が無くても実装の位置ファイルには入らない。fab.py が
      --smd-only で出しているので、非メッキ穴はそもそも対象外（cpl.csv 48 行に留め穴は無い）。
      ⇒ この 4 件は残してよい。**別の名前の足形で mismatch が出たら、そちらは本物。**
    """
    o = []
    for mx, my in MOUNT:
        x, y = bx(mx, my)
        o.append(["footprint", Str("MountingHole:MountingHole_2.2mm_M2"), ["layer", Str("F.Cu")],
                  ["uuid", Str(uid())], ["at", f"{x:.3f}", f"{y:.3f}"], ["attr", "exclude_from_bom"],
                  ["pad", Str(""), "np_thru_hole", "circle", ["at", "0", "0"],
                   ["size", f"{MOUNT_D}", f"{MOUNT_D}"], ["drill", f"{MOUNT_D}"],
                   ["layers", Str("F&B.Cu"), Str("*.Mask")], ["uuid", Str(uid())]]])
    return o


# ---- シルク（読む人のための文字）----
# 🔴 板の上の文字は「自分で挿す口」のためだけに置く（2026-09-16 夕・ユーザー
#    「口の名前と極性を入れて、SMD の記号は消してください」）。
#    表面実装は JLCPCB が付けるので R15・C42 の記号は誰も読まない。読むのは
#    スルーホールの口を手で挿すときで、そこには番号（J4）しか出ていなかった。
#    名前は netlist の Value（"SPK IN" など）と同じ物を、印刷される層に出す。
SILK_H = 1.0          # 文字の高さ [mm]。製造の下限 0.8 に余裕を足す
SILK_T = 0.15         # 線の太さ [mm]。JLCPCB の下限ちょうど（記号の 0.12 は細すぎた）
SILK_GAP = 0.5        # 部品の枠から文字までの隙間 [mm]

# ref → (板に書く名前, 名前を置く向き)。向きは板の図面で N=上 S=下 W=左 E=右
# ⚠ 向きは**希望**。塞がっていれば silk() が残りの向きへ回し、回したことを画面に出す。
#    ここに書いてあるのは「回さずに収まる向き」なので、⚠ が出たら板の方が変わった合図。
SILK_PORT = {
    "J1":  ("XIAO",     "S"),
    "J2":  ("OLED",     "S"),
    "J4":  ("SPK IN",   "S"),   # W は U5 の枠に当たる。S は口の前の帯を外した下側
    "J5":  ("SPK OUT",  "N"),
    "J6":  ("BTN2",     "W"),   # S は挿したプラグの胴が出る帯（📄 ePH.pdf 1 ページ）
    "J7":  ("REED/TGL", "S"),
    "J10": ("BAT",      "W"),   # S は極性の ＋ − が先に座る
}
# 🔴 電池の極性。逆接で INA226 から煙が出た事故があるのに、板の上には一文字も無かった
#    （足形が持つピン 1 の小さな印だけ）。ネット名を出どころにして (ref, pin) で書く。
#    J10 は**裏**にあるので文字も B.SilkS に出る（鏡文字にする）。
SILK_POLARITY = {("J10", "2"): "+", ("J10", "1"): "-"}


def silk_text(txt, x, y, layer, just=None, h=SILK_H):
    e = ["effects", ["font", ["size", f"{h}", f"{h}"], ["thickness", str(SILK_T)]]]
    if just:
        # ⚠ justify の left／right／mirror は**裸の語**で書く。Str() で括ると KiCad が
        #    「'quoted string' が来た」と言って板ごと読めなくなる（2026-09-16 夕に踏んだ）
        e.append(["justify"] + list(just))
    return ["gr_text", Str(txt), ["at", f"{x:.3f}", f"{y:.3f}"], ["layer", Str(layer)],
            ["uuid", Str(uid())], e]


def text_w(txt, h=SILK_H):
    """KiCad の線の書体のおおよその幅 [mm]（板からはみ出していないかを見るだけ）。"""
    return len(txt) * h * 0.8


def silk(placed, boxes):
    """自分で挿す口の名前と、電池の極性を置く。

    位置は**置いたあとの枠**（relax を回したあとの courtyard）から決める。口が動いても
    文字が付いて回るように、数字をここに写さない。

    ⭐ 2026-09-16 夕に**当たり判定**を付けた。それまでは SILK_PORT に書いた向きへ黙って
    置くだけで、`J5 SPK OUT` と `J6 BTN2` が 1.2mm しか離れず「J5 SPK OUTJ6 BTN2」と
    一続きに読めていた（DRC は通る。文字どうしが触れてはいないので）。
    向きは希望として使い、**他の文字・部品の枠・パッド・板の縁**に当たるなら残りの向きへ回す。
    """
    out, warn = [], []
    box = dict(boxes)
    lim = (ORG[0], ORG[1], ORG[0] + BOARD_L, ORG[1] + BOARD_W)
    SIDES = ("N", "E", "S", "W")
    CLR = 0.3        # 文字のまわりに空けるすきま [mm]

    def inside(b):
        return b[0] >= lim[0] and b[1] >= lim[1] and b[2] <= lim[2] and b[3] <= lim[3]

    def hit(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    # ---- 避ける物を集める（面ごと）----
    pads = {"F": [], "B": []}
    for f in placed:
        at = find1(f, "at")
        fx, fy = float(at[1]), float(at[2])
        fa = float(at[3]) if len(at) > 3 else 0.0
        for q in find(f, "pad"):
            pa, sz = find1(q, "at"), find1(q, "size")
            if not sz:
                continue
            dx, dy = rot_xy(float(pa[1]), float(pa[2]), fa)
            r = max(float(sz[1]), float(sz[2])) / 2      # 向きを見ずに外接の丸で見る（安全側）
            lay = str(find1(q, "layers"))
            bb = (fx + dx - r, fy + dy - r, fx + dx + r, fy + dy + r)
            for side, nm in (("F", "F.Cu"), ("B", "B.Cu")):
                if nm in lay or "*.Cu" in lay:
                    pads[side].append(bb)

    # ---- 挿さったプラグの胴が板の上に出る帯 ----
    # 🔴 横挿しの口は、プラグの胴が口の前へ **courtyard の縁から PLUG_BODY** 出る。
    #    ここに文字を置くと DRC は通るのに**プラグで隠れて読めない**（📄 ePH.pdf 1 ページ）。
    #    帯の作り方は通り道の検査（build）と同じ plug_band に閉じる。数字をここに写さない。
    #    ⚠ plug_band と open_dir は **板の座標**で話すので、図面の座標へ直してから使う。
    fps = {}
    for f in placed:
        rs = [pr[2] for pr in find(f, "property") if str(pr[1]) == "Reference"]
        if rs:
            fps[str(rs[0])] = f

    def to_board(b):
        return (b[0] - ORG[0], BOARD_W - (b[3] - ORG[1]), b[2] - ORG[0], BOARD_W - (b[1] - ORG[1]))

    def to_draw(b):
        return (b[0] + ORG[0], ORG[1] + BOARD_W - b[3], b[2] + ORG[0], ORG[1] + BOARD_W - b[1])

    crt = {"F": [], "B": []}
    for r, b in boxes:
        crt["B" if r in BACK_SIDE else "F"].append((r, b))

    plugs = {"F": [], "B": []}
    for ref in CONN:
        if ref not in box or ref not in fps:
            continue
        f = fps[ref]
        at = find1(f, "at")
        ang = float(at[3]) if len(at) > 3 else 0.0
        d = open_dir(f, float(at[1]), float(at[2]), ang)
        band = to_draw(plug_band(to_board(box[ref]), d, PLUG_BODY))
        plugs["B" if ref in BACK_SIDE else "F"].append((ref, band))

    def blocked(bb, back, soft=False):
        """bb に何か居るか。soft=True なら部品の枠は見ない（最後の逃げ場）。"""
        if not inside(bb):
            return "板の外"
        for t in texts:
            if hit(bb, t):
                return "別の文字"
        for b in pads["B" if back else "F"]:
            if hit(bb, b):
                return "パッド"
        for r, b in plugs["B" if back else "F"]:
            if hit(bb, b):
                return f"{r} に挿したプラグの胴"
        if not soft:
            # ⚠ 枠は**同じ面の物だけ**。板の反対側に居る部品の胴は、この面のシルクを隠さない
            #    （これを面ごとにしないと、裏の J10 の極性が表の USB-C の枠に塞がれる）
            for r, b in crt["B" if back else "F"]:
                if hit(bb, b):
                    return f"{r} の枠"
        return None

    texts = []       # 置いた文字の枠（次の文字はここを避ける）

    def put(txt, ref, side, h, back, anchor):
        """anchor（枠）の side 側へ txt を置く。当たるなら他の向きを試す。"""
        x0, y0, x1, y1 = anchor
        w = text_w(txt, h)
        for soft in (False, True):
            for sd in (side,) + tuple(t for t in SIDES if t != side):
                if sd in ("N", "S"):
                    cx = (x0 + x1) / 2
                    cy = y0 - SILK_GAP - h / 2 if sd == "N" else y1 + SILK_GAP + h / 2
                    just = ["mirror"] if back else None
                    bb = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                else:
                    cy = (y0 + y1) / 2
                    cx = x0 - SILK_GAP if sd == "W" else x1 + SILK_GAP
                    j = "right" if sd == "W" else "left"
                    if back:                       # 裏は鏡なので左右の寄せも入れ替わる
                        j = "left" if j == "right" else "right"
                    just = [j] + (["mirror"] if back else [])
                    bb = ((cx - w, cy - h / 2, cx, cy + h / 2) if sd == "W"
                          else (cx, cy - h / 2, cx + w, cy + h / 2))
                why = blocked((bb[0] - CLR, bb[1] - CLR, bb[2] + CLR, bb[3] + CLR), back, soft)
                if why:
                    continue
                if sd != side:
                    warn.append(f"{ref}「{txt}」は {side} が塞がっていたので {sd} へ回した")
                if soft:
                    warn.append(f"{ref}「{txt}」は部品の枠の上に乗せた（他に空きが無い）")
                texts.append(bb)
                out.append(silk_text(txt, cx, cy, "B.SilkS" if back else "F.SilkS", just, h=h))
                return True
        warn.append(f"{ref}「{txt}」を置く場所が無い")
        return False

    # ---- 先に極性。パッドの真ん中から、口の枠の外へまっすぐ逃がす ----
    pad_at = {}
    for f in placed:
        rs = [pr[2] for pr in find(f, "property") if str(pr[1]) == "Reference"]
        if not rs:
            continue
        at = find1(f, "at")
        fx, fy = float(at[1]), float(at[2])
        fa = float(at[3]) if len(at) > 3 else 0.0
        for q in find(f, "pad"):
            if not str(q[1]):
                continue
            pa = find1(q, "at")
            dx, dy = rot_xy(float(pa[1]), float(pa[2]), fa)
            pad_at[(str(rs[0]), str(q[1]))] = (fx + dx, fy + dy)

    pol_h = SILK_H * 1.4        # 極性は少し大きく（一番読めないと困る文字）
    for (ref, pin), mark in sorted(SILK_POLARITY.items()):
        if (ref, pin) not in pad_at or ref not in box:
            warn.append(f"{ref}.{pin} が見つからないので極性を置けない")
            continue
        px, py = pad_at[(ref, pin)]
        x0, y0, x1, y1 = box[ref]
        # 2 つのパッドが並んでいる軸を見て、**直角の向き**へ逃がす。
        # パッドの真上／真横に置きたいので、枠は「そのパッドの列」に細めて渡す
        pins = [v for (r, _), v in pad_at.items() if r == ref]
        horiz = (max(q[0] for q in pins) - min(q[0] for q in pins)
                 >= max(q[1] for q in pins) - min(q[1] for q in pins))
        anchor = ((px, y0, px, y1) if horiz else (x0, py, x1, py))
        put(mark, f"{ref}.{pin}", "S" if horiz else "E", pol_h, ref in BACK_SIDE, anchor)

    # ---- 口の名前（番号と一緒に「J5 SPK OUT」の形で置く）----
    for ref, (name, side) in sorted(SILK_PORT.items()):
        if ref not in box:
            warn.append(f"{ref} が板に無いので名前を置けない")
            continue
        put(f"{ref} {name}", ref, side, SILK_H, ref in BACK_SIDE, box[ref])

    print(f"  シルク: 口の名前 {len(SILK_PORT)} 個・極性 {len(SILK_POLARITY)} 個")
    for w in warn:
        print(f"  ⚠ シルク {w}")
    return out


def vbus_zone():
    """🔴 USB-C の足元に VBUS の小さなベタを置く（2026-09-13）。

    J13 の VBUS は A4・B4・A9・B9 の 4 パッドあり、真ん中の A4 が両隣の信号に囲まれて
    自動配線が届かなかった（未配線 1 本がこれだけ残った）。口の足元にベタを敷けば 4 つが
    まとめてつながる。ふつうの板でも電源はこう引く。
    """
    # ⭐ 2026-09-16: 口を右の縁から前の縁へ移したとき、この長方形が置き去りになって
    #    板の右端に VBUS の島（isolated_copper）が残った。**口の向きに追従させる。**
    #    パッドの列は足形の原点から 4.04 内側（口の反対側）にある。
    x, y, ang = PLACE["J13"]
    d = 4.04
    cx, cy = {0: (x, y + d), 90: (x - d, y), 180: (x, y - d), 270: (x + d, y)}[int(ang) % 360]
    hw, hh = (5.6, 1.6) if int(ang) % 180 == 0 else (1.6, 5.6)
    r = (cx - hw, cy - hh, cx + hw, cy + hh)      # 板の座標での長方形（パッドの列を覆う）
    pts = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    poly = ["polygon", ["pts"] + [["xy", f"{bx(*q)[0]:.3f}", f"{bx(*q)[1]:.3f}"] for q in pts]]
    return [["zone", ["net", str(NETNUM["VBUS"])], ["net_name", Str("VBUS")],
             ["layer", Str("F.Cu")], ["uuid", Str(uid())], ["name", Str("VBUS")],
             ["priority", "1"], ["hatch", "edge", "0.5"],
             ["connect_pads", "yes", ["clearance", "0.25"]],
             ["min_thickness", "0.25"], ["filled_areas_thickness", "no"],
             ["fill", "yes", ["thermal_gap", "0.2"], ["thermal_bridge_width", "0.5"]],
             poly]]


def fp_lib_table(items):
    """足形のライブラリの表（fp-lib-table）を板から作る（2026-09-16）。

    ⭐ これが無いと kicad-cli の DRC は「ライブラリが構成に含まれていません」を足形の数だけ出して、
      **「板の足形が元のライブラリと同じ形か」の検査を丸ごと諦める**（v6.1 では 59 件＝全数）。
      59 件は「問題が 59 個」ではなく「1 度も検査していない」という意味だった。
    置くだけで検査が動く。⚠ 警告 0 になるのではなく、**本当の差が出るようになる**のが目的。
    パスは ${KICAD10_FOOTPRINT_DIR}（KiCad が解く）で書く。PC ごとに KiCad の場所が違うので
    絶対パスにしない（kicad_paths.py の注と同じ理由）。
    """
    # ⚠ placed だけでは足りない。留め穴は mounting_holes() が別に足すので、板の全体から拾う
    libs = sorted({str(e[1]).split(":")[0] for e in items
                   if isinstance(e, list) and e and e[0] == "footprint"})
    rows = ["(fp_lib_table", "  (version 7)"]
    for n in libs:
        uri = ("${KIPRJMOD}/../%s.pretty" % n) if n == "katanori" else ("${KICAD10_FOOTPRINT_DIR}/%s.pretty" % n)
        rows.append('  (lib (name "%s")(type "KiCad")(uri "%s")(options "")(descr ""))' % (n, uri))
    rows.append(")")
    (OUT / "fp-lib-table").write_text(chr(10).join(rows) + chr(10), encoding="utf-8")
    return libs


def ep_vias(placed, nets):
    """放熱パッド（EP）に GND のビアを 2×2 で打つ（2026-09-16・ステップ 3）。

    U1（TPS61090・EP 2.7×2.7）も U2（MCP73871・EP 2.5×2.5）も、データシートは
    「EP をグラウンド面へビアで落とす」前提である。2 層で表の GND ベタだけだと裏へ熱が逃げない。
    MCP73871 は 1A 充電で 1W 近く出る。
    ⚠ 置く場所は **その時の配置から計算する**。座標を書き写すと、部品を動かしたとき置き去りになる
      （USB-C を動かしたとき VBUS のベタが板の右端に残った・同日）。
    穴は縫いのビアと同じ φ0.6/0.3（新しい穴の種類を増やさない）。
    """
    out = []
    for fp in placed:
        ref = next((str(e[2]) for e in find(fp, "property") if str(e[1]) == "Reference"), None)
        if ref not in ("U1", "U2"):
            continue
        fat = find1(fp, "at")
        fx, fy, fa = float(fat[1]), float(fat[2]), float(fat[3]) if len(fat) > 3 else 0.0
        for pad in find(fp, "pad"):
            sz = find1(pad, "size")
            w, h = float(sz[1]), float(sz[2])
            if w < 2.0 or h < 2.0:                     # EP だけ（ふつうのパッドは 1mm 以下）
                continue
            pat = find1(pad, "at")
            dx, dy = rot_xy(float(pat[1]), float(pat[2]), fa)
            cx, cy = fx + dx, fy + dy
            ox, oy = w / 4, h / 4                      # 2×2（EP の四半分の芯）
            for sx in (-1, 1):
                for sy in (-1, 1):
                    out.append(["via", ["locked", "yes"], ["at", f"{cx + sx * ox:.4f}", f"{cy + sy * oy:.4f}"],
                                ["size", "0.6"], ["drill", "0.3"],
                                ["layers", Str("F.Cu"), Str("B.Cu")],
                                ["net", str(nets["GND"])], ["uuid", Str(uid())]])
    return out


def pad_box(placed, ref, num):
    """置いた足形からパッドの (中心x, 中心y, 幅, 高さ) を出す（板の図面の座標）。"""
    for fp in placed:
        r = next((str(e[2]) for e in find(fp, "property") if str(e[1]) == "Reference"), None)
        if r != ref:
            continue
        fat = find1(fp, "at")
        fx, fy, fa = float(fat[1]), float(fat[2]), float(fat[3]) if len(fat) > 3 else 0.0
        for pad in find(fp, "pad"):
            if str(pad[1]) != num:
                continue
            pat, sz = find1(pad, "at"), find1(pad, "size")
            dx, dy = rot_xy(float(pat[1]), float(pat[2]), fa)
            w, h = float(sz[1]), float(sz[2])
            if (float(pat[3]) if len(pat) > 3 else 0.0) % 180 == 90:
                w, h = h, w
            return fx + dx, fy + dy, w, h
    raise SystemExit("パッドが見つからない: %s.%s" % (ref, num))


def kelvin_tracks(placed):
    """シャント R41 のケルビンの線 2 本を、置いてある R41 と U3 から作る。

    電流は R41 の中を X 方向に流れる（右の 1 番から左の 2 番へ）。センスは
    **パッドの内側の縁から、電流と直角に**出す。ここを守らないと途中の銅が
    シャントに足し算され、INA226 が読み違える（並べ直す前は 10mΩ に 86.7mΩ が
    足されて 9.7 倍だった）。
    ⚠ 座標を書き写さない。書き写すと R41 か U3 を動かしたとき線がパッドから外れ、
      しかも **DRC は未接続を出さない**（別経路で繋がるため）ので黙って 10 倍に戻る。
    """
    out = []
    for rpad, upad, net in (("1", "10", "BATP"), ("2", "8", "VLIPO")):
        rx, ry, rw, rh = pad_box(placed, "R41", rpad)
        ox, _, _, _ = pad_box(placed, "R41", "2" if rpad == "1" else "1")
        ux, uy, _, uh = pad_box(placed, "U3", upad)
        inner = rx - rw / 2 if ox < rx else rx + rw / 2      # 相手のパッドを向いた縁
        tap_x = inner + (0.18 if ox < rx else -0.18)
        tap_y = ry - rh / 2 + 0.075 if uy < ry else ry + rh / 2 - 0.075
        end_y = uy + uh / 2 - 0.24 if uy < ry else uy - uh / 2 + 0.24
        mid_y = tap_y - 1.2 if uy < ry else tap_y + 1.2
        out.append((net, "F.Cu", 0.25, [(round(tap_x, 3), round(tap_y, 3)),
                                        (round(ux, 3), round(mid_y, 3)),
                                        (round(ux, 3), round(end_y, 3))]))
    return out


def escape_stub(placed, ref, num, net, length=1.2, w=0.25):
    """細ピッチのパッドから、部品の外へまっすぐ出す短い線を作る。

    QFN の 0.5mm ピッチの辺は、隣のパッドとの廊下が 0.25mm しかなく、自動配線が
    通せずにそのピンだけ浮かせることがある（U2 の 9 番 VBUS で何度も起きた）。
    パッドの列の外まで出してやれば、その先は自動配線が拾う。
    向きは **部品の中心からパッドへ**の向き（長い辺の軸）で決める。
    """
    px, py, pw, ph = pad_box(placed, ref, num)
    for fp in placed:
        r = next((str(e[2]) for e in find(fp, "property") if str(e[1]) == "Reference"), None)
        if r == ref:
            fat = find1(fp, "at")
            cx, cy = float(fat[1]), float(fat[2])
            break
    if ph >= pw:                      # 縦長のパッド ＝ 上下の辺 ⇒ Y へ出す
        d = ph / 2 + length
        end = (px, py + d if py > cy else py - d)
    else:                             # 横長 ＝ 左右の辺 ⇒ X へ出す
        d = pw / 2 + length
        end = (px + d if px > cx else px - d, py)
    return (net, "F.Cu", w, [(round(px, 3), round(py, 3)), (round(end[0], 3), round(end[1], 3))])


def pre_tracks(nets):
    """PRE_TRACKS を板の要素（locked を付けた segment）にする。"""
    out = []
    for net, lay, w, pts in PRE_TRACKS + _KELVIN:
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if f"{xa:.4f},{ya:.4f}" == f"{xb:.4f},{yb:.4f}":
                continue
            out.append(["segment", ["start", f"{xa:.4f}", f"{ya:.4f}"], ["end", f"{xb:.4f}", f"{yb:.4f}"],
                        ["width", f"{w:.3f}"], ["locked", "yes"], ["layer", Str(lay)],
                        ["net", str(nets[net])], ["uuid", Str(uid())]])
    return out


def gnd_zone():
    """🔴 裏面に GND のベタを敷く（2026-09-13）。

    GND は 47 パッドあって全ネットの中で断然いちばん多く、これを自動配線に引かせると
    板が詰まって別のネットが残る（EN と VSYS が 2 本落ちた）。ベタにすれば自動配線から
    47 パッドぶんが消え、同時に戻りの経路も良くなる。
    ⚠ ベタ任せにするとパッドが島に取り残されることがある。**それは KiCad の DRC が
    unconnected_items で出す**ので、検査で捕まえられる。
    """
    pts = outline_pts()
    poly = ["polygon", ["pts"] + [["xy", f"{bx(*q)[0]:.3f}", f"{bx(*q)[1]:.3f}"] for q in pts]]
    # 🔴 **両面に敷く。**裏だけだと、表面実装の GND パッド（この板の GND のほとんど）が
    #    裏のベタに届かない（2026-09-13・裏だけで試したら 40 パッドが未接続で出た）。
    return [["zone", ["net", str(NETNUM["GND"])], ["net_name", Str("GND")],
             ["layer", Str(lay)], ["uuid", Str(uid())], ["name", Str("GND")],
             ["hatch", "edge", "0.5"],
             # 🔴 パッドはベタ直結（thermal relief を使わない）。
             #    足付きの部品だけ thermal にすると、PH や USB-C のシェルのように **幅 1.0mm の
             #    細いパッド**で spoke が 1 本しか立たず、KiCad が starved_thermal（error）を出す。
             #    橋の幅を 0.4〜1.2 で振っても 1 件は残った（2026-09-13）。
             #    ⚠ 代償: 手はんだする足付きの GND（J2・J4・J5・J6・J10・J14 の 7 点）に熱が逃げる。
             #    2 層 1oz なので実害は小さいと見ているが、組むときに温度が要るなら記録すること。
             ["connect_pads", "yes", ["clearance", "0.3"]],
             ["min_thickness", "0.25"], ["filled_areas_thickness", "no"],
             ["fill", "yes", ["thermal_gap", "0.2"], ["thermal_bridge_width", "0.5"]],
             [x for x in poly]] for lay in ("F.Cu", "In1.Cu", "B.Cu")]


NETNUM = {}
INSTS = []
NPTH = []      # 金属化していない穴のまわり（銅を置かせない四角）
# ⚠ 絵のためだけの 3D モデルの差し替え。KiCad 10 は TYPE-C-31-M-12 のモデルを同梱していないので、
#    ピン数と向きが同じ別の USB-C（GCT USB4105・16P 横挿し）を見た目の確認用に割り当てる。
#    **実際に載る部品は C165948（TYPE-C-31-M-12）のままで、足形も変えていない。**
MODEL_VIS = {"J13": ("${KICAD10_3DMODEL_DIR}/Connector_USB.3dshapes/"
                     "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step", (0.0, 0.365, 0.0))}
# 🔒 筐体側が座標を決めた部品。押し離しの対象にしない（動かすと筐体と合わなくなる）
# 🔴 口も動かさない（2026-09-13）。押し離しは**動かす前の**枠からプラグの通り道を作るので、
#    口が動くと通り道だけが取り残され、他の部品がそこへ流れ込む（J2 の通り道に R41 が残った）。
#    口の位置はどれも総当たりで決めた値なので、動かす理由も無い
FIXED = {"J13", "J1", "J14", "U4", "SW1", "J2", "J4", "J5", "J6", "J10"}
MARGIN = 0.5      # 板の縁から部品の枠まで


def fp_pad(p):
    """足形のパッド 1 つ → dsn.py に渡す形。"""
    at = find1(p, "at")
    sz = find1(p, "size")
    return dict(num=str(p[1]), type=str(p[2]), shape=str(p[3]),
                size=(float(sz[1]), float(sz[2])),
                at=(float(at[1]), float(at[2])),
                rot=float(at[3]) if len(at) > 3 else 0.0)


def relax(placed, boxes, rounds=3000):
    """枠が重なっている部品を少しずつ押し離す。🔒 FIXED（筐体側が決めた座標）は動かさない。

    置いた位置の狙い（上の PLACE）は残したいので、動かすのは重なっている分だけにする。
    """
    idx = {b[0]: i for i, b in enumerate(boxes)}
    movable = set(PLACE) - FIXED
    lo = (ORG[0] + MARGIN, ORG[1] + MARGIN)
    hi = (ORG[0] + BOARD_L - MARGIN, ORG[1] + BOARD_W - MARGIN)

    def shift(ref, dx, dy):
        i = idx[ref]
        r, (x0, y0, x1, y1) = boxes[i]
        dx = max(lo[0] - x0, min(hi[0] - x1, dx))
        dy = max(lo[1] - y0, min(hi[1] - y1, dy))
        boxes[i] = (r, (x0 + dx, y0 + dy, x1 + dx, y1 + dy))
        at = find1(placed[i], "at")
        at[1] = f"{float(at[1]) + dx:.3f}"
        at[2] = f"{float(at[2]) + dy:.3f}"
        for it in INSTS:      # 自動配線へ渡す座標も一緒に動かす（別々に持つと片方だけ動く）
            if it["ref"] == ref:
                it["x"] += dx
                it["y"] += dy
        return dx, dy

    # 板の外へ出ている物と、切り欠き・磁石の柱に掛かっている物を先に押し戻す
    blocks = [bx(n[0], n[2]) + bx(n[1], BOARD_W) for n in NOTCHES]
    blocks.append(bx(KEEPOUT_MAGNET[0], KEEPOUT_MAGNET[1]) + bx(KEEPOUT_MAGNET[2], KEEPOUT_MAGNET[3]))
    # 🔴 取付穴（無メッキ）が部品の枠の中に入ると KiCad の DRC が npth_inside_courtyard で落ちる。
    #    配線まで回してから気づくと遠いので、置く段階で押し出す（2026-09-13 に J4 で踏んだ）
    for mxy in MOUNT:
        cx, cy = bx(*mxy)
        r = MOUNT_D / 2 + MOUNT_KEEP
        blocks.append((cx - r, cy - r, cx + r, cy + r))
    for px, py, d in POSTS:                 # 柱の抜き
        cx, cy = bx(px, py)
        r = d / 2 + POST_KEEP
        blocks.append((cx - r, cy - r, cx + r, cy + r))
    # 🔴 口の前の「プラグの通り道」も押し出す所に入れる。入れないと、他の部品が後から
    #    そこへ流れ込む（2026-09-13・電源ブロックを広げたら J2 の通り道に U1 と R13 が入った）。
    #    位置は PLACE の初期値から作る（口はほとんど動かない）。自分の通り道では押されない
    exempt = {}
    for ref, (side, need) in CONN.items():
        if ref not in PLACE:
            continue
        x, y, ang = PLACE[ref]
        ang = 0 if not isinstance(ang, int) else ang
        b = boxes[idx[ref]][1]
        at = find1(placed[idx[ref]], "at")
        dx, dy = open_dir(placed[idx[ref]], float(at[1]), float(at[2]), ang)
        # 🔴 押し離すのは**相手の胴 3.1** だけ。残り（指と曲がり）まで押すと、
        #    板の真ん中に 10mm の空き地が 5 つできて押し離しが発散した（2026-09-13）。
        #    指の側は検査で「何が下に居るか」を出すだけにする
        need = PLUG_KEEP
        if dx:
            r = (b[2], b[1], b[2] + need, b[3]) if dx > 0 else (b[0] - need, b[1], b[0], b[3])
        else:   # 板の座標の +Y は図面の −Y
            r = (b[0], b[1] - need, b[2], b[1]) if dy > 0 else (b[0], b[3], b[2], b[3] + need)
        # 🔴 通り道のうち**板の外**の部分は、板の上の部品を押す理由が無い（そこに部品は置けない）。
        #    板へ切り詰めてから入れる。2026-09-13、切り詰めずに入れて押し離しが発散した
        r = (max(min(r[0], r[2]), ORG[0]), max(min(r[1], r[3]), ORG[1]),
             min(max(r[0], r[2]), ORG[0] + BOARD_L), min(max(r[1], r[3]), ORG[1] + BOARD_W))
        if r[2] - r[0] < 1e-6 or r[3] - r[1] < 1e-6:
            continue
        exempt[len(blocks)] = ref
        blocks.append(r)
    blocks = [(min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3])) for b in blocks]
    for ref in movable:
        shift(ref, 0.0, 0.0)
    for _ in range(rounds):
        moved = False
        pairs = [(boxes[i], boxes[j]) for i in range(len(boxes)) for j in range(i + 1, len(boxes))]
        for (ra, a), (rb, b) in pairs:
            # ⭐ 2026-09-16 夕: **表と裏の物どうしは押し離さない**。板を挟んで別の側に居るので当たらない。
            #    入れていなかったとき、J10（裏）から押される Q2 が板の縁にも押し返されて
            #    「押し離しが収束しなかった」になった
            if (ra in BACK_SIDE) != (rb in BACK_SIDE):
                continue
            a = boxes[idx[ra]][1]
            b = boxes[idx[rb]][1]
            ov_x = min(a[2], b[2]) - max(a[0], b[0])
            ov_y = min(a[3], b[3]) - max(a[1], b[1])
            if ov_x <= 0 or ov_y <= 0:
                continue
            free = [r for r in (ra, rb) if r in movable]
            if not free:
                continue
            push = (min(ov_x, ov_y) + 0.15) / len(free)
            ax = (a[0] + a[2]) / 2 < (b[0] + b[2]) / 2
            ay = (a[1] + a[3]) / 2 < (b[1] + b[3]) / 2
            for r in free:
                if ov_x <= ov_y:
                    shift(r, (1 if (r == rb) == ax else -1) * push, 0)
                else:
                    shift(r, 0, (1 if (r == rb) == ay else -1) * push)
            moved = True
        # 切り欠きと磁石の柱から押し出す
        for ref in movable:
            x0, y0, x1, y1 = boxes[idx[ref]][1]
            for ki, k in enumerate(blocks):
                if exempt.get(ki) == ref:
                    continue
                ox = min(x1, k[2]) - max(x0, k[0])
                oy = min(y1, k[3]) - max(y0, k[1])
                if ox > 0 and oy > 0:
                    if ox <= oy:
                        shift(ref, (ox + 0.2) * (1 if (x0 + x1) / 2 > (k[0] + k[2]) / 2 else -1), 0)
                    else:
                        shift(ref, 0, (oy + 0.2) * (1 if (y0 + y1) / 2 > (k[1] + k[3]) / 2 else -1))
                    moved = True
        if not moved:
            return
    print("  ⚠ 押し離しが収束しなかった")


def build():
    solve_fixed()
    comps, pads, nets = netlist()
    NETNUM.update(nets)
    placed, boxes = [], []
    THPAD = {}          # ref → 板を貫くパッドの枠（図面の座標）。裏表が違う部品どうしの当たりに使う
    FABBOX = {}         # ref → 胴の枠（図面の座標・F.Fab／B.Fab）

    def add(ref, x, y, ang):
        back = ref in BACK_SIDE
        fpnode, raw = place_footprint(ref, comps[ref], x, y, ang, pads, back=back)
        placed.append(fpnode)
        boxes.append((ref, courtyard(raw, x, y, ang)))
        FABBOX[ref] = courtyard(raw, x, y, ang, key="Fab")   # 胴（逃げ抜き）。裏表が違う物どうしの当たりに使う
        INSTS.append(dict(ref=ref, fp=comps[ref]["fp"], x=x, y=y, ang=ang,
                          pads=[fp_pad(p) for p in find(raw, "pad")
                                if str(p[1]) and str(p[2]) != "np_thru_hole"]))
        # 🔴 金属化していない穴（位置決めの穴）も銅を置かせない。伝え忘れると配線が穴すれすれを通る
        #    （2026-09-12・USB-C の受け口で 0.015mm まで寄った）
        for q in find(raw, "pad"):
            if str(q[2]) != "np_thru_hole":
                continue
            d = fp_pad(q)
            dx, dy = rot_xy(d["at"][0], d["at"][1], ang)
            NPTH.append((ref, dx, dy, max(d["size"]) / 2 + 0.3))
        # 🔴 板を**貫く**パッド（thru_hole と np_thru_hole）。裏表が違う部品どうしの当たりは
        #    これだけが本物になる（胴は板を挟んで別の側に居るので当たらない）
        th = []
        for q in find(raw, "pad"):
            if str(q[2]) not in ("thru_hole", "np_thru_hole"):
                continue
            d = fp_pad(q)
            dx, dy = rot_xy(d["at"][0], d["at"][1], ang)
            w, h = d["size"]
            if abs(ang) % 180 == 90:
                w, h = h, w
            th.append((x + dx - w / 2, y + dy - h / 2, x + dx + w / 2, y + dy + h / 2))
        THPAD[ref] = th

    # 置く（板の座標 → 図面の座標）
    # 🔴 縦のピンソケットの足形のパッドは**局所 +Y** に並ぶ（+X ではない）。板の +X へ並べるには 270 度。
    # 🔴 J10 は**板の裏（B.Cu）**に置いてある（BACK_SIDE）。足形が鏡になって 2 ピンの並び
    #    （どちらが VBAT か）が入れ替わるので、置いたあとの座標を CHECK_PADS で必ず検算する。
    #    電池の極性を間違えると煙が出る（docs/PCB-V61.md 8 章）。
    for ref, v in PLACE.items():
        x, y, ang = v
        X, Y = bx(x, y)
        add(ref, X, Y, ang)

    relax(placed, boxes)
    out_of_board = []
    lim = (ORG[0], ORG[1], ORG[0] + BOARD_L, ORG[1] + BOARD_W)
    for ref, b in boxes:
        if ref in FIXED:      # USB-C とスイッチは口とレバーが板の外へ出るのが正しい
            continue
        d = max(lim[0] - b[0], lim[1] - b[1], b[2] - lim[2], b[3] - lim[3])
        if d > 1e-6:
            out_of_board.append((ref, round(d, 2)))
    for ref, d in out_of_board:
        print(f"  板からはみ出し {ref}: {d} mm")

    # 🔴 角度の検算。板の座標で「このパッドはここに来るはず」と突き合わせる（鏡像事故はここで止める）
    fps = {[pr[2] for pr in find(f, "property") if str(pr[1]) == "Reference"][0]: f for f in placed}
    at_of = {find1(f, "uuid")[1]: f for f in placed}
    bad_pad = []
    for f in placed:
        ref = [pr[2] for pr in find(f, "property") if str(pr[1]) == "Reference"][0]
        at = find1(f, "at")
        fx, fy = float(at[1]), float(at[2])
        fa = float(at[3]) if len(at) > 3 else 0.0
        for q in find(f, "pad"):
            key = (str(ref), str(q[1]))
            if key not in CHECK_PADS:
                continue
            pa = find1(q, "at")
            dx, dy = rot_xy(float(pa[1]), float(pa[2]), fa)
            bxx, byy = fx + dx - ORG[0], BOARD_W - (fy + dy - ORG[1])
            wx, wy = CHECK_PADS[key]
            # ⭐ 2026-09-16: None は「その軸は足形の並びに任せる」。USB-C を右の縁から前の縁へ
            #    移したので、見る軸が X から Y へ変わった。どちらの軸も None にできるようにした
            if wy is None:
                wy = round(byy, 2)
            if wx is None:
                wx = round(bxx, 2)
            if abs(bxx - wx) > 0.02 or abs(byy - wy) > 0.02:
                bad_pad.append((key, round(bxx, 2), round(byy, 2), wx, wy))
    for key, gx, gy, wx, wy in bad_pad:
        print(f"  🔴 パッドの位置が違う {key[0]}.{key[1]}: 板 ({gx}, {gy})、{wx}, {wy} のはず")
    if not bad_pad:
        print(f"  パッドの位置の検算 {len(CHECK_PADS)} 点すべて一致")

    # 🔴 取付穴どうし・取付穴と柱の芯間。ねじの頭とナットが並ぶか。
    #    2026-09-13、上の 2 つが OLED の柱から 2.309 しか離れておらず、頭もナットも入らなかった。
    #    枠の重なりだけ見ていて、**ねじを回す物どうしの間隔**を見ていなかった
    sp = []
    for i, (ax, ay) in enumerate(MOUNT):
        for bx2, by2 in MOUNT[i + 1:]:
            d = math.hypot(ax - bx2, ay - by2)
            if d < NUT_R * 2:
                sp.append(f"取付穴 ({ax}, {ay}) ↔ ({bx2}, {by2}): 芯間 {d:.2f}（{NUT_R * 2:.2f} 要る）")
        for px, py, pd in POSTS:
            need = NUT_R + pd / 2 + POST_KEEP
            d = math.hypot(ax - px, ay - py)
            if d < need:
                sp.append(f"取付穴 ({ax}, {ay}) ↔ 柱 ({px}, {py}) φ{pd}: 芯間 {d:.2f}（{need:.2f} 要る）")
    for s in sp:
        print("  🔴 ねじが並ばない " + s)
    if not sp:
        print(f"  取付穴 {len(MOUNT)} か所・柱 {len(POSTS)} 本、ねじの頭とナットが並ぶ間隔がある")

    # 🔴 取付穴のナットの下。銅ではなく **部品** が入っていないか（MOUNT_KEEP とは別の検査）
    nut = []
    for mx, my in MOUNT:
        for ref, b in boxes:
            x0, y0 = b[0] - ORG[0], BOARD_W - b[3] + ORG[1]
            x1, y1 = b[2] - ORG[0], BOARD_W - b[1] + ORG[1]
            cx, cy = min(max(mx, x0), x1), min(max(my, y0), y1)
            d = math.hypot(mx - cx, my - cy)
            if d < NUT_R - 1e-9:
                # 🔒 2026-09-13 筐体側: (40.5, 3.5) はブラケットと共締めで、ナットは板の面ではなく
                #    **ブラケットの足の上**（BRK_FT 2.15 ⇒ ナットの底 6.75）に座る。U4 の天面 6.45 を
                #    0.30 の隙間で宙で跨ぐので、平面で重なっていても当たらない
                if (ref, mx, my) == ("U4", 40.5, 3.5):
                    continue
                nut.append((mx, my, ref, round(NUT_R - d, 2)))
    for mx, my, ref, over in nut:
        print(f"  🔴 ナットの下に部品 ({mx}, {my}) ↔ {ref}: {over} mm 食い込む")
    if not nut:
        print(f"  取付穴 {len(MOUNT)} か所ともナット（対角 4.62・背 1.6）の下は空いている")

    # 🔴 パッドと「板に開いた穴」の間。枠（courtyard）は柱を避けていても、**パッドは避けていない**。
    #    2026-09-13、J2 を 180° 回したらパッドが枠の反対の端へ移り、柱の抜きに SCL と SDA が乗った
    #    （KiCad の copper_edge_clearance 0.000）。配線まで回さないと出ないので、置く段階で見る。
    holes = [(px, py, d / 2) for px, py, d in POSTS] + [(mx, my, MOUNT_D / 2) for mx, my in MOUNT]
    CLR_EDGE = 0.3
    onhole = []
    for f in placed:
        ref = [pr[2] for pr in find(f, "property") if str(pr[1]) == "Reference"][0]
        at = find1(f, "at")
        fx, fy = float(at[1]), float(at[2])
        fa = float(at[3]) if len(at) > 3 else 0.0
        for q in find(f, "pad"):
            pa = find1(q, "at")
            ddx, ddy = rot_xy(float(pa[1]), float(pa[2]), fa)
            pxb, pyb = fx + ddx - ORG[0], BOARD_W - (fy + ddy - ORG[1])
            sz = find1(q, "size")
            rad = max(float(sz[1]), float(sz[2])) / 2
            for hx, hy, hr in holes:
                gap = math.hypot(pxb - hx, pyb - hy) - hr - rad
                if gap < CLR_EDGE - 1e-9:
                    onhole.append((str(ref), str(q[1]), round(hx, 2), round(hy, 2), round(gap, 3)))
    for ref, pin, hx, hy, gap in onhole:
        print(f"  🔴 パッドが穴に近すぎる {ref}.{pin} ↔ ({hx}, {hy}): すきま {gap} mm（下限 {CLR_EDGE}）")
    if not onhole:
        print(f"  パッドと穴（柱 {len(POSTS)} ＋ 取付穴 {len(MOUNT)}）のすきまは全て {CLR_EDGE} 以上")

    # 🔴 プラグの通り道。口の前に、他の部品・板の縁・電池（背 4.4）が無いか
    box = {ref: (b[0] - ORG[0], BOARD_W - (b[3] - ORG[1]),
                 b[2] - ORG[0], BOARD_W - (b[1] - ORG[1])) for ref, b in boxes}
    blocked, soft, wall, need_out, finger = [], [], [], [], []
    for ref, (side, need) in CONN.items():
        if ref not in box:
            continue
        x0, y0, x1, y1 = box[ref]
        fp = fps[ref]
        at = find1(fp, "at")
        ang = float(at[3]) if len(at) > 3 else 0.0
        dx, dy = open_dir(fp, float(at[1]), float(at[2]), ang)
        a = plug_band((x0, y0, x1, y1), (dx, dy), need)
        # 🔴 縁の口は、プラグが板の外へ出るのが**普通**（線は板の外へ抜ける）。
        #    ⇒ 板の外へ出ること自体は間違いではない。分けて数える:
        #      ① 板の上で他の部品に当たる      → 直せるのは板の側。**間違い**
        #      ② 相手の胴（3.1）が板の縁を越える → 殻の壁を貫く。**殻に開けてもらう要求**
        #      ③ 残り（指と曲がり）が縁を越える → 組むときの空き。**殻への注文**
        body = plug_band((x0, y0, x1, y1), (dx, dy), PLUG_BODY)
        why, near = [], []
        for r2, b2 in box.items():
            if r2 == ref:
                continue
            # ⭐ 2026-09-16 夕: 通り道は**その面の上**にしかないので、板の反対側の物の**胴**は相手にならない。
            #    🔴 ただし**板を貫いた足**は相手の面へ出る。裏の物の足がこの面のプラグの下に居たら本物の当たり。
            #       （J10 を裏の右へ移したら、そのはんだ足 2 本が表の J4 の嵌合したプラグの真下に来た。
            #        筐体側の hit_wires が先に見つけた ── ここで捕まえられていなかった）
            if (r2 in BACK_SIDE) != (ref in BACK_SIDE):
                for t in THPAD.get(r2, ()):
                    tb = (t[0] - ORG[0], BOARD_W - (t[3] - ORG[1]), t[2] - ORG[0], BOARD_W - (t[1] - ORG[1]))
                    if (body[0] < tb[2] - 1e-6 and tb[0] < body[2] - 1e-6
                            and body[1] < tb[3] - 1e-6 and tb[1] < body[3] - 1e-6):
                        why.append(f"{r2} の足")
                        break
                continue
            if (body[0] < b2[2] - 1e-6 and b2[0] < body[2] - 1e-6
                    and body[1] < b2[3] - 1e-6 and b2[1] < body[3] - 1e-6):
                why.append(r2)
            elif a[0] < b2[2] - 1e-6 and b2[0] < a[2] - 1e-6 and a[1] < b2[3] - 1e-6 and b2[1] < a[3] - 1e-6:
                near.append(f"{r2}({HEIGHT.get(r2, HEIGHT_DEFAULT)[0]})")
        if near:
            finger.append((ref, near))
        over_body = max(-body[0], -body[1], body[2] - BOARD_L, body[3] - BOARD_W)
        over_all = max(-a[0], -a[1], a[2] - BOARD_L, a[3] - BOARD_W)
        if over_body > 1e-6:
            edge = ("左" if -body[0] == over_body else "下" if -body[1] == over_body
                    else "右" if body[2] - BOARD_L == over_body else "上")
            wall.append((ref, edge, round(over_body, 2)))
        if over_all > 1e-6:
            edge = ("左" if -a[0] == over_all else "下" if -a[1] == over_all
                    else "右" if a[2] - BOARD_L == over_all else "上")
            need_out.append((ref, edge, round(over_all, 2)))
        if why:
            blocked.append((ref, tuple(round(v, 2) for v in a), why))
        # ⚠ 電池の影（天井 4.4）は **組むときは邪魔にならない**（電池は線を挿したあとに載る）。
        #    効くのは組んだあとで挿し直すときだけなので、止めずに注意だけ出す
        elif a[0] < BATTERY[2] and a[2] > BATTERY[0] and a[1] < BATTERY[3] and a[3] > BATTERY[1]:
            soft.append(ref)
    for ref, a, why in blocked:
        print(f"  🔴 プラグが板の上の部品に当たる {ref}: 通り道 X {a[0]}〜{a[2]}・Y {a[1]}〜{a[3]} … "
              + "・".join(why))
    for ref, near in finger:
        print(f"  ⚠ 指と曲がりの所に低い部品が居る {ref}: " + "・".join(near)
              + "（相手の胴 3.1 の外なので挿せるが、指は入らない）")
    for ref, edge, d in wall:
        print(f"  🔴 相手の胴が板の{edge}の縁を {d} mm 越える {ref}（殻の壁を貫く）")
    if need_out:
        print("  ⚠ 殻へ空けてもらう空き（指と曲がりまで）: "
              + "・".join(f"{r} {e}へ {d}" for r, e, d in need_out))
    if soft:
        print("  ⚠ 通り道が電池の下（挿し直すには電池を外す）: " + "・".join(soft))
    if not blocked and not wall:
        print(f"  プラグの通り道 {len(CONN)} 口すべて空いている（相手の胴は板の上で終わる）")

    missing = sorted(set(comps) - {b[0] for b in boxes} - {r for r in comps if r.startswith("#")})
    if missing:
        sys.exit("置き場所が決まっていない部品: " + ", ".join(missing))
    # 🔴 枠の重なり。⭐ 2026-09-16 夕に**面ごと**にした。
    #    それまで表と裏を 1 枚の紙として見ていて、板を挟んで別の側に居る物どうしを重なりと呼んでいた。
    #    （J10 を裏の右の帯へ移したら、表の J4 の胴と 5.25 × 3.3 重なると出た。物は板の反対側に居る）
    #    ⇒ 同じ面どうしは今までどおり枠で見る。**別の面どうしは、板を貫くパッドが相手の枠に
    #      入っていないか**だけを見る（貫いた足の先は相手の側へ出るので、これは本物の当たり）。
    def _ov2(a, b):
        return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6
    bad, xside = [], []
    for i, (ra, a) in enumerate(boxes):
        for rb, b in boxes[i + 1:]:
            if not _ov2(a, b):
                continue
            if (ra in BACK_SIDE) == (rb in BACK_SIDE):
                bad.append((ra, rb, round(min(a[2], b[2]) - max(a[0], b[0]), 2),
                            round(min(a[3], b[3]) - max(a[1], b[1]), 2)))
                continue
            # 相手は **胴**（FABBOX）で見る。courtyard の逃げ 0.3〜0.5 は物ではない
            hit = [r for r, o in ((ra, FABBOX.get(rb, b)), (rb, FABBOX.get(ra, a)))
                   if any(_ov2(t, o) for t in THPAD.get(r, ()))]
            if hit:
                bad.append((ra, rb, round(min(a[2], b[2]) - max(a[0], b[0]), 2),
                            round(min(a[3], b[3]) - max(a[1], b[1]), 2)))
            else:
                xside.append((ra, rb))
    for ra, rb in xside:
        print(f"  表と裏なので当たらない {ra} ↔ {rb}（枠は重なるが、板を貫く足は相手の枠の外）")
    for ra, rb, w, h in bad:
        print(f"  重なり {ra} ↔ {rb}: {w} × {h} mm")
    doc = ["kicad_pcb", ["version", "20241229"], ["generator", Str("katanori/gen_pcb.py")],
           ["generator_version", Str("9.0")],
           ["general", ["thickness", "1.6"], ["legacy_teardrops", "no"]],
           ["paper", Str("A3")],
           ["layers",
            ["0", Str("F.Cu"), "signal"], ["4", Str("In1.Cu"), "power"],
            ["6", Str("In2.Cu"), "signal"], ["2", Str("B.Cu"), "signal"],
            ["9", Str("F.Adhes"), "user", Str("F.Adhesive")], ["11", Str("B.Adhes"), "user", Str("B.Adhesive")],
            ["13", Str("F.Paste"), "user"], ["15", Str("B.Paste"), "user"],
            ["5", Str("F.SilkS"), "user", Str("F.Silkscreen")], ["7", Str("B.SilkS"), "user", Str("B.Silkscreen")],
            ["1", Str("F.Mask"), "user"], ["3", Str("B.Mask"), "user"],
            ["17", Str("Dwgs.User"), "user", Str("User.Drawings")],
            ["19", Str("Cmts.User"), "user", Str("User.Comments")],
            ["21", Str("Eco1.User"), "user", Str("User.Eco1")], ["23", Str("Eco2.User"), "user", Str("User.Eco2")],
            ["25", Str("Edge.Cuts"), "user"], ["27", Str("Margin"), "user"],
            ["31", Str("F.CrtYd"), "user", Str("F.Courtyard")], ["29", Str("B.CrtYd"), "user", Str("B.Courtyard")],
            ["35", Str("F.Fab"), "user"], ["33", Str("B.Fab"), "user"]],
           ["setup",
            # 積層は 1.6mm（プリプレグ 0.1 ＋ コア 1.24 ＋ プリプレグ 0.1）。統合基板と同じ
            ["stackup",
             ["layer", Str("F.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 1"), ["type", Str("prepreg")], ["thickness", "0.1"], ["material", Str("FR4")]],
             ["layer", Str("In1.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 2"), ["type", Str("core")], ["thickness", "1.24"], ["material", Str("FR4")]],
             ["layer", Str("In2.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["layer", Str("dielectric 3"), ["type", Str("prepreg")], ["thickness", "0.1"], ["material", Str("FR4")]],
             ["layer", Str("B.Cu"), ["type", Str("copper")], ["thickness", "0.035"]],
             ["copper_finish", Str("None")], ["dielectric_constraints", "no"]],
            ["pad_to_mask_clearance", "0"],
            ["pcbplotparams", ["layerselection", "0x00000000_00000000_55555555_5755f5ff"],
             ["disableapertmacros", "no"], ["usegerberextensions", "no"], ["usegerberattributes", "yes"],
             ["usegerberadvancedattributes", "yes"], ["creategerberjobfile", "yes"],
             ["dashed_line_dash_ratio", "12.000000"], ["dashed_line_gap_ratio", "3.000000"],
             ["svgprecision", "4"], ["plotframeref", "no"], ["mode", "1"], ["useauxorigin", "no"],
             ["dxfpolygonmode", "yes"], ["dxfimperialunits", "yes"], ["dxfusepcbnewfont", "yes"],
             ["psnegative", "no"], ["psa4output", "no"], ["plot_black_and_white", "yes"],
             ["sketchpadsonfab", "no"], ["plotpadnumbers", "no"], ["hidednponfab", "no"],
             ["sketchdnponfab", "yes"], ["crossoutdnponfab", "yes"], ["subtractmaskfromsilk", "no"],
             ["outputformat", "1"], ["mirror", "no"], ["drillshape", "1"], ["scaleselection", "1"],
             ["outputdirectory", Str("")]]],
           ["net", "0", Str("")]]
    for nm, num in sorted(nets.items(), key=lambda kv: kv[1]):
        doc.append(["net", str(num), Str(nm)])
    global _KELVIN
    # U2（QFN-20・0.5mm ピッチ）の逃げ道。自動配線が通せずにそのピンだけ浮かせるので先に出す
    _KELVIN = kelvin_tracks(placed) + [escape_stub(placed, "U2", "13", "PROG1")]
    doc += (outline() + mounting_holes() + placed + gnd_zone() + vbus_zone() + silk(placed, boxes)
            + pre_tracks(nets) + ep_vias(placed, nets))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(doc) + "\n", encoding="utf-8")
    print(f"{len(placed)} 部品・ネット {len(nets)} 本 → {OUT / (NAME + '.kicad_pcb')}")
    print(f"  足形のライブラリの表: {len(fp_lib_table(doc))} 本 → {OUT / 'fp-lib-table'}")

    # 自動配線に渡す DSN。パネルの外形を囲い、板と板のあいだ・空いている所は銅を置かせない
    bnd = [bx(*q) for q in outline_pts()]
    ko = []
    pos = {it["ref"]: (it["x"], it["y"]) for it in INSTS}   # 押し離したあとの位置
    for ref, dx, dy, rr in NPTH:
        cx, cy = pos[ref]
        ko.append((cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr))
    for px, py, d in POSTS:                                 # 柱の抜き（＋ 逃げ）
        X, Y = bx(px, py)
        r = d / 2 + POST_KEEP
        ko.append((X - r, Y - r, X + r, Y + r))
    for mx, my in MOUNT:                                    # 取付穴（φ2.2 ＋ 逃げ 0.5）
        X, Y = bx(mx, my)
        r = MOUNT_D / 2 + MOUNT_KEEP
        ko.append((X - r, Y - r, X + r, Y + r))
    # 🔴 GND は **自動配線にも渡す**。ベタ（gnd_zone()）任せにすると、U3 のような細ピッチの
    #    GND パッドへベタが入れず、DRC が未接続で出る（2026-09-13 に試した）。
    #    ベタは銅の足しと戻りの経路として残す。
    netpins = {}
    for (ref, pin), net in pads.items():
        netpins.setdefault(net, []).append((ref, pin))
    cls = [("battery", BAT_NETS, BAT_W), ("power", POWER_NETS, POWER_W)]
    # ⚠ 4 層にしても **GND は自動配線に渡したまま**にする。2026-09-17 に外してみたら、
    #   U3（INA226・TSSOP-10）の 2 番と 7 番へ表のベタが届かず、島が 4 つ残った。
    #   ベタ 3 枚と縫いのビアだけでは細ピッチのパッドを拾えない（2 層のときと同じ症状）。
    n_part, n_net = dsn.write_dsn(OUT / f"{NAME}.dsn", NAME, INSTS, netpins, bnd, ko, classes=cls,
                                  copper=ROUTE_COPPER, via=VIA4)
    # 先に引いた線と、EP の放熱ビアを protect で渡す（自動配線が動かさない・避けて引く）
    # 🔴 ビアを渡し忘れると、自動配線がその上に別のネットを通して短絡になる（2026-09-16・3 件出た）
    rows = []
    for net, lay, w, pts in PRE_TRACKS + _KELVIN:
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            rows.append(f'    (wire (path {lay} {round(w * dsn.SCALE)} {dsn._x(xa)} {dsn._y(ya)} '
                        f'{dsn._x(xb)} {dsn._y(yb)}) (net "{net}") (type protect))')
    for v in ep_vias(placed, nets):
        at = find1(v, "at")
        vnet = next(nm for nm, num in nets.items() if str(num) == str(find1(v, "net")[1]))
        # ⚠ 穴の名前は **この板の層数と穴径から作る**。dsn.VIA（2 層の Via[0-1]_800:400）を
        #   そのまま渡すと DSN に定義の無い穴を指すことになり、Freerouting が黙って
        #   空の SES を返す（2026-09-17・4 層にした直後に起きた）
        vianame = f'Via[0-{len(ROUTE_COPPER) - 1}]_{round(VIA4[0] * 1000)}:{round(VIA4[1] * 1000)}_um'
        rows.append(f'    (via {vianame} {dsn._x(float(at[1]))} {dsn._y(float(at[2]))} '
                    f'(net "{vnet}") (type protect))')
    if rows:
        f = OUT / f"{NAME}.dsn"
        nl = chr(10)
        body = "  (wiring" + nl + nl.join(rows) + nl + "  )"
        f.write_text(f.read_text(encoding="utf-8").replace("  (wiring" + nl + "  )", body),
                     encoding="utf-8")
        print(f"  先に引いた線とビア {len(rows)} 個を protect で渡した")
    print(f"自動配線へ: {n_part} 部品・{n_net} ネット → {OUT / (NAME + '.dsn')}")
    for cname, ns, w in cls:
        have = sorted(n for n in ns if len(netpins.get(n, ())) > 1)
        print(f"  {cname}（{w}mm）: {' '.join(have)}")
        miss = sorted(ns - set(have))
        if miss:
            sys.exit(f"{cname} に板へ出ていない名前がある: {miss}")
    if bad:
        sys.exit(f"部品が {len(bad)} 組重なっている")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
