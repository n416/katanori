# -*- coding: utf-8 -*-
"""筐体 v6 の内側の**空き高さの地図**を作り、電池が入る帯を場所ごとに出す。

🔴 2026-09-13 の反省 3 つ（全部この道具に埋めた）
  ① 「空きは 5.355 しかない」と**スカラー 1 個**で言った。実際の天井 U3 は
     7.90 × 5.28 の**島**（X 10.772〜18.672 / Y 27.347〜32.627・底 14.755）で、
     電池の足形 1200mm² の 3.5% しか塞いでいない。⇒ 地図で出す。
  ② 足形ひとつを丸ごと当てて **bbox の min/max** を床・天井と呼んだ。
     相手が飛び飛びだと bbox は窓いっぱいに広がり、**全部 0.02** になった。
     ⇒ **升ごと**に測る。升の中なら min/max が本当に床と天井になる。
  ③ 窓を閉区間で取ると、天面がちょうど窓の縁にある相手（J2 の天面 = 9.400）と
     **厚み 0 で接触**し、manifold がかけらを返す。⇒ 縁を E だけ開ける。

やり方: 内寸を STEP mm の升に切り、升ごとに
   床   = Z SPLIT より下にある物の一番高い所（無ければ板の上 FLOOR）
   天井 = Z SPLIT より上にある物の一番低い所（無ければ内寸の天 CEIL）
  ⇒ 電池の帯 = 足形が覆う升の (天井の最小 − 床の最大)。
  ⚠ SPLIT より上に**もっと広い帯**があっても見つけない。控えめに外す側の道具。

使い方:
   python hardware/frozen/v6/tools/_v6_batmap.py scan [きざみ]     升の地図を作る（数分・キャッシュ）
   python hardware/frozen/v6/tools/_v6_batmap.py fit 幅 丈          その地図から帯を出す
"""
import subprocess, os, sys, tempfile, json
OS = r"C:/Program Files/OpenSCAD (Nightly)/openscad.exe"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))   # frozen/v6/tools → リポジトリの根
sys.path.insert(0, os.path.join(ROOT, 'hardware', 'tools')); from stl_read import tris
SCAD  = os.path.join(tempfile.gettempdir(), "_v6_batmap.scad")
STL   = os.path.join(tempfile.gettempdir(), "_v6_batmap.stl")
CACHE = os.path.join(tempfile.gettempdir(), "_v6_batmap.json")
FLOOR, SPLIT, CEIL = 4.6, 9.4, 21.0        # 板の上 / 割る高さ / 内寸の天
IX0, IX1, IY0, IY1 = 2.0, 46.0, 2.0, 86.0  # 内寸
E = 0.02                                   # 窓の縁を開ける分（③）
open(SCAD, "w", encoding="utf-8").write(
 'include <%s/hardware/frozen/v6/_v6_portrait.scad>\npart = "none";\nB = [0,0,0,1,1,1];\n'
 'module blockers() { oled(); respeaker(); hub_board(); chg_usb(); speaker(); gear_train();\n'
 '  slide_switch(); post_solids(); shell_shell();\n'
 '  translate([37.4,3.0,8.8]) cube([8.3,6.7,6.64]); }\n'
 'intersection() { translate([B[0],B[1],B[2]]) cube([B[3]-B[0],B[4]-B[1],B[5]-B[2]]); blockers(); }\n'
 % ROOT.replace("\\","/"))
EMPTY = "Current top level object is empty"
def zrange(b):
    """3 分岐: (zmin, zmax) / 空なら None / それ以外は落とす。"""
    if os.path.exists(STL): os.remove(STL)
    r = subprocess.run([OS,"--backend=manifold","-o",STL,
                        "-D","B=[%g,%g,%g,%g,%g,%g]"%tuple(b),SCAD],capture_output=True)
    if os.path.exists(STL):
        zs=[q[2] for t in tris(STL) for q in t]
        return (min(zs), max(zs))
    if EMPTY in (r.stderr or b"").decode("utf-8","replace"): return None
    raise SystemExit("🔴 検査が落ちた（空ではない）rc=%d B=%s" % (r.returncode, b))
def scan(step):
    nx, ny = int(round((IX1-IX0)/step)), int(round((IY1-IY0)/step))
    # 🔒 対照: 必ず当たる柱。空なら地図全部が嘘。
    if zrange([IX0+E, IY0+E, 0.0, IX1-E, IY1-E, 25.0]) is None:
        sys.exit("🔴 対照が空 ⇒ 検査が死んでいる")
    fl = [[0.0]*nx for _ in range(ny)]; ce = [[0.0]*nx for _ in range(ny)]
    for j in range(ny):
        for i in range(nx):
            x0, y0 = IX0+i*step+E, IY0+j*step+E
            x1, y1 = x0+step-2*E, y0+step-2*E
            lo = zrange([x0, y0, FLOOR,   x1, y1, SPLIT-E])
            hi = zrange([x0, y0, SPLIT+E, x1, y1, CEIL-E])
            fl[j][i] = FLOOR if lo is None else lo[1]
            ce[j][i] = CEIL  if hi is None else hi[0]
        sys.stderr.write("  行 %d/%d\n" % (j+1, ny)); sys.stderr.flush()
    json.dump({"step":step,"nx":nx,"ny":ny,"floor":fl,"ceil":ce}, open(CACHE,"w"))
    print("升 %d x %d（きざみ %g）を %s に書いた" % (nx, ny, step, CACHE))
def load():
    if not os.path.exists(CACHE): sys.exit("🔴 地図が無い ⇒ 先に scan を回す")
    return json.load(open(CACHE))
def fit(W, H):
    m = load(); st, nx, ny = m["step"], m["nx"], m["ny"]; fl, ce = m["floor"], m["ceil"]
    cw, ch = int(round(W/st+0.4999)), int(round(H/st+0.4999))   # 升は切り上げ（控えめ）
    if cw > nx or ch > ny: sys.exit("🔴 %g x %g は内寸に入らない" % (W, H))
    print("電池 %g x %g ＝ 升 %d x %d（きざみ %g・切り上げ＝控えめ）" % (W, H, cw, ch, st))
    rows = []
    for j in range(ny-ch+1):
        r = []
        for i in range(nx-cw+1):
            f = max(fl[j+b][i+a] for b in range(ch) for a in range(cw))
            c = min(ce[j+b][i+a] for b in range(ch) for a in range(cw))
            r.append((round(c-f,3), round(f,3), round(c,3)))
        rows.append(r)
    xs = [IX0+i*st for i in range(len(rows[0]))]
    print("\n      " + "".join("%6.1f" % x for x in xs) + "   ← X（電池の左端）")
    for j, r in enumerate(rows):
        print("Y%5.1f" % (IY0+j*st) + "".join("%6.2f" % v[0] for v in r))
    best = sorted(((v[0], IX0+i*st, IY0+j*st, v[1], v[2])
                   for j, r in enumerate(rows) for i, v in enumerate(r)), reverse=True)
    print("\n=== 帯の広い置き場 8 つ ===")
    for v, x, y, f, c in best[:8]:
        print("  帯 %5.2f   位置 X %5.1f  Y %5.1f   床 %6.3f  天井 %6.3f" % (v, x, y, f, c))
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        scan(float(sys.argv[2]) if len(sys.argv) > 2 else 2.0)
    elif len(sys.argv) > 3 and sys.argv[1] == "fit":
        fit(float(sys.argv[2]), float(sys.argv[3]))
    else:
        sys.exit(__doc__)
