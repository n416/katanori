# -*- coding: utf-8 -*-
"""段差リフター（EmGi の LifterBig/Small の原理）を M2 で MuJoCo に組む（2026-09-07）。
   ホッパー: 床がリフター側（-y）へ下がる箱。リフター: 厚 LT の板が壁に沿って STROKE 上がる。
   上端に沿って寝たねじだけが持ち上がるはず。1 ストロークで何本拾えるか・向きが揃っているかを数える。
   使い方: python sim_lifter.py [seed 0] [gif] n=30 lt=2.0 stroke=15 floor_tilt=20 strokes=4
"""
import sys, math, random, io
import numpy as np, mujoco

SC = 0.01
KW = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
POS = [a for a in sys.argv[1:] if '=' not in a and a != 'gif']
SEED = int(POS[0]) if len(POS) > 0 else 0
GIF = 'gif' in sys.argv
MU = float(KW.get("mu", 0.3))
HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
LENS = [4, 6, 8, 10, 12]
N = int(KW.get("n", 30))
LT = float(KW.get("lt", 2.0))          # リフターの厚み
LL = float(KW.get("ll", 40.0))         # リフターの長さ（x）
STROKE = float(KW.get("stroke", 15.0))
FLOOR_TILT = float(KW.get("floor_tilt", 20.0))   # 床がリフター側へ下がる角度
HX, HY = 60.0, 35.0                    # ホッパーの内のり（x, y）。リフターは y=0 の壁に沿う
STROKES = int(KW.get("strokes", 4)); T_UP = 1.0; T_HOLD = 0.6; T_DOWN = 0.8; T_SETTLE = 1.5

geoms = []
def box(name, cx, cy, cz, hx, hy, hz, xy=None, rgba="0.7 0.75 0.8 1"):
    ax = f' xyaxes="{" ".join(f"{v:.6f}" for v in xy)}"' if xy else ""
    geoms.append(f'<geom name="{name}" type="box" pos="{cx*SC:.5f} {cy*SC:.5f} {cz*SC:.5f}" size="{hx*SC:.5f} {hy*SC:.5f} {hz*SC:.5f}"{ax} rgba="{rgba}" friction="{MU} 0.005 0.0001"/>')
# 床: y=LT（リフターの手前）で z=0、+y へ上がる。傾いた箱
a = math.radians(FLOOR_TILT)
fy = LT + HY / 2; fz = (HY / 2) * math.tan(a) - 2.0 / math.cos(a)
box("floor", HX / 2, fy, fz, HX / 2 + 2, (HY / 2) / math.cos(a) + 1, 2.0, xy=(1, 0, 0, 0, math.cos(a), math.sin(a)))
# 壁: リフターの背面の壁（y<0）、両側、手前
box("wall_back", HX / 2, -2.0, 25, HX / 2 + 6, 2.0, 40)
box("wall_front", HX / 2, LT + HY + 2, 25, HX / 2 + 6, 2.0, 40)
box("wall_l", -2, LT + HY / 2, 25, 2.0, HY / 2 + 6, 40)
box("wall_r", HX + 2, LT + HY / 2, 25, 2.0, HY / 2 + 6, 40)
geoms.append('<geom name="ground" type="plane" pos="0 0 -1" size="3 3 0.1"/>')
# リフター: mocap。上端 z=0 から始まる（床と面一）。板の x 範囲は 10..10+LL
lifter = f'''<body name="lifter" mocap="true" pos="{(10 + LL / 2)*SC:.5f} {LT / 2*SC:.5f} {-20*SC:.5f}">
  <geom name="lifter_g" type="box" size="{LL/2*SC:.5f} {LT/2*SC:.5f} {20*SC:.5f}" rgba="0.9 0.5 0.5 1" friction="{MU} 0.005 0.0001"/>
</body>'''
random.seed(SEED)
lens = [LENS[i % len(LENS)] for i in range(N)]; random.shuffle(lens)
bodies = []
for i, Ln in enumerate(lens):
    x = 8 + random.random() * (HX - 16); y = LT + 4 + random.random() * (HY - 8); z = 12 + i * 2.5
    q = np.random.RandomState(SEED * 100 + i).normal(size=4); q /= np.linalg.norm(q)
    bodies.append(f'''<body name="s{i}" pos="{x*SC:.5f} {y*SC:.5f} {z*SC:.5f}" quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}"><freejoint/>
<geom name="s{i}_sh" type="cylinder" size="{SHANK/2*SC:.5f} {Ln/2*SC:.5f}" pos="0 0 {Ln/2*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
<geom name="s{i}_hd" type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(Ln+HEAD_H/2)*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')
def cam(pos, target, up=(0, 0, 1)):
    p = np.array(pos); f = np.array(target) - p; f /= np.linalg.norm(f)
    x_ = np.cross(f, up); x_ /= np.linalg.norm(x_); y_ = np.cross(x_, f)
    return " ".join(f"{v:.4f}" for v in p), " ".join(f"{v:.4f}" for v in np.concatenate([x_, y_]))
cp, cxy = cam((HX / 2 * SC, 0.9, 0.55), (HX / 2 * SC, 0.15, 0.05))
xml = f'''<mujoco model="lifter"><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody><light pos="0.5 -1 2" dir="-0.3 0.5 -1"/><camera name="iso" pos="{cp}" xyaxes="{cxy}"/>
{chr(10).join(geoms)}
{lifter}
{chr(10).join(bodies)}
</worldbody></mujoco>'''
open('hardware/sim/m2_sorter/lifter.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
sid = [model.body(f"s{i}").id for i in range(N)]
renderer = mujoco.Renderer(model, 720, 1280) if GIF else None
frames = []; dt = model.opt.timestep; t = 0.0
def step(n):
    global t
    for k in range(n):
        mujoco.mj_step(model, data); t += dt
        if renderer is not None and int(t / dt) % int(0.1 / dt) == 0:
            renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
step(int(T_SETTLE / dt))
out = io.StringIO()
print(f"seed {SEED} ねじ {N} 本  リフター 厚 {LT} 長さ {LL} ストローク {STROKE}  床の傾き {FLOOR_TILT}", file=out)
total = 0
for s in range(STROKES):
    for k in range(int(T_UP / dt)):
        data.mocap_pos[0][2] = (-20 + STROKE * (k / (T_UP / dt))) * SC; step(1)
    step(int(T_HOLD / dt))
    # 上で載っている物: 重心が板の上端より上、y が板の幅の中（±LT/2+1.2）、x が板の範囲
    top_z = STROKE
    picked = []
    for i in range(N):
        p = data.xpos[sid[i]] / SC; R = data.xmat[sid[i]].reshape(3, 3); ax = R[:, 2]
        if p[2] > top_z - 0.5 and abs(p[1] - LT / 2) < LT / 2 + 1.5 and 10 - 2 < p[0] < 10 + LL + 2:
            ang = math.degrees(math.acos(min(1, abs(ax[0]))))     # 板の縁（x）との角度
            picked.append((lens[i], round(ang), "頭+" if ax[0] > 0 else "頭-"))
    total += len(picked)
    print(f"  ストローク {s + 1}: 上端に {len(picked)} 本 {picked}", file=out)
    for k in range(int(T_DOWN / dt)):
        data.mocap_pos[0][2] = (-20 + STROKE * (1 - k / (T_DOWN / dt))) * SC; step(1)
    step(int(0.8 / dt))
print(f"合計 {total} 本 / {STROKES} ストローク", file=out)
print(out.getvalue())
if frames:
    from PIL import Image
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(f'hardware/sim/m2_sorter/lifter_{SEED}.gif', save_all=True, append_images=imgs[1:], duration=100, loop=0); print("gif", len(frames))
