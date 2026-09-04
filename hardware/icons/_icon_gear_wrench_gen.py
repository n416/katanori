import math
from shapely.geometry import LineString, Polygon, MultiLineString
from shapely.affinity import rotate, translate

cx, cy = 74, 42
Ro, Rr = 34, 26            # 歯先 / 歯底
N = 8
half_top, half_base = 7, 11
sw = 5                     # 線幅
GAP = 4                    # ギアの線とレンチの線の間の空き（インク同士）
STEP = 1.0                 # 弧の分割角(deg)

def pt(r, deg):
    a = math.radians(deg); return (cx + r*math.cos(a), cy + r*math.sin(a))
def arc(r, a0, a1, center=(0,0)):
    n = max(2, int(abs(a1-a0)/STEP)+1)
    return [(center[0]+r*math.cos(math.radians(a0+(a1-a0)*i/n)),
             center[1]+r*math.sin(math.radians(a0+(a1-a0)*i/n))) for i in range(n+1)]

# --- ギア中心線（閉じた折れ線） ---
g = []
for k in range(N):
    t = -90 + k*360/N
    g += arc(Rr, t-(360/N-half_base), t-half_base, (cx,cy))[1:] if k else [pt(Rr, t-half_base)]
    g += [pt(Ro, t-half_top), pt(Ro, t+half_top), pt(Rr, t+half_base)]
# 最後の歯底弧: 最終歯の右端 → 最初の歯の左端
t_last = -90 + (N-1)*360/N
g += arc(Rr, t_last+half_base, -90-half_base+360, (cx,cy))[1:]
gear = LineString(g)

# --- レンチ中心線（ローカル: 軸 +x, 頭が原点） ---
R, jw, hw, L = 15, 7, 6, 38
jx = math.sqrt(R*R-jw*jw); hx = math.sqrt(R*R-hw*hw)
# 上側の弧: 角度 atan2(-hw,-hx)(約-157°→ 203°) から atan2(-jw,jx)(約-25°→335°) へ増加方向
a0 = math.degrees(math.atan2(-hw,-hx)) % 360; a1 = math.degrees(math.atan2(-jw,jx)) % 360
w = [(-L,-hw), (-hx,-hw)] + arc(R, a0, a1)[1:]
w += [(3,-jw), (3,jw), (jx,jw)]
a0 = math.degrees(math.atan2(jw,jx)); a1 = math.degrees(math.atan2(hw,-hx))
w += arc(R, a0, a1)[1:]
w += [(-L,hw)] + arc(hw, 90, 270, (-L,0))[1:]
wrench = Polygon(w)
wrench = translate(rotate(wrench, -45, origin=(0,0)), cx, cy)

# --- ギアをレンチ周りで切る ---
cut = wrench.buffer(sw + GAP, join_style=1)   # 線幅/2 ×2 + 空き
pieces = gear.difference(cut)
if pieces.geom_type == "LineString": pieces = [pieces]
else: pieces = list(pieces.geoms)

def path(coords, close=False):
    coords = list(coords)
    s = "M " + " L ".join("%.2f %.2f" % c for c in coords)
    return s + (" Z" if close else "")

gear_paths = "\n".join(f'    <path d="{path(p.simplify(0.02).coords)}"/>' for p in pieces)
wc = list(wrench.exterior.coords)[:-1]
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="480" height="480">
  <g fill="none" stroke="#555" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round">
{gear_paths}
    <path d="{path(LineString(wc).simplify(0.02).coords, close=True)}"/>
  </g>
</svg>
'''
open("gear_wrench.svg","w",encoding="utf-8").write(svg)
print(len(pieces), "pieces;", len(svg), "bytes")
