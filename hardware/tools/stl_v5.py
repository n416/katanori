# -*- coding: utf-8 -*-
"""筐体 v5 の印刷部品を hardware/stl/v5/ へ全部書き出す（frozen/v1-v4/_stl_v4.py の移植・2026-09-05）。
   python hardware/tools/stl_v5.py              全部（18 点）
   python hardware/tools/stl_v5.py floor top    名前を指定（stl/v5/v5_<名前>.stl）
   ⚠ 出力先は書き出す前に必ず消す（OpenSCAD は空だと STL を書かないので、古いファイルを読む事故が起きる）。
   ⚠ 支柱とラフトは parts/props_v5_gen.scad（`python hardware/tools/props_gen.py`）が持っている。形を変えたら**先にあちらを回す**。
   書き出したら `python hardware/tools/_stl_preflight.py "hardware/stl/v5/*.stl"` を通す（PRINT.md §4）。
   刷る向きは case_v5.scad の print_<部品>（板 6 枚は外面を下・ブリッジは皿の裏を下・蓋/ロック/床の板は外面を下・前板は皿に付く面を下）。
   つまみ 2 点は parts/knob_v5.scad（knob / wall）、会話ボタン 2 点は parts/btn_v3.scad（print_piston / print_tub）。
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))          # hardware/tools
HW = os.path.dirname(HERE)                                   # hardware
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
OUT = os.path.join(HW, 'stl', 'v5')

CASE = os.path.join(HW, 'case_v5.scad')
KNOB = os.path.join(HW, 'parts', 'knob_v5.scad')
BTN  = os.path.join(HW, 'parts', 'btn_v3.scad')
SPK  = os.path.join(HW, 'parts', 'spk_v5.scad')
# ファイル名 → (元の .scad, part の値)。名前は v5_<キー>.stl になる。
PARTS = [(k, CASE, 'print_%s' % k) for k in
         ['floor', 'lwall', 'rwall', 'top', 'front', 'hatch', 'bridge', 'brgfront',
          'strap_a', 'strap_b', 'strap_c', 'inabar', 'shutter', 'lock', 'shutfloor']] + [
    ('inabar_a', CASE, 'print_inabar_a'),   # 試し刷り A: 凹み 3.0・上のダボ 2.8（🔒 ユーザー 2026-09-10）
    ('inabar_b', CASE, 'print_inabar_b'),   # 試し刷り B: 凹み 3.35・上のダボ 2.9・見分けの溝
    ('inabar_c', CASE, 'print_inabar_c'),   # 試し刷り C: B に φ1.5 の抜き穴（吸盤をやめる、2026-09-10）
] + [   # inabar: 電流計の小帯（2026-09-07・上面を下）
    ('piston',   BTN,  'print_piston2'),  # 会話ボタンの押し子 2（根元寄りの線・台形の足。🔒 2026-09-07 決定。天面を下）
    ('tub',      BTN,  'print_tub'),      # 会話ボタンのバスタブ（底を下）
    ('knob',     KNOB, 'knob'),           # つまみ本体
    ('knobwall', KNOB, 'wall'),           # つまみの島（座金＋タブ）
    ('knobdeck', KNOB, 'deck'),           # つまみの試し刷り: 天板の切れ端＋台座＋手（皿の支柱とラフト込み・天面を下・2026-09-08）
    ('knobhangtest', KNOB, 'hangtest'),   # つまみの手だけの試し刷り（手の周りの塊 16×36×4・2026-09-08。バスタブ 2 の調査用）
    ('knobhang', KNOB, 'hang'),           # つまみのバスタブ 2（板を下・壁が立つ・2026-09-08）
    ('spktest',  SPK,  'print_deck'),     # スピーカーの吊りの試し刷り（天板の切れ端＋座＋縁＋板＋足・後ろの面を下・2026-09-08）
    ('spktub',   SPK,  'print_tub'),      # スピーカーのバスタブ 3（板を下・2026-09-08）
]
NAMES = [k for k, _, _ in PARTS]

want = sys.argv[1:] or NAMES
os.makedirs(OUT, exist_ok=True)
for k in want:
    if k not in NAMES: raise SystemExit('知らない部品: %s（%s）' % (k, ' '.join(NAMES)))
    src, pname = next((f, p) for n, f, p in PARTS if n == k)
    dst = os.path.join(OUT, 'v5_%s.stl' % k)
    if os.path.exists(dst): os.remove(dst)
    t = time.time()
    r = subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', dst,
                        '-D', 'part="%s"' % pname, src], capture_output=True)
    if not os.path.exists(dst):
        print('%-10s NG 書けなかった\n%s' % (k, r.stderr[-800:].decode('utf-8', 'replace'))); continue
    warn = r.stderr.decode('utf-8', 'replace').count('WARNING')
    print('%-10s %8d bytes  %5.1fs  warn %d' % (k, os.path.getsize(dst), time.time() - t, warn))
