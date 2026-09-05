# -*- coding: utf-8 -*-
"""STL を頂点のつながりで塊に分け、塊ごとの外形と体積を出す。python tools/stl_parts.py a.stl ..."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__)); from stl_read import tris
def parts(t):
    key = lambda v: (round(v[0], 4), round(v[1], 4), round(v[2], 4))
    parent = {}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    for tr in t:
        ks = [key(v) for v in tr]
        for k in ks: parent.setdefault(k, k)
        union(ks[0], ks[1]); union(ks[1], ks[2])
    groups = {}
    for tr in t: groups.setdefault(find(key(tr[0])), []).append(tr)
    return list(groups.values())
for p in sys.argv[1:]:
    nm = os.path.basename(p).replace('.stl', '')
    if not os.path.exists(p): print('%-14s MISSING (empty)' % nm); continue
    t = tris(p)
    if not t: print('%-14s EMPTY' % nm); continue
    print(nm)
    for g in sorted(parts(t), key=lambda g: -len(g)):
        v = 0.0
        for a, b, c in g: v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
        lo = [min(vv[k] for tr in g for vv in tr) for k in range(3)]; hi = [max(vv[k] for tr in g for vv in tr) for k in range(3)]
        print('  %8.3f mm3  X %6.2f..%6.2f  Y %6.2f..%6.2f  Z %6.2f..%6.2f' % (abs(v), lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
