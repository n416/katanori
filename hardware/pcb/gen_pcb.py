# -*- coding: utf-8 -*-
"""hub_power.kicad_pcb（部品を置いただけの板・配線はまだ）を作る。

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
sys.path.insert(0, str(HERE.parent / "parts"))
import kisym  # noqa: E402
from kisym import Str, find, find1  # noqa: E402
import hub_ports  # noqa: E402
import dsn  # noqa: E402

CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
FPDIR = pathlib.Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
OUT = HERE / "hub_power"
NAME = "hub_power"
_n = [0]


def uid():
    _n[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"katanori/pcb/{_n[0]}"))


# ---- 板の寸法（🔒 2026-09-13 ユーザー「歯車 3 枚」→ 筐体の幅 48・板 44 × 81.2 で確定）----
# 座標は **板の左下が原点・X 右・Y 上**。図面（KiCad）の座標へは bx() で移す。
# ⚠ ここは筐体側（別セッション）が決めた数字をそのまま写す場所で、こちらで動かさない。
BOARD_L, BOARD_W = 44.0, 81.2
# 上の縁の切り欠き: ReSpeaker の J2（スピーカーのソケット・トップ型）のプラグが線込み 15 で
# 降りてきて板を貫くため。プラグの実寸は板 X 13.04〜20.99・Y 73.91〜80.91 で、四方に 0.9〜1.0 の逃げ
NOTCH = (12.0, 22.0, 73.0)        # x0, x1, この y から上端まで
# 🔴 2026-09-13: 上の 2 つは Y 69.5 だった。OLED の柱（3.30/40.70, 71.80）との芯間が **2.309** で、
#    M2 のなべ頭 φ3.8 もナット（二面幅 4.0）も並ばず、通し穴どうしが 0.09 重なって長穴になっていた。
#    ⇒ Y 65.25 へ下げた（柱まで 6.55）。格子は 37 × 66 → **37 × 61.75**
MOUNT = [(3.5, 3.5), (40.5, 3.5), (3.5, 65.25), (40.5, 65.25)]   # M2
MOUNT_D = 2.2                     # φ2.2（M2）
MOUNT_KEEP = 0.5                  # 穴のまわりに **銅** を置かせない幅（部品の背の話ではない）
# 🔴 2026-09-13 筐体側: ねじの頭は背面・**ナットは板の側**（横差しのポケット）。
#    ⇒ 取付穴のまわりに M2 の六角ナット（二面幅 4.0 ＝ 対角 4.62・背 1.6）が 4 個立つ。
#    MOUNT_KEEP は銅の話なので、**部品がナットの下に入っていないかは別に見る**。
NUT_R = 4.62 / 2 + 0.25           # 対角の半径 ＋ 逃げ（M2 のなべ頭 φ3.8 より大きいので、これで両方見られる）
# 🔒 2026-09-13: 背面の殻の床から立つ柱が **板を貫いて**上の部品まで行く。
#    (x, y, 抜きの径)。外形の切り抜きとして開け、まわりに銅も部品も置かない。
#    ⚠ ReSpeaker の 2 本は柱そのものを板の帯（箱 Z 3.0〜4.6）でだけ φ3.5 に細らせてもらった
#      （φ5.5 のままだと U4 のパッドを 0.138 削り、板の下の縁を 0.290 欠いた）。
POSTS = [(3.30, 38.80, 6.5), (40.70, 38.80, 6.5), (3.30, 71.80, 6.5), (40.70, 71.80, 6.5),
         (31.58, 2.46, 4.0), (2.66, 60.17, 4.0)]
POST_KEEP = 0.5                   # 抜きのまわりに銅を置かせない幅（0.3 だと KiCad の copper_edge_clearance が出た）
# 🔴 磁石と歯車の軸が降りてくる柱。ここに置いてよいのは AS5600（U4）だけ
KEEPOUT_MAGNET = (33.2, 4.0, 39.2, 10.0)
# 電池の影。🔒 2026-09-13 デザイン担当が確定した位置（603040・800mAh）。
#    底は板の面から 4.8 ＝ J2 の天面と面一（J2 を X で避けられなかったので Z で避けた）。
#    ⇒ 高さ 4.8 未満の物はこの下に置ける。効くのは組んだあとで線を挿し直すときだけ
BATTERY = (6.5, 24.2, 36.5, 64.2)
ORG = (60.0, 40.0)                # 図面の上での板の左上
# 筐体（箱）の座標と板の座標のずれ。**箱 = 板 + BOX**。
#    🔒 2026-09-13、筐体セッションの数字 2 組で裏を取った:
#      柱 RSP5   板 (2.66, 60.17) → 箱 (4.657, 63.167)
#      取付穴 HUB8 板 (3.50, 65.25) → 箱 (5.5, 68.25)
#    向きは同じ（X 右・Y 上）。回転も鏡も無い
BOX = (2.0, 3.0)


def bx(x, y):
    """板の座標（左下が原点・Y 上向き）→ 図面の座標（Y 下向き）。"""
    return (ORG[0] + x, ORG[1] + (BOARD_W - y))


# ---- 足形の差し替え（KiCad の標準に無い物は katanori.pretty に作る） ----
LOCAL = HERE / "katanori.pretty"
FP_OVERRIDE = {
    # 🔒 2026-09-12 リレーは表面実装の Omron G6S-2F へ替えたので、自作の足形は要らなくなった
    #    （KiCad 標準の Relay_SMD:Relay_DPDT_Omron_G6S-2F を使う）。
    # 🔴 2026-09-12 ユーザー「別に両方の足が出なくてもいいんじゃないの？」＋ CASE-V4-OPEN.md 119 行
    #    （口が外面の 0.8 裏だとプラグが奥で止まる・ベベルでは逃げられない）。
    #    前寄りのシェルの足 2 本を省いて、本体を板の縁から 3.0mm 出す
    "J13": "katanori:USB_C_HRO_TYPE-C-31-M-12_NoFrontLegs",
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


PLACE = {
    # ======== 電池の影（X 0〜35・Y 25〜75・天井 4.4）========
    # 電源・充電・電流計。いちばん背が高いのがインダクタの 1.8 なので 4.4 に楽に入る。
    # 🔴 USB-C（J13）・電池の PH（J10）はここへ入れない（背 3.16 と 4.8 で、口が板の外を向く）
    # 🔴 CC の引き下げ 2 本は **USB-C の足元**に置く。旧電源板の並びをそのまま写したら
    #    J13 から 40mm 離れて CC2 が 1 本つながらなかった（2026-09-13）
    "R44": (27.0, 71.0, 0), "R45": (23.5, 71.0, 0),
    "C8": pwr(12.0, 4.0), "C7": pwr(16.0, 4.0),
    "U2": pwr(12.0, 9.5),
    "R6": pwr(4.0, 17.0, 90), "R7": pwr(4.0, 20.0, 90),
    "R16": pwr(9.0, 18.0), "R17": pwr(12.5, 18.0), "R15": pwr(16.0, 18.0),
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
    "C31": (6.0, 22.5, 0), "R32": (10.0, 22.5, 0), "R31": (14.0, 22.5, 0),
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
    "J2": (41.75, 46.0, 90),   # OLED（右の帯・PH 横 4 ピン・口は板の内側 −X を向く）
    "J4": (39.0, 70.5, 180),   # スピーカー IN（右の帯・PH 横・口は −Y。取付穴を下げたぶん逃げた）
    "J10": (39.0, 30.0, 0),    # 電池の PH 横（右の帯・口は +Y）
    # 🔒 2026-09-13: リードと会話ボタンは 1 つの 4 ピン PH（J6）にまとまった。
    # 4 ピンの PH は幅 10.90 あり、入るのは「谷」（幅 11.6）と「上の縁」（幅 12）の 2 か所だけ。
    # OLED は前の上へ行くので上の縁、リード＋会話ボタンは谷に置く
    "J6": (14.0, 8.0, 0),      # リード＋会話ボタン（XIAO の下の谷。天井 8.5〜9.0 に対して 4.8）
}

# 🔴 口は「枠が重なっていない」だけでは挿せない。**プラグの通り道**を別に見る。
#    2026-09-13 ユーザー「J4J5どうやって挿すんだ」。私は当たりの検査しか書いておらず、
#    J4・J6・J8 の 3 つで通り道が塞がっていた。[[clearance-is-not-assemblability]]
#    値: (足形の中でのプラグの向き, 通り道の長さ)
#      PH の横挿し   … 口は局所 −Y。プラグの胴 7.6 ＋ 指と曲がり 2.4 = 10.0
#      2.54 の L 字   … 口は局所 −X。DuPont のハウジング 14（hardware/parts/plug.scad）＋ 2 = 16.0
CONN = {
    "J2": ("-y", 10.0), "J4": ("-y", 10.0), "J5": ("-y", 10.0),
    "J6": ("-y", 10.0), "J10": ("-y", 10.0),
}
# 板の座標での向き。足形を ang 度回したとき、局所の −Y / −X が板のどちらを向くか
OPEN_DIR = {
    ("-y", 0): (0, 1), ("-y", 90): (-1, 0), ("-y", 180): (0, -1), ("-y", 270): (1, 0),
    ("-x", 0): (-1, 0), ("-x", 90): (0, -1), ("-x", 180): (1, 0), ("-x", 270): (0, 1),
}

# ---- 板の面からの背の高さ [mm] ----
# 🔴 筐体側は板を「44 × 81.2 × 4.0 の塊」として持っていた（2026-09-13 に判明）。
#    実体に割るのに要るので、部品ごとの背をここに置く。**出どころを必ず付ける。**
#      📄 = データシート／図面で取った   ⚠ = 一般値（パッケージから推した・未確認）
HEIGHT = {
    "K31":  (9.33, "📄 en-g6s.pdf 5 ページ ＋ KiCad の STEP（Z 0〜9.330）"),
    "J1":   (8.5,  "筐体側の数字（2.54 のメスソケット）"),
    "J14":  (8.5,  "同上"),
    # 📄 ePH.pdf 3 ページ「Header（Through-hole type）・Side entry type」の側面図は
    #    **板が縦に描いてある**（足が横向きで (3.4) も横）。⇒ 4.8 が板からの高さ・7.6 が板の面の奥行き。
    #    courtyard 8.60 ＝ 7.6 ＋ 逃げ 0.5 × 2 で裏が取れる。
    #    挿した相手（PHR・厚み 4.5）は口の中に収まるので、**挿しても 4.8 を超えない**
    #    （📄 2 ページの SMT 型の組立図で、挿した外形の高さ (5.5) ＝ SMT の口自身の高さ 5.5）。
    "J2":   (4.8,  "📄 ePH.pdf 3 ページ Side entry"),
    "J4":   (4.8,  "📄 同"),
    "J5":   (4.8,  "📄 同"),
    "J6":   (4.8,  "📄 同"),
    "J10":  (4.8,  "📄 同"),
    "SW1":  (4.0,  "📄 MST-12D18G3.pdf（胴 3.5 ＋ 浮き 0.5。レバーは Z 2.3〜3.8）"),
    "J13":  (3.16, "⚠ 二次資料（PCBWiki）・メーカー図は未取得"),
    "U4":   (1.75, "⚠ 一般値 SOIC-8"),
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
CHECK_PADS = {
    ("J1", "1"): (9.40, 2.90), ("J1", "7"): (9.40, 18.14),
    ("J14", "1"): (24.63, 2.90), ("J14", "7"): (24.63, 18.14),
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


def courtyard(fp, x, y, ang):
    xs, ys = [], []

    def walk(n):
        if isinstance(n, list):
            if n and n[0] in ("fp_line", "fp_poly", "fp_rect", "fp_circle"):
                lay = find1(n, "layer")
                if lay and "CrtYd" in str(lay[1]):
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


def place_footprint(ref, comp, x, y, ang, pads):
    fp = load_fp(comp["fp"])
    out = ["footprint", Str(comp["fp"]), ["layer", Str("F.Cu")], ["uuid", Str(uid())],
           ["at", f"{x:.3f}", f"{y:.3f}"] + ([f"{ang:.0f}"] if ang else []),
           ["property", Str("Reference"), Str(ref), ["at", "0", "-2.5", "0"], ["layer", Str("F.SilkS")],
            ["uuid", Str(uid())], ["effects", ["font", ["size", "0.8", "0.8"], ["thickness", "0.12"]]]],
           ["property", Str("Value"), Str(comp["value"]), ["at", "0", "2.5", "0"], ["layer", Str("F.Fab")],
            ["hide", "yes"], ["uuid", Str(uid())],
            ["effects", ["font", ["size", "0.8", "0.8"], ["thickness", "0.12"]]]],
           ["property", Str("LCSC"), Str(comp.get("lcsc", "")), ["at", "0", "3.5", "0"],
            ["layer", Str("F.Fab")], ["hide", "yes"], ["uuid", Str(uid())],
            ["effects", ["font", ["size", "0.8", "0.8"], ["thickness", "0.12"]]]],
           ["attr", "through_hole" if find1(fp, "attr") and "through_hole" in str(find1(fp, "attr")[1:])
            else "smd"]]
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
    nx0, nx1, ny = NOTCH
    # 左下 →（右回り）。上の辺は切り欠きで 2 本に割れる
    pts = [(0, 0), (BOARD_L, 0), (BOARD_L, BOARD_W),
           (nx1, BOARD_W), (nx1, ny), (nx0, ny), (nx0, BOARD_W),
           (0, BOARD_W)]
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
    """M2（φ2.2）4 つ。板 X 3.5 と 40.5・Y 3.5 と 69.5（37 × 66 の格子・🔒 筐体側 2026-09-13）。"""
    o = []
    for mx, my in MOUNT:
        x, y = bx(mx, my)
        o.append(["footprint", Str("MountingHole:MountingHole_2.2mm_M2"), ["layer", Str("F.Cu")],
                  ["uuid", Str(uid())], ["at", f"{x:.3f}", f"{y:.3f}"], ["attr", "exclude_from_bom"],
                  ["pad", Str(""), "np_thru_hole", "circle", ["at", "0", "0"],
                   ["size", f"{MOUNT_D}", f"{MOUNT_D}"], ["drill", f"{MOUNT_D}"],
                   ["layers", Str("F&B.Cu"), Str("*.Mask")], ["uuid", Str(uid())]]])
    return o


def vbus_zone():
    """🔴 USB-C の足元に VBUS の小さなベタを置く（2026-09-13）。

    J13 の VBUS は A4・B4・A9・B9 の 4 パッドあり、真ん中の A4 が両隣の信号に囲まれて
    自動配線が届かなかった（未配線 1 本がこれだけ残った）。口の足元にベタを敷けば 4 つが
    まとめてつながる。ふつうの板でも電源はこう引く。
    """
    x, y, ang = PLACE["J13"]
    r = (x - 5.6, y - 5.6, x + 5.6, y - 0.2)      # 板の座標での長方形（口の内側だけ）
    pts = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    poly = ["polygon", ["pts"] + [["xy", f"{bx(*q)[0]:.3f}", f"{bx(*q)[1]:.3f}"] for q in pts]]
    return [["zone", ["net", str(NETNUM["VBUS"])], ["net_name", Str("VBUS")],
             ["layer", Str("F.Cu")], ["uuid", Str(uid())], ["name", Str("VBUS")],
             ["priority", "1"], ["hatch", "edge", "0.5"],
             ["connect_pads", "yes", ["clearance", "0.25"]],
             ["min_thickness", "0.25"], ["filled_areas_thickness", "no"],
             ["fill", "yes", ["thermal_gap", "0.2"], ["thermal_bridge_width", "0.5"]],
             poly]]


def gnd_zone():
    """🔴 裏面に GND のベタを敷く（2026-09-13）。

    GND は 47 パッドあって全ネットの中で断然いちばん多く、これを自動配線に引かせると
    板が詰まって別のネットが残る（EN と VSYS が 2 本落ちた）。ベタにすれば自動配線から
    47 パッドぶんが消え、同時に戻りの経路も良くなる。
    ⚠ ベタ任せにするとパッドが島に取り残されることがある。**それは KiCad の DRC が
    unconnected_items で出す**ので、検査で捕まえられる。
    """
    nx0, nx1, ny = NOTCH
    pts = [(0, 0), (BOARD_L, 0), (BOARD_L, BOARD_W),
           (nx1, BOARD_W), (nx1, ny), (nx0, ny), (nx0, BOARD_W), (0, BOARD_W)]
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
             [x for x in poly]] for lay in ("F.Cu", "B.Cu")]


NETNUM = {}
INSTS = []
NPTH = []      # 金属化していない穴のまわり（銅を置かせない四角）
# ⚠ 絵のためだけの 3D モデルの差し替え。KiCad 10 は TYPE-C-31-M-12 のモデルを同梱していないので、
#    ピン数と向きが同じ別の USB-C（GCT USB4105・16P 横挿し）を見た目の確認用に割り当てる。
#    **実際に載る部品は C165948（TYPE-C-31-M-12）のままで、足形も変えていない。**
MODEL_VIS = {"J13": ("${KICAD10_3DMODEL_DIR}/Connector_USB.3dshapes/"
                     "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step", (0.0, 0.365, 0.0))}
# 🔒 筐体側が座標を決めた部品。押し離しの対象にしない（動かすと筐体と合わなくなる）
FIXED = {"J13", "J1", "J14", "U4", "SW1"}
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
    blocks = [bx(NOTCH[0], NOTCH[2]) + bx(NOTCH[1], BOARD_W),
              bx(KEEPOUT_MAGNET[0], KEEPOUT_MAGNET[1]) + bx(KEEPOUT_MAGNET[2], KEEPOUT_MAGNET[3])]
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
        dx, dy = OPEN_DIR[(side, ang)]
        if dx:
            r = (b[2], b[1], b[2] + need, b[3]) if dx > 0 else (b[0] - need, b[1], b[0], b[3])
        else:   # 板の座標の +Y は図面の −Y
            r = (b[0], b[1] - need, b[2], b[1]) if dy > 0 else (b[0], b[3], b[2], b[3] + need)
        exempt[len(blocks)] = ref
        blocks.append(r)
    blocks = [(min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3])) for b in blocks]
    for ref in movable:
        shift(ref, 0.0, 0.0)
    for _ in range(rounds):
        moved = False
        pairs = [(boxes[i], boxes[j]) for i in range(len(boxes)) for j in range(i + 1, len(boxes))]
        for (ra, a), (rb, b) in pairs:
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
    comps, pads, nets = netlist()
    NETNUM.update(nets)
    placed, boxes = [], []

    def add(ref, x, y, ang):
        fpnode, raw = place_footprint(ref, comps[ref], x, y, ang, pads)
        placed.append(fpnode)
        boxes.append((ref, courtyard(raw, x, y, ang)))
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

    # 置く（板の座標 → 図面の座標）。"xiao" は 1×7 の縦ソケット。
    # 🔴 この足形のパッドは**局所 +Y** に並ぶ（+X ではない）。板の +Y へ並べるには 180 度回す。
    #    最初 90 で書いて CHECK_PADS に捕まえてもらった（2026-09-13）
    for ref, (x, y, ang) in PLACE.items():
        X, Y = bx(x, y)
        add(ref, X, Y, 180 if ang == "xiao" else ang)

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

    # 🔴 プラグの通り道。口の前に、他の部品・板の縁・電池（背 4.4）が無いか
    box = {ref: (b[0] - ORG[0], BOARD_W - (b[3] - ORG[1]),
                 b[2] - ORG[0], BOARD_W - (b[1] - ORG[1])) for ref, b in boxes}
    blocked, soft = [], []
    for ref, (side, need) in CONN.items():
        if ref not in box:
            continue
        x0, y0, x1, y1 = box[ref]
        dx, dy = OPEN_DIR[(side, PLACE[ref][2] if isinstance(PLACE[ref][2], int) else 0)]
        if dx:      # 左右へ挿す
            a = (x1, y0, x1 + need, y1) if dx > 0 else (x0 - need, y0, x0, y1)
        else:       # 上下へ挿す
            a = (x0, y1, x1, y1 + need) if dy > 0 else (x0, y0 - need, x1, y0)
        why = []
        if a[0] < 0 or a[1] < 0 or a[2] > BOARD_L or a[3] > BOARD_W:
            why.append("板の外へ出る")
        for r2, b2 in box.items():
            if r2 == ref:
                continue
            if a[0] < b2[2] - 1e-6 and b2[0] < a[2] - 1e-6 and a[1] < b2[3] - 1e-6 and b2[1] < a[3] - 1e-6:
                why.append(r2)
        if why:
            blocked.append((ref, tuple(round(v, 2) for v in a), why))
        # ⚠ 電池の影（天井 4.4）は **組むときは邪魔にならない**（電池は線を挿したあとに載る）。
        #    効くのは組んだあとで挿し直すときだけなので、止めずに注意だけ出す
        elif a[0] < BATTERY[2] and a[2] > BATTERY[0] and a[1] < BATTERY[3] and a[3] > BATTERY[1]:
            soft.append(ref)
    for ref, a, why in blocked:
        print(f"  🔴 プラグが入らない {ref}: 通り道 X {a[0]}〜{a[2]}・Y {a[1]}〜{a[3]} … " + "・".join(why))
    if soft:
        print("  ⚠ 通り道が電池の下（挿し直すには電池を外す）: " + "・".join(soft))
    if not blocked:
        print(f"  プラグの通り道 {len(CONN)} 口すべて空いている")

    missing = sorted(set(comps) - {b[0] for b in boxes} - {r for r in comps if r.startswith("#")})
    if missing:
        sys.exit("置き場所が決まっていない部品: " + ", ".join(missing))
    bad = []
    for i, (ra, a) in enumerate(boxes):
        for rb, b in boxes[i + 1:]:
            if a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                bad.append((ra, rb, round(min(a[2], b[2]) - max(a[0], b[0]), 2),
                            round(min(a[3], b[3]) - max(a[1], b[1]), 2)))
    for ra, rb, w, h in bad:
        print(f"  重なり {ra} ↔ {rb}: {w} × {h} mm")
    doc = ["kicad_pcb", ["version", "20241229"], ["generator", Str("katanori/gen_pcb.py")],
           ["generator_version", Str("9.0")],
           ["general", ["thickness", "1.6"], ["legacy_teardrops", "no"]],
           ["paper", Str("A3")],
           ["layers",
            ["0", Str("F.Cu"), "signal"], ["2", Str("B.Cu"), "signal"],
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
           ["setup", ["pad_to_mask_clearance", "0"],
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
    doc += outline() + mounting_holes() + placed + gnd_zone() + vbus_zone()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NAME}.kicad_pcb").write_text(kisym.dump(doc) + "\n", encoding="utf-8")
    print(f"{len(placed)} 部品・ネット {len(nets)} 本 → {OUT / (NAME + '.kicad_pcb')}")
    # 自動配線に渡す DSN。パネルの外形を囲い、板と板のあいだ・空いている所は銅を置かせない
    bnd = [bx(0, 0), bx(BOARD_L, 0), bx(BOARD_L, BOARD_W),
           bx(NOTCH[1], BOARD_W), bx(NOTCH[1], NOTCH[2]), bx(NOTCH[0], NOTCH[2]),
           bx(NOTCH[0], BOARD_W), bx(0, BOARD_W)]
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
    n_part, n_net = dsn.write_dsn(OUT / f"{NAME}.dsn", NAME, INSTS, netpins, bnd, ko)
    print(f"自動配線へ: {n_part} 部品・{n_net} ネット → {OUT / (NAME + '.dsn')}")
    if bad:
        sys.exit(f"部品が {len(bad)} 組重なっている")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
