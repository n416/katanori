# -*- coding: utf-8 -*-
"""最小構成: 傾いた床の上に立ったねじ 1 本が、高さ w の壁を越えて倒れるか。MuJoCo の物理が信用できるかの検算。
   使い方: python topple_min.py tilt w L [mu]"""
import sys, math, numpy as np, mujoco
tilt, w, L = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
mu = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
OPT = sys.argv[5:]   # center: ねじをスリット中央（壁から 2.3）に置く / deck: 壁の上に水平の板
SC = 0.01; HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
a = math.radians(tilt)
# 床: 原点を通り +Y へ tilt 下がる板（厚 5）。壁: 床の +Y 側 y=6 の位置に、床の面から高さ w（床に垂直に立つ）
floor_xy = f"1 0 0 0 {math.cos(a):.6f} {-math.sin(a):.6f}"
def on_floor(y_along, z_up):   # 床の面に沿った座標 → 世界
    return (y_along * math.cos(a) - z_up * (-math.sin(a)) * 0 + z_up * math.sin(a) * 0, 0)
def frame(y_along, z_up):
    y = y_along * math.cos(a) + z_up * math.sin(a); z = -y_along * math.sin(a) + z_up * math.cos(a)
    return y, z
fy, fz = frame(0, -2.5); wy, wz = frame(6 + 2.5, w / 2 - 20)   # 壁は床の面から w まで（下は床に埋める）
sy, sz = frame(6 - (2.3 if "center" in OPT else 1.05), 0.05)   # ねじ: 先を壁の際（or スリット中央）に、軸は壁と平行（床に垂直）
qa = math.radians(-tilt / 2)
# デッキ: 壁の内側上の角（床の面から w、壁の面）を通る水平の板。厚 1・+Y へ 6
cy, cz = frame(6, w)          # 壁の内側上の角（世界）
DW = 0.75 if "narrow" in OPT else 3.0
deck_geom = f'<geom name="deck" type="box" pos="0 {(cy + 0.2 + DW)*SC:.5f} {(cz - 6)*SC:.5f}" size="0.3 {DW*SC:.5f} {6*SC:.5f}" friction="{mu} 0.005 0.0001"/>' if "deck" in OPT else ""   # 壁の角より 0.2 外から、厚 12。narrow で幅 1.5
xml = f'''<mujoco><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<worldbody>
<geom name="floor" type="box" pos="0 {fy*SC:.5f} {fz*SC:.5f}" size="0.3 0.3 {2.5*SC:.5f}" xyaxes="{floor_xy}" friction="{mu} 0.005 0.0001"/>
<geom name="wall" type="box" pos="0 {wy*SC:.5f} {wz*SC:.5f}" size="0.3 {2.5*SC:.5f} {(w/2+20)*SC:.5f}" xyaxes="{floor_xy}" friction="{mu} 0.005 0.0001"/>
<geom name="ground" type="plane" pos="0 0 -0.5" size="2 2 0.1"/>
{deck_geom}
<body name="s" pos="0 {sy*SC:.5f} {sz*SC:.5f}" quat="{math.cos(qa):.6f} {math.sin(qa):.6f} 0 0"><freejoint/>
<geom type="cylinder" size="{SHANK/2*SC:.5f} {L/2*SC:.5f}" pos="0 0 {L/2*SC:.5f}" density="7850" friction="{mu} 0.005 0.0001"/>
<geom type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(L+HEAD_H/2)*SC:.5f}" density="7850" friction="{mu} 0.005 0.0001"/>
</body></worldbody></mujoco>'''
m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
def tiltdeg(): R = d.xmat[m.body("s").id].reshape(3, 3); return math.degrees(math.acos(max(-1, min(1, R[2, 2]))))
tr = []
for k in range(int(4.0 / m.opt.timestep)):
    mujoco.mj_step(m, d)
    if k % int(0.5 / m.opt.timestep) == 0: tr.append(f"{tiltdeg():.0f}°")
p = d.xpos[m.body("s").id] / SC
vs = math.pi * (SHANK/2)**2 * L; vh = math.pi * (HEAD_D/2)**2 * HEAD_H; hc = (vs*L/2 + vh*(L+HEAD_H/2)) / (vs+vh)
pred = "倒れる" if (hc - w) * math.sin(a) > (SHANK/2) * math.cos(a) else "残る"
res = "外へ落ちた" if p[1] > 9 and p[2] < 0 else ("壁の外へ倒れた" if p[1] > 8 else "残った")
print(f"{' '.join(OPT):14s} tilt {tilt:>4.0f}  w {w:4.1f}  x{L:.0f}  重心 {hc:.2f}  式の予想 {pred}  → 結果 {res}  (y={p[1]:.1f} z={p[2]:.1f} 傾き {tiltdeg():.0f}°)  経過 {' '.join(tr)}")
