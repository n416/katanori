# -*- coding: utf-8 -*-
"""ユーザー案（漏斗 → スリット → 櫛で押す）を「1 本ずつ装填する段」として MuJoCo で回す（2026-09-07）。
   mode=entry : 漏斗の口（幅 FUN_W × 長さ FUN_L）の下にスリット（幅 SLIT_W・棚厚 SHELF_T・床の深さ D）。山盛りを落として揺すり、
                何本が頭で吊るされて（先が下・頭が棚の上）入ったかを数える。
   mode=lay   : 吊るされたねじ 1 本を櫛で押し、出口手前の登り（床が D → 0）で寝かせる。出口の先は Zavion3D 型の溝（幅 TRACK_W・深さ TRACK_D）
                と板。押し出した後の姿勢（頭が溝の中か・軸が板の上に寝たか・向き）を出す。
   使い方: python sim_feed.py mode=entry [seed] [gif] n=20 shake=6 shake_a=10 slit=2.4
           python sim_feed.py mode=lay single=8 [gif]
"""
import sys, math, random, io
import numpy as np, mujoco

SC = 0.01
KW = dict(a.split('=') for a in sys.argv[1:] if '=' in a)
POS = [a for a in sys.argv[1:] if '=' not in a and a != 'gif']
SEED = int(POS[0]) if len(POS) > 0 else 0
GIF = 'gif' in sys.argv
MODE = KW.get("mode", "entry")
MU = float(KW.get("mu", 0.3))
HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
LENS = [4, 6, 8, 10, 12]
SLIT_W = float(KW.get("slit", 2.4)); SHELF_T = 1.5; D = 14.0
FUN_L, FUN_W = float(KW.get("fl", 15.0)), SLIT_W          # 漏斗の口（スリットと同じ幅）
RIB = 4.0
geoms = []
def box(name, cx, cy, cz, hx, hy, hz, xy=None, rgba="0.7 0.75 0.8 1"):
    ax = f' xyaxes="{" ".join(f"{v:.6f}" for v in xy)}"' if xy else ""
    geoms.append(f'<geom name="{name}" type="box" pos="{cx*SC:.5f} {cy*SC:.5f} {cz*SC:.5f}" size="{hx*SC:.5f} {hy*SC:.5f} {hz*SC:.5f}"{ax} rgba="{rgba}" friction="{MU} 0.005 0.0001"/>')
def qaxes(ex, ey, ez):
    Rm = np.array([ex, ey, ez]).T; q = np.zeros(4); mujoco.mju_mat2Quat(q, Rm.flatten()); return q
def cam(pos, target, up=(0, 0, 1)):
    p = np.array(pos); f = np.array(target) - p; f /= np.linalg.norm(f)
    x_ = np.cross(f, up); x_ /= np.linalg.norm(x_); y_ = np.cross(x_, f)
    return " ".join(f"{v:.4f}" for v in p), " ".join(f"{v:.4f}" for v in np.concatenate([x_, y_]))
bodies = []; mocap = ""
random.seed(SEED)

if MODE == "entry":
    N = int(KW.get("n", 20)); L = 40.0
    # スリット: x 0..L、y ±SLIT_W/2、床 z=-D、棚（上面 z=0、厚 SHELF_T）の両脇 RIB、壁は床まで
    for sgn in (-1, 1):
        box(f"shelf{sgn}", L / 2, sgn * (SLIT_W / 2 + RIB / 2), -D / 2, L / 2, RIB / 2, D / 2)
    box("floor", L / 2, 0, -D - 1, L / 2, SLIT_W / 2 + RIB, 1)
    box("end0", -1, 0, -D / 2, 1, SLIT_W / 2 + RIB, D / 2 + 1); box("end1", L + 1, 0, -D / 2, 1, SLIT_W / 2 + RIB, D / 2 + 1)
    # 漏斗: 口の上に四角錐台の壁 4 枚（傾き 60°）、高さ 25、口 FUN_L × FUN_W、上 40 × 30
    FH = 25.0; TOPX, TOPY = 40.0, 30.0; x0 = L / 2 - FUN_L / 2
    for sgn in (-1, 1):
        # y 側の壁: 口の縁 y=±FUN_W/2（z=0）から上の縁 y=±TOPY/2（z=FH）へ
        dy = (TOPY - FUN_W) / 2; ln = math.hypot(dy, FH); ang = math.atan2(FH, dy)     # 壁の面の角度（水平から）
        ny, nz = sgn * math.sin(ang), -math.cos(ang)                                       # 外向きの法線（外＝±y、下向き成分）
        cy = sgn * (FUN_W / 2 + dy / 2) + ny * 0.75; cz = FH / 2 + nz * 0.75
        box(f"funy{sgn}", L / 2, cy, cz, TOPX / 2 + 1, ln / 2, 0.75, xy=(1, 0, 0, 0, sgn * math.cos(ang), math.sin(ang)))
        # x 側の壁: 口の縁 x=L/2±FUN_L/2 から上の縁 x=L/2±TOPX/2 へ
        dx = (TOPX - FUN_L) / 2; ln2 = math.hypot(dx, FH); ang2 = math.atan2(FH, dx)
        nx, nz2 = sgn * math.sin(ang2), -math.cos(ang2)
        cx = L / 2 + sgn * (FUN_L / 2 + dx / 2) + nx * 0.75; cz2 = FH / 2 + nz2 * 0.75
        box(f"funx{sgn}", cx, 0, cz2, ln2 / 2, TOPY / 2 + 1, 0.75, xy=(sgn * math.cos(ang2), 0, math.sin(ang2), 0, 1, 0))
    geoms.append('<geom name="ground" type="plane" pos="0 0 -0.2" size="3 3 0.1"/>'.replace("-0.2", f"{(-D - 3) * SC:.4f}"))
    lens = [LENS[i % len(LENS)] for i in range(N)]; random.shuffle(lens)
    for i, Ln in enumerate(lens):
        x = L / 2 + random.uniform(-10, 10); y = random.uniform(-7, 7); z = FH - 6 + i * 2.5
        q = np.random.RandomState(SEED * 100 + i).normal(size=4); q /= np.linalg.norm(q)
        bodies.append(f'''<body name="s{i}" pos="{x*SC:.5f} {y*SC:.5f} {z*SC:.5f}" quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}"><freejoint/>
<geom name="s{i}_sh" type="cylinder" size="{SHANK/2*SC:.5f} {Ln/2*SC:.5f}" pos="0 0 {Ln/2*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
<geom name="s{i}_hd" type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(Ln+HEAD_H/2)*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')
    cp, cxy = cam((L / 2 * SC, -0.7, 0.5), (L / 2 * SC, 0, 0.05))
else:
    # lay: スリット x 0..LS（床 -D）、登り x LS..LS+RL で床が -D → -TRACK_D（溝の床）に上がる。出口 x=LS+RL で棚が終わり、
    # その先は Zavion 型: 溝（y 方向に TRACK_W、床 -TRACK_D）が x 方向に走る … ここでは押す向き +x = 樋の y（後ろ→手前）とし、
    # 溝を x=LS+RL..LS+RL+TRACK_W に置き、その先（+x）が板（上面 -PLATE_DROP）
    N = 1; lens = [int(KW.get("single", 8))]
    LS = 30.0; RL = float(KW.get("rl", 25)); TRACK_W, TRACK_D = float(KW.get("tw", 3.0)), float(KW.get("td", 1.3)); PLATE_DROP = float(KW.get("pd", 1.0))
    KW.setdefault("reach", str(PLATE_DROP - 0.2))
    for sgn in (-1, 1):
        box(f"shelf{sgn}", (LS + RL) / 2, sgn * (SLIT_W / 2 + RIB / 2), -D / 2, (LS + RL) / 2, RIB / 2, D / 2)
    box("floor0", LS / 2, 0, -D - 1, LS / 2, SLIT_W / 2 + RIB, 1)
    # 登り: (LS, -D) → (LS+RL, -TRACK_D)
    rise = D - PLATE_DROP; ln = math.hypot(RL, rise); ang = math.atan2(rise, RL)   # 登りの終わりは板の上面（-PD）
    cx = LS + RL / 2 + 1.0 * math.sin(ang); cz = -D + rise / 2 - 1.0 * math.cos(ang)
    box("ramp", cx, 0, cz, ln / 2, SLIT_W / 2 + RIB, 1.0, xy=(math.cos(ang), 0, math.sin(ang), 0, 1, 0))
    # 出口の先: 溝（床 -TRACK_D）と、その先の板（上面 -PLATE_DROP…板は溝の床より TRACK_D 高い）。幅は y ±20
    X1 = LS + RL
    box("track", X1 + TRACK_W / 2, 0, -PLATE_DROP - TRACK_D - 1.0, TRACK_W / 2, 20, 1.0)
    box("plate", X1 + TRACK_W + 20, 0, -PLATE_DROP - 1.4, 20, 20, 1.4)
    box("backwall", X1 - 0.01 - 5, 0, 0.0, 5, 20, 0.01, rgba="0.6 0.6 0.6 0.3")   # 棚の高さ（描画用の薄板）
    geoms.append('<geom name="ground" type="plane" pos="0 0 -0.4" size="3 3 0.1"/>')
    Ln = lens[0]
    # 吊るされたねじ: 頭の下面が棚の上（z=0）、先が -Ln
    q = qaxes((1, 0, 0), (0, 1, 0), (0, 0, 1))
    STAND = KW.get("stand") == "1"      # 立ち版: 先を床（-D）に付けて立てる（スリット 4.6 の案）
    z0 = (-D + 0.05) if STAND else (-Ln + 0.05)
    bodies.append(f'''<body name="s0" pos="{8*SC:.5f} 0 {z0*SC:.5f}"><freejoint/>
<geom name="s0_sh" type="cylinder" size="{SHANK/2*SC:.5f} {Ln/2*SC:.5f}" pos="0 0 {Ln/2*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
<geom name="s0_hd" type="cylinder" size="{HEAD_D/2*SC:.5f} {HEAD_H/2*SC:.5f}" pos="0 0 {(Ln+HEAD_H/2)*SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')
    # 櫛: 頭を押す板（棚の上、z 0..8、幅 SLIT_W+2RIB-1）
    BL_W = float(KW.get("blade", 1.8)); BL_DN = float(KW.get("reach", 1.0))   # 刃の幅（スリット 2.4 の中）と、棚の上面から下へ届く深さ
    mocap = f'''<body name="pusher" mocap="true" pos="{3*SC:.5f} 0 {((8 - BL_DN) / 2)*SC:.5f}"><geom name="tooth" type="box" size="{1.0*SC:.5f} {BL_W/2*SC:.5f} {((8 + BL_DN) / 2)*SC:.5f}" rgba="0.9 0.5 0.5 1" friction="{MU} 0.005 0.0001"/></body>'''
    cp, cxy = cam(((LS + RL) * SC, -0.6, 0.35), ((LS + RL) * SC, 0, -0.05))

xml = f'''<mujoco model="feed"><option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody><light pos="0.5 -1 2" dir="-0.3 0.5 -1"/><camera name="iso" pos="{cp}" xyaxes="{cxy}"/>
{chr(10).join(geoms)}
{mocap}
{chr(10).join(bodies)}
</worldbody></mujoco>'''
open('hardware/sim/m2_sorter/feed.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
sid = [model.body(f"s{i}").id for i in range(N)]
renderer = mujoco.Renderer(model, 720, 1280) if GIF else None
frames = []; dt = model.opt.timestep; t = 0.0
def step(n, f=None):
    global t
    for k in range(n):
        if f: f(t)
        mujoco.mj_step(model, data); t += dt
        if renderer is not None and int(round(t / dt)) % int(0.1 / dt) == 0:
            renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
out = io.StringIO()
if MODE == "entry":
    SH_T = float(KW.get("shake", 6)); SH_A = float(KW.get("shake_a", 10)); SH_F = float(KW.get("shake_f", 5))
    g0 = np.array([0, 0, -9.81])
    def shake(tt):
        if tt < SH_T:
            ph = 2 * math.pi * SH_F * tt; a = math.radians(SH_A)
            model.opt.gravity[:] = g0 + 9.81 * np.array([math.sin(a) * math.sin(ph), math.sin(a) * math.sin(ph * 1.31), 0])
        else: model.opt.gravity[:] = g0
    step(int((SH_T + 2.0) / dt), shake)
    hung = []; inside = 0; standing = []
    for i in range(N):
        p = data.xpos[sid[i]] / SC; R = data.xmat[sid[i]].reshape(3, 3); ax = R[:, 2]
        if abs(p[1]) < SLIT_W and 0 < p[0] < L and p[2] < 0:     # スリットの中
            inside += 1
            if ax[2] > 0.9 and abs(p[2] - (-lens[i])) < 1.0: hung.append(lens[i])
            elif ax[2] > 0.9 and p[2] < -D + 1.0: standing.append(lens[i])
    angs = []
    for i in range(N):
        p = data.xpos[sid[i]] / SC; R = data.xmat[sid[i]].reshape(3, 3); ax = R[:, 2]
        if abs(p[1]) < SLIT_W and 0 < p[0] < L and p[2] < 0: angs.append(round(math.degrees(math.acos(min(1, abs(ax[2]))))))
    print(f"   立って床に着いた {len(standing)} 本 {standing}   スリットの中のねじの軸の傾き(度) {sorted(angs)}", file=out)
    for i in range(N):
        p = data.xpos[sid[i]] / SC; R = data.xmat[sid[i]].reshape(3, 3); ax = R[:, 2]
        print(f"   x{lens[i]:2d}: 先 ({p[0]:6.1f},{p[1]:6.1f},{p[2]:6.1f}) 軸z {ax[2]:+.2f}", file=out)
    print(f"entry seed {SEED}: {N} 本落として揺すり {SH_T}s（振幅 {SH_A}°）→ スリットの中 {inside} 本、そのうち頭で吊るされて立った {len(hung)} 本 {hung}", file=out)
else:
    T0 = [None]
    def push(tt):
        if T0[0] is None: T0[0] = tt
        data.mocap_pos[0][0] = (3 + 12.0 * (tt - T0[0])) * SC          # 12mm/s（押し始めからの時間）
    step(int(0.5 / dt))
    trace = []
    def push2(tt):
        push(tt)
        if int(round(tt / dt)) % int(0.5 / dt) == 0:
            p = data.xpos[sid[0]] / SC; names = set()
            for c in data.contact[:data.ncon]:
                g1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom1); g2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom2)
                if 's0' in (g1 or '') or 's0' in (g2 or ''): names.add((g1 or '') + '-' + (g2 or ''))
            trace.append(f"{tt:.1f}s 櫛x={data.mocap_pos[0][0]/SC:.1f} ねじx={p[0]:.1f} z={p[2]:.1f} 接触{sorted(names)}")
    step(int(((LS + RL + 6) / 12.0) / dt), push2); step(int(1.5 / dt))
    print(chr(10).join(trace), file=out)
    p = data.xpos[sid[0]] / SC; R = data.xmat[sid[0]].reshape(3, 3); ax = R[:, 2]
    head = p + ax * (lens[0] + HEAD_H / 2)
    ang_x = math.degrees(math.acos(min(1, abs(ax[0])))); lying = abs(ax[2]) < 0.3
    X1 = LS + RL
    in_track = X1 - 0.5 < head[0] < X1 + TRACK_W + 0.5 and head[2] < -PLATE_DROP + 1.9 + 0.3
    print(f"lay x{lens[0]}: 頭 x={head[0]:.1f} z={head[2]:.1f}  先 x={p[0]:.1f} z={p[2]:.1f}  軸と押す向きの角 {ang_x:.0f}°  {'寝た' if lying else '寝ていない'}  頭は{'溝の中' if in_track else '溝の外'}", file=out)
print(out.getvalue())
if frames:
    from PIL import Image
    imgs = [Image.fromarray(f) for f in frames]
    imgs[0].save(f'hardware/sim/m2_sorter/feed_{MODE}_{SEED}.gif', save_all=True, append_images=imgs[1:], duration=100, loop=0); print("gif", len(frames))
