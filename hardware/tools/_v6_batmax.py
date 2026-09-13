# -*- coding: utf-8 -*-
"""ある足形を置いたとき、**厚みをいくつまで上げられるか**を二分で出す（筐体 v6）。

🔴 「入るか / 入らないか」だけ聞くと、あと何ミリなのか分からない。
   ⇒ **上限そのもの**を返す。電池にもスピーカーにも使う。
🔒 error / empty / 数値 の 3 分岐。対照を毎回 1 本通す。
🔴 窓の縁の厚み 0 の接触を避けるため、当てる箱は XY を E だけ内側に取る
   （記憶 `manifold-zero-thickness-contact`）。

使い方: python hardware/tools/_v6_batmax.py 幅 丈 [X きざみ] [Y きざみ] [床,床,…]
例    : python hardware/tools/_v6_batmax.py 30 40 3.5 4 6.4,9.4
        python hardware/tools/_v6_batmax.py 23 15 3 4 4.6,6.4,8.6
"""
import subprocess, os, sys, tempfile
OS = r"C:/Program Files/OpenSCAD (Nightly)/openscad.exe"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__)); from stl_read import tris
# 🔴 名前に PID を入れる。固定名だと**同時に 2 本回したとき互いの STL を消し合う**
#   （別セッションが同じ道具を回すこともある ── 記憶 `parallel-sessions-same-repo`）
SCAD = os.path.join(tempfile.gettempdir(), "_v6_batmax_%d.scad" % os.getpid())
STL  = os.path.join(tempfile.gettempdir(), "_v6_batmax_%d.stl" % os.getpid())
IX0, IX1, IY0, IY1, CEIL = 2.0, 46.0, 2.0, 86.0, 21.0
E, RES = 0.02, 0.05
open(SCAD, "w", encoding="utf-8").write(
 'include <%s/hardware/_v6_portrait.scad>\npart="none";\nB=[0,0,0,1,1,1];\nC=0;\n'
 'module blockers(){ oled(); respeaker(); hub_board(); chg_usb(); speaker(); gear_train();\n'
 '  slide_switch(); post_solids(); shell_shell();\n'
 '  translate([37.4,3.0,8.8]) cube([8.3,6.7,6.64]); }\n'
 'intersection(){ translate([B[0],B[1],B[2]]) cube([B[3]-B[0],B[4]-B[1],B[5]-B[2]]);\n'
 '  if(C==1) cube([99,99,99]); else blockers(); }\n' % ROOT.replace("\\","/"))
EMPTY = "Current top level object is empty"
# 🔒 模型に焼き込まずに試すための上書き。例: V6_DEFS="J2_H=2.95"
DEFS = [x for x in os.environ.get("V6_DEFS", "").split(",") if x.strip()]
def vol(b, ctl=0):
    if os.path.exists(STL): os.remove(STL)
    cmd = [OS,"--backend=manifold","-o",STL,
           "-D","B=[%g,%g,%g,%g,%g,%g]"%tuple(b),"-D","C=%d"%ctl]
    for kv in DEFS: cmd += ["-D", kv]          # 環境変数 V6_DEFS="J2_H=2.95,..." で上書き
    r = subprocess.run(cmd + [SCAD], capture_output=True)
    if os.path.exists(STL):
        v=0.0
        for a,c,d in tris(STL):
            v+=(a[0]*(c[1]*d[2]-c[2]*d[1])-a[1]*(c[0]*d[2]-c[2]*d[0])+a[2]*(c[0]*d[1]-c[1]*d[0]))/6.0
        return abs(v)
    if EMPTY in (r.stderr or b"").decode("utf-8","replace"): return 0.0
    raise SystemExit("🔴 検査が落ちた（空ではない）rc=%d B=%s" % (r.returncode, b))
def maxT(x, y, z, W, H):
    """床 z に置いたとき入る厚みの上限。0.0 なら床のところで既に当たっている。"""
    lo, hi = 0.0, CEIL - z
    if vol([x+E, y+E, z, x+W-E, y+H-E, z+RES]) > 1e-6: return 0.0
    while hi - lo > RES:
        m = (lo + hi) / 2
        if vol([x+E, y+E, z, x+W-E, y+H-E, z+m]) > 1e-6: hi = m
        else: lo = m
    return lo
def main():
    W, H = float(sys.argv[1]), float(sys.argv[2])
    sx = float(sys.argv[3]) if len(sys.argv) > 3 else 3.5
    sy = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0
    zs = [float(v) for v in sys.argv[5].split(',')] if len(sys.argv) > 5 else [9.4]
    c = vol([10, 30, 10, 20, 40, 15], ctl=1)
    print("対照（箱 × 99 の塊）: %.3f mm3  ⇒ 検査は生きている" % c)
    if c < 1e-6: sys.exit("🔴 対照が 0")
    xs = [round(IX0+i*sx, 2) for i in range(int((IX1-W-IX0)/sx)+1)]
    ys = [round(IY0+j*sy, 2) for j in range(int((IY1-H-IY0)/sy)+1)]
    print("足形 %g x %g   置き場 %d 通り × 床 %s   分解能 %g" % (W, H, len(xs)*len(ys), zs, RES))
    best = []
    for z in zs:
        print("\n=== 床 Z %.2f ===" % z)
        print("      " + "".join("%6.1f" % x for x in xs) + "   ← X（左端）")
        for y in ys:
            row = [maxT(x, y, z, W, H) for x in xs]
            best += [(row[i], xs[i], y, z) for i in range(len(xs))]
            print("Y%5.1f" % y + "".join("%6.2f" % v for v in row))
    best.sort(reverse=True)
    print("\n=== 厚みを取れる置き場 8 つ ===")
    for t, x, y, z in best[:8]:
        print("  厚み %5.2f まで   X %5.1f  Y %5.1f  床 Z %.2f  （天面 %.2f）" % (t, x, y, z, z+t))
if __name__ == "__main__": main()
