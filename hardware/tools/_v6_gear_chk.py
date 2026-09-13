# -*- coding: utf-8 -*-
"""v6 機構の当たり検査を 1 本ずつ回す。
  python hardware/tools/_v6_gear_chk.py             … _v6_gear.scad の chk_* を全部
  python hardware/tools/_v6_gear_chk.py chk_mesh_ki … 名前を指定

🔴 回す前に古い STL を必ず消す（古い STL を読んで「当たり 0」と報告した事故がある）。
🔴 出そうとした所:
     空      … 交差が無い（OpenSCAD は rc=1 ＋ "Current top level object is empty." を返す。
                これは ERROR ではない。ここを取り違えると全部 ERROR に見える）
     0.0000  … 面で接触しているが体積は無い（座が相手の面に乗っている等）
     数値     … 食い込んでいる
     ERROR   … 評価そのものが落ちた。🔴 0 と数えない
"""
import os, re, subprocess, sys
SCAD  = os.path.join('hardware', '_v6_gear.scad')
OSC   = r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe'
OUT   = os.path.join('hardware', '_tmp_v6chk')
EMPTY = 'Current top level object is empty.'
sys.path.insert(0, os.path.join('hardware', 'tools')); from stl_read import tris

def vol(p):
    v = 0.0; t = tris(p)
    for a, b, c in t:
        v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    return (len(t), abs(v))

names = sys.argv[1:]
if not names:
    src = open(SCAD, encoding='utf-8').read()
    names = sorted(set(re.findall(r'part == "(chk_[a-z0-9_]+)"', src)))
os.makedirs(OUT, exist_ok=True)
groups = ((  [n for n in names if not n.startswith('chk_ctrl')], '実体（空 か 0 が正）'),
          (  [n for n in names if n     .startswith('chk_ctrl')], '対照（反応しなければ検査が壊れている）'))
bad = 0
warned = []
dead = []      # 反応しなかった対照（＝何も証明していない）
for group, label in groups:
    if not group: continue
    print('--- %s ---' % label)
    for n in group:
        stl = os.path.join(OUT, n + '.stl')
        if os.path.exists(stl): os.remove(stl)              # 🔴 先に消す
        r = subprocess.run([OSC, '--backend=manifold', '-o', stl, '-D', 'part="%s"' % n, SCAD],
                           capture_output=True, text=True, errors='replace')
        se   = r.stderr or ''
        warn = [l for l in se.splitlines() if ('ERROR' in l or 'WARNING' in l)]
        tail = ('  ⚠ ' + ' | '.join(warn)[:140]) if warn else ''
        if warn: warned.append(n)
        is_ctrl = n.startswith('chk_ctrl')
        if r.returncode != 0 and EMPTY in se:
            print('%-18s 空（交差なし）%s' % (n, tail))
            if is_ctrl: dead.append(n)
        elif r.returncode != 0:
            print('%-18s ERROR (rc=%d) %s' % (n, r.returncode, se.replace('\n', ' | ')[:240])); bad += 1
        elif not os.path.exists(stl):
            print('%-18s ERROR rc=0 なのに STL が無い%s' % (n, tail)); bad += 1
        else:
            nt, v = vol(stl)
            print('%-18s %s%s' % (n, 'EMPTY（面 0）' if nt == 0 else '%.4f mm3' % v, tail))
            if is_ctrl and (nt == 0 or v < 1e-6): dead.append(n)
print('ERROR %d 本' % bad)
if warned:
    print('🔴 警告のある検査 %d 本: %s' % (len(warned), ', '.join(warned)))
    print('   警告が出ている間は「空」を証拠にしない（形が壊れて空になっていることがある）')
else:
    print('警告 0 本')
if dead:
    print('🔴 反応しなかった対照 %d 本: %s' % (len(dead), ', '.join(dead)))
    print('   対照は**わざと外した図**なので、空なら対になっている実体の「空」は何も証明していない。')
    print('   相手の形が変わると、実体は空のまま対照だけが静かに失効する（2026-09-13 の OLED）')
else:
    print('対照はすべて反応')
ok = (bad == 0 and not warned and not dead)
print('')
print('==== 判定: %s ====' % ('通り（実体は当たっていない・検査は生きている）' if ok
      else '🔴 通っていない。上の ERROR / 警告 / 反応しなかった対照を見ること'))
print('（この 1 行だけ読めば足ります。共有する実体［殻・OLED・ReSpeaker・板・電池］の形を')
print('  割った／動かしたら、この 1 コマンドを回してください ── 2026-09-13 の規則 2）')
