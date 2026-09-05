# -*- coding: utf-8 -*-
"""binary STL の体積 [mm3]。python tools/stl_vol.py a.stl ..."""
import struct, sys
for p in sys.argv[1:]:
    with open(p,'rb') as f:
        f.read(80); n = struct.unpack('<I', f.read(4))[0]; v = 0.0
        for _ in range(n):
            r = f.read(50); a = struct.unpack_from('<fff', r, 12); b = struct.unpack_from('<fff', r, 24); c = struct.unpack_from('<fff', r, 36)
            v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    print('%-12s %s' % (p.split('/')[-1].replace('.stl',''), 'EMPTY' if n == 0 else '%.2f mm3' % abs(v)))
