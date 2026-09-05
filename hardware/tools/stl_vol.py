# -*- coding: utf-8 -*-
"""STL の体積 [mm3]。python tools/stl_vol.py a.stl ...。無いファイルは MISSING（OpenSCAD は空の結果を書かない）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); from stl_read import tris
for p in sys.argv[1:]:
    nm = p.split('/')[-1].replace('.stl', '')
    if not os.path.exists(p): print('%-12s MISSING (empty)' % nm); continue
    v = 0.0; t = tris(p)
    for a, b, c in t:
        v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    print('%-12s %s' % (nm, 'EMPTY' if not t else '%.2f mm3' % abs(v)))
