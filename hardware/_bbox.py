import sys, struct
def tris(p):
    d=open(p,'rb').read()
    if d[:5]==b'solid' and b'facet' in d[:400]:
        t=d.decode('utf8','ignore').split(); pts=[];i=0
        while i<len(t):
            if t[i]=='vertex': pts.append(tuple(float(x) for x in t[i+1:i+4])); i+=4
            else: i+=1
        return [pts[i:i+3] for i in range(0,len(pts),3)]
    n=struct.unpack('<I',d[80:84])[0]
    return [[struct.unpack('<12f',d[84+i*50:84+i*50+48])[j:j+3] for j in (3,6,9)] for i in range(n)]
for p in sys.argv[1:]:
    T=tris(p); xs=[v[0] for t in T for v in t]; ys=[v[1] for t in T for v in t]; zs=[v[2] for t in T for v in t]
    v=abs(sum((a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6 for a,b,c in T))
    print(f"{p}: {max(xs)-min(xs):.2f} x {max(ys)-min(ys):.2f} x {max(zs)-min(zs):.2f}  min=({min(xs):.2f},{min(ys):.2f},{min(zs):.2f})  vol={v:.0f}mm3  tris={len(T)}")
