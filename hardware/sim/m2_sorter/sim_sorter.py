# -*- coding: utf-8 -*-
"""m2_slope_sorter.scad の機構を MuJoCo で回す（2026-09-07）。
   皿・くさび・櫛は SCAD と同じ数字から箱で組む（STL は凸包になるので使わない）。
   1 単位 = 1cm（mm の 10 倍。接触の許容誤差を稼ぐ。倒れる／残るは形と摩擦で決まり、大きさには依らない）。
   使い方: python hardware/sim/m2_sorter/sim_sorter.py [摩擦 0.3] [seed 0] [gif]
"""
import sys, math, random, io
import numpy as np
import mujoco

SC = 0.01           # mm → m（1mm = 1cm の世界）
MU = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 0
GIF = 'gif' in sys.argv
KW = dict(a.split('=') for a in sys.argv[3:] if '=' in a)   # tilt=12  single=床番号,長さ（1 本だけ置いて押さない）

# ---- SCAD の数字（parts/m2_slope_sorter.scad）----
HEAD_D, HEAD_H, SHANK = 3.8, 1.4, 2.0
LENS = [12, 10, 8, 6, 4]
SLIT_W, WALL, BOT_T = 4.6, 5.0, 3.0
FUN_L, FLAT_L = 15, 41
STEP_D = [7.45, 6.37, 5.26, 4.10, 1.75]
FLOOR_L, RISE_L, RISE0_L = 8, 4, 13
SLIT_TILT, TRANS_L, TRANS_N = float(KW.get("tilt", 20)), 20, 16
D_DEEP, END_L, POCKET_DZ = 14.0, 6, 1.5
CATCH_W, CATCH_ANG, DIV_T = 25, 20, 1.2
TOOTH_W, TOOTH_T, PUSH_REACH = float(KW.get("tooth", 1.2)), 2.0, 9.5

LOAD_L = FUN_L + FLAT_L
RAMP_L = RISE0_L + FLOOR_L + (len(STEP_D) - 1) * (RISE_L + FLOOR_L)
W = SLIT_W + 2 * WALL
L = 2 * WALL + LOAD_L + RAMP_L + END_L
Z_T = BOT_T + D_DEEP
X_R0 = WALL + LOAD_L
PY = WALL                       # スリットの −Y の面
LANE_Y = WALL + SLIT_W / 2
PZ = Z_T - D_DEEP - POCKET_DZ   # ポケットの底
TILT_PZ = (PZ + Z_T) / 2        # 傾ける軸の高さ
XT = X_R0 - TRANS_L             # ねじれの始まり
# +Y の壁の、各床からの高さ（傾いたスリットに沿って測る）。walls=a,b,c,d,e で与える。wall=v は single の床にだけ v
WALLS = [float(v) for v in KW["walls"].split(",")] if "walls" in KW else [3.0, 2.5, 2.0, 1.5, 1.0]
def div_x(i): return X_R0 + RISE0_L - 2 if i == 0 else X_R0 + RISE0_L + FLOOR_L + (i - 1) * (RISE_L + FLOOR_L) + RISE_L / 2

# 階段の頂点列 [x, depth]（SCAD の step_pts と同じ）
pts = [(X_R0, D_DEEP)]
for i, d in enumerate(STEP_D):
    x0 = X_R0 + (RISE0_L if i == 0 else RISE0_L + FLOOR_L + (i - 1) * (RISE_L + FLOOR_L) + RISE_L)
    x1 = X_R0 + RISE0_L + FLOOR_L + i * (RISE_L + FLOOR_L)
    pts += [(x0, d), (x1, d)]
pts.append((L - WALL, STEP_D[-1]))

geoms = []
DROP = KW.get("drop", "catch+div").split("+")   # 名前の頭がこれに当たる箱を作らない（切り分け用）
def box(name, center, half, xy=None, group=0, rgba="0.7 0.75 0.8 1"):
    if any(name.startswith(d) for d in DROP if d): return
    c = " ".join(f"{v * SC:.6f}" for v in center); h = " ".join(f"{v * SC:.6f}" for v in half)
    ax = f' xyaxes="{" ".join(f"{v:.6f}" for v in xy)}"' if xy is not None else ""
    geoms.append(f'<geom name="{name}" type="box" pos="{c}" size="{h}"{ax} rgba="{rgba}" friction="{MU} 0.005 0.0001"/>')

def rot_x(v, ang):   # X 軸まわり ang 度（SCAD の rotate([ang,0,0])）
    a = math.radians(ang); y, z = v[1], v[2]
    return (v[0], y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))

def slit_slice(name, x0, x1, ang, floor_top_rel, floor_box=True):
    """x0..x1 の区間に、軸 (PY, TILT_PZ) まわりに -ang 傾けたスリットの壁 2 枚と床（床の上面 = 軸から floor_top_rel）"""
    xc = (x0 + x1) / 2; dx = (x1 - x0) / 2
    def place(off_y, off_z, hy, hz, nm):
        oy, oz = rot_x((0, off_y, off_z), -ang)[1:]
        xy = (1, 0, 0) + rot_x((0, 1, 0), -ang)
        box(nm, (xc, PY + oy, TILT_PZ + oz), (dx, hy, hz), xy=xy)
    # 壁の上端（スリット側の角）が板の上面 Z_T に来る高さ。下は皿の底より下まで
    a = math.radians(ang)
    hz_m = (Z_T - TILT_PZ) / math.cos(a); hz_p = (Z_T - TILT_PZ + SLIT_W * math.sin(a)) / math.cos(a)
    place(-2.5, hz_m - 12, 2.5, 12, name + "_wm")         # −Y の壁（厚 5・高さ 24。上端 = Z_T）
    place(SLIT_W + 2.5, hz_p - 12, 2.5, 12, name + "_wp") # +Y の壁
    if floor_box:
        place(SLIT_W / 2, floor_top_rel - 2.5, SLIT_W / 2 + 2, 2.5, name + "_fl")

# 皿の外形（当たりに要る所だけ）: レールの床、端の壁 2 枚
box("floor_rail", ((WALL + XT) / 2, W / 2, (Z_T - D_DEEP) / 2), ((XT - WALL) / 2, W / 2, (Z_T - D_DEEP) / 2))
box("wall_rail_m", ((WALL + XT) / 2, PY / 2, Z_T / 2), ((XT - WALL) / 2, PY / 2, Z_T / 2))
box("wall_rail_p", ((WALL + XT) / 2, (PY + SLIT_W + W) / 2, Z_T / 2), ((XT - WALL) / 2, (W - PY - SLIT_W) / 2, Z_T / 2))
box("end_wall_0", (WALL / 2, W / 2, Z_T / 2), (WALL / 2, W / 2, Z_T / 2))
box("end_wall_1", (L - WALL / 2, W / 2, Z_T / 2), (WALL / 2, W / 2, Z_T / 2))
# ねじれの区間: 刻みごとに角度を変えた壁と床（床の上面は D_DEEP のまま）
for k in range(TRANS_N):
    x0 = XT + k * TRANS_L / TRANS_N; x1 = XT + (k + 1) * TRANS_L / TRANS_N
    slit_slice(f"tw{k}", x0 - 0.05, x1 + 0.05, SLIT_TILT * (k + 0.5) / TRANS_N, (Z_T - D_DEEP) - TILT_PZ)
# 傾いた区間: −Y の壁は 1 本。+Y の壁は床ごとに高さ w_i（区間 = 手前の登り + 床）。床は階段（くさび）
def seg_x0(i): return X_R0 if i == 0 else X_R0 + RISE0_L + FLOOR_L + (i - 1) * (RISE_L + FLOOR_L)
def seg_x1(i): return L - WALL if i == len(STEP_D) - 1 else X_R0 + RISE0_L + FLOOR_L + i * (RISE_L + FLOOR_L)
_a = math.radians(SLIT_TILT)
_oy, _oz = rot_x((0, -2.5, (Z_T - TILT_PZ) / math.cos(_a) - 12), -SLIT_TILT)[1:]
box("tilt_wm", ((X_R0 + L - WALL) / 2, PY + _oy, TILT_PZ + _oz), ((L - WALL - X_R0) / 2, 2.5, 12), xy=(1, 0, 0) + rot_x((0, 1, 0), -SLIT_TILT))
for i in range(len(STEP_D)):
    wi = float(KW["wall"]) if ("wall" in KW and "single" in KW and int(KW["single"].split(",")[0]) == i) else WALLS[i]
    top_rel = (Z_T - STEP_D[i]) - TILT_PZ + wi          # 壁の上端（傾いた枠の z）
    oy, oz = rot_x((0, SLIT_W + 2.5, top_rel - 12), -SLIT_TILT)[1:]
    box(f"wp{i}", ((seg_x0(i) + seg_x1(i)) / 2, PY + oy, TILT_PZ + oz), ((seg_x1(i) - seg_x0(i)) / 2, 2.5, 12), xy=(1, 0, 0) + rot_x((0, 1, 0), -SLIT_TILT))
for (xa, da), (xb, db) in zip(pts[:-1], pts[1:]):
    za, zb = (Z_T - da) - TILT_PZ, (Z_T - db) - TILT_PZ          # 軸から見た床の高さ
    seg = math.hypot(xb - xa, zb - za); alpha = math.atan2(zb - za, xb - xa)
    # 傾いていない枠での箱: 中心 = 区間の中点から法線の下へ 2.5
    nx, nz = -math.sin(alpha), math.cos(alpha)
    cx = (xa + xb) / 2 - 2.5 * nx; cz = (za + zb) / 2 - 2.5 * nz; cy = SLIT_W / 2
    ex = (math.cos(alpha), 0, math.sin(alpha))
    xy = ex + rot_x((0, 1, 0), -SLIT_TILT)
    ex_t = (ex[0], 0, ex[2])
    # 軸まわりに傾ける: 中心の y,z を回す。x 軸の向きも回す（x 成分はそのまま、z 成分が y,z に散る）
    oy, oz = rot_x((0, cy, cz), -SLIT_TILT)[1:]
    exr = rot_x(ex_t, -SLIT_TILT)
    xy = exr + rot_x((0, 1, 0), -SLIT_TILT)
    box(f"fl_{xa:.0f}", (cx, PY + oy, TILT_PZ + oz), (seg / 2 + 0.3, SLIT_W / 2 + 1.5, 2.5), xy=xy)
# 板の上面（デッキ）: スリットの口の両脇。口の +Y の縁は最大 PY + SLIT_W cos12 + 7.75 sin12 = 11.1
box("deck_m", ((XT + L - WALL) / 2, PY / 2, (Z_T + 4) / 2), ((L - WALL - XT) / 2, PY / 2, (Z_T - 4) / 2))
EDGE_P = PY + SLIT_W * math.cos(math.radians(SLIT_TILT)) + (Z_T - TILT_PZ) * math.sin(math.radians(SLIT_TILT)) + 0.2   # 口の +Y の縁
# デッキは厚くして、傾いた壁の箱の上面（外へ向かって下がる）との間に隙間（ひさし）を作らない。口の縁より外は全部の高さで塞ぐ
DECK_W_OUT = W + float(KW.get("deckw", 0))   # 切り分け用: デッキを皿の幅より外へ伸ばす
if EDGE_P < W and "nodeck" not in KW: box("deck_p", ((XT + X_R0) / 2, (EDGE_P + DECK_W_OUT) / 2, (Z_T + 4) / 2), ((X_R0 - XT) / 2, (DECK_W_OUT - EDGE_P) / 2, (Z_T - 4) / 2))
print(f"口の +Y の縁 y={EDGE_P:.1f}  皿の幅 W={W}  壁の上の平ら {W - EDGE_P:.1f}")
# 受けの斜面（縁なし）と仕切り
ca = math.radians(CATCH_ANG); drop = CATCH_W * math.tan(ca)
ny, nz = math.sin(ca), math.cos(ca)      # 斜面の法線（上向き）
cyc = W + CATCH_W / 2 - 2.5 * ny; czc = Z_T - drop / 2 - 2.5 * nz
box("catch", ((WALL + FUN_L + L) / 2, cyc, czc), ((L - WALL - FUN_L) / 2, CATCH_W / (2 * math.cos(ca)), 2.5), xy=(1, 0, 0, 0, math.cos(ca), -math.sin(ca)))
for i in range(len(STEP_D)):
    box(f"div{i}", (div_x(i), W + CATCH_W / 2, Z_T / 2), (DIV_T / 2, CATCH_W / 2, Z_T / 2))
# 落ちた物を受ける地面
box("ground", (L / 2, W / 2, -30), (200, 200, 1), rgba="0.9 0.9 0.9 1")

# ---- ねじ ----
random.seed(SEED)
N = 10
lens = [LENS[i % len(LENS)] for i in range(N)]; random.shuffle(lens)
xs = [8 + i * 4.7 for i in range(N)]
zs = [Z_T - D_DEEP + 0.05] * N
ys = [LANE_Y] * N
if "single" in KW:   # 床 fi の中央に長さ Ln を 1 本。傾いたスリットの中で、床の上・+Y の壁の際に立てる
    fi, Ln1 = KW["single"].split(","); fi = int(fi); Ln1 = float(Ln1)
    N = 1; lens = [Ln1]
    xc = X_R0 + RISE0_L + FLOOR_L / 2 + fi * (RISE_L + FLOOR_L)
    yr, zr = rot_x((0, SLIT_W / 2, (Z_T - STEP_D[fi]) - TILT_PZ + 0.1), -SLIT_TILT)[1:]
    xs = [xc]; ys = [PY + yr]; zs = [TILT_PZ + zr]
bodies = []
for i, (x, Ln) in enumerate(zip(xs, lens)):
    z0 = zs[i] * SC
    # single のときはスリットと同じ角度に傾けて置く（真っ直ぐ置くと傾いたスリットの壁に食い込む）
    qa = math.radians(-SLIT_TILT / 2) if "single" in KW else 0.0
    bodies.append(f'''<body name="s{i}" pos="{x * SC:.5f} {ys[i] * SC:.5f} {z0:.5f}" quat="{math.cos(qa):.6f} {math.sin(qa):.6f} 0 0">
  <freejoint/>
  <geom name="s{i}_sh" type="cylinder" size="{SHANK / 2 * SC:.5f} {Ln / 2 * SC:.5f}" pos="0 0 {Ln / 2 * SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
  <geom name="s{i}_hd" type="cylinder" size="{HEAD_D / 2 * SC:.5f} {HEAD_H / 2 * SC:.5f}" pos="0 0 {(Ln + HEAD_H / 2) * SC:.5f}" density="7850" rgba="0.8 0.65 0.2 1" friction="{MU} 0.005 0.0001"/>
</body>''')

# ---- 櫛（mocap で X に動かす）----
push_x0 = 4.0
pusher = f'''<body name="pusher" mocap="true" pos="{push_x0 * SC:.5f} {LANE_Y * SC:.5f} {(Z_T - PUSH_REACH / 2) * SC:.5f}">
  <geom name="tooth" type="box" size="{TOOTH_T / 2 * SC:.5f} {TOOTH_W / 2 * SC:.5f} {PUSH_REACH / 2 * SC:.5f}" rgba="0.9 0.5 0.5 1" friction="{MU} 0.005 0.0001"/>
</body>'''

def cam(pos, target, up=(0, 0, 1)):
    p = np.array(pos); f = np.array(target) - p; f /= np.linalg.norm(f)
    x = np.cross(f, up); x /= np.linalg.norm(x); y = np.cross(x, f)
    return " ".join(f"{v:.4f}" for v in p), " ".join(f"{v:.4f}" for v in np.concatenate([x, y]))
cam_pos, cam_xy = cam((0.95, 0.75, 0.55), (0.95, 0.10, 0.05))
xml = f'''<mujoco model="sorter">
<option timestep="0.0004" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic" impratio="10"><flag multiccd="enable"/></option>
<visual><global offwidth="1280" offheight="720"/></visual>
<worldbody>
<light pos="0.5 -1 2" dir="-0.3 0.5 -1"/>
<camera name="iso" pos="{cam_pos}" xyaxes="{cam_xy}"/>
{chr(10).join(geoms)}
{pusher}
{chr(10).join(bodies)}
</worldbody>
</mujoco>'''
open('hardware/sim/m2_sorter/sorter.xml', 'w', encoding='utf-8').write(xml)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)

# 落ち着かせる
for _ in range(int(0.6 / model.opt.timestep)):
    mujoco.mj_step(model, data)
sid = [model.body(f"s{i}").id for i in range(N)]
def tilt_deg(i):
    R = data.xmat[sid[i]].reshape(3, 3); return math.degrees(math.acos(max(-1, min(1, R[2, 2]))))
print("落ち着いた後の傾き(度):", [round(tilt_deg(i)) for i in range(N)], " z:", [round(data.xpos[sid[i]][2] / SC, 1) for i in range(N)])

# 押す: 5mm/s（世界では 5cm/s）で X_END まで
SPEED = 5.0 * SC; X_END = L - WALL - 3
frames = []
renderer = None
if GIF:
    try:
        renderer = mujoco.Renderer(model, 720, 1280)
    except Exception as e:
        print("renderer なし:", e); renderer = None
t = 0.0; dt = model.opt.timestep; fall_x = {}; fall_t = {}
sid = [model.body(f"s{i}").id for i in range(N)]
step = 0
if "single" in KW:
    T_SINGLE = float(KW.get("T", 3.0)); trace = []
    for k in range(int(T_SINGLE / dt)):
        mujoco.mj_step(model, data); t += dt
        if k % int(0.5 / dt) == 0: trace.append(f"{t:.1f}s:{tilt_deg(0):.0f}°/y{data.xpos[sid[0]][1] / SC:.1f}")
    if "T" in KW: print("   経過:", " ".join(trace))
    p = data.xpos[sid[0]] / SC
    fi = int(KW["single"].split(",")[0])
    if "contacts" in KW:
        for c in data.contact[:data.ncon]:
            f6 = np.zeros(6); mujoco.mj_contactForce(model, data, list(data.contact).index(c) if False else 0, f6)
            print("   接触:", mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom1), "-", mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom2), "at", np.round(c.pos / SC, 2), "normal", np.round(c.frame[:3], 2))
    wi = float(KW.get("wall", WALLS[fi]))
    print(f"tilt {SLIT_TILT:.0f}  床 {fi} 壁 {wi:.1f} x{lens[0]:.0f}: y={p[1]:.1f} z={p[2]:.1f} 傾き {tilt_deg(0):.0f}°  → " + ("落ちた" if (p[1] > W + 1 or p[2] < 0) else ("残った" if tilt_deg(0) < 45 else "中で倒れた")))
    sys.exit(0)
while data.mocap_pos[0][0] < X_END * SC:
    data.mocap_pos[0][0] = (push_x0 * SC) + SPEED * t
    mujoco.mj_step(model, data); t += dt; step += 1
    for i in range(N):
        if i not in fall_x:
            p = data.xpos[sid[i]]
            if p[1] > (W + 1.0) * SC or p[2] < 0:   # +Y の壁の外へ出た／落ちた
                fall_x[i] = p[0] / SC; fall_t[i] = t
    if renderer is not None and step % int(0.25 / dt) == 0:
        renderer.update_scene(data, camera="iso"); frames.append(renderer.render().copy())
# 最後に少し待つ
for _ in range(int(1.0 / dt)):
    mujoco.mj_step(model, data)

out = io.StringIO()
print(f"摩擦 {MU}  seed {SEED}  ねじ {N} 本  押し {t:.1f}s", file=out)
print("仕切り x:", [round(div_x(i), 1) for i in range(len(STEP_D))], " 床の担当: 12 10 8 6 4", file=out)
bins = {}
for i in range(N):
    p = data.xpos[sid[i]] / SC
    if i in fall_x:
        fx = fall_x[i]
        b = sum(1 for k in range(len(STEP_D)) if fx > div_x(k)) - 1   # 0..4 = 12,10,8,6,4 の区画、-1 = 仕切りの手前
        expect = LENS.index(lens[i])
        bins[i] = b
        ok = "OK" if b == expect else "NG"
        print(f"  x{lens[i]:2d}: 壁を越えた x = {fx:6.1f} → 区画 {b} ({LENS[b] if 0 <= b < 5 else '?'})  期待 {expect} ({lens[i]})  {ok}   今 x={p[0]:.1f} y={p[1]:.1f} z={p[2]:.1f}", file=out)
    else:
        print(f"  x{lens[i]:2d}: 落ちていない   今 x={p[0]:.1f} y={p[1]:.1f} z={p[2]:.1f}", file=out)
n_ok = sum(1 for i in bins if bins[i] == LENS.index(lens[i]))
print(f"正しい区画 {n_ok}/{N}  落ちていない {N - len(bins)}", file=out)
print(out.getvalue())
open(f'hardware/sim/m2_sorter/result_mu{MU}_s{SEED}.txt', 'w', encoding='utf-8').write(out.getvalue())
if frames:
    try:
        from PIL import Image
        imgs = [Image.fromarray(f) for f in frames]
        imgs[0].save(f'hardware/sim/m2_sorter/sim_mu{MU}_s{SEED}.gif', save_all=True, append_images=imgs[1:], duration=120, loop=0)
        print("gif:", f'hardware/sim/m2_sorter/sim_mu{MU}_s{SEED}.gif', len(frames), "frames")
    except Exception as e:
        print("gif 失敗:", e)
