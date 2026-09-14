# -*- coding: utf-8 -*-
"""V 溝を長手方向に滑らせ、溝の底の穴（長さが段々長い）に落とす式を M2 で回す（2026-09-07）。
   ねじは V 溝の中で溝に沿って並ぶ（自分で向きが揃う）。落ちたねじは経路から抜けるので詰まらない。
   使い方: python sim_slide.py [傾き 25] [摩擦 0.3] [seed 0] [gif]
            single=長さ hole=穴の長さ head=1（頭が先）      … 1 本・穴 1 つで落ちるかどうか
            holes=a,b,c,d [n=10] [random=1]                 … 穴を順に並べて山盛りを流す
"""
import sys, math, random, io
import numpy as np, mujoco

SC = 0.01
KW = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
POS = [a for a in sys.argv[1:] if '=' not in a and a != 'gif']
INCL = float(POS[0]) if len(POS) > 0 else 25.0
MU = float(POS[1]) if len(POS) > 1 else 0.3
SEED = int(POS[2]) if len(POS) > 2 else 0
GIF = 'gif' in sys.argv
HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
LENS = [4, 6, 8, 10, 12]
LEAD = 40; SEG = 20; VW = 7.0; VT = 2.0     # 入口の長さ、穴と穴のあいだ、V の面の幅（斜面に沿って）、面の厚み
HOLES = [float(v) for v in KW["holes"].split(",")] if "holes" in KW else ([float(KW["hole"])] if "hole" in KW else [4, 5, 6, 7])
a = math.radians(INCL)
def world(x, y, z): return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))
geoms = []
def vface(name, x0, x1, sgn):
    """V の片面: 底の線（y=0,z=0）を通り、±45° に立つ板。中心は面の中央、法線の下へ VT/2"""
    c = math.cos(math.radians(45)); s_ = math.sin(math.radians(45))
    # 面に沿った単位ベクトル（底から外へ上がる）: (0, sgn*c, s_)。法線（溝の内側向き）: (0, -sgn*s_, c)
    uy, uz = sgn * c, s_; ny, nz = -sgn * s_, c
    cy = uy * VW / 2 - ny * VT / 2; cz = uz * VW / 2 - nz * VT / 2
    wx, wy, wz = world((x0 + x1) / 2, cy, cz)
    # 箱の x 軸 = 樋の x、y 軸 = 面に沿った向き（世界へ回す）
    ex = (math.cos(a), 0, -math.sin(a)); ey = world(0, uy, uz)   # world() は原点を通る線形写像なので向きにも使える
    geoms.append(f'<geom name="{name}" type="box" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" size="{(x1-x0)/2*SC:.5f} {VW/2*SC:.5f} {VT/2*SC:.5f}" '
                 f'xyaxes="{ex[0]:.6f} {ex[1]:.6f} {ex[2]:.6f} {ey[0]:.6f} {ey[1]:.6f} {ey[2]:.6f}" rgba="0.7 0.75 0.8 1" friction="{MU} 0.005 0.0001"/>')
# 実体の区間（穴の無い所）
solids = []; x = 0.0
solids.append((0.0, LEAD)); x = LEAD
hole_pos = []
for g in HOLES:
    hole_pos.append((x, x + g)); x += g
    solids.append((x, x + SEG)); x += SEG
L_TOTAL = x
for i, (x0, x1) in enumerate(solids):
    vface(f"vL{i}", x0, x1, -1); vface(f"vR{i}", x0, x1, +1)
CH = float(KW.get("chamfer", 0))   # 穴の向こうの縁の登り坂の長さ（x）。穴の底 −CH から縁の高さ 0 へ 45° で上がる
if CH > 0:
    for j, (h0, h1) in enumerate(hole_pos):
        # 坂の面: (h1-CH, -CH) → (h1, 0)。厚み 2 の板を 45° で置く（V 溝の幅いっぱい）
        cxr = h1 - CH / 2; czr = -CH / 2
        ex = (math.cos(a + math.radians(45)), 0, -math.sin(a + math.radians(45)))   # 樋の x を 45° 起こした向き（世界）
        wx, wy, wz = world(cxr - 0.7, 0, czr - 0.7)
        geoms.append(f'<geom name="ramp{j}" type="box" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" size="{CH/2*math.sqrt(2)*SC:.5f} {6*SC:.5f} {1.0*SC:.5f}" '
                     f'xyaxes="{ex[0]:.6f} 0 {ex[2]:.6f} 0 1 0" rgba="0.6 0.8 0.6 1" friction="{MU} 0.005 0.0001"/>')
geoms.append('<geom name="ground" type="plane" pos="0 0 -0.6" size="3 3 0.1"/>')

random.seed(SEED)
if "single" in KW:
    N = 1; lens = [float(KW["single"])]
else:
    N = int(KW.get("n", 10)); lens = [LENS[i % len(LENS)] for i in range(N)]; random.shuffle(lens)
HEADFIRST = KW.get("head", "0") == "1"
RAND = "random" in KW
bodies = []
for i, Ln in enumerate(lens):
    H = Ln + HEAD_H
    if RAND:
        xc = 4 + random.random() * (LEAD - 12); yaw = random.uniform(-180, 180); h = 4 + i * 3.0; pitch = random.uniform(-20, 20)
    else:
        xc = 6 + i * (H + 3); yaw = 180.0 if HEADFIRST else 0.0; h = 1.6; pitch = 0.0
    # 軸を樋の x 向きに: 円柱 z → x は y 軸まわり +90°。それから樋の傾き（y 軸まわり）を足す。yaw は樋の法線まわり
    def qmul(p_, q_):
        w1, x1, y1, z1 = p_; w2, x2, y2, z2 = q_
        return (w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2, w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2)
    ang = math.radians(90 + INCL + pitch)     # z → 樋の +x（下り向き）
    q_ax = (math.cos(ang / 2), 0, math.sin(ang / 2), 0)
    nz = world(0, 0, 1); cy_ = math.cos(math.radians(yaw / 2)); sy_ = math.sin(math.radians(yaw / 2))
    q_yaw = (cy_, nz[0] * sy_, nz[1] * sy_, nz[2] * sy_)
    q = qmul(q_yaw, q_ax)
    dx = math.cos(math.radians(yaw)); dy = math.sin(math.radians(yaw))     # 軸の向き（樋の面内）: 先 → 頭
    wx, wy, wz = world(xc - dx * H / 2, -dy * H / 2, h)                    # 原点 = 先
    bodies.append(f'''<body name="s{i}" pos="{wx*SC:.5f} {wy*SC:.5f} {wz*SC:.5f}" quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}"><freejoint/>
<geom name="s{i}_sh" type="cylinder" size="{SHANK/2*SC:.5f} {Ln/2*SC:.5f}" pos="0 0 {Ln/2*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
<geom name="s{i}_hd" type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(Ln+HEAD_H/2)*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')

def cam(pos, target, up=(0, 0, 1)):
    p = np.array(pos); f = np.array(target) - p; f /= np.linalg.norm(f)
    x_ = np.cross(f, up); x_ /= np.linalg.norm(x_); y_ = np.cross(x_, f)
    return " ".join(f"{v:.4f}" for v in p), " ".join(f"{v:.4f}" for v in np.concatenate([x_, y_]))
mid = world(L_TOTAL / 2, 0, 0)
cp, cxy = cam((mid[0] * SC, -0.9, mid[2] * SC + 0.45), (mid[0] * SC, 0, mid[2] * SC - 0.05))
xml = f'''<mujoco model="slide"><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody><light pos="0.5 -1 2" dir="-0.3 0.5 -1"/><camera name="iso" pos="{cp}" xyaxes="{cxy}"/>
{chr(10).join(geoms)}
{chr(10).join(bodies)}
</worldbody></mujoco>'''
open('hardware/sim/m2_sorter/slide.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
sid = [model.body(f"s{i}").id for i in range(N)]
renderer = mujoco.Renderer(model, 720, 1280) if GIF else None
frames = []; dt = model.opt.timestep; t = 0.0; fell = {}
T_END = float(KW.get("T", 6.0))
def tray(p): return (p[0] * math.cos(a) - p[2] * math.sin(a), p[0] * math.sin(a) + p[2] * math.cos(a))
for k in range(int(T_END / dt)):
    mujoco.mj_step(model, data); t += dt
    for i in range(N):
        if i not in fell:
            xr, zr = tray(data.xpos[sid[i]] / SC)
            if zr < -6: fell[i] = (xr, t)
    if renderer is not None and k % int(0.1 / dt) == 0:
        renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
def hole_of(x):
    for j, (h0, h1) in enumerate(hole_pos):
        if h0 - 8 <= x <= h1 + 8: return j
    return -1
out = io.StringIO()
if "single" in KW:
    i = 0; Ln = lens[0]; H = Ln + HEAD_H
    if 0 in fell: res = f"落ちた（x={fell[0][0]:.1f} t={fell[0][1]:.1f}s）"
    else:
        xr, zr = tray(data.xpos[sid[0]] / SC); res = f"通過（x={xr:.1f}）" if xr > hole_pos[0][1] + 2 else f"止まった（x={xr:.1f}）"
    print(f"傾き {INCL:.0f} 摩擦 {MU} {'頭先' if HEADFIRST else '先が先'} x{Ln:.0f}（全長 {H:.1f}） 穴 {HOLES[0]:.1f}: {res}", file=out)
else:
    print(f"傾き {INCL}  摩擦 {MU}  seed {SEED}  穴 {HOLES}  {'山盛り' if RAND else '整列'}", file=out)
    ok = 0
    for i in range(N):
        Ln = lens[i]; H = Ln + HEAD_H
        expect = LENS.index(Ln) if Ln in LENS else -1
        if i in fell:
            j = hole_of(fell[i][0]); r = "OK" if j == expect else "NG"; ok += (j == expect)
            print(f"  x{Ln:2d}: 穴 {j} に落ちた x={fell[i][0]:.1f} t={fell[i][1]:.1f}s  期待 {expect}  {r}", file=out)
        else:
            xr, zr = tray(data.xpos[sid[i]] / SC); r = "OK" if expect == len(HOLES) else "NG"; ok += (r == "OK")
            print(f"  x{Ln:2d}: 落ちていない x={xr:.1f}  期待 {expect}  {r}", file=out)
    print(f"正解 {ok}/{N}", file=out)
print(out.getvalue())
if frames:
    from PIL import Image
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(f'hardware/sim/m2_sorter/slide_{INCL:.0f}_{MU}_{SEED}.gif', save_all=True, append_images=imgs[1:], duration=100, loop=0)
    print("gif frames", len(frames))
