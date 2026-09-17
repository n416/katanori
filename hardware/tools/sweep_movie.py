# -*- coding: utf-8 -*-
u"""入れる道の動画を焼く（sweep_chk.py が書いた JSON を読む）。

  python hardware/tools/sweep_chk.py             ← 先にこちらで検査（5 本とも）
  python hardware/tools/sweep_movie.py          ← 5 場面とも動画（all でも同じ）
  python hardware/tools/sweep_movie.py bat      ← 1 場面だけ（蓋は lid）
  python hardware/tools/sweep_movie.py bat --peek  ← 3 枚だけ焼いて、動いているか見る（速い）
  python hardware/tools/sweep_movie.py --save      ← 焼いて docs/_img/sweep/<日付>/ に残す

なぜ動画か: 数字だけでは人が判定できない。SolidWorks の Motion Study も
「再生しながらフレームごとに干渉を探し、フレーム番号・時刻・部品・干渉量の表を出す」形をしている。
docs/COLLISION-SURVEY.md 参照。

出る物: hardware/_tmp_sweep/<key>.mp4（作業場・git に入らない。--save で節目の物を残す）
  色は 3 段。青 = めり込み無し（触れているのも含む）/ 橙 = 台帳にある（了承済み）/ 赤 = 新しいめり込み
  🔒 ユーザー 2026-09-18: 皮で触れているだけの所を黄色にしたら道の全域が黄色になり
  「入らない」と読めた。触れていることは文字（touch）に残す
  焼き込みの文字: s（道のどこか）・gap（隙間 mm）・HIT（めり込みの厚みと体積）
"""
import json, math, os, shutil, subprocess, sys, time
import numpy as np, trimesh

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_chk import TMP, ROOT, TOL, SKIN_T, motion_bound, pose_mat, pose_at, delta   # noqa: E402

BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
MM_PER_FRAME = 0.5    # 1 コマで物が動く距離 mm
FPS = 24
HOLD_HIT = 20         # いちばん深い所で止めるコマ数（動く物を消して交わりを見せる）
HOLD_END = 60         # 🔒 ユーザー 2026-09-18「組み立て完了の状態で数秒維持してほしい」。
                      #    最後は必ず**組み上がった姿勢**で終わり、ここで 2.5 秒止める


def stl_from_off(key, which):
    off = os.path.join(TMP, "%s_%s.off" % (key, which))
    stl = os.path.join(TMP, "%s_%s.stl" % (key, which))
    m = trimesh.load(off)
    m.export(stl)
    return m


def shapes_of(rep, key, name, j):
    u"""たわむ物は、たわみ量ごとに形が違う。全部 STL にして (d, ファイル名, メッシュ) で返す。
    たわまない物は 1 つだけ（従来どおり）"""
    out = []
    for d in (rep.get("deltas") or [0.0]) if rep.get("flex") else [None]:
        tag = "" if d is None else "_d%03d" % int(round(d * 100))
        m = trimesh.load(os.path.join(TMP, "%s_mover%s.off" % (key, tag)))
        nm = "%s_m%d%s.stl" % (name, j, tag)
        m.export(os.path.join(TMP, nm))
        out.append((0.0 if d is None else d, nm, m))
    return out


def pick(shapes, d):
    return min(shapes, key=lambda x: abs(x[0] - d))[1]


def nearest(lst, s, get):
    return min(lst, key=lambda x: abs(get(x) - s)) if lst else None


SCENES = {}   # 1 つの動画に 2 つ以上の物を出したいときだけ書く（いまは全部 1 つ）


def members(name):
    return SCENES.get(name, [name])


def pad(path, n):
    u"""通過点の数を揃える（短い道は最後の姿勢を繰り返す）。
    場面の中の物は同じ時間軸で動くので、区間の数を合わせる"""
    return list(path) + [path[-1]] * (n - len(path))


def build_frames(reps, shapes_by, world):
    u"""場面のコマを作る。reps は {名前: 検査の結果}。物が 2 つ以上なら同じ時間軸で動かす"""
    names = list(reps.keys())
    nseg = max(len(reps[k]["path"]) - 1 for k in names)
    paths = {k: pad(reps[k]["path"], nseg + 1) for k in names}
    # 区間ごとに「いちばん大きく動く物」でコマ数を決める
    grid = []
    for i in range(nseg):
        mv = max(motion_bound(paths[k][i], paths[k][i + 1], reps[k]["r"]) for k in names)
        n = max(1, int(round(mv / MM_PER_FRAME)))
        grid += [i + j / float(n) for j in range(n)]
    grid.append(float(nseg))
    # 道が「座った姿勢 → 外」で書かれている物（PATH_BAT）は逆に再生して、組み上がりで終わらせる
    k0 = names[0]
    p0 = reps[k0]["path"]
    if np.linalg.norm(np.array(p0[-1][:3], float)) > np.linalg.norm(np.array(p0[0][:3], float)):
        grid.reverse()
    s_end = grid[-1]
    # ①入れる ②（当たりがあれば）いちばん深い所で、当たっている物だけ消して交わりを見せる
    # ③組み上がった姿勢に戻して数秒止める（ここで終わる）
    worst_k, worst = None, None
    for k in names:
        w = reps[k]["worst"]
        if w and w["thick"] >= SKIN_T and (worst is None or w["thick"] > worst["thick"]):
            worst_k, worst = k, w
    seq = [(x, None) for x in grid]
    if worst:
        seq += [(worst["s"], worst_k)] * HOLD_HIT
    seq += [(s_end, None)] * HOLD_END
    out, hitshapes = [], []
    for fi, (s, ghost_k) in enumerate(seq):
        movers, notes, hit_any = [], [], None
        for k in names:
            rep = reps[k]
            # 台帳に載っている当たり（済）と、載っていない当たり（新）は色で分ける。
            # 決着済みの物で画面を赤くすると、皮を黄色にしていた頃と同じ間違いになる
            newk = set(tuple(round(x, 0) for x in d["bmin"]) for d in rep.get("new", []))
            ss = min(s, len(rep["path"]) - 1.0)          # 揃えるために伸ばした区間では最後の姿勢のまま
            R, t = pose_mat(pose_at(rep["path"], ss, rep["c"]), rep["c"])
            M = np.eye(4)
            M[:3, :3], M[:3, 3] = R, t
            d = nearest(rep["samples"], ss, lambda x: x["s"])["d"]
            inside = any(lo - 1e-9 <= ss <= hi + 1e-9 for lo, hi in rep["intervals"])
            e = nearest([h for h in rep["exact"] if h["faces"]], ss, lambda x: x["s"])
            hit = e if (inside and e and e["thick"] >= SKIN_T) else None
            is_new = bool(hit) and any(tuple(round(x, 0) for x in d["bmin"]) in newk
                                       for d in hit.get("deep", []))
            movers.append({"m": [float(x) for x in M.flatten()], "hidden": (k == ghost_k),
                           "shape": pick(shapes_by[k], delta(pose_at(rep["path"], ss, rep["c"]))),
                           "state": (2 if is_new else 1) if hit else 0})   # 0 無し / 1 済 / 2 新
            if hit:
                hit_any = hit
                notes.append("%s %s t=%.3fmm V=%.3fmm3"
                             % (k, "NEW" if is_new else "known", hit["thick"], hit["vol"]))
            elif d <= TOL:
                notes.append("%s touch" % k)
            else:
                notes.append("%s gap=%.2fmm" % (k, d))
        note = "%s  s=%.3f   %s" % ("+".join(names), s, "   ".join(notes))
        if ghost_k:
            note = "%s  s=%.3f   >> overlap  (%s ghosted)   t=%.3fmm V=%.3fmm3" % (
                "+".join(names), s, ghost_k, worst["thick"], worst["vol"])
        elif fi >= len(seq) - HOLD_END:
            note = "%s  s=%.3f   >> assembled   %s" % ("+".join(names), s, "   ".join(notes))
        out.append({"movers": movers, "note": note,
                    "hit": (hit_any["off_deep"].replace(".off", ".stl")
                            if hit_any and hit_any.get("off_deep") else None),
                    "bbox": [hit_any["bmin"], hit_any["bmax"]] if hit_any else None,
                    "show_hit": bool(ghost_k)})
    # 交わりの形を STL にしておく（Blender が赤い塊として出す）
    for k in names:
        for h in reps[k]["exact"]:
            if h.get("off_deep"):                # 皮でない塊だけ（h["off"] は皮も入っている）
                g = trimesh.load(os.path.join(TMP, h["off_deep"]))
                nm = h["off_deep"].replace(".off", ".stl")
                g.export(os.path.join(TMP, nm))
                hitshapes.append(nm)
    lo, hi = world.bounds[0].copy(), world.bounds[1].copy()
    for j, k in enumerate(names):
        tr = np.array([[f["movers"][j]["m"][3], f["movers"][j]["m"][7], f["movers"][j]["m"][11]]
                       for f in out])
        for _, _, m in shapes_by[k]:
            lo = np.minimum(lo, m.bounds[0] + tr.min(axis=0))
            hi = np.maximum(hi, m.bounds[1] + tr.max(axis=0))
    return {"frames": out, "names": names,
            "mover_shapes": [[nm for _, nm, _ in shapes_by[k]] for k in names],
            "bbox": [list(map(float, lo)), list(map(float, hi))],
            "shapes": hitshapes, "tol": TOL, "skin": SKIN_T, "margin": 4.0}


KEYS = ["hub", "rsp", "oled", "bat", "lid"]
KEEP = os.path.join(os.path.dirname(ROOT), "docs", "_img", "sweep")   # 節目の動画を残す所


def save(tag, keys):
    u"""焼いた動画を docs/_img/sweep/<tag>/ へ残す（🔒 ユーザー 2026-09-18「節目のものだけ残す」）。
    そのときの検査の結果も README に書いておく（動画だけ残っても、何を了承したかが分からないため）"""
    dst = os.path.join(KEEP, tag)
    os.makedirs(dst, exist_ok=True)
    lines = [u"# 入れる道の動画 — %s" % tag, u"",
             u"`python hardware/tools/sweep_movie.py --save=%s` が焼いた物。" % tag,
             u"読み方と回し方は [SWEEP.md](../../SWEEP.md)。", u"",
             u"| 動画 | 道 | 判定 | めり込み |", u"|---|---|---|---|"]
    for name in keys:
        src = os.path.join(TMP, "%s.mp4" % name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst, "%s.mp4" % name))
        for k in members(name):
            f = os.path.join(TMP, "%s.json" % k)
            if not os.path.exists(f):
                continue
            r = json.load(open(f, encoding="utf-8"))
            hits = [u"厚み %.3f・%s（%s）" % (d["thick"], d["bmin"], u"済" if d.get("acc") else u"**新**")
                    for d in r.get("ok", []) + r.get("new", [])]
            lines.append(u"| [%s](%s.mp4) | %s | %s | %s |"
                         % (name, name, k, r.get("verdict", "?"), u"<br>".join(hits) or u"無し"))
    lines += [u"", u"了承済みの当たりの理由は `hardware/sweep_accept.json`。"]
    with open(os.path.join(dst, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(chr(10).join(lines) + chr(10))
    print(u"残しました: %s" % dst)


def blender(key):
    r = subprocess.run([BLENDER, "--background", "--python",
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "_sweep_blender.py"),
                        "--", key, TMP], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if "SWEEP_MOVIE_OK" not in (r.stdout or ""):
        print((r.stdout or "")[-3000:])
        print((r.stderr or "")[-3000:])
        sys.exit("Blender が焼けなかった")


def cp(src, dst):
    u"""場面の名前が物の名前と同じとき（1 つだけの場面）は自分自身へのコピーになる。
    Windows はそれを WinError 32 で断る"""
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)


def bake(name, peek=False):
    ks = members(name)
    reps, meshes = {}, {}
    for k in ks:
        f = os.path.join(TMP, "%s.json" % k)
        if not os.path.exists(f):
            sys.exit("%s が無い。先に python hardware/tools/sweep_chk.py %s を回すこと" % (f, k))
        reps[k] = json.load(open(f, encoding="utf-8"))
        meshes[k] = shapes_of(reps[k], k, name, ks.index(k))
    world = stl_from_off(ks[0], "world")       # 相手はどの物から見ても同じ世界（蓋なら world_for_lid）
    cp(os.path.join(TMP, "%s_world.stl" % ks[0]), os.path.join(TMP, "%s_world.stl" % name))
    plan = build_frames(reps, meshes, world)
    if peek:                                   # 頭・入れ終わり（か交わり）・組み上がり の 3 枚だけ
        n = len(plan["frames"])
        pick = sorted({0, max(0, n - HOLD_END - 1), n - 1})
        plan["frames"] = [plan["frames"][i] for i in pick]
    out = os.path.join(TMP, name + "_frames")
    os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):                # 🔴 前回の連番を消してから焼く（古い絵が混ざる）
        os.remove(os.path.join(out, old))
    json.dump(plan, open(os.path.join(TMP, "%s_frames.json" % name), "w", encoding="utf-8"))
    print(u"%-7s %d コマ%s" % (name, len(plan["frames"]),
                              u"（覗き見）" if peek else u"（%.1f 秒）を焼きます" % (len(plan["frames"]) / FPS)))
    blender(name)
    if peek:
        print(u"        %s の f*.png を開いて、物が動いているか目で確かめること" % out)
        return
    mp4 = os.path.join(TMP, "%s.mp4" % name)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(out, "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4], check=True)
    print(u"        できました: %s" % mp4)


def main():
    peek = "--peek" in sys.argv
    tag = next((a.split("=", 1)[1] if "=" in a else time.strftime("%Y-%m-%d")
                for a in sys.argv[1:] if a.startswith("--save")), None)
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    keys = KEYS if (not args or args == ["all"]) else args
    for k in keys:
        bake(k, peek)
    if tag and not peek:
        save(tag, keys)


if __name__ == "__main__":
    main()
