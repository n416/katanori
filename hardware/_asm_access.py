# -*- coding: utf-8 -*-
# 組み立ての「手と工具の道」の検査（2026-08-26）。
#
#   python hardware/_asm_access.py
#
# それまでの検査は**部品が通るか**しか見ていなかった（当たり体積が 0 か）。
# 「その手順のときに箱の中に在る物」へ向かって、**ドライバの軸・ナットの落ちる道・ピンセットの道**を
# 円筒で撃ち、真っ直ぐ何 mm 入れるかを測る。v3 の _asm_probe.py（clear_len）をそのまま使う。
#
# ビスの位置は手で写さない。ネジの現物（brg_hw / seat_hw）を STL に出して連結成分に割り、
# その bbox から軸と頭の高さを取る。段の中身は _asm_sim_v4.scad の upto() が正。
import os, subprocess, sys, math, io
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _asm_probe import clear_len

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.environ.get('ACCESS_TMP', os.path.join(HERE, '_access_tmp'))
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')

DRIVER = 3.2      # 🔒 ドライバの先端（座ぐり φ3.4 に入る上限）
GRIP   = 20.0     # 柄。箱の外でしか要らないが、外に出た後に何 mm 空いているかを見る
TWEEZ  = 5.0      # ピンセットの先（v3 と同じ φ5）
NUT_M2 = 4.3      # M2 ナットの二面幅（落とす道）
NUT_M3_D = 6.7    # M3 ナットの対角（二面幅 5.8 ÷ cos30）。落とす道はこの太さが要る
NUT_DRV_OD = 9.0  # 📄 5.5mm ナットドライバのボックス外径（HOZAN D-840-5.5 の寸法表・2026-08-26 に確認）
FINGER = 12.0     # 指の腹


def scad(out, args):
    subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', out] + args,
                   check=True, capture_output=True)


def newest_scad():
    """hardware/*.scad の一番新しい更新時刻。焼いた STL がこれより古ければ作り直す"""
    return max(os.path.getmtime(os.path.join(HERE, f))
               for f in os.listdir(HERE) if f.endswith('.scad'))


def fresh(p):
    """🔴 2026-08-27（9 度目の机上の通し）: ここは `if not os.path.exists(p)` だけで、
    **形が変わっても焼き直さなかった**。この日 `_access_tmp` に 6 時間前の STL が残っていて、
    充電基板の受けを床から出す前の姿で測り続け、手順 1 の「後ろ左 φ10.1」が φ7.19 に化けていた。
    マニュアルは「この表は作り直すたびに測り直すので古くならない」と書いてあるが、
    それが本当になるのはこの判定を入れてから"""
    return os.path.exists(p) and os.path.getmtime(p) >= newest_scad()


def stage(n):
    """手順 n を終えた状態（皮も中身も）。n に "topsub" を渡すと天面の小組だけ"""
    name = n if isinstance(n, str) else 'st%d' % n
    p = os.path.join(TMP, '%s.stl' % name)
    if not fresh(p):
        scad(p, ['-D', 'ST="%s"' % name, os.path.join(HERE, '_asm_sim_v4.scad')])
    return p


def hardware(w):
    """ネジとナットの現物だけ（W="hw_brg" / "hw_seat"）"""
    p = os.path.join(TMP, '%s.stl' % w)
    if not fresh(p):
        scad(p, ['-D', 'W="%s"' % w, os.path.join(HERE, '_v4_core.scad')])
    return p


def hub_ports():
    """ハブの口 10 本（名前・中心・挿し切ったときの頭 Z）。座標は手で写さず _asm_plugs.scad の echo から取る"""
    out = []
    r = subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl',
                        '-o', os.path.join(TMP, 'hub.stl'), '-D', 'P="hub"',
                        os.path.join(HERE, '_asm_plugs.scad')],
                       check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    for ln in ((r.stdout or '') + (r.stderr or '')).splitlines():
        if 'PORT|' in ln:
            f = ln.split('PORT|')[1].rstrip('"').split('|')
            out.append((f[0],) + tuple(float(v) for v in f[1:]))
    return out


def load(p):
    import struct
    d = open(p, 'rb').read()
    n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(d[84:84 + n * 50], dtype=np.uint8).reshape(n, 50)
    return a[:, 12:48].copy().view('<f4').reshape(n, 3, 3).astype(np.float64)


def clumps(T, tol=3):
    """連結成分（頂点を丸めた union-find）ごとの bbox"""
    par = {}
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    def uni(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: par[ra] = rb
    key = lambda v: tuple(np.round(v, tol))
    for t in T:
        ks = [key(v) for v in t]
        for k in ks: par.setdefault(k, k)
        uni(ks[0], ks[1]); uni(ks[1], ks[2])
    g = {}
    for i, t in enumerate(T): g.setdefault(find(key(t[0])), []).append(i)
    out = []
    for idx in g.values():
        S = T[idx].reshape(-1, 3)
        out.append((S.min(0), S.max(0)))
    return sorted(out, key=lambda b: (round(b[0][1], 1), round(b[0][0], 1)))


def probe(stl, origin, axis, sign, dia, maxlen=200.0):
    return clear_len(load(stl), np.asarray(origin, float), axis, sign, dia, maxlen)


def widest(stl, x, y, z_top, target, lo=4.0, hi=20.0):
    """(x, y) の真上から降ろして target の高さまで届く**一番太い円筒**（二分）。
       ナットを回す工具が入るかは、口の太さではなくこの値で決まる"""
    f = lambda d: z_top - probe(stl, (x, y, z_top), 2, -1, d) <= target + 1e-6
    if f(hi):
        return hi
    for _ in range(12):
        mid = (lo + hi) / 2
        if f(mid): lo = mid
        else: hi = mid
    return lo


ROWS = []
def row(what, step, tool, dia, need, got, note='', cex=False):
    """cex=True は**反例**の行（止まるのが正）。「その手順でしか出来ない」ことの裏取りに使う"""
    ok = ('止まる（反例）' if got < need else '⚠ 通ってしまう') if cex else          ('通る' if got >= need else '止まる ***')
    ROWS.append((what, step, tool, '%.1f' % dia, '%.1f' % need,
                 ('外まで' if got >= 199 else '%.1f' % got), ok, note))


def run():
    ROWS.clear()
    os.makedirs(TMP, exist_ok=True)

    # ---- ① 床の裏から入れる 3 本（手順 4）。箱を伏せずに机の端へ出して下から締める ----
    st4 = stage(4)
    for (x, y) in [(4.2, 4.75), (81.8, 4.75), (82.0, 69.5)]:
        d = probe(st4, (x, y, -2.0 + 0.01), 2, -1, DRIVER)
        row('床の裏 → 壁の柱 (%.1f, %.1f)' % (x, y), '4', 'ドライバ', DRIVER, 5.0, d,
            '箱の下に空きが要る。机の端か台に載せる')
        d = probe(st4, (x, y, 12.0 - 0.01), 2, +1, NUT_M2)
        row('同 ナットを上から落とす (%.1f, %.1f)' % (x, y), '4', 'ナット', NUT_M2, 20.0, d)

    # ---- ② ブリッジを壁の棚へ留める 3 本（手順 5）----
    st5 = stage(5)
    for lo, hi in clumps(load(hardware('hw_brg'))):
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        d = probe(st5, (cx, cy, hi[2] - 0.01), 2, +1, DRIVER)
        row('ブリッジ → 壁の棚 (%.1f, %.1f)' % (cx, cy), '5', 'ドライバ', DRIVER, 60.0, d,
            '頭 Z %.1f から真上' % hi[2])

    # ---- ③ 電流計と PowerBoost を座へ留める 6 本（手順 8）----
    st8 = stage(8)
    for lo, hi in clumps(load(hardware('hw_seat'))):
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        d = probe(st8, (cx, cy, hi[2] - 0.01), 2, +1, DRIVER)
        row('基板 → 帯の座 (%.1f, %.1f)' % (cx, cy), '8', 'ドライバ', DRIVER, 40.0, d,
            '頭 Z %.1f から真上' % hi[2])

    # ---- ④ OLED を天面の L へ（天面を載せた後・フロントを差す前＝手順 10 の状態）----
    st10 = stage(10)
    topsub = stage('topsub')
    for x in (10.002, 76.102):
        d = probe(topsub, (x, 3.0 - 0.01, 46.1), 1, -1, DRIVER)
        row('OLED → 天面の L (X %.1f)' % x, '10', 'ドライバ', DRIVER, 20.0, d, '天面を裏返して前から')
        # 🔒 2026-08-26 T-2: 右を塞いでいたのは「つまみの島」ではなく**スピーカーの右前の丸み**だった
        #    （前端 Y 6.8 ＝ L の裏の面 6.6 の 0.2 後ろ。部品別に撃って: 天板だけ 8.0 / つまみだけ 8.0 / スピーカーだけ 1.3）。
        #    ✅ 同日 つまみとスピーカーを内側（−X）へ 4 動かして解決（右 1.3 → 15.7）。
        for stl, lbl, st_no in ((topsub, '天面の小組（箱の外）', '10'), (st10, '天面を載せた後', '11')):
            # 🔴 2026-08-26 夜: ここは **φ2.0 で撃っていた**。ナットは 4.3 幅なので、φ2.0 が通っても
            #    ナットが通るとは限らない（左は φ2.0 だと外まで抜けるが、φ2.5 から 0.19mm で止まる）。
            #    通るかどうかは**二面幅 4.3 の側**で決まる。厚み 1.6 は「要る mm」の方。
            d = probe(stl, (x, 4.6 + 2.0 + 0.01, 46.1), 1, +1, NUT_M2)
            row('L の後ろへナット (X %.1f)・%s' % (x, lbl), st_no, 'ナット 4.3×1.6', NUT_M2, 1.6, d,
                '右は 2026-08-26 につまみとスピーカーを −X へ 4 動かして通った（T-2）。左は同日、会話ボタンの受けの手前左の角を欠いて 0.19 → 3.4（T-3）')

    # ---- ⑤ 天面の四隅（手順 11・全部載せた後・上から）----
    st12 = stage(12)
    for (x, y, nm) in [(5.194, 68.5, '後ろ左'), (80.854, 68.5, '後ろ右'),
                       (4.198, 6.0, '前左'), (81.853, 6.0, '前右')]:
        d = probe(st12, (x, y, 50.954 + 0.01), 2, +1, DRIVER)
        row('天面の四隅 %s (%.1f, %.1f)' % (nm, x, y), '11', 'ドライバ', DRIVER, 5.0, d, '外から真上')
    # ナットは天面を載せる前（手順 9 の終わり）に上から落とす
    st9 = stage(9)
    for (x, y, nm) in [(5.194, 68.5, '後ろ左'), (80.854, 68.5, '後ろ右'),
                       (4.198, 6.0, '前左'), (81.853, 6.0, '前右')]:
        d = probe(st9, (x, y, 48.454 - 1.8 + 0.01), 2, +1, NUT_M2)
        row('天面のナット %s (%.1f, %.1f)' % (nm, x, y), '9', 'ナット', NUT_M2, 20.0, d,
            '天面を載せる前にしか入らない')

    # ---- ⑦ 電池を鞘の奥まで押す指（手順 7）----
    #   鞘は 6mm 高なので指は入らない。入るのは「帯の後ろの面」までで、そこが電池の座る奥（Y 63.9）より
    #   1.0mm 奥なら、指の腹で押し切れる。電池の現物は X 11.5〜46.5・Y 13.9〜63.9・Z 23.4〜29.4。
    st6 = stage(6)
    for (x, nm) in [(29.0, '中央'), (14.0, '左端'), (44.0, '右端')]:
        d = probe(st6, (x, 78.0, 26.4), 1, -1, FINGER)
        row('電池を奥まで押す指 (X %.0f)' % x, '7', '指 φ12', FINGER, 78.0 - 63.9, d,
            'Y 78 から −Y。電池の後端 63.9 まで 14.1 要る')

    # ---- ⑬ 電池のコネクタ対（🆕 2026-08-27・11 度目の机上の通し）------------
    #   🔒 ユーザー「後ろの 8.35mm にコネクタ対を置きましょ」。置き場は電池の尻の後ろ
    #   （X 27〜41・Y 64.2〜69.2・Z 23.4〜29.4）。嵌合した PH2.0 は約 14mm あって Y には寝ないので X に寝かせる。
    #   順は「電池を奥まで押す → 真上から嵌める」。先に嵌めると電池の尻を押す指の前にコネクタが立つ。
    st7c = stage(7)
    for dia, tool in ((TWEEZ, 'ピンセット'), (FINGER, '指 φ12')):
        d = probe(st7c, (34.0, 66.7, 60.0), 2, -1, dia)
        row('コネクタ対を真上から嵌める', '7', tool, dia, 60.0 - 29.4, d,
            'コネクタの頭 Z 29.4 まで 30.6 要る。板はまだ載っていない')
    d = probe(stage(8), (34.0, 66.7, 60.0), 2, -1, TWEEZ)
    row('（反例）コネクタ対を 板を載せた後から', '8', 'ピンセット', TWEEZ, 60.0 - 29.4, d,
        'PowerBoost の L 字ハウジングの腹（Z 35.03）が真上に来る。⇒ 嵌めるのは手順 7 だけ', cex=True)
    stsw = stage('swap')
    d = probe(stsw, (34.0, 90.0, 26.4), 1, -1, TWEEZ)
    row('交換: コネクタを口から掴む', '交換', 'ピンセット', TWEEZ, 90.0 - 69.2, d,
        'Y 90 から −Y。コネクタの尻 69.2 まで 20.8 要る。蓋とロックを外した姿')
    d = probe(stsw, (34.0, 90.0, 26.4), 1, -1, FINGER)
    row('（反例）交換: 指でコネクタを掴む', '交換', '指 φ12', FINGER, 90.0 - 69.2, d,
        '電池口は高さ 7.0 しかない。止まるのが正 ＝ 掴むのはピンセット。'
        '指で足りるのは「電池ごと後ろへ引く」ほうで、その道は case_v4 の chk_swap（0）が見ている', cex=True)

    # ---- ⑫ 電池の蓋のロックのビス（ハッチの外から −Y）----
    st12b = stage(12)
    d = probe(st12b, (56.4, 90.0, 26.4), 1, -1, DRIVER)
    row('蓋のロックのビス (56.4, 26.4)', '12', 'ドライバ', DRIVER, 90.0 - 74.6, d, '外から。頭は Y 74.6')
    d = probe(st12b, (56.4, 90.0, 26.4), 1, -1, GRIP)
    row('同 柄が振れるか', '12', '柄 φ20', GRIP, 90.0 - 74.6, d, '外なので当たるのはビスの頭だけ')

    # ---- ⑥ 指が入るか: ハブの口へ線を挿す（手順 3・上は開いている）----
    st2 = stage(2)
    for (x, y, nm) in [(35.382, 19.04, 'XIAO'), (34.112, 64.76, 'INA'),
                       (67.132, 64.76, 'PWR'), (12.522, 58.41, 'BTN2')]:
        d = probe(st2, (x, y, 16.6 + 0.01), 2, +1, FINGER)
        row('ハブの口へ手を入れる %s (%.1f, %.1f)' % (nm, x, y), '3', '指 φ12', FINGER, 40.0, d,
            '壁もブリッジもまだ無い')

    # ---- ⑦-2 留め帯を置いて押し込む手（🆕 2026-08-27・9 度目の机上の通し）--------
    #   🔴 手順 6 はこの表に 1 行も無かった。帯は「+2.0 ずらした位置へ上から降ろして、まっすぐ −X へ 2.0 押す」
    #   という**手でしか出来ない動き**なのに、当てていたのは部品の軌跡（CHK="strap" / "strap_down"）だけ。
    #   帯の位置は手で写さない: ST="straponly" の STL を連結成分に割って 3 本の bbox から取る。
    straps = clumps(load(stage('straponly')))
    for (lo, hi), nm in zip(straps, ('A（電流計の前）', 'B（電流計の後＋PB の前）', 'C（PB の後ろ）')):
        cx, cy, ztop = (lo[0] + hi[0]) / 2 + 2.0, (lo[1] + hi[1]) / 2, hi[2]
        for dia, tool in ((FINGER, '指 φ12'), (TWEEZ, 'ピンセット')):
            d = probe(st5, (cx, cy, 60.0), 2, -1, dia)
            row('帯 %s を上から摘まむ' % nm, '6', tool, dia, 60.0 - ztop, d,
                '天板の頭 Z %.1f まで。+2.0 ずらした位置（押し込む前）で撃つ' % ztop)
        # −X へ 2.0 押す道。天板に指を載せたまま押すのが本番だが、横から棒を当てる道も見ておく
        need_x = 84.0 - (hi[0] + 2.0)
        df = probe(st5, (84.0, cy, ztop - 1.0), 0, -1, FINGER)
        d = probe(st5, (84.0, cy, ztop - 1.0), 0, -1, DRIVER)
        # 🔴 2026-08-27（11 度目の机上の通し）: ここは 3 本とも「指は止まる」と書いていたが、
        #    帯 B だけは実測 82.3mm で**通っている**（要る 33.0）。文が事実と逆だった。測った値で言い分ける
        fin = ('指 φ12 も横から入る（%.1fmm・要る %.1f）' % (df, need_x)) if df >= need_x else               ('指 φ12 を横から差し込む道は %.1fmm で止まる（右の溝の高さが足りない）' % df)
        row('帯 %s を −X へ 2.0 押す（横から棒）' % nm, '6', '棒 φ3.2', DRIVER, need_x, d,
            fin + '。押すのは上から天板に指を載せたまま')

    # ---- ⑧ コネクタを挿す道（2026-08-27 に初めて当てた）------------------------
    #   それまでの検査は**ビスとナットと指**だけで、「口に挿す」動きを一度も見ていなかった。
    #   口の座標は手で写さない: _asm_plugs.scad が口だけを STL に出し、その bbox から取る。
    #   ・挿し代（口が軸方向に何 mm 動けるか）= ピンの長さ 6.0（parts.scad の足の出）を要る mm にする
    #   ・上から掴めるか = 口の頭まで真上から φ5（ピンセット）が届くか
    st3 = stage(3)
    st9r, st10r = stage('st9r'), stage('st10r')   # 線を抜いた剛体だけの段（線は口と一緒に動くので障害物ではない）

    # ⑧-1 スピーカー IN（ReSpeaker の J2）。皿の下に入るので**ブリッジより先**にしか挿せない
    J2 = (9.5, 21.0)   # 確保空間 X 9.00〜10.08 の中。頭は Z 23.5
    d3 = probe(st3, (J2[0], J2[1], 50.0), 2, -1, TWEEZ)
    row('J2（スピーカー IN）の口へ真上から', '3', 'ピンセット', TWEEZ, 50.0 - 23.5 - 0.1, d3,
        '口の頭 Z 23.5 まで 26.5 要る。ハブ側だけでなく**この口も手順 3 で挿す**')
    d5 = probe(st5, (J2[0], J2[1], 50.0), 2, -1, TWEEZ)
    row('（反例）J2 の口へ ブリッジの後から', '5', 'ピンセット', TWEEZ, 50.0 - 23.5 - 0.1, d5,
        '皿（X 9〜49・Z 21.4〜23.4）が真上に載る。手順 5 以降は挿せないことの裏取り', cex=True)

    # ⑧-2 充電の 2 本（Type-C 基板の DuPont）。🔴 2026-08-27（9 度目）まで口の頭 Z を 19.23 / 9.07 と
    #   **直書き**していた。板の Z（CHG_C_LW）を 0.25 上げたら、測る側だけ動いて要る mm が古いまま残り、
    #   「上の口へ真上から」が 0.25 足りずに赤くなった。ハブの口と同じで、口の座標は模型から取る。
    hous = clumps(load(stage('tchous')))          # 下の口・上の口（連結成分 2 つ）
    CHG = (5.8, 53.0)
    z_lo, z_hi = sorted(h[2] for _, h in hous)    # それぞれの頭の Z
    d4 = probe(st4, (CHG[0], CHG[1], 50.0), 2, -1, TWEEZ)
    row('充電の口（上）へ真上から', '4', 'ピンセット', TWEEZ, 50.0 - z_hi - 0.1, d4,
        '口の頭 Z %.1f まで %.1f 要る。指 φ12 は左の溝（幅 7.6）に入らない' % (z_hi, 50.0 - z_hi - 0.1))
    row('充電の口（下）へ真上から', '4', 'ピンセット', TWEEZ, 50.0 - z_lo - 0.1, d4,
        '下の口は上の口の**真下**（同じ X・Y）なので真上からは触れない。⇒ 2 本とも壁を降ろす前に板へ挿す', cex=True)
    d5c = probe(st5, (CHG[0], CHG[1], 50.0), 2, -1, TWEEZ)
    row('（反例）充電の口へ ブリッジの後から', '5', 'ピンセット', TWEEZ, 50.0 - z_hi - 0.1, d5c,
        '帯（Y 50.5〜62.9・全幅）が真上に載る。手順 5 以降は挿せないことの裏取り', cex=True)

    # ⑧-3 手順 9 で挿す口の**挿し代**（軸方向に 6.0 動けるか）。座標は _asm_plugs.scad の bbox
    PINL = 6.0
    CONN = [('電流計 INPUT +', (11.80, 19.87, 46.50), 2, +1, 3.6, '縦。上は開いている（天面は手順 11）'),
            ('電流計 INPUT −', (11.80, 24.14, 46.50), 2, +1, 3.6, '縦'),
            ('電流計 OUT +',   (11.80, 28.40, 46.50), 2, +1, 3.6, '縦'),
            ('電流計 OUT −',   (11.80, 32.67, 46.50), 2, +1, 3.6, '縦'),
            ('電流計 I2C（横）', (49.37, 26.45, 36.50), 0, +1, 3.6, '逃げ箱の後ろ端から +X'),
            ('PB の L 3 ピン',  (19.31, 69.70, 36.30), 1, +1, 3.6, '後ろ（ハッチ側）へ抜ける'),
            ('PB の L 3 ピン EN', (28.20, 69.70, 36.30), 1, +1, 3.6, '同'),
            ('PB の USB ピン',  (16.40, 58.90, 49.72), 2, +1, 3.6, '縦。逃げの頭は天面の裏のポケットに入る'),
            ('OLED の 4 連',    (43.05, 20.70, 46.50), 1, +1, 10.8, '後ろへ。天面を載せた後は 1.6 で止まる（抜けない）')]
    for nm, p, ax, sg, dia, note in CONN:
        q = list(p); q[ax] += sg * 0.01
        row('%s を挿す（挿し代）' % nm, '9', '口そのもの', dia, PINL,
            probe(st9r, q, ax, sg, dia), note)

    # ---- ⑨ 口を「持つ道」（2026-08-27・5 度目の机上の通し）-------------------
    #   🔴 ⑧ は**口そのものの太さ**（φ3.6）でしか撃っていなかった。口は指かピンセットに掌まれて動くので、
    #   φ3.6 が通っても道具が通るとは限らない。2026-08-26 に OLED の L のナットで同じ間違いをしている
    #   （φ2.0 で撃って通し、実際は二面幅 4.3 のナットが 0.19mm で止まっていた）。
    for nm, x, y, z, top, wl0, wl1 in hub_ports():
        d = probe(st2, (x, y, top - 0.01), 2, +1, TWEEZ)
        row('ハブの口 %s を摑む (%.1f, %.1f)' % (nm, x, y), '3', 'ピンセット', TWEEZ, PINL, d,
            '口の頭 Z %.1f から真上。壁もブリッジもまだ無い' % top)
        d = probe(st2, (x, y, top - 0.01), 2, +1, FINGER)
        row('同 指 φ12 で %s' % nm, '3', '指 φ12', FINGER, PINL, d, '')
    for nm, p, ax, sg, dia, note in CONN:
        q = list(p); q[ax] += sg * 0.01
        row('%s を摑んだまま 6 動かす' % nm, '9', 'ピンセット', TWEEZ, PINL,
            probe(st9r, q, ax, sg, TWEEZ), '⑧ と同じ軌を φ5 で')

    # ---- ⑩ 手順 1 の M3 ナット 4 個を**回す**道（2026-08-27・5 度目の机上の通し）----
    #   🔴 それまでの検査は M2 のナットを**落とす／差す**道だけだった。ハブの M3 だけは
    #   ビスの頭が丸いザグリ（φ6.0 × 2.2・回り止め無し）なので、ナットを回すあいだ下から頭を押さえる。
    #   ＝ ナットの側に**工具の外径**ぶんの縦の道が要る。落ちる道（対角 6.7）とは別の数字。
    st1 = stage(1)
    NUT_SEAT = 4.1   # ハブ基板の上面（BOARD_Z 2.5 ＋ 板 1.6）＝ナットの座
    for (x, y, nm) in [(9.002, 18.9, '前左'), (77.002, 18.9, '前右'),
                       (9.002, 64.9, '後ろ左'), (77.002, 64.9, '後ろ右')]:
        d = probe(st1, (x, y, 50.0), 2, -1, NUT_M3_D)
        row('M3 ナットを落とす %s (%.1f, %.1f)' % (nm, x, y), '1', 'ナット 対角 6.7', NUT_M3_D,
            50.0 - NUT_SEAT, d, '座は Z 4.1')
        w = widest(st1, x, y, 50.0, NUT_SEAT)
        # 🆕 2026-08-27（D-1）**4 本ともナットドライバで締まるようになった。**
        #    後ろ左 [9.0, 64.9] は φ7.19 しか無く、2026-08-26 は 🔒 ユーザー決定でピンセットの運用にしていた。
        #    塞いでいたのは充電基板の受けの補強の三角で、受けが床から出て**手順 4 で入る部品**になったため、
        #    手順 1 の段には居ない。反例の行と、ピンセットの掴み代の行はここで外した。
        row('同 ナットを回す工具 %s' % nm, '1', '工具の外径', w, NUT_DRV_OD, w,
            '座 Z 4.1 まで届く一番太い円筒。要る %.1f は 📄 HOZAN D-840-5.5（M3 用）のボックス外径' % NUT_DRV_OD)
        d = probe(st1, (x, y, -2.0 + 0.01), 2, +1, DRIVER)
        row('同 ビスの頭を下から押さえる %s' % nm, '1', 'ドライバ', DRIVER, 2.2, d,
            'ザグリ φ6.0 × 2.2 は丸くて回り止めが無いので、ナットを回すあいだ押さえる。'
            '要る 2.2 はザグリの深さ。⚠ 床が机にベタ置きだとそもそも入らない（台に載せる）')

    # ---- ⑭ つまみの島のねじ 2 本（🆕 2026-08-27・12 度目の机上の通し）----------
    #   🔴 この表には**つまみまわりの道が 1 本も無かった**。手順 10 のつまみの小組そのものが
    #   マニュアルに無かったので、掃く対象にもなっていなかった。
    #   相手は ST="topnut" ＝ **天面と、へこみに置いた島だけ**（つまみ・E リング・AS5600 の基板はまだ付いていない）。
    #   島のナットは天面の裏の**下向き**ポケット（AF 4.3 × 深さ 1.8・裏面と面一）で、置いておけない。
    topnut = stage('topnut')
    KX, KY, KZ = 65.704 - 2.5, 33.8 + 7.0, 50.954   # KNOB_AT ＋ top_knob の translate([-2.5, 7, 0])
    Z_NUT, Z_HEAD, Z_LO = KZ - 10.5, KZ - 4.3, 20.0
    for sx, nm in ((-1, '左'), (1, '右')):
        x = KX + sx * 7.9
        d = probe(topnut, (x, KY, 70.0), 2, -1, DRIVER)
        row('島のねじ %s を上から回す (X %.1f)' % (nm, x), '10', 'ドライバ', DRIVER, 70.0 - Z_HEAD, d,
            'つまみを挿す前。頭は島のザグリの底 Z %.1f。⚠ ザグリは φ3.4 なので φ3.4 の先は 48.3 で止まる' % Z_HEAD)
        need = Z_NUT - Z_LO - 0.01     # 0.01 は面ちょうどで止まる丸めの見込み（工具は口に当たれば足りる）
        d = probe(topnut, (x, KY, Z_LO), 2, +1, NUT_M2)
        row('島のナット %s を下から当てる (X %.1f)' % (nm, x), '10', 'ナット 4.3', NUT_M2, need, d,
            'ポケットの口は Z %.1f（裏面と面一・AF 4.3 × 深さ 1.8）。下向きなので置けない' % Z_NUT)
        # 押さえる工具。空いている太さは二分で出す（口の太さではなく、柱 4 本のあいだの太さで決まる）
        lo, hi = 2.0, 14.0
        if probe(topnut, (x, KY, Z_LO), 2, +1, hi) >= need:
            wid = hi
        else:
            for _ in range(16):
                mid = (lo + hi) / 2
                if probe(topnut, (x, KY, Z_LO), 2, +1, mid) >= need: lo = mid
                else: hi = mid
            wid = lo
        d = probe(topnut, (x, KY, Z_LO), 2, +1, TWEEZ)
        row('同 ピンセットで押さえる %s' % nm, '10', 'ピンセット', TWEEZ, need, d,
            'ポケットの口まで空いているのは φ%.1f まで（AS5600 の柱 4 本のあいだ）' % wid)
        d = probe(topnut, (x, KY, Z_LO), 2, +1, FINGER)
        row('（反例）同 指で押さえる %s' % nm, '10', '指 φ12', FINGER, need, d,
            '柱 4 本に Z %.1f で止まる（ポケットの口まであと %.1fmm）。'
            '⇒ ナットを押さえるのは**ピンセット**' % (Z_LO + d, Z_NUT - Z_LO - d), cex=True)

    # 横から寄るスパナ（⚠ 平たい顎を φ6 の円筒で代用している。ナットの中心まで 2.75 に寄れば掴める）
    for (ax, sg, start, lbl) in ((0, +1, -30.0, '左から'), (1, -1, 120.0, '後ろから')):
        o = [9.002, 64.9, 5.3]; o[ax] = start
        d = probe(st1, o, ax, sg, 6.0)
        c = 9.002 if ax == 0 else 64.9
        need = abs(c - start) - 2.75        # ナットの中心まで 2.75（＝二面幅の半分）に寄れないと掴めない
        row('後ろ左のナットへ %sスパナ' % lbl, '1', 'スパナ ⚠ φ6', 6.0, need, d,
            'ナットの高さ Z 5.3 で横から寄る。⚠ 平たい顎を円筒で代用。'
            '止まるのが正 ＝「横からは掴めない」ことの裏取り（残り %.1fmm）' % abs(start + sg * d - c),
            cex=True)

    return ROWS


def main():
    run()
    hdr = ('何を入れるか', '手順', '道具', 'φ', '要る mm', '通った mm', '結果', '備考')
    w = [max(len(str(r[i])) for r in [hdr] + ROWS) for i in range(8)]
    line = lambda r: '  '.join(str(r[i]).ljust(w[i]) for i in range(8))
    print(line(hdr)); print('-' * (sum(w) + 16))
    for r in ROWS: print(line(r))
    bad = [r for r in ROWS if r[6].startswith('止まる ') or r[6].startswith('⚠')]
    print('\n止まったもの: %d / %d' % (len(bad), len(ROWS)))
    for r in bad: print('  ***', r[0], '->', r[5], 'mm で止まる')


if __name__ == '__main__':
    main()
