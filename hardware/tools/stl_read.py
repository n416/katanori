# -*- coding: utf-8 -*-
"""STL（binary / ASCII どちらも）を三角形のリストで読む。stl_bbox.py と stl_vol.py が使う"""
import struct
def tris(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:5] == b'solid' and b'facet' in data[:400]:
        out = []; cur = []
        for line in data.decode('ascii', 'ignore').splitlines():
            w = line.split()
            if len(w) == 4 and w[0] == 'vertex':
                cur.append((float(w[1]), float(w[2]), float(w[3])))
                if len(cur) == 3: out.append(tuple(cur)); cur = []
        return out
    n = struct.unpack_from('<I', data, 80)[0]
    return [tuple(struct.unpack_from('<fff', data, 84 + 50 * i + 12 + 12 * k) for k in range(3)) for i in range(n)]
