# -*- coding: utf-8 -*-
"""Zavion3D の樋を、実物の STL から測った数字で MuJoCo に組む（2026-09-07）。
   板の枠: x = 転がる向き（下り）、y = 後ろ→手前、z = 板の法線。板の上面 z=0。
   後ろの縁（y<0）と、頭の溝（y 0..TRACK_W、床 -TRACK_D）、溝の手前の壁（y=TRACK_W、板の上面まで）、板（y>TRACK_W）。
   穴: y = TRACK_W+0.5 から TRACK_W + ラベル + 1.0 まで、x 方向の幅 HOLE_W、桟 BAR。
   板は手前（+y）へ FRONT_TILT 下がり、転がる向き（+x）へ ROLL_TILT 下がる。
   使い方: python sim_zav2.py [ROLL_TILT 10] [FRONT_TILT 22] [摩擦 0.3] [seed 0] [gif] [m3=1] [n=10] [random=1]
"""
import sys, math, random, io
import numpy as np, mujoco

SC = 0.01
KW = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
POS = [a for a in sys.argv[1:] if '=' not in a and a != 'gif']
ROLL_TILT = float(POS[0]) if len(POS) > 0 else 10.0
FRONT_TILT = float(POS[1]) if len(POS) > 1 else 22.0
MU = float(POS[2]) if len(POS) > 2 else 0.3
SEED = int(POS[3]) if len(POS) > 3 else 0
GIF = 'gif' in sys.argv
M3 = KW.get("m3") == "1"
if M3:   # 実物: M3 キャップボルト。溝 6.9 × 1.86、穴 = ラベル + 1.0
    HEAD_D, HEAD_H, SHANK = 5.5, 3.0, 3.0
    LENS = [5, 10, 15, 20, 25, 30]
    LABELS = [5, 10, 15, 20, 25, 30]
    TRACK_W, TRACK_D = 6.9, 1.86; HOLE_W, BAR = 24.0, 3.0; LEAD = 30.0; PLATE_W = 50.0
else:    # M2 なべ: 頭 3.8 × 1.4。溝は頭の厚みに合わせて 3.0 × 1.3。穴 = 長さ + 1.0
    HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
    LENS = [4, 6, 8, 10, 12]
    LABELS = [4, 6, 8, 10, 12]
    TRACK_W, TRACK_D = float(KW.get("tw", 3.0)), float(KW.get("td", 1.3)); HOLE_W, BAR = float(KW.get("hw", 14)), 2.0; LEAD = 30.0; PLATE_W = 24.0
HOLE_EXTRA = float(KW.get("extra", 1.0))
N = int(KW.get("n", 10))
RIM_W = 3.0            # 後ろの縁の幅
PT = 2.8               # 板の厚み

a_r = math.radians(ROLL_TILT); a_f = math.radians(FRONT_TILT)
def world(x, y, z):
    x1, y1, z1 = x * math.cos(a_r) + z * math.sin(a_r), y, -x * math.sin(a_r) + z * math.cos(a_r)   # +x 下り
    return (x1, y1 * math.cos(a_f) + z1 * math.sin(a_f), -y1 * math.sin(a_f) + z1 * math.cos(a_f))   # +y 下り
def wdir(v): return world(*v)
geoms = []
def box(name, cx, cy, cz, hx, hy, hz, rgba="0.7 0.75 0.8 1"):
    wx, wy, wz = world(cx, cy, cz); ex = wdir((1, 0, 0)); ey = wdir((0, 1, 0))
    geoms.append(f'<geom name="{name}" type="box" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" size="{hx*SC:.5f} {hy*SC:.5f} {hz*SC:.5f}" '
                 f'xyaxes="{ex[0]:.6f} {ex[1]:.6f} {ex[2]:.6f} {ey[0]:.6f} {ey[1]:.6f} {ey[2]:.6f}" rgba="{rgba}" friction="{MU} 0.005 0.0001"/>')
L_TOTAL = LEAD + len(LABELS) * (HOLE_W + BAR) + 10
# 後ろの縁（板の上面と同じ高さ）、溝の床、溝の手前の壁（= 板の縁）
box("rim", L_TOTAL / 2, -RIM_W / 2, -PT / 2, L_TOTAL / 2, RIM_W / 2, PT / 2)
box("track", L_TOTAL / 2, TRACK_W / 2, -TRACK_D - (PT - TRACK_D) / 2, L_TOTAL / 2, TRACK_W / 2, (PT - TRACK_D) / 2)
box("endwall0", -1, PLATE_W / 2 - RIM_W, 1, 1, PLATE_W / 2 + RIM_W, 3)
# 板: 入口、穴の区間（穴の手前側だけ）、桟
x = 0.0; hole_x = []
box("lead", LEAD / 2, TRACK_W + PLATE_W / 2, -PT / 2, LEAD / 2, PLATE_W / 2, PT / 2); x = LEAD
for i, lab in enumerate(LABELS):
    depth = lab + HOLE_EXTRA                      # 溝の手前の壁からの穴の奥行き
    hole_x.append((x, x + HOLE_W))
    box(f"lip{i}", x + HOLE_W / 2, TRACK_W + 0.25, -PT / 2, HOLE_W / 2, 0.25, PT / 2)          # 溝の壁の厚み 0.5（実物 13.2→13.7）
    box(f"front{i}", x + HOLE_W / 2, TRACK_W + (depth + PLATE_W) / 2, -PT / 2, HOLE_W / 2, (PLATE_W - depth) / 2, PT / 2)
    x += HOLE_W
    box(f"bar{i}", x + BAR / 2, TRACK_W + PLATE_W / 2, -PT / 2, BAR / 2, PLATE_W / 2, PT / 2); x += BAR
box("end", x + 5, TRACK_W + PLATE_W / 2, -PT / 2, 5, PLATE_W / 2, PT / 2)
box("endwall1", L_TOTAL + 1, PLATE_W / 2, 1, 1, PLATE_W / 2 + RIM_W, 3)
geoms.append('<geom name="ground" type="plane" pos="0 0 -0.8" size="4 4 0.1"/>')

random.seed(SEED)
if "single" in KW: N = 1; lens = [int(KW["single"])]
else: lens = [LENS[i % len(LENS)] for i in range(N)]; random.shuffle(lens)
RAND = "random" in KW
bodies = []
def quat_from_axes(ex, ey, ez):
    Rm = np.array([ex, ey, ez]).T; q = np.zeros(4); mujoco.mju_mat2Quat(q, Rm.flatten()); return q
for i, Ln in enumerate(lens):
    H = Ln + HEAD_H
    if RAND:
        xc = 3 + random.random() * (LEAD - 8); yaw = random.uniform(-30, 30); yh = TRACK_W / 2 + random.uniform(-1, 1); h = HEAD_D / 2 + 1 + i * 2.0
    else:
        xc = 4 + i * (HEAD_D + 1.0); yaw = 0.0; yh = TRACK_W / 2; h = HEAD_D / 2 - TRACK_D + 0.3
    # 軸: 頭が後ろ（溝の中）、先が手前（+y）。円柱の +z（原点＝先から頭へ）を板の -y 向きに
    az = (-math.sin(math.radians(yaw)), -math.cos(math.radians(yaw)), 0.0)
    ax = (math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)), 0.0); ayv = (0.0, 0.0, 1.0)
    q = quat_from_axes(wdir(ax), wdir(ayv), wdir(az))
    tip_y = yh + HEAD_H / 2 + Ln
    wx, wy, wz = world(xc, tip_y, h)
    bodies.append(f'''<body name="s{i}" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}"><freejoint/>
<geom name="s{i}_sh" type="cylinder" size="{SHANK/2*SC:.5f} {Ln/2*SC:.5f}" pos="0 0 {Ln/2*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
<geom name="s{i}_hd" type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(Ln+HEAD_H/2)*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')

def cam(pos, target, up=(0, 0, 1)):
    p = np.array(pos); f = np.array(target) - p; f /= np.linalg.norm(f)
    x_ = np.cross(f, up); x_ /= np.linalg.norm(x_); y_ = np.cross(x_, f)
    return " ".join(f"{v:.4f}" for v in p), " ".join(f"{v:.4f}" for v in np.concatenate([x_, y_]))
mid = world(L_TOTAL / 2, PLATE_W / 2, 0)
cp, cxy = cam((mid[0] * SC, mid[1] * SC + 0.8, mid[2] * SC + 0.7), (mid[0] * SC, mid[1] * SC, mid[2] * SC - 0.05))
xml = f'''<mujoco model="zav2"><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody><light pos="0.5 -1 2" dir="-0.3 0.5 -1"/><camera name="iso" pos="{cp}" xyaxes="{cxy}"/>
{chr(10).join(geoms)}
{chr(10).join(bodies)}
</worldbody></mujoco>'''
open('hardware/sim/m2_sorter/zav2.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
sid = [model.body(f"s{i}").id for i in range(N)]
renderer = mujoco.Renderer(model, 720, 1280) if GIF else None
frames = []; dt = model.opt.timestep; t = 0.0; fell = {}
T_END = float(KW.get("T", 8.0))
Wm = np.array([wdir((1, 0, 0)), wdir((0, 1, 0)), wdir((0, 0, 1))])
def plate(p): return Wm @ np.array(p)
SHAKE_T = float(KW.get("shake", 0))      # 最初の何秒か、板を揺する（重力の向きを x と y に振る。振幅 SHAKE_A 度、周波数 SHAKE_F Hz）
SHAKE_A = float(KW.get("shake_a", 8)); SHAKE_F = float(KW.get("shake_f", 6))
g0 = np.array([0, 0, -9.81])
for k in range(int(T_END / dt)):
    if t < SHAKE_T:
        ph = 2 * math.pi * SHAKE_F * t; ang = math.radians(SHAKE_A)
        # 板の x と y の向きへ交互に振る（世界の向きに変換）
        ex = np.array(wdir((1, 0, 0))); ey = np.array(wdir((0, 1, 0)))
        g = g0 + 9.81 * (ex * math.sin(ang) * math.sin(ph) + ey * math.sin(ang) * math.sin(ph * 1.37)) 
        model.opt.gravity[:] = g
    elif t < SHAKE_T + 0.01: model.opt.gravity[:] = g0
    mujoco.mj_step(model, data); t += dt
    for i in range(N):
        if i not in fell:
            xr, yr, zr = plate(data.xpos[sid[i]] / SC)
            if zr < -8: fell[i] = (xr, t)
    if renderer is not None and k % int(0.1 / dt) == 0:
        renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
def hole_of(x):
    for j, (h0, h1) in enumerate(hole_x):
        if h0 - 2 <= x <= h1 + 2: return j
    return -1
out = io.StringIO()
print(f"転がり {ROLL_TILT} / 前下がり {FRONT_TILT}  摩擦 {MU}  seed {SEED}  {'M3' if M3 else 'M2'}  穴 {[l + HOLE_EXTRA for l in LABELS]}  {'山盛り' if RAND else '整列'}  {N} 本", file=out)
ok = 0
for i in range(N):
    Ln = lens[i]; expect = LABELS.index(Ln)
    if i in fell:
        j = hole_of(fell[i][0]); r = "OK" if j == expect else "NG"; ok += (j == expect)
        print(f"  x{Ln:2d}: 穴 {j}（{LABELS[j] if 0 <= j < len(LABELS) else '?'}）に落ちた x={fell[i][0]:.1f} t={fell[i][1]:.1f}s  期待 {expect}  {r}", file=out)
    else:
        xr, yr, zr = plate(data.xpos[sid[i]] / SC)
        print(f"  x{Ln:2d}: 落ちていない x={xr:.1f} y={yr:.1f}  期待 {expect}  NG", file=out)
print(f"正解 {ok}/{N}", file=out)
print(out.getvalue())
if frames:
    from PIL import Image
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(f'hardware/sim/m2_sorter/zav2_{"m3" if M3 else "m2"}_{ROLL_TILT:.0f}_{FRONT_TILT:.0f}_{SEED}.gif', save_all=True, append_images=imgs[1:], duration=100, loop=0)
    print("gif frames", len(frames))
