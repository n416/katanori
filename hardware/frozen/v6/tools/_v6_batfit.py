# -*- coding: utf-8 -*-
"""電池が入るか、模型の実体に当てて調べる。
   🔴 2026-09-13: 障害物に wire_bay()（実体でない予約の箱）を入れていた。
      予約は消して wires()（5 本の道）にしたが、**道はまだ避けて引いていない**ので
      障害物には入れない。⇒ 入れるのは実体だけ。
   🔴 2026-09-13(2): hit() が **STL が無い＝0.0** を返していた。
      OpenSCAD が落ちた（エラー）のと、当たりが無い（空）のが**同じ 0** に潰れていて、
      落ちた掃引が「全部入る」に見える。⇒ **error / empty / 数値 の 3 分岐**にした。
      さらに **必ず当たる対照**を毎回 1 本通す（0 なら検査そのものが死んでいる）。
      指摘: 調停役。記憶 `empty-is-not-clean` と同じ形。
   使い方: python hardware/frozen/v6/tools/_v6_batfit.py 幅 丈 厚み [逃げ]
   🔒 障害物は「部品の表」ではなく `_v6_portrait.scad` の実体（respeaker_lite() 込み）から取る。
      表には除外・置き直しがある（J1 は STEP から手で置き直されていて、表のエントリは使われていない）。
   置き方を総当たりするので「入らない」も言える（貪欲に広げる探し方では言えなかった）。"""
import subprocess, os, sys, tempfile
OS = r"C:/Program Files/OpenSCAD (Nightly)/openscad.exe"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))   # frozen/v6/tools → リポジトリの根
sys.path.insert(0, os.path.join(ROOT, 'hardware', 'tools')); from stl_read import tris
SCAD = os.path.join(tempfile.gettempdir(), "_v6_batfit.scad")
STL  = os.path.join(tempfile.gettempdir(), "_v6_batfit.stl")
open(SCAD, "w", encoding="utf-8").write(
 'include <%s/hardware/frozen/v6/_v6_portrait.scad>\npart = "none";\nB = [0,0,0,1,1,1];\n'
 'module cand() translate([B[0],B[1],B[2]]) cube([B[3]-B[0],B[4]-B[1],B[5]-B[2]]);\n'
 'module blockers() { oled(); respeaker(); hub_board(); chg_usb(); speaker(); gear_train();\n'
 '  slide_switch(); post_solids(); shell_shell();\n'
 '  translate([37.4,3.0,8.8]) cube([8.3,6.7,6.64]); }\n'
 'intersection() { cand(); blockers(); }\n' % ROOT.replace("\\","/"))
EMPTY = "Current top level object is empty"
N_EMPTY = [0]; N_NUM = [0]
def hit(b):
    """3 分岐。数値を返すか、空なら 0.0 を返すか、**それ以外は落とす**。"""
    if os.path.exists(STL): os.remove(STL)
    r = subprocess.run([OS,"--backend=manifold","-o",STL,
                        "-D","B=[%g,%g,%g,%g,%g,%g]"%tuple(b),SCAD],capture_output=True)
    if os.path.exists(STL):
        v=0.0
        for a,c,d in tris(STL):
            v+=(a[0]*(c[1]*d[2]-c[2]*d[1])-a[1]*(c[0]*d[2]-c[2]*d[0])+a[2]*(c[0]*d[1]-c[1]*d[0]))/6.0
        N_NUM[0]+=1; return abs(v)
    err = (r.stderr or b"").decode("utf-8","replace")
    if EMPTY in err:
        N_EMPTY[0]+=1; return 0.0
    raise SystemExit("🔴 検査が落ちた（空ではない）rc=%d  B=%s\n%s" % (r.returncode, b, err[-2000:]))
def control():
    """🔒 必ず当たる 1 本。箱を天地に貫く柱を入れて、床・柱・殻に当てる。
       ここが 0 か空なら、掃引の 0 は「入る」ではなく「検査が死んでいる」。"""
    v = hit([8.0, 22.0, 0.0, 38.0, 62.0, 25.0])
    if v < 1e-6:
        raise SystemExit("🔴 対照が当たらない ⇒ 検査そのものが死んでいる（掃引の 0 を信じてはいけない）")
    return v
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
    print("対照（箱を天地に貫く柱 × 障害物）: %.3f mm3  ⇒ 検査は生きている" % control())
    v,p,n=fit(W,H,T,cl)
    print("%.1f x %.1f x %.1f（逃げ %.2f/片側）: %s  位置 %s  試した置き方 %d"
          %(W,H,T,cl,("入る" if v<1e-6 else "🔴 入らない 最小の食い込み %.2fmm3"%v),p,n))
    print("   内訳: 数値 %d 回・空 %d 回・エラー 0 回（エラーは即座に落とす）" % (N_NUM[0], N_EMPTY[0]))
