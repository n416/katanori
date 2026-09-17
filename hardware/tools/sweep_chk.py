# -*- coding: utf-8 -*-
u"""入れる道の当たり検査（ブーリアンを取らずに距離で走る）。

  python hardware/tools/sweep_chk.py hub rsp oled bat

やること
  1. OpenSCAD から「動かす物」と「相手」を OFF で 1 回だけ出す
  2. FCL の距離クエリで道を走る。刻みは固定せず、空いている距離から出す（Conservative Advancement）
     ── 空いていれば飛ばし、狭い所だけ細かくなる。すり抜けが起きない
  3. 隙間が TOL 以下になった区間の中だけ、OpenSCAD で 1 姿勢ずつ厳密な交わりを取る
     ── 厚みが 0 なら同一平面の皮（＝誤報）、厚みがあれば本物のめり込み
  4. 動画（tools/sweep_movie.py）が読む JSON を書く

なぜこの形か: 姿勢を n 個 union して交わりの体積を作る旧 sweep_pose() は、
姿勢の数だけ面数が増える。0.25 刻みで 400 姿勢 × 28782 面 ＝ 1150 万面で PC が固まった（2026-09-17）。
距離クエリは形を作らないので、同じ道が 188 姿勢・1 秒で終わる。docs/COLLISION-SURVEY.md 参照。
"""
import json, math, os, re, subprocess, sys, time
import numpy as np, trimesh, fcl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows の cp932 で日本語が化けないように

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # hardware/
SCAD = os.path.join(ROOT, "tools", "_sweep_v61.scad")
TMP = os.path.join(ROOT, "_tmp_sweep")
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe")

TOL = 0.05          # これ以下の隙間は「接触」として扱う（clash tolerance。意図した面接触を落とす）
MIN_MOVE = 0.02     # 接触区間で 1 歩に進む距離 mm（道具が止まらないための下限）
EXACT_MOVE = 0.30   # 接触区間の中で厳密な交わりを取る間隔 mm
EXACT_MAX = 12      # 1 区間あたりの厳密評価の上限（重くしないため）
SKIN_T = 0.01       # 交わりの厚みがこれ未満なら同一平面の皮 ＝ めり込みではない


def scad(args, out=None):
    cmd = [OPENSCAD, "--backend=manifold", "-o", out or os.path.join(TMP, "_.echo"),
           "-D", 'part="__none__"'] + args + [SCAD]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def read_paths():
    os.makedirs(TMP, exist_ok=True)
    ec = os.path.join(TMP, "pose.echo")
    scad(["-D", 'SW_MODE="pose"'], ec)
    m = re.search(r"SWPOSE = (\[.*\])", open(ec, encoding="utf-8", errors="replace").read())
    if not m:
        sys.exit("SWPOSE が読めない")
    return {p[0]: {"path": p[1], "c": p[2], "r": p[3]} for p in json.loads(m.group(1))}


def export(mode, name, key):
    f = os.path.join(TMP, "%s_%s.off" % (key, mode))
    var = "MOVER" if mode == "mover" else "WORLD"
    scad(["-D", 'SW_MODE="%s"' % mode, "-D", 'SW_%s="%s"' % (var, name)], f)
    if not os.path.exists(f):
        sys.exit("%s の書き出しに失敗" % f)
    return trimesh.load(f)


# ---- 姿勢（OpenSCAD の at_pose と同じ）----
def rot(rx, ry, rz):
    a, b, c = map(math.radians, (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx                                    # OpenSCAD rotate([x,y,z])


def pose_mat(q, c):
    R = rot(q[3], q[4], q[5])
    c = np.asarray(c, float)
    return R, np.asarray(q[:3], float) + c - R @ c


def lerp(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(6)]


def motion_bound(a, b, r):
    u"""a→b で物のどの点も、これ以上は動かない（上限）。回すと端がいちばん動く"""
    d = float(np.linalg.norm(np.array(b[:3], float) - np.array(a[:3], float)))
    th = max(abs(b[3] - a[3]), abs(b[4] - a[4]), abs(b[5] - a[5]))
    return d + r * math.radians(th)


def bvh(mesh):
    m = fcl.BVHModel()
    m.beginModel(len(mesh.vertices), len(mesh.faces))
    m.addSubModel(np.asarray(mesh.vertices, np.float64), np.asarray(mesh.faces, np.int32))
    m.endModel()
    return m


def march(mover, world, path, c, r):
    u"""距離クエリで道を走る。刻みは空いている距離から決める（Conservative Advancement）"""
    mo = fcl.CollisionObject(bvh(mover), fcl.Transform())
    wo = fcl.CollisionObject(bvh(world), fcl.Transform())
    out = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        M = motion_bound(a, b, r)
        if M < 1e-9:
            continue
        t = 0.0
        while True:
            R, tr = pose_mat(lerp(a, b, t), c)
            mo.setTransform(fcl.Transform(R, tr))
            res = fcl.DistanceResult()
            d = float(fcl.distance(mo, wo, fcl.DistanceRequest(), res))
            out.append({"s": i + t, "d": d})
            if t >= 1.0:
                break
            t = min(1.0, t + max(d - TOL, MIN_MOVE) / M)
    return out


def intervals(samples):
    u"""隙間が TOL 以下の区間をまとめる"""
    iv, cur = [], None
    for s in samples:
        if s["d"] <= TOL:
            cur = cur or [s["s"], s["s"]]
            cur[1] = s["s"]
        elif cur:
            iv.append(cur)
            cur = None
    if cur:
        iv.append(cur)
    return iv


def exact_hit(key, q, c, idx=0):
    u"""1 姿勢だけ厳密に交わりを取る（OpenSCAD の manifold）。厚み 0 なら同一平面の皮。
    交わりの形そのものも残す（動画がこれを赤い塊として出す）"""
    f = os.path.join(TMP, "%s_hit%03d.off" % (key, idx))
    if os.path.exists(f):
        os.remove(f)
    scad(["-D", 'SW_MODE="hit"', "-D", 'SW_MOVER="%s"' % key, "-D", 'SW_WORLD="%s"' % key,
          "-D", "SW_Q=%s" % json.dumps([round(v, 6) for v in q]),
          "-D", "SW_C=%s" % json.dumps(list(c))], f)
    empty = {"faces": 0, "thick": 0.0, "vol": 0.0, "ext": [0, 0, 0], "bmin": None, "bmax": None,
             "off": None}
    if not os.path.exists(f) or os.path.getsize(f) < 40:
        return empty
    m = trimesh.load(f)
    if len(m.faces) == 0:
        return empty
    # 厚みは主軸で測る（軸に平行でない皮を「厚い」と誤判定しないため）
    v = np.asarray(m.vertices, float)
    ax = np.linalg.svd(v - v.mean(0), full_matrices=False)[2]
    ext = sorted(float(x) for x in ((v - v.mean(0)) @ ax.T).ptp(0))
    vol = float(abs(m.volume)) if m.is_watertight else 0.0
    return {"faces": int(len(m.faces)), "thick": round(ext[0], 4), "vol": round(vol, 4),
            "ext": [round(x, 3) for x in ext[::-1]],
            "bmin": [round(float(x), 3) for x in m.bounds[0]],
            "bmax": [round(float(x), 3) for x in m.bounds[1]],
            "off": os.path.basename(f)}


def pose_at(path, s, c):
    i = min(int(s), len(path) - 2)
    return lerp(path[i], path[i + 1], s - i)


def check(key, spec):
    t0 = time.time()
    mover = export("mover", key, key)
    world = export("world", key, key)
    sam = march(mover, world, spec["path"], spec["c"], spec["r"])
    t_march = time.time() - t0
    iv = intervals(sam)
    M = sum(motion_bound(spec["path"][i], spec["path"][i + 1], spec["r"])
            for i in range(len(spec["path"]) - 1))
    for old in os.listdir(TMP):
        if old.startswith("%s_hit" % key):
            os.remove(os.path.join(TMP, old))       # 前回の交わりを残さない
    hits = []
    for lo, hi in iv:
        n = max(1, min(EXACT_MAX, int(math.ceil((hi - lo) * M / EXACT_MOVE))))
        for k in range(n + 1):
            s = lo + (hi - lo) * k / n
            e = exact_hit(key, pose_at(spec["path"], s, spec["c"]), spec["c"], len(hits))
            e["s"] = round(s, 4)
            hits.append(e)
    worst = max(hits, key=lambda h: (h["thick"], h["vol"], h["faces"]), default=None)
    rep = {"key": key, "n_samples": len(sam), "sec_march": round(t_march, 2),
           "sec_total": round(time.time() - t0, 2),
           "min_clearance": round(min(s["d"] for s in sam), 4),
           "intervals": [[round(a, 4), round(b, 4)] for a, b in iv],
           "n_exact": len(hits), "worst": worst,
           "verdict": "入る" if (not worst or worst["thick"] < SKIN_T) else "めり込む",
           "path": spec["path"], "c": spec["c"], "r": spec["r"],
           "samples": [{"s": round(s["s"], 5), "d": round(s["d"], 4)} for s in sam],
           "exact": hits, "tris": {"mover": len(mover.faces), "world": len(world.faces)}}
    json.dump(rep, open(os.path.join(TMP, "%s.json" % key), "w", encoding="utf-8"), ensure_ascii=False)
    return rep


def main():
    keys = sys.argv[1:] or ["hub", "rsp", "oled", "bat"]
    paths = read_paths()
    for k in keys:
        if k not in paths:
            print("%-5s : 道が無い" % k)
            continue
        r = check(k, paths[k])
        print(u"%-5s 姿勢 %d（%.2f 秒）＋ 厳密 %d 回 ＝ %.1f 秒 | 面 %d/%d"
              % (k, r["n_samples"], r["sec_march"], r["n_exact"], r["sec_total"],
                 r["tris"]["mover"], r["tris"]["world"]))
        print(u"      最小隙間 %.3f mm / 接触区間 %s" % (r["min_clearance"], r["intervals"] or "無し"))
        w = r["worst"]
        if w and w["faces"]:
            print(u"      いちばん深い所 s=%s: 厚み %.3f mm・体積 %.3f mm3・広がり %s・角 %s"
                  % (w["s"], w["thick"], w["vol"], w["ext"], w["bmin"]))
        skin = u"（同一平面の皮。めり込みではない）" if w and w["faces"] and w["thick"] < SKIN_T else u""
        print(u"      判定: %s%s" % (r["verdict"], skin))


if __name__ == "__main__":
    main()
