# -*- coding: utf-8 -*-
"""最初の案（頭で吊るして滑らせ、階段の床で止める）を MuJoCo で回す（2026-09-07）。
   皿 1 本のスリット: 幅 SLIT_W の溝が板を貫き、下の床は 13 → 11 → 9 → 7 → 5 の階段。皿全体を X に傾けて、吊るされたねじを滑らせる。
   使い方: python sim_hang.py [皿の傾き 25] [摩擦 0.3] [seed 0] [gif] [n=10] [T=8] [single=長さ]
"""
import sys, math, random, io
import numpy as np, mujoco

SC = 0.01
KW = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
POS = [a for a in sys.argv[1:] if '=' not in a and a != 'gif']
INCL = float(POS[0]) if len(POS) > 0 else 25.0     # 皿の傾き（スリットに沿って下る）
MU = float(POS[1]) if len(POS) > 1 else 0.3
SEED = int(POS[2]) if len(POS) > 2 else 0
GIF = 'gif' in sys.argv
HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
LENS = [12, 10, 8, 6, 4]
SLIT_W = float(KW.get("slit", 2.4))
SHELF_T = 1.5            # 頭が乗る板の厚み
LOAD_L = 30; BIN_L = 16
FLOORS = [13, 11, 9, 7, 5]   # 入れ口＋区画 0 は 13、以後の区画
WALL = 2.0; RIB = 3.0        # スリットの両脇の肉

# 皿の座標: x = 進む向き（下り）、y = 幅、z = 上。板の上面 z=0。スリット中心 y=0
a = math.radians(INCL)
def world(x, y, z): return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))
geoms = []
def box(name, cx, cy, cz, hx, hy, hz, rgba="0.7 0.75 0.8 1"):
    wx, wy, wz = world(cx, cy, cz)
    geoms.append(f'<geom name="{name}" type="box" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" size="{hx*SC:.5f} {hy*SC:.5f} {hz*SC:.5f}" '
                 f'xyaxes="{math.cos(a):.6f} 0 {-math.sin(a):.6f} 0 1 0" rgba="{rgba}" friction="{MU} 0.005 0.0001"/>')
L = LOAD_L + BIN_L * len(FLOORS) + WALL
# 棚（頭が乗る板）: スリットの両脇、上面 z=0、厚 SHELF_T。幅方向は RIB
for sgn in (-1, 1):
    box(f"shelf{sgn}", L / 2, sgn * (SLIT_W / 2 + RIB / 2), -SHELF_T / 2, L / 2, RIB / 2, SHELF_T / 2)
# スリットの壁（棚の下、床まで）: 軸が横へ逃げないように
for sgn in (-1, 1):
    box(f"side{sgn}", L / 2, sgn * (SLIT_W / 2 + RIB / 2), -8, L / 2, RIB / 2, 8)
# 床の階段: 入れ口＋区画 0 は 13、区画 i は FLOORS[i]
segs = [(0, LOAD_L + BIN_L, FLOORS[0])] + [(LOAD_L + BIN_L * i, LOAD_L + BIN_L * (i + 1), FLOORS[i]) for i in range(1, len(FLOORS))]
for i, (x0, x1, d) in enumerate(segs):
    box(f"floor{i}", (x0 + x1) / 2, 0, -d - 1.5, (x1 - x0) / 2, SLIT_W / 2 + RIB, 1.5)
    if i > 0:   # 段の壁（前の床から今の床へ上がる）
        d_prev = segs[i - 1][2]
        box(f"riser{i}", x0 + 0.5, 0, -(d + d_prev) / 2, 0.5, SLIT_W / 2 + RIB, (d_prev - d) / 2 + 0.01)
box("endwall", L - WALL / 2, 0, -5, WALL / 2, SLIT_W / 2 + RIB, 12)
geoms.append('<geom name="ground" type="plane" pos="0 0 -0.6" size="3 3 0.1"/>')

random.seed(SEED)
N = 1 if "single" in KW else int(KW.get("n", 10))
lens = [float(KW["single"])] if "single" in KW else [LENS[i % len(LENS)] for i in range(N)]
if "single" not in KW: random.shuffle(lens)
bodies = []
for i, Ln in enumerate(lens):
    x = 4 + i * 4.2                      # 入れ口に並べて吊るす（頭の下面が棚の上面）
    wx, wy, wz = world(x, 0, -Ln + 0.05)  # 原点 = 先。頭の下面 = 先 + Ln = 棚の上 0.05
    # 軸を皿の z 向きに: 皿は y 軸まわりに傾いているので、ねじも同じだけ回す
    q = (math.cos(a / 2), 0, math.sin(a / 2), 0)   # y 軸まわり +a: z → (sin a, 0, cos a) = 皿の z
    bodies.append(f'''<body name="s{i}" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" quat="{q[0]:.6f} 0 {q[2]:.6f} 0"><freejoint/>
<geom name="s{i}_sh" type="cylinder" size="{SHANK/2*SC:.5f} {Ln/2*SC:.5f}" pos="0 0 {Ln/2*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
<geom name="s{i}_hd" type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(Ln+HEAD_H/2)*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')

def cam(pos, target, up=(0, 0, 1)):
    p = np.array(pos); f = np.array(target) - p; f /= np.linalg.norm(f)
    x = np.cross(f, up); x /= np.linalg.norm(x); y = np.cross(x, f)
    return " ".join(f"{v:.4f}" for v in p), " ".join(f"{v:.4f}" for v in np.concatenate([x, y]))
mid = world(L / 2, 0, 0)
cp, cxy = cam((mid[0] * SC, -0.9, mid[2] * SC + 0.25), (mid[0] * SC, 0, mid[2] * SC - 0.05))
xml = f'''<mujoco model="hang"><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody><light pos="0.5 -1 2" dir="-0.3 0.5 -1"/><camera name="iso" pos="{cp}" xyaxes="{cxy}"/>
{chr(10).join(geoms)}
{chr(10).join(bodies)}
</worldbody></mujoco>'''
open('hardware/sim/m2_sorter/hang.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
sid = [model.body(f"s{i}").id for i in range(N)]
renderer = mujoco.Renderer(model, 720, 1280) if GIF else None
frames = []; dt = model.opt.timestep; t = 0.0
T_END = float(KW.get("T", 8.0))
def tray_xz(p):   # 世界 → 皿の座標 (x, z)
    return (p[0] * math.cos(a) - p[2] * math.sin(a), p[0] * math.sin(a) + p[2] * math.cos(a))
x_start = [tray_xz(data.xpos[sid[i]] / SC)[0] for i in range(N)]
for k in range(int(T_END / dt)):
    mujoco.mj_step(model, data); t += dt
    if renderer is not None and k % int(0.1 / dt) == 0:
        renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
out = io.StringIO()
print(f"皿の傾き {INCL}  摩擦 {MU}  seed {SEED}  スリット {SLIT_W}  床 {FLOORS}  区画 {BIN_L}", file=out)
ok = 0
def seg_of(x): return 0 if x < LOAD_L + BIN_L else min(len(FLOORS) - 1, int((x - LOAD_L) // BIN_L))
for i in range(N):
    Ln = lens[i]; p = data.xpos[sid[i]] / SC; xr, zr = tray_xz(p)
    R = data.xmat[sid[i]].reshape(3, 3); ax = R[:, 2]     # ねじの軸（世界）
    # 皿の z 向きとの角度
    tz = np.array(world(0, 0, 1)); tilt = math.degrees(math.acos(max(-1, min(1, float(np.dot(ax, tz))))))
    expect = LENS.index(int(Ln)) if int(Ln) in LENS else -1
    seg = seg_of(xr); moved = xr - x_start[i]
    hanging = abs(zr - (-Ln)) < 0.6 and tilt < 30
    res = "OK" if (hanging and seg == expect) else "NG"; ok += (res == "OK")
    state = "吊るされたまま" if hanging else f"外れた（先 z={zr:.1f} 傾き {tilt:.0f}°）"
    print(f"  x{Ln:4.1f}: x={xr:6.1f}（{moved:+6.1f} 動いた）区画 {seg}  期待 {expect}  {state}  {res}", file=out)
print(f"正解 {ok}/{N}", file=out)
print(out.getvalue())
if frames:
    from PIL import Image
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(f'hardware/sim/m2_sorter/hang_{INCL:.0f}_{MU}_{SEED}.gif', save_all=True, append_images=imgs[1:], duration=100, loop=0)
    print("gif frames", len(frames))
