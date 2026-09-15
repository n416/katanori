# -*- coding: utf-8 -*-
"""ASCII STL をバイナリ STL に上書き変換する。python hardware/tools/stl_bin.py a.stl [b.stl ...]。
   見積りサイト（3d-print-express.com 等）はバイナリ STL しか受け付けない物がある（80〜84 バイト目を三角形数として読む）。
   OpenSCAD で書き出すときは --export-format=binstl を付ければこのツールは要らない。既にバイナリの物は触らない。"""
import struct, sys
for p in sys.argv[1:]:
    data = open(p,'rb').read()
    if not (data[:5]==b'solid' and b'facet' in data[:400]):
        print(p, 'already binary'); continue
    tris=[]; n=None; cur=[]
    for line in data.decode('ascii','ignore').splitlines():
        w=line.split()
        if len(w)==5 and w[:2]==['facet','normal']: n=tuple(float(x) for x in w[2:])
        elif len(w)==4 and w[0]=='vertex':
            cur.append(tuple(float(x) for x in w[1:]))
            if len(cur)==3: tris.append((n,cur)); cur=[]
    out=bytearray(b'OpenSCAD_Model'.ljust(80,b'\0'))+struct.pack('<I',len(tris))
    for n,vs in tris:
        out+=struct.pack('<fff',*n)
        for v in vs: out+=struct.pack('<fff',*v)
        out+=b'\0\0'
    open(p,'wb').write(out)
    print(p, len(tris),'tris', len(out),'bytes', 'site-check:', 'OK' if len(tris)>0 and len(out)==84+50*len(tris) else 'NG')
