# -*- coding: utf-8 -*-
"""つまみを回しながら当たりを掃く。  python hardware/tools/_v6_gear_sweep.py

🔴 静止の 1 姿勢だけの検査は、回る機構の証拠にならない。
🔴 可動域は SPIN −160.02 〜 +160.02（止めピンは島の反対側 180 度から出発する）。
   **0〜320 ではない。**最初そう掃いて、途中の 160〜200（島に当たる窓）を 40 度刻みが跨いでいた。
🔒 掃き方の設計:
   ① 細: 歯の噛み合いの模様は**つまみの歯 1 枚分 360/28 = 12.857 度で一巡する**
        （中継〜読み取りの側も、同じ鎖で回るので周期は同じ）。そこを 0.5 度刻みで全部見る
   ② 粗: 止めピンは周期を持たない（可動域の中を一度だけ通る）ので、全域を 20 度刻み
   ③ 対照: 可動域の外（±170・180）で spin_shell が反応すること
"""
import os, subprocess, sys
SCAD  = os.path.join('hardware', '_v6_gear.scad')
OSC   = r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe'
OUT   = os.path.join('hardware', '_tmp_v6chk')
EMPTY = 'Current top level object is empty.'
sys.path.insert(0, os.path.join('hardware', 'tools')); from stl_read import tris

PITCH  = 360.0 / 28
TRAVEL = 160.02
FINE   = ['spin_shell', 'spin_rs', 'spin_mesh_ki', 'spin_mesh_is']   # 歯の位相で変わる
COARSE = ['spin_shell', 'spin_brk', 'spin_pin']                      # 止めピン・軸まわり

def run(part, spin):
    stl = os.path.join(OUT, 'sw.stl')
    if os.path.exists(stl): os.remove(stl)
    r = subprocess.run([OSC, '--backend=manifold', '-o', stl, '-D', 'part="%s"' % part,
                        '-D', 'SPIN=%s' % spin, SCAD], capture_output=True, text=True, errors='replace')
    se = r.stderr or ''
    warn = [l for l in se.splitlines() if 'WARNING' in l or 'ERROR:' in l]
    if r.returncode != 0 and EMPTY in se: return ('空', 0.0, warn)
    if r.returncode != 0: return ('ERROR', None, warn + [se.strip()[:120]])
    if not os.path.exists(stl): return ('ERROR(STLなし)', None, warn)
    t = tris(stl); v = 0.0
    for a, b, c in t:
        v += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    return ('数値', abs(v), warn)

hits, warned, errs = [], [], []
def sweep(title, parts, angles):
    print(title)
    print('  %-9s %s' % ('SPIN', ' '.join('%-13s' % p for p in parts)))
    for a in angles:
        cells = []
        for p in parts:
            kind, v, w = run(p, a)
            if w: warned.append((p, a, w[0][:80]))
            if kind == '空':     cells.append('%-13s' % '空')
            elif kind == '数値':
                cells.append('%-13s' % ('%.4f' % v))
                if v > 1e-6: hits.append((p, a, v))
            else:
                cells.append('%-13s' % kind); errs.append((p, a, kind))
        print('  %-9.2f %s' % (a, ' '.join(cells)))

sweep('① 細: 歯 1 枚分 %.3f 度を 0.5 度刻み（歯の位相はこれで全部通る）' % PITCH,
      FINE, [round(i * 0.5, 2) for i in range(int(PITCH / 0.5) + 2)])
print('')
sweep('② 粗: 可動域 ±%.2f 度を 20 度刻み' % TRAVEL,
      COARSE, [round(x, 2) for x in [-160.02] + [i * 20.0 for i in range(-7, 8)] + [160.02]])
print('')
print('③ 対照: 可動域の外。止めピンが島に当たるはず')
for a in (170, 180, -170, -180):
    kind, v, w = run('spin_shell', a)
    mark = '✅ 止めが効いている' if kind == '数値' and v > 1e-6 else '🔴 反応しない'
    print('   spin_shell @ %-6s %s  %s' % (a, ('%.4f mm3' % v) if kind == '数値' else kind, mark))
print('')
if errs:   print('🔴 ERROR %d 件: %s' % (len(errs), errs[:5]))
if warned: print('🔴 警告 %d 件: %s' % (len(warned), warned[:3]))
if hits:
    print('🔴 可動域の中で当たった姿勢 %d 件:' % len(hits))
    for p, a, v in hits[:20]: print('   %s @ %.2f 度 … %.4f mm3' % (p, a, v))
else:
    print('==== 判定: 可動域の全域・歯の全位相で当たり無し（ERROR 0・警告 0）====')
