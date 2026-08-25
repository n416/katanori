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
FINGER = 12.0     # 指の腹


def scad(out, args):
    subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', out] + args,
                   check=True, capture_output=True)


def stage(n):
    """手順 n を終えた状態（皮も中身も）"""
    p = os.path.join(TMP, 'st%d.stl' % n)
    if not os.path.exists(p):
        scad(p, ['-D', 'ST="st%d"' % n, os.path.join(HERE, '_asm_sim_v4.scad')])
    return p


def hardware(w):
    """ネジとナットの現物だけ（W="hw_brg" / "hw_seat"）"""
    p = os.path.join(TMP, '%s.stl' % w)
    if not os.path.exists(p):
        scad(p, ['-D', 'W="%s"' % w, os.path.join(HERE, '_v4_core.scad')])
    return p


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


ROWS = []
def row(what, step, tool, dia, need, got, note=''):
    ok = '通る' if got >= need else '止まる ***'
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

    # 3 本目（帯の左端の上の耳。brg_hw() に入っていないので座標を直に書く。⚠ _v4_core の BLU_SCR）
    d = probe(st5, (4.194, 66.2, 26.4 + 0.01), 2, +1, DRIVER)
    row('ブリッジ → 帯の左端の耳 (4.2, 66.2)', '5', 'ドライバ', DRIVER, 60.0, d,
        '頭 Z 26.4 から真上。⚠ この 1 本は brg_hw() に描かれていない')

    # ---- ③ 電流計と PowerBoost を座へ留める 6 本（手順 8）----
    st8 = stage(8)
    for lo, hi in clumps(load(hardware('hw_seat'))):
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        d = probe(st8, (cx, cy, hi[2] - 0.01), 2, +1, DRIVER)
        row('基板 → 帯の座 (%.1f, %.1f)' % (cx, cy), '8', 'ドライバ', DRIVER, 40.0, d,
            '頭 Z %.1f から真上' % hi[2])

    # ---- ④ OLED を天面の L へ（天面を載せた後・フロントを差す前＝手順 10 の状態）----
    st10 = stage(10)
    for x in (10.002, 76.102):
        d = probe(st10, (x, 3.0 - 0.01, 46.1), 1, -1, DRIVER)
        row('OLED → 天面の L (X %.1f)' % x, '11', 'ドライバ', DRIVER, 20.0, d, '前から −Y へ')
        d = probe(st10, (x, 4.6 + 3.2 + 0.01, 46.1), 1, +1, TWEEZ)
        row('同 L の後ろへナット (X %.1f)' % x, '11', 'ピンセット', TWEEZ, 8.0, d,
            '後ろから +Y へ。ナット 1.6 ＋ 先をつまんで引き抜く分')

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

    # ---- ⑥ 指が入るか: ハブの口へ線を挿す（手順 3・上は開いている）----
    st2 = stage(2)
    for (x, y, nm) in [(35.382, 19.04, 'XIAO'), (34.112, 64.76, 'INA'),
                       (67.132, 64.76, 'PWR'), (12.522, 58.41, 'BTN2')]:
        d = probe(st2, (x, y, 16.6 + 0.01), 2, +1, FINGER)
        row('ハブの口へ手を入れる %s (%.1f, %.1f)' % (nm, x, y), '3', '指 φ12', FINGER, 40.0, d,
            '壁もブリッジもまだ無い')

    return ROWS


def main():
    run()
    hdr = ('何を入れるか', '手順', '道具', 'φ', '要る mm', '通った mm', '結果', '備考')
    w = [max(len(str(r[i])) for r in [hdr] + ROWS) for i in range(8)]
    line = lambda r: '  '.join(str(r[i]).ljust(w[i]) for i in range(8))
    print(line(hdr)); print('-' * (sum(w) + 16))
    for r in ROWS: print(line(r))
    bad = [r for r in ROWS if r[6].startswith('止まる')]
    print('\n止まったもの: %d / %d' % (len(bad), len(ROWS)))
    for r in bad: print('  ***', r[0], '->', r[5], 'mm で止まる')


if __name__ == '__main__':
    main()
