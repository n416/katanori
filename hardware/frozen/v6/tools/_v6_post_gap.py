# -*- coding: utf-8 -*-
"""柱どうしの隔たりを 4 段で出す（筐体 v6）。

🔴 「柱の肉が当たっていない」だけを見る検査は、**ねじの頭が当たる組を見逃す**。
   柱が離れていても、皿ぐり φ4.0・頭 φ3.8・ナット 4.0 は当たることがある。
   ⇒ 4 段を**別々に**出す。1 つにまとめない。
     ① 柱の肉  … 刷れるか（立った壁の下限 0.30）
     ② 皿ぐり  … 背面の座 φ4.0
     ③ 通し穴  … 8 の字になっていないか
     ④ 頭／ナット … 締められるか（M2 なべ頭 3.8・ナット 二面幅 4.0）

⚠ 2026-09-13、OLED の柱とハブの柱が芯間 2.309 で、**通し穴どうしが 0.09 重なって**いた。
   「枠が重ならない」だけ見ていて、ねじを回す物どうしを見ていなかった（ユーザーが発見）。

出どころ: hardware/frozen/v6/_v6_portrait.scad の POSTS を読む（手で写さない）。
使い方  : python hardware/frozen/v6/tools/_v6_post_gap.py
"""
import io
import math
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))   # frozen/v6/tools → リポジトリの根
SRC = os.path.join(ROOT, 'hardware', 'frozen', 'v6', '_v6_portrait.scad')

CB = 4.0        # 背面の皿ぐり φ4.0（CB_D）
HEAD = 3.8      # M2 なべ頭
NUT = 4.0       # M2 ナット 二面幅
MINWALL = 0.30  # 立った壁の下限（PRINT.md 2 章）

NAMES = ('BODY_X', 'BODY_Y', 'BODY_Z', 'WALL', 'SCR_Y', 'SCR_IN', 'OL_T', 'OL_RS_GAP',
         'OL_X', 'OL_Y', 'OL_Z', 'RS_X', 'RS_Y', 'RS_Z', 'HB_X', 'HB_Y', 'HB_Z',
         'HB_W', 'HB_L', 'HB_T', 'LAYER')


def env_of(src):
    # 🔴 名前を並べた表で拾うと、定義の順（HB_X は HB_W の後）を外して落ちる。
    #    ⇒ **ファイルに書いてある順**にそのまま拾う。
    env = {}
    for g in re.finditer(r'^([A-Z][A-Z0-9_]*)\s*=\s*(.+?);', src, re.M):
        try:
            env[g.group(1)] = float(eval(g.group(2), {}, dict(env)))
        except Exception:
            pass
    return env


def posts(src, env):
    m = re.search(r'POSTS\s*=\s*\[(.*?)\n\];', src, re.S)
    if not m:
        sys.exit('POSTS が読めない')
    out = []
    for line in m.group(1).split('\n'):
        g = re.match(r'\s*\[([^\]]+)\]', line)
        if not g:
            continue
        f = [x.strip() for x in g.group(1).split(',')]
        out.append((float(eval(f[0], {}, env)), float(eval(f[1], {}, env)),
                    float(f[3]), float(f[4])))
    return out


def main():
    src = io.open(SRC, encoding='utf-8').read()
    P = posts(src, env_of(src))
    print('柱 %d 本（hardware/frozen/v6/_v6_portrait.scad の POSTS から読んだ）' % len(P))
    rows = []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            (x0, y0, d0, h0), (x1, y1, d1, h1) = P[i], P[j]
            dd = math.hypot(x0 - x1, y0 - y1)
            if dd > 14:
                continue
            rows.append((dd, i, j,
                         [('① 柱の肉', dd - (d0 + d1) / 2, MINWALL),
                          ('② 皿ぐり', dd - CB, 0.0),
                          ('③ 通し穴', dd - (h0 + h1) / 2, 0.0),
                          ('④ 頭/ナット', dd - max(HEAD, NUT), 0.0)]))
    rows.sort()
    bad = 0
    for dd, i, j, g in rows:
        print('\n  柱%d (%.2f, %.2f) φ%.1f  ↔  柱%d (%.2f, %.2f) φ%.1f    芯間 %.3f'
              % (i, P[i][0], P[i][1], P[i][2], j, P[j][0], P[j][1], P[j][2], dd))
        for name, v, lim in g:
            ng = v < lim
            bad += 1 if ng else 0
            print('     %-12s %+7.3f   %s'
                  % (name, v, ('🔴 下限 %.2f を割る' % lim) if ng else 'OK'))
    print('\n==== %s ====' % ('通り（4 段とも下限の上）' if bad == 0
                              else '🔴 %d 件が下限を割っている' % bad))


if __name__ == '__main__':
    main()
