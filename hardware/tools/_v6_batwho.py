# -*- coding: utf-8 -*-
"""電池を置いてみて、**当たった相手を 1 つずつ**出す（筐体 v6）。

🔴 合計や最小だけ見ると、要素が死んでいても正常に見える（記憶 `check-each-not-the-total`）。
   ⇒ 相手ごとに分けて出す。**空も 0.000 と書いて並べる**（黙って消さない）。
🔒 error / empty / 数値 の 3 分岐。対照を毎回 1 本通す。

使い方: python hardware/tools/_v6_batwho.py 幅 丈 X Z  厚み,厚み,… Y,Y,…
例    : python hardware/tools/_v6_batwho.py 30 40 8.5 9.4  5.0,5.5,6.0,6.5  27.2,30.0,32.7,34.3
"""
import subprocess, os, sys, tempfile
OS = r"C:/Program Files/OpenSCAD (Nightly)/openscad.exe"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__)); from stl_read import tris
SCAD = os.path.join(tempfile.gettempdir(), "_v6_batwho.scad")
STL  = os.path.join(tempfile.gettempdir(), "_v6_batwho.stl")
FOES = ["respeaker()", "hub_board()", "post_solids()", "shell_shell()", "gear_train()",
        "oled()", "chg_usb()", "speaker()", "slide_switch()",
        "translate([37.4,3.0,8.8]) cube([8.3,6.7,6.64])"]
open(SCAD, "w", encoding="utf-8").write(
 'include <%s/hardware/_v6_portrait.scad>\npart="none";\nB=[0,0,0,1,1,1];\nF=0;\n'
 'module foe(i){ %s }\n'
 'intersection(){ translate([B[0],B[1],B[2]]) cube([B[3]-B[0],B[4]-B[1],B[5]-B[2]]); foe(F); }\n'
 % (ROOT.replace("\\","/"),
    " ".join('if(i==%d) %s;' % (i, f) for i, f in enumerate(FOES + ["cube([99,99,99])"]))))
EMPTY = "Current top level object is empty"
# 🔒 模型に焼き込まずに試すための上書き。例: V6_DEFS="J2_H=2.95"
DEFS = [x for x in os.environ.get("V6_DEFS", "").split(",") if x.strip()]
def vol(b, f):
    if os.path.exists(STL): os.remove(STL)
    cmd = [OS,"--backend=manifold","-o",STL,
           "-D","B=[%g,%g,%g,%g,%g,%g]"%tuple(b),"-D","F=%d"%f]
    for kv in DEFS: cmd += ["-D", kv]          # 環境変数 V6_DEFS="J2_H=2.95,..." で上書き
    r = subprocess.run(cmd + [SCAD], capture_output=True)
    if os.path.exists(STL):
        v=0.0
        for a,c,d in tris(STL):
            v+=(a[0]*(c[1]*d[2]-c[2]*d[1])-a[1]*(c[0]*d[2]-c[2]*d[0])+a[2]*(c[0]*d[1]-c[1]*d[0]))/6.0
        return abs(v)
    if EMPTY in (r.stderr or b"").decode("utf-8","replace"): return 0.0
    raise SystemExit("🔴 検査が落ちた（空ではない）rc=%d F=%d B=%s" % (r.returncode, f, b))
def main():
    W,H,X,Z = map(float, sys.argv[1:5])
    Ts = [float(v) for v in sys.argv[5].split(',')]
    Ys = [float(v) for v in sys.argv[6].split(',')]
    c = vol([X,20.0,Z,X+W,60.0,Z+5.0], len(FOES))   # 🔒 対照: 99 の塊と必ず重なる
    print("対照（電池の箱 × 99 の塊）: %.3f mm3  ⇒ 検査は生きている" % c)
    if c < 1e-6: sys.exit("🔴 対照が 0")
    print("電池 %g x %g  X %g  Z %g" % (W,H,X,Z))
    for T in Ts:
        for Y in Ys:
            b = [X,Y,Z,X+W,Y+H,Z+T]
            rows = [(FOES[i], vol(b,i)) for i in range(len(FOES))]
            tot = sum(v for _,v in rows)
            print("\n  厚み %.1f  Y %.1f  (Z %.2f..%.2f / Y %.2f..%.2f)   合計 %s"
                  % (T, Y, Z, Z+T, Y, Y+H, "**空・入る**" if tot < 1e-6 else "%.3f mm3" % tot))
            for n,v in rows:
                print("      %-46s %9.3f" % (n, v))
if __name__ == "__main__": main()
