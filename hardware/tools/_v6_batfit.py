# -*- coding: utf-8 -*-
"""電池が入るか、模型の実体に当てて調べる。
   使い方: python hardware/tools/_v6_batfit.py 幅 丈 厚み [逃げ]
   🔒 障害物は「部品の表」ではなく `_v6_portrait.scad` の実体（respeaker_lite() 込み）から取る。
      表には除外・置き直しがある（J1 は STEP から手で置き直されていて、表のエントリは使われていない）。
   置き方を総当たりするので「入らない」も言える（貪欲に広げる探し方では言えなかった）。"""
import subprocess, os, sys, tempfile
OS = r"C:/Program Files/OpenSCAD (Nightly)/openscad.exe"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__)); from stl_read import tris
SCAD = os.path.join(tempfile.gettempdir(), "_v6_batfit.scad")
STL  = os.path.join(tempfile.gettempdir(), "_v6_batfit.stl")
open(SCAD, "w", encoding="utf-8").write(
 'include <%s/hardware/_v6_portrait.scad>\npart = "none";\nB = [0,0,0,1,1,1];\n'
 'module cand() translate([B[0],B[1],B[2]]) cube([B[3]-B[0],B[4]-B[1],B[5]-B[2]]);\n'
 'module blockers() { oled(); respeaker(); hub_board(); chg_usb(); speaker(); gear_train();\n'
 '  slide_switch(); wire_bay(); post_solids(); shell_shell();\n'
 '  translate([37.4,3.0,8.8]) cube([8.3,6.7,6.64]); }\n'
 'intersection() { cand(); blockers(); }\n' % ROOT.replace("\\","/"))
def hit(b):
    if os.path.exists(STL): os.remove(STL)
    subprocess.run([OS,"--backend=manifold","-o",STL,"-D","B=[%g,%g,%g,%g,%g,%g]"%tuple(b),SCAD],capture_output=True)
    if not os.path.exists(STL): return 0.0
    v=0.0
    for a,c,d in tris(STL):
        v+=(a[0]*(c[1]*d[2]-c[2]*d[1])-a[1]*(c[0]*d[2]-c[2]*d[0])+a[2]*(c[0]*d[1]-c[1]*d[0]))/6.0
    return abs(v)
def frange(a,b,s):
    x=a
    while x<=b+1e-9: yield round(x,2); x+=s
def fit(W,H,T,cl=0.0):
    W+=2*cl; H+=2*cl; T+=cl
    best=(1e9,None); n=0
    for z in frange(8.6, 15.6-T, 0.2):
        for x in frange(8.0, 40.0-W, 0.5):
            for y in frange(22.0, 79.0-H, 0.5):
                n+=1; v=hit([x,y,z,x+W,y+H,z+T])
                if v<best[0]: best=(v,(x,y,z))
                if v<1e-6: return 0.0,(x,y,z),n
    return best[0],best[1],n
if __name__=="__main__":
    W,H,T=map(float,sys.argv[1:4]); cl=float(sys.argv[4]) if len(sys.argv)>4 else 0.0
    v,p,n=fit(W,H,T,cl)
    print("%.1f x %.1f x %.1f（逃げ %.2f/片側）: %s  位置 %s  試した置き方 %d"
          %(W,H,T,cl,("入る" if v<1e-6 else "🔴 入らない 最小の食い込み %.2fmm3"%v),p,n))
