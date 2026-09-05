# -*- coding: utf-8 -*-
"""STL の外形 [x0 x1 y0 y1 z0 z1] を出す。python tools/stl_bbox.py a.stl [b.stl ...]。無いファイルは MISSING（OpenSCAD は空の結果を書かない）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); from stl_read import tris
for p in sys.argv[1:]:
    nm = p.split('/')[-1].replace('.stl', '')
    if not os.path.exists(p): print('%-14s MISSING (empty)' % nm); continue
    t = tris(p)
    if not t: print('%-14s EMPTY' % nm); continue
    lo = [min(v[k] for tr in t for v in tr) for k in range(3)]; hi = [max(v[k] for tr in t for v in tr) for k in range(3)]
    print('%-14s X %6.2f..%6.2f  Y %6.2f..%6.2f  Z %6.2f..%6.2f' % (nm, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
