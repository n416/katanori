# -*- coding: utf-8 -*-
"""転がす式（Zavion3D の原理）を M2 で MuJoCo に組む（2026-09-07）。
   傾いた床の真ん中に、幅が段々広がる溝。ねじは溝をまたいで横向きに寝て転がり、全長（頭込み）より溝が広い所で落ちる。
   使い方: python sim_roll.py [傾き 15] [摩擦 0.3] [seed 0] [gif] [gaps=6.4,8.4,10.4,12.4] [seg=25] [tw=18]
"""
import sys, math, random, io
import numpy as np, mujoco

SC = 0.01
KW = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
POS = [a for a in sys.argv[1:] if '=' not in a and a != 'gif']
INCL = float(POS[0]) if len(POS) > 0 else 15.0     # 樋の傾き（進む向きに下る）
MU = float(POS[1]) if len(POS) > 1 else 0.3
SEED = int(POS[2]) if len(POS) > 2 else 0
GIF = 'gif' in sys.argv
HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
LENS = [4, 6, 8, 10, 12]
GAPS = [float(v) for v in KW.get("gaps", "6.4,8.4,10.4,12.4").split(",")]   # 溝の幅（頭込みの全長 5.4/7.4/9.4/11.4/13.4 の中間）
SEG_L = float(KW.get("seg", 25))      # 1 段の長さ（進む向き）
TW = float(KW.get("tw", 18))          # 樋の内幅（溝をまたぐ向き）。最長 13.4 より広い
LEAD = 30                             # 入口の平ら（溝なし）
RAIL_T = 3.0; WALL_H = 6.0; WALL_T = 2.0
N = int(KW.get("n", 10))

# 樋の座標系: x = 進む向き（下り）、y = 溝をまたぐ向き（樋の中心 y=0）、z = 床の法線。世界へは x 軸まわりでなく y 軸まわりに -INCL 回す
a = math.radians(INCL)
def world(x, y, z):   # 樋の座標 → 世界（樋の原点は世界原点。x が進むほど z が下がる）
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))
geoms = []
def box(name, cx, cy, cz, hx, hy, hz, rgba="0.7 0.75 0.8 1"):
    wx, wy, wz = world(cx, cy, cz)
    geoms.append(f'<geom name="{name}" type="box" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" size="{hx*SC:.5f} {hy*SC:.5f} {hz*SC:.5f}" '
                 f'xyaxes="{math.cos(a):.6f} 0 {-math.sin(a):.6f} 0 1 0" rgba="{rgba}" friction="{MU} 0.005 0.0001"/>')
L_TOTAL = LEAD + SEG_L * len(GAPS) + 10
# 入口の床（溝なし）
box("lead", LEAD / 2, 0, -RAIL_T / 2, LEAD / 2, TW / 2, RAIL_T / 2)
# 段ごとの床: 溝の両側のレール
for i, g in enumerate(GAPS):
    x0 = LEAD + i * SEG_L; xc = x0 + SEG_L / 2
    rw = (TW - g) / 2
    box(f"railL{i}", xc, -(g / 2 + rw / 2), -RAIL_T / 2, SEG_L / 2, rw / 2, RAIL_T / 2)
    box(f"railR{i}", xc, +(g / 2 + rw / 2), -RAIL_T / 2, SEG_L / 2, rw / 2, RAIL_T / 2)
# 最後の床（全部落ちなかった物の受け）
box("end", LEAD + SEG_L * len(GAPS) + 5, 0, -RAIL_T / 2, 5, TW / 2, RAIL_T / 2)
# 側壁
for sgn in (-1, 1):
    box(f"wall{sgn}", L_TOTAL / 2, sgn * (TW / 2 + WALL_T / 2), WALL_H / 2 - RAIL_T, L_TOTAL / 2, WALL_T / 2, WALL_H / 2 + RAIL_T / 2)
# 落ちた物を受ける段ごとの箱（床のずっと下）
geoms.append('<geom name="ground" type="plane" pos="0 0 -0.6" size="3 3 0.1"/>')

random.seed(SEED)
lens = [LENS[i % len(LENS)] for i in range(N)]; random.shuffle(lens)
if "single" in KW: N = 1; lens = [int(KW["single"])]
bodies = []
RAND = "random" in KW    # 山盛り: 向き（yaw）も位置も高さもばらばらに落とす
for i, Ln in enumerate(lens):
    H = Ln + HEAD_H
    if RAND:
        x = 3 + random.random() * (LEAD - 8); yaw = random.uniform(-180, 180); yc = random.uniform(-3, 3); h = 3 + i * 2.5
        head_sign = 1
    else:
        x = 4 + i * float(KW.get("pitch", 2.6)); yaw = 0.0; yc = float(KW.get("y0", 0)); h = SHANK / 2 + 0.3
    # 軸を y 向き（x 軸まわり -90°）にしてから、樋の法線まわりに yaw 回す。全長の中心を (x, yc) に
    def qmul(a_, b_):
        w1, x1, y1, z1 = a_; w2, x2, y2, z2 = b_
        return (w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2, w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2)
    q_lay = (math.cos(math.radians(-45)), math.sin(math.radians(-45)), 0, 0)          # z → y
    nz = world(0, 0, 1); cy_ = math.cos(math.radians(yaw / 2)); sy_ = math.sin(math.radians(yaw / 2))
    q_yaw = (cy_, nz[0] * sy_, nz[1] * sy_, nz[2] * sy_)                              # 樋の法線まわり
    q = qmul(q_yaw, q_lay)
    # 先の位置 = 中心から軸の向き（yaw 後）に -H/2
    ax = (-math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))                  # 樋の面内での軸の向き（yaw=0 で +y）
    wx, wy, wz = world(x - ax[0] * H / 2, yc - ax[1] * H / 2, h)
    bodies.append(f'''<body name="s{i}" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}"><freejoint/>
<geom name="s{i}_sh" type="cylinder" size="{SHANK/2*SC:.5f} {Ln/2*SC:.5f}" pos="0 0 {Ln/2*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
<geom name="s{i}_hd" type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(Ln+HEAD_H/2)*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')

def cam(pos, target, up=(0, 0, 1)):
    p = np.array(pos); f = np.array(target) - p; f /= np.linalg.norm(f)
    x = np.cross(f, up); x /= np.linalg.norm(x); y = np.cross(x, f)
    return " ".join(f"{v:.4f}" for v in p), " ".join(f"{v:.4f}" for v in np.concatenate([x, y]))
mid = world(L_TOTAL / 2, 0, 0)
cp, cxy = cam((mid[0] * SC, -1.1, 0.5), (mid[0] * SC, 0, mid[2] * SC - 0.1))
xml = f'''<mujoco model="roll"><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody><light pos="0.5 -1 2" dir="-0.3 0.5 -1"/><camera name="iso" pos="{cp}" xyaxes="{cxy}"/>
{chr(10).join(geoms)}
{chr(10).join(bodies)}
</worldbody></mujoco>'''
open('hardware/sim/m2_sorter/roll.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
sid = [model.body(f"s{i}").id for i in range(N)]
renderer = mujoco.Renderer(model, 720, 1280) if GIF else None
frames = []; dt = model.opt.timestep; t = 0.0; fell = {}
T_END = float(KW.get("T", 6.0))
for k in range(int(T_END / dt)):
    mujoco.mj_step(model, data); t += dt
    for i in range(N):
        if i not in fell:
            p = data.xpos[sid[i]] / SC
            # 樋の座標に戻して、床より 5 下なら落ちた
            xr = p[0] * math.cos(a) - p[2] * math.sin(a); zr = p[0] * math.sin(a) + p[2] * math.cos(a)
            if zr < -5: fell[i] = (xr, t)
    if renderer is not None and k % int(0.1 / dt) == 0:
        renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
out = io.StringIO()
print(f"傾き {INCL}  摩擦 {MU}  seed {SEED}  溝 {GAPS}  段 {SEG_L}  樋の幅 {TW}", file=out)
ok = 0
for i in range(N):
    Ln = lens[i]; H = Ln + HEAD_H
    expect = sum(1 for g in GAPS if g < H)          # 期待する段（全長より広い最初の溝）: 0 = 溝 6.4 で落ちる ...
    if i in fell:
        xr, tf = fell[i]; seg = int((xr - LEAD) // SEG_L) if xr >= LEAD else -1
        res = "OK" if seg == expect else "NG"; ok += (seg == expect)
        print(f"  x{Ln:2d}（全長 {H:4.1f}）: 段 {seg}（溝 {GAPS[seg] if 0 <= seg < len(GAPS) else '?'}）で落ちた x={xr:.1f} t={tf:.1f}s  期待 段 {expect}  {res}", file=out)
    else:
        p = data.xpos[sid[i]] / SC; xr = p[0] * math.cos(a) - p[2] * math.sin(a)
        res = "OK" if expect == len(GAPS) else "NG"; ok += (expect == len(GAPS))
        print(f"  x{Ln:2d}（全長 {H:4.1f}）: 落ちていない x={xr:.1f}  期待 段 {expect}  {res}", file=out)
print(f"正解 {ok}/{N}", file=out)
print(out.getvalue())
if frames:
    from PIL import Image
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(f'hardware/sim/m2_sorter/roll_{INCL:.0f}_{MU}_{SEED}.gif', save_all=True, append_images=imgs[1:], duration=100, loop=0)
    print("gif frames", len(frames))
