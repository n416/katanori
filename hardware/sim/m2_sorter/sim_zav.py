# -*- coding: utf-8 -*-
"""Zavion3D の樋（写真・GIF から読んだ形）を M2 で MuJoCo に組む（2026-09-07）。
   板の後ろの縁に壁（帯）。ねじは横向きに寝て、頭を壁に当てて壁に沿って転がる。板には壁から手前へ伸びる長方形の穴が並び、
   穴の長さ = ねじの全長の中間。先が穴の向こうに届かないねじは落ちる。
   使い方: python sim_zav.py [転がる向きの傾き 12] [頭を壁へ寄せる傾き 4] [摩擦 0.3] [seed 0] [gif]
            n=10 random=1 holes=6.4,8.4,10.4,12.4 seg=14 single=長さ
"""
import sys, math, random, io
import numpy as np, mujoco

SC = 0.01
KW = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
POS = [a for a in sys.argv[1:] if '=' not in a and a != 'gif']
INCL_X = float(POS[0]) if len(POS) > 0 else 12.0     # 転がる向き（+x が下り）
INCL_Y = float(POS[1]) if len(POS) > 1 else 4.0      # 壁の側（-y）が下がる傾き
MU = float(POS[2]) if len(POS) > 2 else 0.3
SEED = int(POS[3]) if len(POS) > 3 else 0
GIF = 'gif' in sys.argv
if KW.get("m3") == "1":   # 検算用: M3 キャップボルト（頭 φ5.5 × 3.0・軸 3.0）。Zavion3D の実物と同じ対象
    HEAD_D, HEAD_H, SHANK = 5.5, 3.0, 3.0
    LENS = [10, 15, 20, 25, 30]
    HOLES = [float(v) for v in KW.get("holes", "12,17,22,27").split(",")]     # 作者「穴は表記より約 2 広い」
else:
    HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
    LENS = [4, 6, 8, 10, 12]
    HOLES = [float(v) for v in KW.get("holes", "6.4,8.4,10.4,12.4").split(",")]   # 壁から手前への穴の長さ（全長 5.4/7.4/9.4/11.4/13.4 の中間）
LEDGE = KW.get("ledge") == "1"    # 壁ぎわに一段高い帯（幅 4・高さ = 頭の半径 − 軸の半径）。頭だけがこの上に乗る
SEG = float(KW.get("seg", 14 if KW.get("m3") != "1" else 22))     # 穴の幅（転がる向き）
GAP = float(KW.get("gap", 6))      # 穴と穴のあいだ
LEAD = float(KW.get("lead", 40 if KW.get("m3") != "1" else 70))   # 入口（穴なし）
PW = 24.0 if KW.get("m3") != "1" else 40.0   # 板の奥行き（壁から手前）
WALL_H = 4.0                       # 壁の高さ
N = int(KW.get("n", 10))

# 板の座標: x = 転がる向き（下り）、y = 壁から手前（+y）、z = 板の法線。壁は y=0 に立つ
ax_ = math.radians(INCL_X); ay_ = math.radians(INCL_Y)
def world(x, y, z):
    # 先に y 軸まわり（x 下り）、次に x 軸まわり（-y 側が下がる = +y 側が上がる）
    x1, y1, z1 = x * math.cos(ax_) + z * math.sin(ax_), y, -x * math.sin(ax_) + z * math.cos(ax_)
    return (x1, y1 * math.cos(ay_) - z1 * math.sin(ay_), y1 * math.sin(ay_) + z1 * math.cos(ay_))
def wdir(v): return world(*v)   # 原点を通る線形写像なので向きにも使える
geoms = []
def box(name, cx, cy, cz, hx, hy, hz, rgba="0.7 0.75 0.8 1"):
    wx, wy, wz = world(cx, cy, cz); ex = wdir((1, 0, 0)); ey = wdir((0, 1, 0))
    geoms.append(f'<geom name="{name}" type="box" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" size="{hx*SC:.5f} {hy*SC:.5f} {hz*SC:.5f}" '
                 f'xyaxes="{ex[0]:.6f} {ex[1]:.6f} {ex[2]:.6f} {ey[0]:.6f} {ey[1]:.6f} {ey[2]:.6f}" rgba="{rgba}" friction="{MU} 0.005 0.0001"/>')
# 板: 入口、穴の区間（穴の手前側だけ板が残る）、穴のあいだ
x = 0.0; hole_x = []
box("lead", LEAD / 2, PW / 2, -1.0, LEAD / 2, PW / 2, 1.0); x = LEAD
for i, g in enumerate(HOLES):
    hole_x.append((x, x + SEG))
    box(f"front{i}", x + SEG / 2, (g + PW) / 2, -1.0, SEG / 2, (PW - g) / 2, 1.0)   # 穴の向こう（手前側）の板
    x += SEG
    box(f"gap{i}", x + GAP / 2, PW / 2, -1.0, GAP / 2, PW / 2, 1.0); x += GAP
L_TOTAL = x + 10
box("end", x + 5, PW / 2, -1.0, 5, PW / 2, 1.0)
box("wall", L_TOTAL / 2, -1.0, WALL_H / 2 - 2, L_TOTAL / 2, 1.0, WALL_H / 2 + 1)      # 後ろの壁（板より 2 下から WALL_H 上まで）
LH = (HEAD_D - SHANK) / 2
if LEDGE: box("ledge", L_TOTAL / 2, 2.0, LH / 2, L_TOTAL / 2, 2.0, LH / 2, rgba="0.6 0.7 0.6 1")
box("endwall", L_TOTAL + 1, PW / 2, 1, 1, PW / 2, 3)
box("frontlip", L_TOTAL / 2, PW + 1, 0.5, L_TOTAL / 2, 1, 1.5)                       # 手前の縁（落下防止）
geoms.append('<geom name="ground" type="plane" pos="0 0 -0.6" size="3 3 0.1"/>')

random.seed(SEED)
if "single" in KW: N = 1; lens = [int(KW["single"])]
else: lens = [LENS[i % len(LENS)] for i in range(N)]; random.shuffle(lens)
RAND = "random" in KW
bodies = []
def qmul(p_, q_):
    w1, x1, y1, z1 = p_; w2, x2, y2, z2 = q_
    return (w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2, w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2)
def quat_from_axes(ex, ey, ez):   # 列ベクトルで回転行列 → quat
    R = np.array([ex, ey, ez]).T; q = np.zeros(4); mujoco.mju_mat2Quat(q, R.flatten()); return q
for i, Ln in enumerate(lens):
    H = Ln + HEAD_H
    if RAND:
        xc = 4 + random.random() * (LEAD - 10); yaw = random.uniform(-25, 25); yh = 2.5 + random.uniform(0, 3); h = 2 + i * 2.2
    else:
        xc = 5 + i * (HEAD_D + 0.7); yaw = 0.0; yh = HEAD_D / 2 + 0.2; h = HEAD_D / 2 + 0.05 + (LH if LEDGE else 0)
    # ねじの軸 = 板の -y 向き（頭が壁側 y=yh、先が手前）。円柱の z 軸を板の (-sin yaw, -cos yaw, 0) に
    az = (-math.sin(math.radians(yaw)), -math.cos(math.radians(yaw)), 0.0)
    ax = (math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)), 0.0); ayv = (0.0, 0.0, 1.0)
    q = quat_from_axes(wdir(ax), wdir(ayv), wdir(az))
    # 原点 = 先: 頭の中心 (xc, yh) から先は +y へ Ln
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
mid = world(L_TOTAL / 2, PW / 2, 0)
cp, cxy = cam((mid[0] * SC, mid[1] * SC + 0.7, mid[2] * SC + 0.6), (mid[0] * SC, mid[1] * SC, mid[2] * SC - 0.05))
xml = f'''<mujoco model="zav"><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody><light pos="0.5 -1 2" dir="-0.3 0.5 -1"/><camera name="iso" pos="{cp}" xyaxes="{cxy}"/>
{chr(10).join(geoms)}
{chr(10).join(bodies)}
</worldbody></mujoco>'''
open('hardware/sim/m2_sorter/zav.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
sid = [model.body(f"s{i}").id for i in range(N)]
renderer = mujoco.Renderer(model, 720, 1280) if GIF else None
frames = []; dt = model.opt.timestep; t = 0.0; fell = {}
T_END = float(KW.get("T", 8.0))
Wm = np.array([wdir((1, 0, 0)), wdir((0, 1, 0)), wdir((0, 0, 1))])   # 行 = 板の軸（世界）
def plate(p): return Wm @ np.array(p)
for k in range(int(T_END / dt)):
    mujoco.mj_step(model, data); t += dt
    for i in range(N):
        if i not in fell:
            xr, yr, zr = plate(data.xpos[sid[i]] / SC)
            if zr < -6: fell[i] = (xr, t)
    if renderer is not None and k % int(0.1 / dt) == 0:
        renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
def hole_of(x):
    for j, (h0, h1) in enumerate(hole_x):
        if h0 - 3 <= x <= h1 + 3: return j
    return -1
out = io.StringIO()
print(f"傾き 転がり {INCL_X} / 壁へ {INCL_Y}  摩擦 {MU}  seed {SEED}  穴 {HOLES}  幅 {SEG}  {'山盛り' if RAND else '整列'}  {N} 本", file=out)
ok = 0
for i in range(N):
    Ln = lens[i]; H = Ln + HEAD_H
    expect = sum(1 for g in HOLES if g < H)     # 全長より短い穴は通過。最初に H < g となる穴が期待
    if i in fell:
        j = hole_of(fell[i][0]); r = "OK" if j == expect else "NG"; ok += (j == expect)
        print(f"  x{Ln:2d}（全長 {H:4.1f}）: 穴 {j}（{HOLES[j] if 0 <= j < len(HOLES) else '?'}）に落ちた x={fell[i][0]:.1f} t={fell[i][1]:.1f}s  期待 {expect}  {r}", file=out)
    else:
        xr, yr, zr = plate(data.xpos[sid[i]] / SC); r = "OK" if expect == len(HOLES) else "NG"; ok += (r == "OK")
        print(f"  x{Ln:2d}（全長 {H:4.1f}）: 落ちていない x={xr:.1f} y={yr:.1f}  期待 {expect}  {r}", file=out)
print(f"正解 {ok}/{N}", file=out)
print(out.getvalue())
if frames:
    from PIL import Image
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(f'hardware/sim/m2_sorter/zav_{INCL_X:.0f}_{INCL_Y:.0f}_{SEED}.gif', save_all=True, append_images=imgs[1:], duration=100, loop=0)
    print("gif frames", len(frames))
