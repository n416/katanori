import sys, struct
def vol(p):
    d=open(p,'rb').read()
    if d[:5]==b'solid' and b'facet' in d[:400]:
        t=d.decode('utf8',"ignore").split(); v=[];pts=[]
        i=0; 
        while i<len(t):
            if t[i]=='vertex': pts.append(tuple(float(x) for x in t[i+1:i+4])); i+=4
            else: i+=1
        tris=[pts[i:i+3] for i in range(0,len(pts),3)]
    else:
        n=struct.unpack('<I',d[80:84])[0]; tris=[]
        for i in range(n):
            o=84+i*50; f=struct.unpack('<12f',d[o:o+48]); tris.append([f[3:6],f[6:9],f[9:12]])
    s=0.0
    for a,b,c in tris:
        s+= (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0]))/6.0
    return abs(s)
for p in sys.argv[1:]: print(p, round(vol(p),2), "mm3")
