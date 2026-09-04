# -*- coding: utf-8 -*-
# 組み立ての当たり検査を全部回して mm³ を出す（2026-08-29）。
#
#   python hardware/_asm_chk.py            全部回す
#   python hardware/_asm_chk.py brg strap  名前を指定して回す
#
# なぜこれが要るか:
#   _asm_manual_v4.py の CHECKS 表は**手書き**で、図面に自動で追従しない。表の頭にも
#   「図面を触ったら回し直して書き換えること」と書いてあるが、回す手段が repo に無く、
#   毎回その場でコマンドを組み立てていた。2026-08-28〜29 に図面が 5 回動いたあいだ、
#   表は 08-28 の朝の数字のまま残っていた。⇒ 回し方をファイルにする。
#
# 呼び方が 3 系統に散っているのは、検査の置き場所がファイルごとに違うため:
#   CHK=  … _asm_sim_v4.scad（手順の順に入れる軌跡）
#   part= … case_v4.scad（皮の閉じ・部品どうしの総当たり）
#   W=    … _v4_core.scad（ブリッジの金物まわり）
#   どれも _asm_sim_v4.scad に -D で渡せば通る（case_v4 → _v4_core を include しているため）。
import os, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding='utf-8')   # Windows の既定は cp932 で、絵文字と 🔴 が落ちる
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _vol import vol

OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
SIM = os.path.join(HERE, '_asm_sim_v4.scad')

# (名前, 変数, 期待, 覚え書き)  期待は表に載っている値。ここは**照合用**で、正ではない
CHECKS = [
    ('hub',            'CHK',  '0',    '手順 1 ハブ基板を柱へ載せる'),
    ('rsp',            'CHK',  '0',    '手順 2 ReSpeaker を床の溝へ差す'),
    ('rsp_after',      'CHK',  '444',  '反例 壁の後から入れる'),
    ('seat',           'CHK',  '0',    '手順 4 受けを床の枠へ落とす'),
    ('seat_bad',       'CHK',  '383',  '反例 壁と基板の後から落とす'),
    ('ldgnut_lf',      'CHK',  '0',    '手順 4 棚のナット 左前'),
    ('ldgnut_lb',      'CHK',  '0',    '手順 4 棚のナット 左後'),
    ('ldgnut_r',       'CHK',  '0',    '手順 4 棚のナット 右'),
    ('ldgnut_bad',     'CHK',  '5.1',  '反例 3 本目を逆の面から'),
    ('wall_l',         'CHK',  '0',    '手順 4 左の壁を降ろす'),
    ('wall_r',         'CHK',  '0.01', '手順 4 右の壁を降ろす'),
    ('wall_l_seat',    'CHK',  '0',    '手順 4 左の壁（受けを入れて）'),
    ('wall_r_seat',    'CHK',  '0.01', '手順 4 右の壁（受けを入れて）'),
    ('tcwall',         'CHK',  '0',    '手順 4 左の壁が Type-C を抱いて降りる'),
    ('brgf',           'CHK',  '0',    '手順 5 前板を床の溝へ差す'),
    ('brgf_bad',       'CHK',  '1450', '反例 前板をブリッジの後から'),
    ('brg',            'CHK',  '46',   '手順 5 ブリッジ本体を降ろす'),
    ('brgldg',         'W',    '0',    '手順 5 ブリッジの棚'),
    ('brghw',          'W',    '0',    '手順 5 ブリッジのビスとナット'),
    ('brgchk',         'W',    '16.3',   '手順 5 ブリッジ本体 ↔ 全部'),
    ('brg_bad',        'CHK',  '1010', '反例 上の道を先に通す'),
    ('strap',          'CHK',  '0.57', '手順 6 留め帯を横へ 2mm'),
    ('strap_dry',      'CHK',  '0.57', '手順 6 同上（線を除いた剛体だけ）'),
    ('strap_down',     'CHK',  '15',   '手順 6 押し込む前の位置へ上から'),
    ('strap_top',      'CHK',  '81',   '反例 上からかぶせる'),
    ('strap_bad',      'CHK',  '201',  '反例 電池を先に入れる'),
    ('bat',            'CHK',  '0',    '手順 7 電池を後ろから差し込む'),
    ('chk_swap',       'part', '0',    '電池をコネクタごと後ろへ引き出す'),
    ('chk_wire_pwr',   'part', '0',    '電池のコネクタ対と延長（止まった姿）'),
    ('boards',         'CHK',  '12.3',  '手順 8 電流計と PowerBoost を座へ'),
    ('oled',           'CHK',  '0',    '手順 9 OLED を上から降ろす'),
    ('whigh',          'CHK',  '0',    '手順 9 上の道と電源の線'),
    ('close_top',      'part', '0.09',    '手順 11 天面一式を降ろす'),
    ('close_front',    'part', '0.13', '手順 11 フロントを前から差す'),
    ('close_hatch',    'part', '0.02', '手順 12 ハッチを閉じる'),
    ('chk_all',        'part', '0.12', '組み上がった姿（皮 ↔ 中身）'),
    ('chk_press',      'part', '4.94',  'ReSpeaker の押さえ（0 だと不合格）'),
    ('chk_shut_slide', 'part', '0',    '交換 蓋を横へずらす'),
    ('chk_lock_out',   'part', '0',    '交換 ロックを後ろへ外す'),
    ('chk_shut_out',   'part', '0',    '交換 蓋を後ろへ抜く'),
    # 🆕 2026-08-28〜29 に作られた検査。2026-08-29 に表へ入れた（それまで 1 行も無かった）
    ('chk_self',       'part', '41.9',    '天板に足している物 6 つの総当たり 15 組'),
    ('chk_top_spk',    'part', '0',    '天板 ↔ 沈めたスピーカーの枠'),
]


def run(name, var):
    """1 本回して mm³ を返す。空（当たり無し）なら 0.0。"""
    fd, tmp = tempfile.mkstemp(suffix='.stl'); os.close(fd)
    try:
        p = subprocess.run([OPENSCAD, '--backend=manifold', '-o', tmp,
                            '-D', '%s="%s"' % (var, name), SIM],
                           capture_output=True, text=True, errors='replace')
        # 🔴 当たりが無い（＝合格）とき、OpenSCAD は STL を書かずに終了コードを立てる。
        #    "Current top level object is empty." は**エラーではなく 0mm³** なので、
        #    本物のエラーと分けて拾う。ここを分けないと、合格の 7 本が全部エラーに見える。
        if 'Current top level object is empty' in (p.stderr or ''):
            return 0.0, ''
        if p.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            err = chr(10).join(l for l in (p.stderr or '').splitlines()
                               if not l.startswith('ECHO:'))
            return None, err[-400:]
        return vol(tmp), ''
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    pick = set(sys.argv[1:])
    rows = [c for c in CHECKS if not pick or c[0] in pick]
    print('%-16s %-5s %10s %10s  %s' % ('名前', '変数', '実測', '表の値', '中身'))
    print('-' * 92)
    moved, failed = [], []
    for name, var, want, note in rows:
        got, err = run(name, var)
        if got is None:
            failed.append(name)
            print('%-16s %-5s %10s %10s  %s' % (name, var, 'エラー', want, err.replace(chr(10), ' ')[:60]))
            continue
        g = '%.3f' % got
        same = want != '?' and abs(got - float(want)) <= max(0.005, float(want) * 0.02)
        if not same:
            moved.append((name, g, want))
        print('%-16s %-5s %10s %10s  %s%s' % (name, var, g, want, '' if same else '🔴 ', note))
    print('-' * 92)
    if failed:
        print('エラー %d 本: %s' % (len(failed), ' '.join(failed)))
    if moved:
        print('表と違う %d 本:' % len(moved))
        for n, g, w in moved:
            print('   %-16s %s → %s' % (n, w, g))
    else:
        print('表の値と全部一致')


if __name__ == '__main__':
    main()
