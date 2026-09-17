# -*- coding: utf-8 -*-
u"""Blender の中で動く側（tools/sweep_movie.py が --background で呼ぶ）。

  blender --background --python _sweep_blender.py -- <key> <tmpdir>

<key>_frames.json（姿勢・隙間・めり込み）と <key>_mover.stl / <key>_world.stl を読み、
1 フレームずつ PNG を焼く。箱は半透明・動く物は不透明。
めり込んだ所には赤い針金の箱を置く（大きさは交わりの外接箱 + 2mm）。
"""
import bpy, json, math, mathutils, os, sys

argv = sys.argv[sys.argv.index("--") + 1:]
KEY, TMP = argv[0], argv[1]
D = json.load(open(os.path.join(TMP, KEY + "_frames.json"), encoding="utf-8"))
OUT = os.path.join(TMP, KEY + "_frames")
os.makedirs(OUT, exist_ok=True)

# 🔒 ユーザー 2026-09-18: 皮で触れているだけの所まで黄色にしていたので、
#   `lidflap` が最初から最後まで黄色になり「入らない」と読めてしまった。
#   ⇒ **2 色だけにする。青 ＝ 問題なし（触れているのも含む）／赤 ＝ めり込み。**
#   触れていることは焼き込みの文字（touch）に残す
#   さらに 2026-09-18: **台帳の状態**で分ける。決着済みの当たりで画面を赤くすると、
#   皮を黄色にしていた頃と同じ間違いになる（蓋の最後の絵が真っ赤になった）
C_STATE = [(0.16, 0.45, 0.85, 1.0),    # 0 = めり込み無し（触れているのも含む）
           (0.90, 0.60, 0.15, 1.0),    # 1 = 了承済みのめり込み（台帳にある。決着済み）
           (0.92, 0.12, 0.10, 1.0)]    # 2 = 新しいめり込み（判断が要る）


def load_stl(path, name):
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    o = bpy.context.selected_objects[0]
    o.name = name
    return o


def mat(name, rgba, alpha=1.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = 0.45
    if "Metallic" in b.inputs:
        b.inputs["Metallic"].default_value = 0.0
    if emit:
        b.inputs["Emission Color"].default_value = rgba
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"):
            # 🔴 半透明どうしは EEVEE で前後関係が壊れる（2026-09-17: 動く物が箱の裏に消えた）。
            #   箱は BLENDED、動く物は **DITHERED**（深度を書くので正しく並ぶ）。
            #   動く物は普段 alpha 1.0（＝不透明・粒も出ない）で、交わりを見せるコマだけ透かす
            m.surface_render_method = "BLENDED" if alpha < 0.9 else "DITHERED"
        else:
            m.blend_method = "BLEND" if alpha < 0.9 else "HASHED"
        m.show_transparent_back = False
    return m, b


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 相手は 2 つに分けて描く: 箱は半透明、**先に入っている物は不透明**。
    #   1 つの半透明の物にすると手前の殻より奥が描かれず、中身が消える（2026-09-18）
    wp = D.get("world_parts", {})
    mw, _ = mat("m_world", (0.80, 0.84, 0.88, 1.0), alpha=0.20)
    if wp.get("shell"):
        load_stl(os.path.join(TMP, wp["shell"]), "shell").data.materials.append(mw)
    if wp.get("units"):
        mu, _ = mat("m_units", (0.52, 0.55, 0.58, 1.0))
        load_stl(os.path.join(TMP, wp["units"]), "units").data.materials.append(mu)
    # 動く物は 1 つとは限らず、**たわむ物は形が何通りもある**（たわみ量ごとに 1 つ）。
    #   全部読み込んでおいて、コマごとに使う 1 つだけを出す
    movers, mbs = [], []
    for j, nm in enumerate(D.get("names", ["mover"])):
        m, b = mat("m_%s" % nm, C_STATE[0], emit=0.25, alpha=0.999)
        shapes = {}
        for fn in D["mover_shapes"][j]:
            o = load_stl(os.path.join(TMP, fn), "%s:%s" % (nm, fn))
            o.data.materials.append(m)
            o.hide_render = True
            shapes[fn] = o
        movers.append(shapes)
        mbs.append(b)

    # めり込んだ塊そのもの（交わりの形）。当たっているコマだけ出す
    mk, _ = mat("m_mark", (1.0, 0.06, 0.06, 1.0), emit=5.0)
    lo, hi = D["bbox"]
    diag = math.sqrt(sum((hi[i] - lo[i]) ** 2 for i in range(3)))
    # 交わりが小さいと画面で見つけられないので、場所を囲む針金の箱も出す
    bpy.ops.mesh.primitive_cube_add(size=1)
    loc = bpy.context.object
    loc.name = "locator"
    wf = loc.modifiers.new("wire", "WIREFRAME")
    wf.thickness = max(0.35, diag / 260.0)
    wf.use_relative_offset = False
    loc.data.materials.append(mk)
    loc.hide_render = True
    # ⚠ Wireframe は物を拡大する前に効くので、scale で大きくすると線まで太る。
    #   毎コマ頂点そのものを書く（scale は 1 のまま）
    loc_base = [tuple(v.co) for v in loc.data.vertices]
    loc_pad = diag / 26.0
    hitobjs = {}                                  # 交わりの塊（動く物の形の入れ物と名前を分ける）
    for name in D.get("shapes", []):
        o = load_stl(os.path.join(TMP, name), name)
        o.data.materials.append(mk)
        o.hide_render = True
        hitobjs[name] = o

    # 明かりと背景
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 200))
    bpy.context.object.data.energy = 5.0
    bpy.context.object.rotation_euler = (math.radians(40), 0, math.radians(-35))
    bw = bpy.data.worlds.new("bg")
    bw.use_nodes = True
    bw.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)
    bpy.context.scene.world = bw

    # カメラ（世界の外接箱の中心を向く平行投影）
    ctr = [(lo[i] + hi[i]) / 2 for i in range(3)]
    bpy.ops.object.empty_add(location=ctr)
    tgt = bpy.context.object
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    d = diag * 2.0
    cam.location = (ctr[0] - d * 0.55, ctr[1] - d * 0.70, ctr[2] + d * 0.45)
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt

    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 48   # DITHERED の粒を消すため
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    bpy.context.view_layer.update()                       # TRACK_TO を効かせてから測る
    inv = cam.matrix_world.inverted()
    px = py = 0.0
    for i in range(8):
        v = inv @ mathutils.Vector((lo[0] if i & 1 else hi[0], lo[1] if i & 2 else hi[1],
                                    lo[2] if i & 4 else hi[2]))
        px, py = max(px, abs(v.x)), max(py, abs(v.y))
    asp = sc.render.resolution_x / sc.render.resolution_y
    cam.data.ortho_scale = max(2 * px, 2 * py * asp) * 1.10
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    for a in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame",
              "use_stamp_scene", "use_stamp_filename", "use_stamp_camera", "use_stamp_lens",
              "use_stamp_marker", "use_stamp_sequencer_strip", "use_stamp_memory",
              "use_stamp_hostname", "use_stamp_frame_range"):
        if hasattr(sc.render, a):
            setattr(sc.render, a, False)
    sc.render.use_stamp = True
    sc.render.use_stamp_note = True
    sc.render.stamp_font_size = 30
    sc.render.stamp_background = (0, 0, 0, 0.85)
    sc.render.stamp_foreground = (1, 1, 1, 1)

    for i, f in enumerate(D["frames"]):
        for j, msh in enumerate(movers):
            mv = f["movers"][j]
            m = mv["m"]
            use = mv.get("shape") or list(msh)[0]
            for fn, o in msh.items():
                # 🔴 素の配列を matrix_world に入れると**列として**入り、平行移動が落ちる
                #   （2026-09-17 に踏んだ: 動画で物が 1mm も動かなかった）。mathutils.Matrix に包む
                o.matrix_world = mathutils.Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
                o.hide_render = (fn != use)      # そのコマのたわみ量の形だけを出す
            col = C_STATE[int(mv.get("state", 0))]
            mbs[j].inputs["Base Color"].default_value = col
            mbs[j].inputs["Emission Color"].default_value = col
            # 交わりを見せるコマは、消さずに**透かす**（消えると不具合にしか見えない）
            mbs[j].inputs["Alpha"].default_value = 0.22 if mv.get("hidden") else 0.999
        show = bool(f.get("show_hit"))
        for nm, o in hitobjs.items():
            o.hide_render = not (show and f.get("hit") == nm)
        bb = f.get("bbox")
        if show and bb:
            for vi, v in enumerate(loc.data.vertices):
                b = loc_base[vi]
                v.co = [(bb[0][k] - loc_pad) if b[k] < 0 else (bb[1][k] + loc_pad) for k in range(3)]
            loc.hide_render = False
        else:
            loc.hide_render = True
        sc.render.stamp_note_text = f["note"]
        sc.render.filepath = os.path.join(OUT, "f%05d.png" % i)
        bpy.ops.render.render(write_still=True)
    print("SWEEP_MOVIE_OK %d" % len(D["frames"]))


main()
