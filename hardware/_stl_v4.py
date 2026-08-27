# -*- coding: utf-8 -*-
"""筐体 v4 の印刷部品を hardware/stl/v4/ へ全部書き出す。
   python hardware/_stl_v4.py              全部
   python hardware/_stl_v4.py seat floor   名前を指定（stl/v4/v4_<名前>.stl）
   ⚠ 出力先は書き出す前に必ず消す（OpenSCAD は空だと STL を書かないので、古いファイルを読む事故が起きる）。
   ⚠ 支柱とラフトは _v4_props.scad（`python hardware/_v4_props.py`）が持っている。形を変えたら先にあちらを回す。
   書き出したら `python hardware/_stl_preflight.py "hardware/stl/v4/*.stl"` を通す（PRINT.md §4）。
   書き出しの最後に _v4_plate.py を回すので、case_v4.scad の part="plate"（刷る物を全部並べた絵）も一緒に付いてくる。
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
OUT = os.path.join(HERE, 'stl', 'v4')
SRC = os.path.join(HERE, 'case_v4.scad')

# ファイル名 → part。名前は v4_<キー>.stl になる
PARTS = ['floor', 'lwall', 'rwall', 'top', 'front', 'hatch', 'shutter', 'lock', 'tail',
         'bridge', 'brgfront', 'strap_a', 'strap_b', 'strap_c', 'btn',
         'seat']   # seat = 充電基板の受け（2026-08-27・D-1 で床から独立した部品になった）

want = sys.argv[1:] or PARTS
os.makedirs(OUT, exist_ok=True)
for k in want:
    if k not in PARTS: raise SystemExit('知らない部品: %s（%s）' % (k, ' '.join(PARTS)))
    dst = os.path.join(OUT, 'v4_%s.stl' % k)
    if os.path.exists(dst): os.remove(dst)
    t = time.time()
    r = subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', dst,
                        '-D', 'part="print_%s"' % k, SRC], capture_output=True)
    if not os.path.exists(dst):
        print('%-10s ❌ 書けなかった\n%s' % (k, r.stderr[-800:])); continue
    print('%-10s %8d bytes  %5.1fs' % (k, os.path.getsize(dst), time.time() - t))

# 並べた絵（part="plate"）を焼いた STL に合わせて作り直す
subprocess.run([sys.executable, os.path.join(HERE, '_v4_plate.py')])
