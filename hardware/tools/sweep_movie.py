# -*- coding: utf-8 -*-
u"""入れる道の動画を焼く（sweep_chk.py が書いた JSON を読む）。

  python hardware/tools/sweep_chk.py             ← 先にこちらで検査（6 本とも）
  python hardware/tools/sweep_movie.py          ← 6 本とも動画（all でも同じ）
  python hardware/tools/sweep_movie.py bat      ← 1 本だけ
  python hardware/tools/sweep_movie.py bat --peek  ← 3 枚だけ焼いて、動いているか見る（速い）
  python hardware/tools/sweep_movie.py --save      ← 焼いて docs/_img/sweep/<日付>/ に残す

なぜ動画か: 数字だけでは人が判定できない。SolidWorks の Motion Study も
「再生しながらフレームごとに干渉を探し、フレーム番号・時刻・部品・干渉量の表を出す」形をしている。
docs/COLLISION-SURVEY.md 参照。

出る物: hardware/_tmp_sweep/<key>.mp4（作業場・git に入らない。--save で節目の物を残す）
  青 = 空いている / 黄 = 触れているだけ（皮。めり込みではない）/ 赤 = めり込んでいる
  めり込んでいる間は動く物を透かし、**交わりの塊そのもの**を赤い実体で出す
  焼き込みの文字: s（道のどこか）・gap（隙間 mm）・HIT（めり込みの厚みと体積）
"""
import json, math, os, shutil, subprocess, sys, time
import numpy as np, trimesh

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_chk import TMP, ROOT, TOL, SKIN_T, motion_bound, pose_mat, pose_at   # noqa: E402

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


def nearest(lst, s, get):
    return min(lst, key=lambda x: abs(get(x) - s)) if lst else None


def build_frames(rep, mover, world):
    path, c, r = rep["path"], rep["c"], rep["r"]
    segs = [motion_bound(path[i], path[i + 1], r) for i in range(len(path) - 1)]
    total = sum(segs)
    n = max(2, int(round(total / MM_PER_FRAME)))
    frames = []
    for k in range(n + 1):
        want = total * k / n                       # 道のりで等間隔（時間が実物の動きと合う）
        acc, s = 0.0, len(path) - 1.0
        for i, L in enumerate(segs):
            if want <= acc + L or i == len(segs) - 1:
                s = i + (0.0 if L <= 0 else min(1.0, (want - acc) / L))
                break
            acc += L
        frames.append(s)
    # 道は「座った姿勢 → 外」の向きで書かれている物がある（PATH_BAT）。
    # 動画は**座る姿勢で終わる**方が読めるので、その場合はコマ順を逆にする。
    # 剛体なので「入れる」は「抜く」の逆再生で同じ（当たりの集合は向きに依らない）。
    import numpy as _np
    if _np.linalg.norm(_np.array(path[-1][:3], float)) > _np.linalg.norm(_np.array(path[0][:3], float)):
        frames.reverse()
    # コマの並び: ①入れる ②（当たりがあれば）いちばん深い所で動く物を消して交わりを見せる
    #             ③**組み上がった姿勢に戻して数秒止める**（ここで終わる）
    s_end = frames[-1]                             # 道の終わり ＝ 組み上がった姿勢（逆再生なら逆順の最後）
    seq = [(x, False) for x in frames]
    worst = rep["worst"]
    if worst and worst["thick"] >= SKIN_T:
        seq += [(worst["s"], True)] * HOLD_HIT
    seq += [(s_end, False)] * HOLD_END
    out = []
    for fi, (s, ghost) in enumerate(seq):
        R, t = pose_mat(pose_at(path, s, c), c)
        M = np.eye(4)
        M[:3, :3], M[:3, 3] = R, t
        d = nearest(rep["samples"], s, lambda x: x["s"])["d"]
        # 厳密評価は接触区間の中を粗く刻むので、そのコマが区間の中にあるなら
        # いちばん近い評価の値を使う（距離で切ると、間のコマが「接触」に化ける）
        inside = any(lo - 1e-9 <= s <= hi + 1e-9 for lo, hi in rep["intervals"])
        e = nearest([h for h in rep["exact"] if h["faces"]], s, lambda x: x["s"])
        hit = e if (inside and e and e["thick"] >= SKIN_T) else None
        note = "%s  s=%.3f  gap=%.2fmm" % (rep["key"], s, d)
        if ghost:
            note = "%s  s=%.3f   >> overlap only (part hidden)" % (rep["key"], s)
        elif fi >= len(seq) - HOLD_END:
            note = "%s  s=%.3f   >> assembled" % (rep["key"], s)
        if hit:
            note += "   HIT  t=%.3fmm  V=%.3fmm3" % (hit["thick"], hit["vol"])
        elif d <= TOL:
            note += "   touch (skin)"
        out.append({"m": [float(x) for x in M.flatten()], "d": float(d), "note": note,
                    "thick": float(hit["thick"]) if hit else 0.0, "ghost": ghost,
                    "bbox": [hit["bmin"], hit["bmax"]] if hit else None,
                    "hit": hit["off"].replace(".off", ".stl") if hit and hit.get("off") else None})
    lo = np.minimum(world.bounds[0], mover.bounds[0] + np.min([f["m"][3::4][:3] for f in out], axis=0))
    hi = np.maximum(world.bounds[1], mover.bounds[1] + np.max([f["m"][3::4][:3] for f in out], axis=0))
    # 交わりの形を STL にしておく（Blender が赤い塊として出す）
    shapes = []
    for h in rep["exact"]:
        if h.get("off"):
            g = trimesh.load(os.path.join(TMP, h["off"]))
            name = h["off"].replace(".off", ".stl")
            g.export(os.path.join(TMP, name))
            shapes.append(name)
    return {"frames": out, "bbox": [list(map(float, lo)), list(map(float, hi))],
            "shapes": shapes, "tol": TOL, "skin": SKIN_T, "margin": 4.0}


KEYS = ["hub", "rsp", "oled", "bat", "lidmain", "lidflap"]
KEEP = os.path.join(os.path.dirname(ROOT), "docs", "_img", "sweep")   # 節目の動画を残す所


def save(tag, keys):
    u"""焼いた動画を docs/_img/sweep/<tag>/ へ残す（🔒 ユーザー 2026-09-18「節目のものだけ残す」）。
    そのときの検査の結果も README に書いておく（動画だけ残っても、何を了承したかが分からないため）"""
    dst = os.path.join(KEEP, tag)
    os.makedirs(dst, exist_ok=True)
    lines = [u"# 入れる道の動画 — %s" % tag, u"",
             u"`python hardware/tools/sweep_movie.py --save=%s` が焼いた物。" % tag,
             u"読み方と回し方は [SWEEP.md](../../SWEEP.md)。", u"",
             u"| 道 | 判定 | めり込み |", u"|---|---|---|"]
    for k in keys:
        src = os.path.join(TMP, "%s.mp4" % k)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst, "%s.mp4" % k))
        f = os.path.join(TMP, "%s.json" % k)
        if not os.path.exists(f):
            continue
        r = json.load(open(f, encoding="utf-8"))
        hits = [u"厚み %.3f・%s（%s）" % (d["thick"], d["bmin"], u"済" if d.get("acc") else u"**新**")
                for d in r.get("ok", []) + r.get("new", [])]
        lines.append(u"| [%s](%s.mp4) | %s | %s |" % (k, k, r.get("verdict", "?"),
                                                      u"<br>".join(hits) or u"無し"))
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


def bake(key, peek=False):
    f = os.path.join(TMP, "%s.json" % key)
    if not os.path.exists(f):
        sys.exit("%s が無い。先に python hardware/tools/sweep_chk.py %s を回すこと" % (f, key))
    rep = json.load(open(f, encoding="utf-8"))
    mover = stl_from_off(key, "mover")
    world = stl_from_off(key, "world")
    plan = build_frames(rep, mover, world)
    if peek:                                   # 頭・いちばん深い所・終わりの 3 枚だけ（動いているかの確認用）
        n = len(plan["frames"])
        pick = sorted({0, max(0, n - HOLD_END - 1), n - 1})   # 頭・入れ終わり（か交わり）・組み上がり
        plan["frames"] = [plan["frames"][i] for i in pick]
    out = os.path.join(TMP, key + "_frames")
    if os.path.isdir(out):                     # 🔴 前回の連番を消してから焼く（少ないコマ数で焼くと古い絵が混ざる）
        for old in os.listdir(out):
            os.remove(os.path.join(out, old))
    json.dump(plan, open(os.path.join(TMP, "%s_frames.json" % key), "w", encoding="utf-8"))
    print(u"%-7s %d コマ%s" % (key, len(plan["frames"]),
                              u"（覗き見）" if peek else u"（%.1f 秒）を焼きます" % (len(plan["frames"]) / FPS)))
    blender(key)
    if peek:
        print(u"        %s\\f*.png を開いて、物が動いているか目で確かめること" % out)
        return
    mp4 = os.path.join(TMP, "%s.mp4" % key)
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
