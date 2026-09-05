# -*- coding: utf-8 -*-
"""binary STL の外形 [x0 x1 y0 y1 z0 z1] を出す。python tools/stl_bbox.py a.stl [b.stl ...]"""
import struct, sys
def bbox(path):
    with open(path, 'rb') as f:
        f.read(80); n = struct.unpack('<I', f.read(4))[0]
        lo = [1e9]*3; hi = [-1e9]*3
        for _ in range(n):
            rec = f.read(50)
            for k in range(3):
                x, y, z = struct.unpack_from('<fff', rec, 12 + 12*k)
                for i, v in enumerate((x, y, z)):
                    lo[i] = min(lo[i], v); hi[i] = max(hi[i], v)
    return n, lo, hi
for p in sys.argv[1:]:
    n, lo, hi = bbox(p)
    if n == 0: print(p, 'EMPTY'); continue
    print('%-14s X %6.2f..%6.2f  Y %6.2f..%6.2f  Z %6.2f..%6.2f' % (p.split('/')[-1].replace('.stl',''), lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
