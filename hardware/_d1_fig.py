# -*- coding: utf-8 -*-
# D-1（充電基板の受けが床の背を決めている）の絵を作り直す。
#   python hardware/_d1_fig.py
# 形は _d1_fig.scad（＝ case_v4.scad）の側にある。ここは カメラ と出力先だけ。
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
SRC = os.path.join(HERE, '_d1_fig.scad')

VIEWS = [
    # (出力, Q2, カメラ, 追加の -D)
    ('_d1_floor.png', 'floor_now', '0,0,0,62,0,225,0', []),
    ('_d1_near.png',  'near',      '0,0,0,68,0,200,0', ['-D', 'HOUS=false']),
    ('_d1_wall.png',  'wall_in',   '0,0,0,68,0,120,0', []),
    ('_d1_side.png',  'side',      '0,0,0,90,0,90,0',  []),
]

for out, q2, cam, extra in VIEWS:
    dst = os.path.join(HERE, out)
    if os.path.exists(dst): os.remove(dst)   # ⚠ 古い絵を読む事故を防ぐ
    subprocess.run([OPENSCAD, '--backend=manifold', '--render=full', '--projection=o',
                    '--autocenter', '--viewall', '--camera=' + cam, '--imgsize=1000,900',
                    '-o', dst, '-D', 'part="none"', '-D', 'Q2="%s"' % q2] + extra + [SRC],
                   check=True, capture_output=True)
    print(dst, os.path.getsize(dst), 'bytes')
