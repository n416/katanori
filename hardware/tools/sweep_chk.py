# -*- coding: utf-8 -*-
u"""入れる道の当たり検査（ブーリアンを取らずに距離で走る）。

  sweep_chk.py hub rsp oled bat lidmain lidflap

やること
  1. OpenSCAD から「動かす物」と「相手」を OFF で 1 回だけ出す
  2. FCL の距離クエリで道を走る。刻みは固定せず、空いている距離から出す（Conservative Advancement）
     ── 空いていれば飛ばし、狭い所だけ細かくなる。すり抜けが起きない
  3. 隙間が TOL 以下になった区間の中だけ、OpenSCAD で 1 姿勢ずつ厳密な交わりを取る
     ── 厚みが 0 なら同一平面の皮（＝誤報）、厚みがあれば本物のめり込み
  4. 見つけた塊を **hardware/sweep_accept.json（了承済みの当たりの台帳）** と突き合わせ、
     載っていない物だけを「新」として出す。新しい当たりがあれば終了コード 1
  5. 判定を hardware/check/<材料>/sweep/<key>.json に書く（git に入る証拠。模型の刻印つき・tools/check_stamp.py）。
     動画（tools/sweep_movie.py）とマニュアルはこれを読む。OFF・STL などの中間物は hardware/_tmp_sweep/<材料>/（git に入らない）

なぜこの形か: 姿勢を n 個 union して交わりの体積を作る旧 sweep_pose() は、
姿勢の数だけ面数が増える。0.25 刻みで 400 姿勢 × 28782 面 ＝ 1150 万面で PC が固まった（2026-09-17）。
距離クエリは形を作らないので、同じ道が 188 姿勢・1 秒で終わる。docs/COLLISION-SURVEY.md 参照。
"""
import json, math, os, re, subprocess, sys, time
import numpy as np, trimesh, fcl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_stamp import stamp, out_dir                                            # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_stamp import stamp, out_dir                                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows の cp932 で日本語が化けないように

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # hardware/
SCAD = os.path.join(ROOT, "tools", "_sweep_v61.scad")
# 🔒 ユーザー 2026-09-15「レジン版とナイロン版はスイッチできるわけで、それに応じてアラートを分けて」:
#   材料は -D MAT= で OpenSCAD へ渡し、出る物も材料ごとに分ける（混ざると前の材料の OFF を使ってしまう）
MAT = "nylon"
TMP = os.path.join(ROOT, "_tmp_sweep", MAT)              # 中間物（git に入らない）
OUT = os.path.join(ROOT, "check", MAT, "sweep")          # 判定（git に入る）
OPENSCAD = os.environ.get("OPENSCAD", r"C:\Program Files\OpenSCAD (Nightly)\openscad.exe")

TOL = 0.05          # これ以下の隙間は「接触」として扱う（clash tolerance。意図した面接触を落とす）
MIN_MOVE = 0.02     # 接触区間で 1 歩に進む距離 mm（道具が止まらないための下限）
EXACT_MOVE = 0.30   # 接触区間の中で厳密な交わりを取る間隔 mm
EXACT_MAX = 12      # 1 区間あたりの厳密評価の上限（重くしないため）
SKIN_T = 0.10       # 交わりの厚みがこれ未満なら当たりに数えない（同一平面の皮 ＋ 物が入る分）。
#   🔒 ユーザー 2026-09-18「0.1mm くらい何でも入るよ」── 刷った物の公差も硬化の縮みもこれより大きい。
#   ⚠ 2026-09-18 まで 0.01（皮だけを落とす値）だったので、0.1 未満の擦りが全部「めり込み」として出ていた
# ---- たわむ物（2026-09-18）----
# 道の 1 点は [dx, dy, dz, rx, ry, rz, d]。**7 つ目 d はたわみ量**で、これが変わると**形が変わる**。
# 形は OpenSCAD に作り直させるので、d は刻んで丸める（作り直す回数を抑える）。
# 🔴 丸めは**小さい側**へ。たわみが小さい方が逃げが少なく、判定として厳しい側に倒れる。
DELTA_STEP = 0.1
DEFL_RATIO = 2.5    # d が 1 変わると物のどの点も最大これだけ動く（板の下端が d の 2.4 倍出る）


_SRC_MT = None


def src_mtime():
    u"""模型の元ファイル（*.scad）のうち、いちばん新しい更新時刻"""
    global _SRC_MT
    if _SRC_MT is None:
        # 🔴 2026-09-19: 模型の元ファイルは check_stamp.scad_files() に 1 か所で持つ（基板の pcb/ と STL も入る）。
        #   ここで別に並べていたら pcb/ が抜けていて、基板を直しても作り置きの OFF が古いまま使われた
        import check_stamp
        _SRC_MT = max([os.path.getmtime(SCAD)] + [os.path.getmtime(f) for f in check_stamp.scad_files()])
    return _SRC_MT


def cached(f):
    u"""キャッシュした OFF がそのまま使えるか。
    🔴 **「あれば使う」にしてはいけない。**模型を直しても作り直されず、古い形のまま検査も動画も走る。
      2026-09-18 に踏んだ: front_mover.off が 1 時間古く、動かす物に OLED の付いていない動画を焼いた。
      当たりを探す段（距離で走る所）も古い形を見ていて、直した形でだけ出る当たりを 7 件見落としていた"""
    return os.path.exists(f) and os.path.getmtime(f) >= src_mtime()


SCAD_HANG = 60     # 出力を書き終えてから、これだけ待っても終わらなければ固まったと見る（秒）
SCAD_MAX = 900     # 出力が出ないまま、これだけ経ったらあきらめる（秒）


def scad(args, out=None):
    u"""OpenSCAD を 1 回回す。
    🔴 2026-09-18: OpenSCAD（Nightly）が**出力を書き終えた後に終わらず固まる**ことがある。
      hatch_hit008.off は 17:24 に書き終えて中身も正しいのに 14 分終わらず、掃引が止まった
      （前日の oled_hit001 も同じで 15 時間残っていた。外から kill もできない）。
      ⇒ 書かれた出力の大きさが SCAD_HANG 秒変わらなければ、待つのをやめて先へ進む"""
    out = out or os.path.join(TMP, "_.echo")
    cmd = [OPENSCAD, "--backend=manifold", "-o", out,
           "-D", 'part="__none__"', "-D", 'MAT="%s"' % MAT,
           "-D", "RIDE_ON=false", "-D", "PCB_SILK=false"] + args + [SCAD]   # 乗る物は world から外す（sw_ride が別に出す）。シルクは厚み 0 の皮なので外す
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    seen = None
    while p.poll() is None:
        time.sleep(0.2)
        # 前の回の古いファイルを「書き終えた」と取り違えない（この回に書かれた物だけ見る）
        if os.path.exists(out) and os.path.getmtime(out) >= t0:
            sz = os.path.getsize(out)
            if seen is None or seen[0] != sz:
                seen = (sz, time.time())
            elif time.time() - seen[1] > SCAD_HANG:
                try:
                    p.kill()
                except Exception:
                    pass
                print(u"  ⚠ OpenSCAD が出力を書いた後に終わらない。待たずに先へ進む（%s）" % os.path.basename(out))
                return None
        elif time.time() - t0 > SCAD_MAX:
            try:
                p.kill()
            except Exception:
                pass
            print(u"  ⚠ OpenSCAD が %d 秒たっても出力を書かない。あきらめる（%s）" % (SCAD_MAX, os.path.basename(out)))
            return None
    return None


def read_paths():
    os.makedirs(TMP, exist_ok=True)
    ec = os.path.join(TMP, "pose.echo")
    scad(["-D", 'SW_MODE="pose"'], ec)
    txt = open(ec, encoding="utf-8", errors="replace").read()
    m = re.search(r"SWPOSE = (\[.*\])", txt)
    if not m:
        sys.exit("SWPOSE が読めない")
    r = re.search(r"SWRIDE = (\[.*?\])", txt)
    global RIDE
    RIDE = json.loads(r.group(1)) if r else None   # [軸の Y, 軸の Z, 軸から後ろの穴まで]
    return {p[0]: {"path": p[1], "c": p[2], "r": p[3]} for p in json.loads(m.group(1))}


RIDE = None   # [軸の Y, 軸の Z, 軸から後ろの穴まで]。read_paths が SWRIDE から読む


def ride_tf(lift):
    u"""乗る物（仮締めで逃げる物）の姿勢。持ち上げ量 lift のとき、前 2 本のねじの線を軸に傾く。
    OpenSCAD の hub_ride() と同じ式。軸の値は SWRIDE で受け取る（2 か所に書くとずれる）"""
    a = np.arctan2(float(lift), float(RIDE[2]))
    ca, sa = np.cos(a), np.sin(a)
    R = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]], float)
    p = np.array([0.0, float(RIDE[0]), float(RIDE[1])])
    return R, p - R.dot(p)


def export_ride(key):
    u"""乗る物だけを素の姿勢で出す。無い場面は None（OpenSCAD は中身が空だと何も書かない）"""
    f = os.path.join(TMP, "%s_ride.off" % key)
    if not cached(f):
        if os.path.exists(f):
            os.remove(f)
        scad(["-D", 'SW_MODE="ride"', "-D", 'SW_WORLD="%s"' % key], f)
    return trimesh.load(f) if os.path.exists(f) and os.path.getsize(f) > 40 else None


def export(mode, name, key, d=None):
    u"""動かす物／相手を OFF で出す。d を渡すと、そのたわみ量の形を作る（形ごとに 1 ファイル）"""
    tag = "" if d is None else "_d%03d" % int(round(d * 100))
    f = os.path.join(TMP, "%s_%s%s.off" % (key, mode, tag))
    var = "MOVER" if mode == "mover" else "WORLD"   # ride も WORLD（場面の名前で引く）
    if not cached(f):
        args = ["-D", 'SW_MODE="%s"' % mode, "-D", 'SW_%s="%s"' % (var, name)]
        if d is not None:
            args += ["-D", "SW_D=%s" % d]
        scad(args, f)
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
    n = max(len(a), len(b))
    g = lambda q, i: q[i] if i < len(q) else 0.0
    return [g(a, i) + (g(b, i) - g(a, i)) * t for i in range(n)]


def delta(q):
    u"""道の点からたわみ量を取り出して刻みに丸める（小さい側 ＝ 厳しい側へ）"""
    d = q[6] if len(q) > 6 else 0.0
    return round(math.floor(d / DELTA_STEP + 1e-9) * DELTA_STEP, 3)


def motion_bound(a, b, r):
    u"""a→b で物のどの点も、これ以上は動かない（上限）。回すと端がいちばん動き、
    たわみが変わると形そのものが動く（板の下端が d の 2.4 倍出るので DEFL_RATIO を掛ける）"""
    d = float(np.linalg.norm(np.array(b[:3], float) - np.array(a[:3], float)))
    th = max(abs(b[3] - a[3]), abs(b[4] - a[4]), abs(b[5] - a[5]))
    dd = abs((b[6] if len(b) > 6 else 0.0) - (a[6] if len(a) > 6 else 0.0))
    return d + r * math.radians(th) + DEFL_RATIO * dd


def bvh(mesh):
    m = fcl.BVHModel()
    m.beginModel(len(mesh.vertices), len(mesh.faces))
    m.addSubModel(np.asarray(mesh.vertices, np.float64), np.asarray(mesh.faces, np.int32))
    m.endModel()
    return m


def march(mover_at, world, path, c, r, ride=None):
    u"""距離クエリで道を走る。刻みは空いている距離から決める（Conservative Advancement）。
    mover_at(d) は、そのたわみ量の物（形が変わるので姿勢だけでは足りない）"""
    wo = fcl.CollisionObject(bvh(world), fcl.Transform())
    ro = fcl.CollisionObject(bvh(ride), fcl.Transform()) if ride is not None else None
    out = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        M = motion_bound(a, b, r)
        if M < 1e-9:
            continue
        t = 0.0
        while True:
            q = lerp(a, b, t)
            mo = mover_at(delta(q))
            R, tr = pose_mat(q, c)
            mo.setTransform(fcl.Transform(R, tr))
            res = fcl.DistanceResult()
            d = float(fcl.distance(mo, wo, fcl.DistanceRequest(), res))
            if ro is not None:                      # 乗る物は、その姿勢のときの持ち上げ量に追従する
                Rr, tr2 = ride_tf(q[2])
                ro.setTransform(fcl.Transform(Rr, tr2))
                d = min(d, float(fcl.distance(mo, ro, fcl.DistanceRequest(), fcl.DistanceResult())))
            out.append({"s": i + t, "d": d, "dd": delta(q)})
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
          "-D", "RIDE_LIFT=%s" % round(float(q[2]), 6),   # 乗る物をこの持ち上げ量の姿勢に置く
          "-D", "SW_Q=%s" % json.dumps([round(v, 6) for v in q[:6]]),
          "-D", "SW_D=%s" % delta(q),                     # たわみ量。形が変わるので姿勢とは別に渡す
          "-D", "SW_C=%s" % json.dumps(list(c))], f)
    empty = {"faces": 0, "thick": 0.0, "vol": 0.0, "ext": [0, 0, 0], "bmin": None, "bmax": None,
             "off": None}
    if not os.path.exists(f) or os.path.getsize(f) < 40:
        return empty
    m = trimesh.load(f)
    if len(m.faces) == 0:
        return empty
    # 🔴 **塊ごとに測る。** 交わりは離れた複数の塊になる（蓋は縁のぐるり全部で触れる）。
    #   まとめて主軸を取ると、別々の平面にある皮が寄り集まって「厚い」に化ける
    #   （2026-09-17 に踏んだ: lidmain が体積 0 のまま厚み 5.198 と出た）。
    best, pieces, deep, deepm = None, 0, [], []
    for g in m.split(only_watertight=False) or [m]:
        v = np.asarray(g.vertices, float)
        if len(v) < 3:
            continue
        ax = np.linalg.svd(v - v.mean(0), full_matrices=False)[2]
        ext = sorted(float(x) for x in ((v - v.mean(0)) @ ax.T).ptp(0))
        vol = float(abs(g.volume)) if g.is_watertight else 0.0
        if not math.isfinite(vol):
            vol = 0.0              # 潰れた塊は体積が NaN になる（JSON が壊れる）
        pieces += 1
        cur = {"faces": int(len(g.faces)), "thick": round(ext[0], 4), "vol": round(vol, 4),
               "ext": [round(x, 3) for x in ext[::-1]],
               "bmin": [round(float(x), 3) for x in g.bounds[0]],
               "bmax": [round(float(x), 3) for x in g.bounds[1]]}
        if cur["thick"] >= SKIN_T:
            deep.append(dict(cur))               # 皮でない塊（＝本物のめり込み）は全部残す
            deepm.append(g)
            #   ⚠ dict() で写しを取る。best と同じ物を入れると JSON が循環参照で書けない
        if best is None or (cur["thick"], cur["vol"]) > (best["thick"], best["vol"]):
            best = cur
    if best is None:
        return empty
    best["off"] = os.path.basename(f)
    # 🔴 塊の体積を足した「合計」は持たない（🔒 ユーザー 2026-09-17「合計は無意味」）。
    #   小さな接触が 6 か所あるのと、大きなめり込みが 1 か所あるのを、足すと区別できなくなる。
    #   塊ごとに分けた意味が消えるので、出すのは**いちばん深い塊**と**塊の数**だけ
    best["pieces"] = pieces
    best["faces_all"] = int(len(m.faces))
    best["deep"] = sorted(deep, key=lambda x: -x["thick"])[:20]
    # 🔴 絵に出すのは**皮でない塊だけ**。全部出すと、めり込みではないと決めた皮まで赤くなる
    #   （2026-09-18: 交わりを見せるコマで細い赤が散り、本物と見分けられなかった）
    if deepm:
        g = trimesh.util.concatenate(deepm)
        fd = f.replace(".off", "_deep.off")
        g.export(fd)
        best["off_deep"] = os.path.basename(fd)
    return best


ACCEPT_F = os.path.join(ROOT, "sweep_accept.json")


def load_accept():
    u"""了承済みの当たりの台帳（hardware/sweep_accept.json）"""
    if not os.path.exists(ACCEPT_F):
        return []
    return json.load(open(ACCEPT_F, encoding="utf-8")).get("accept", [])


def inside(piece, box):
    return all(box[0][i] - 1e-6 <= piece["bmin"][i] and piece["bmax"][i] <= box[1][i] + 1e-6
               for i in range(3))


def classify(key, pieces, accept):
    u"""塊を「了承済み」と「新規」に分ける。箱の外へ出た／厚みが育った物は新規"""
    ok, new = [], []
    for d in pieces:
        hit = next((a for a in accept if a["key"] == key and a.get("mat", "nylon") == MAT
                    and inside(d, a["box"])
                    and d["thick"] <= a["thick"] + 1e-6), None)
        (ok if hit else new).append(dict(d, acc=hit["id"] if hit else None,
                                         why=hit["why"] if hit else None))
    return ok, new


def gather(hits):
    u"""道ぜんたいで見つかった皮でない塊を、場所でまとめる（姿勢ごとに同じ物が出るため）"""
    seen = {}
    for e in hits:
        for d in e.get("deep", []):
            k = tuple(round(x, 0) for x in d["bmin"])
            if k not in seen or d["thick"] > seen[k]["thick"]:
                seen[k] = d
    return sorted(seen.values(), key=lambda x: -x["thick"])


def pose_at(path, s, c):
    i = min(int(s), len(path) - 2)
    return lerp(path[i], path[i + 1], s - i)


def check(key, spec):
    t0 = time.time()
    # たわむ物は、たわみ量ごとに形が違う。要る形だけ作って持っておく
    ds = sorted({delta(q) for q in spec["path"]})
    flex = len(ds) > 1 or ds != [0.0]
    cache, meshes = {}, {}

    def mover_at(d):
        if d not in cache:
            meshes[d] = export("mover", key, key, d if flex else None)
            cache[d] = fcl.CollisionObject(bvh(meshes[d]), fcl.Transform())
        return cache[d]

    mover_at(delta(spec["path"][0]))
    world = export("world", key, key)
    ride = export_ride(key)
    sam = march(mover_at, world, spec["path"], spec["c"], spec["r"], ride)
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
    ok, new = classify(key, gather(hits), load_accept())
    rep = {"key": key, "n_samples": len(sam), "sec_march": round(t_march, 2),
           "sec_total": round(time.time() - t0, 2),
           "min_clearance": round(min(s["d"] for s in sam), 4),
           "intervals": [[round(a, 4), round(b, 4)] for a, b in iv],
           "n_exact": len(hits), "worst": worst, "ok": ok, "new": new,
           "verdict": "入る" if not new and not ok else ("新しい当たり" if new else "了承済みの当たりだけ"),
           "path": spec["path"], "c": spec["c"], "r": spec["r"],
           "samples": [{"s": round(s["s"], 5), "d": round(s["d"], 4)} for s in sam],
           "flex": flex, "deltas": sorted(meshes),
           "exact": hits, "tris": {"mover": max(len(m.faces) for m in meshes.values()),
                                   "world": len(world.faces)}}
    rep["src"] = stamp()                                     # どの模型から出た判定か
    json.dump(rep, open(os.path.join(out_dir(MAT, "sweep"), "%s.json" % key), "w", encoding="utf-8"), ensure_ascii=False)
    return rep


def snippet(key, d):
    u"""新規の当たりを、そのまま sweep_accept.json に貼れる形で出す（理由は人が書く）"""
    pad = 0.5
    box = [[round(d["bmin"][i] - pad, 2) for i in range(3)],
           [round(d["bmax"][i] + pad, 2) for i in range(3)]]
    return json.dumps({"id": "%s-%s-????" % (MAT, key), "key": key, "mat": MAT,
                       "why": "（なぜ了承するかを書く）",
                       "box": box, "thick": round(d["thick"] + 0.05, 3),
                       "since": time.strftime("%Y-%m-%d")}, ensure_ascii=False)


def main():
    global MAT, TMP, OUT
    args = sys.argv[1:]
    for i, a in enumerate(list(args)):                       # --mat resin / --mat=resin
        if a == "--mat" and i + 1 < len(args):
            MAT = args[i + 1]; args = args[:i] + args[i + 2:]; break
        if a.startswith("--mat="):
            MAT = a.split("=", 1)[1]; args = [x for x in args if x != a]; break
    if MAT not in ("resin", "nylon"):
        sys.exit("--mat は resin か nylon")
    TMP = os.path.join(ROOT, "_tmp_sweep", MAT)
    OUT = os.path.join(ROOT, "check", MAT, "sweep")
    os.makedirs(TMP, exist_ok=True)
    paths = read_paths()
    keys = args or list(paths)                               # 道は材料で違う（ナイロン lid / レジン lwall rwall top hatch）
    print(u"材料 %s（判定は hardware/check/%s/sweep/・中間物は hardware/_tmp_sweep/%s/）" % (MAT, MAT, MAT))
    news = []
    for k in keys:
        if k not in paths:
            print("%-7s : 道が無い" % k)
            continue
        r = check(k, paths[k])
        print(u"%-7s 姿勢 %d（%.2f 秒）＋ 厳密 %d 回 ＝ %.1f 秒 | 面 %d/%d"
              % (k, r["n_samples"], r["sec_march"], r["n_exact"], r["sec_total"],
                 r["tris"]["mover"], r["tris"]["world"]))
        print(u"        最小隙間 %.3f mm / 接触区間 %s" % (r["min_clearance"], r["intervals"] or "無し"))
        for d in r["ok"]:
            print(u"        済  厚み %.3f・%s  %s" % (d["thick"], d["bmin"], d["why"]))
        for d in r["new"]:
            print(u"        新  厚み %.3f・体積 %.3f・広がり %s・角 %s"
                  % (d["thick"], d["vol"], d["ext"], d["bmin"]))
            news.append((k, d))
        if not r["ok"] and not r["new"]:
            print(u"        めり込み無し（触れているのは同一平面の皮だけ）")
        print(u"        判定: %s" % r["verdict"])
    print(u"\n==== [%s] 新しい当たり %d 件 / 了承済みの台帳 %d 件（hardware/sweep_accept.json の %s の分）"
          % (MAT, len(news), len([a for a in load_accept() if a.get("mat", "nylon") == MAT]), MAT))
    if news:
        print(u"見て「これでよい」と判じたら、理由を書いて台帳の accept に足す:")
        for k, d in news:
            print(u"  " + snippet(k, d))
    raise SystemExit(1 if news else 0)


if __name__ == "__main__":
    main()
