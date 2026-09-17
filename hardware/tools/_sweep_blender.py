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

C_MOVE = (0.16, 0.45, 0.85, 1.0)     # 空いている
C_TOUCH = (0.95, 0.68, 0.10, 1.0)    # 触れているだけ（皮。めり込みではない）
C_HIT = (0.92, 0.12, 0.10, 1.0)      # めり込んでいる


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
            m.surface_render_method = "BLENDED"    # 半透明は箱だけ。動く物は不透明にして前後関係を壊さない
        else:
            m.blend_method = "BLEND"
        m.show_transparent_back = False
    return m, b


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    world = load_stl(os.path.join(TMP, KEY + "_world.stl"), "world")
    mover = load_stl(os.path.join(TMP, KEY + "_mover.stl"), "mover")
    mw, _ = mat("m_world", (0.80, 0.84, 0.88, 1.0), alpha=0.20)
    mm, mm_b = mat("m_mover", C_MOVE, emit=0.25)   # 当たっている間だけ透かす
    world.data.materials.append(mw)
    mover.data.materials.append(mm)

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
    shapes = {}
    for name in D.get("shapes", []):
        o = load_stl(os.path.join(TMP, name), name)
        o.data.materials.append(mk)
        o.hide_render = True
        shapes[name] = o

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
    sc.eevee.taa_render_samples = 24
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
        m = f["m"]
        # 🔴 素の配列を matrix_world に入れると**列として**入り、平行移動が落ちる
        #   （2026-09-17 に踏んだ: 動画で物が 1mm も動かなかった）。mathutils.Matrix に包む
        mover.matrix_world = mathutils.Matrix([m[0:4], m[4:8], m[8:12], m[12:16]])
        t = f.get("thick", 0.0)
        hitting = t >= D["skin"]
        col = C_HIT if hitting else (C_TOUCH if f["d"] <= D["tol"] else C_MOVE)
        mm_b.inputs["Base Color"].default_value = col
        mm_b.inputs["Emission Color"].default_value = col
        mover.hide_render = bool(f.get("ghost"))          # 停止コマは動く物を消して交わりだけ見せる
        for nm, o in shapes.items():
            o.hide_render = not (hitting and f.get("hit") == nm)
        bb = f.get("bbox")
        if hitting and bb:
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
