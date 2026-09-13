# 案のファイルの単位どうしの重なりを 1 組ずつ STL に出して数える（2026-09-13）
#   python hardware/concepts/tools/pairs.py hardware/concepts/concept_a_frame.scad
#   結果は 3 分岐: ERROR（OpenSCAD が落ちた）／ 空（重なり無し）／ 数値（重なりの体積 mm³）
import subprocess, sys, os, itertools, struct, re
O = r"C:/Program Files/OpenSCAD (Nightly)/openscad.exe"
f = sys.argv[1]
src = open(f, encoding="utf-8").read()
m = re.search(r'UNITS\s*=\s*\[(.*?)\];', src)
units = re.findall(r'"(\w+)"', m.group(1))
tmp = os.path.join(os.path.dirname(f), "_pair.stl")

def vol(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:5] == b"solid":
        tris = re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data.decode("ascii", "ignore"))
        pts = [tuple(float(c) for c in t) for t in tris]
        tri = [pts[i:i + 3] for i in range(0, len(pts), 3)]
    else:
        n = struct.unpack("<I", data[80:84])[0]
        tri = []
        for i in range(n):
            o = 84 + i * 50 + 12
            v = struct.unpack("<9f", data[o:o + 36])
            tri.append([v[0:3], v[3:6], v[6:9]])
    xs=[p[0] for t in tri for p in t]; ys=[p[1] for t in tri for p in t]; zs=[p[2] for t in tri for p in t]
    global bbox; bbox = (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)) if tri else None
    s = 0.0
    for a, b, c in tri:
        s += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return len(tri), abs(s)

rows = []
for a, b in itertools.combinations(units, 2):
    if os.path.exists(tmp): os.remove(tmp)
    r = subprocess.run([O, "--backend=manifold", "-o", tmp, "-D", 'part="pair"', "-D", f'A="{a}"', "-D", f'B="{b}"', f],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    err = [l for l in (r.stdout + r.stderr).splitlines() if "ERROR" in l or "WARNING" in l]
    if err or (r.returncode != 0 and "empty" not in (r.stdout + r.stderr)):
        rows.append((a, b, "ERROR " + (err[0] if err else str(r.returncode))))
        continue
    if not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
        rows.append((a, b, "空"))
        continue
    n, v = vol(tmp)
    rows.append((a, b, "空" if n == 0 else f"{v:.2f} mm3 ({n} tri) bbox X {bbox[0]:.1f}..{bbox[1]:.1f} Y {bbox[2]:.1f}..{bbox[3]:.1f} Z {bbox[4]:.1f}..{bbox[5]:.1f}"))
if os.path.exists(tmp): os.remove(tmp)
out = os.path.join(os.path.dirname(f), "_pairs_" + os.path.basename(f).replace(".scad", ".txt"))
with open(out, "w", encoding="utf-8") as fh:
    for a, b, s in rows:
        fh.write(f"{a:5s} x {b:5s} : {s}\n")
print(out)
