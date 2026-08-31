# -*- coding: utf-8 -*-
"""刷るぞー ── STL を測る層。

🔒 **数字は自分で作らない。** 接地面積・島・持たれていない天井は
   [_stl_preflight.py](../hardware/_stl_preflight.py) の実装をそのまま呼ぶ。
   同じ数字が 2 か所にあると片方だけ動くため（記憶 same-number-in-two-places）。

   ⚠ `_stl_preflight` は **import しただけで本体が走る**（モジュールの一番外側に
     `for p in sorted(glob.glob(sys.argv[1])):` が置いてある）。読み込む間だけ argv を
     差し替えて、**どのファイルにも当たらない glob** を渡す。ループが 0 回まわって
     終わるので、関数の定義だけが手に入る。⇒ 相手のファイルは書き換えない。
"""
import json, math, os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_HW = os.path.join(os.path.dirname(_HERE), "hardware")

_saved = sys.argv
# argv[1] = 当たらない glob（本体のループを 0 回で終わらせる）／argv[2] = 薄肉のしきい値
sys.argv = [sys.argv[0], os.path.join(_HERE, "__surugo_no_match__*.stl"), "0.30"]
sys.path.insert(0, _HW)
import _stl_preflight as PF        # noqa: E402
sys.argv = _saved

import numpy as np                 # noqa: E402

DZ = PF.DZ                         # 層の高さ 0.050mm（PRINT.md §1）
GRIP_BAD = PF.GRIP_BAD             # 1709mm² 剥がれず・プレートに傷（PRINT.md §4）
GRIP_WARN = PF.GRIP_WARN           # 585mm² 角が欠けた

CACHE = os.path.join(_HERE, ".measure_cache.json")
SCHEMA = 6      # 返す形を変えたら上げる（上げないと古い結果が残る）。4→5: warn の文面を直した


def _load_cache():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(c):
    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False)
    os.replace(tmp, CACHE)


def measure(path, pitch=0.25):
    """1 個の STL を測る。重いのでファイルの mtime とサイズで覚えておく。"""
    st = os.stat(path)
    key = "v%d|%s|%d|%d" % (SCHEMA, os.path.abspath(path), st.st_mtime_ns, st.st_size)
    cache = _load_cache()
    if key in cache:
        return cache[key]

    tris = PF.read_stl(path)
    grip, long_mm, isl, ceil, height, grip_max = PF.grip_and_islands(tris, pitch)
    prof = _profile(tris, pitch)

    lo = tris.reshape(-1, 3).min(axis=0)
    hi = tris.reshape(-1, 3).max(axis=0)

    r = {
        "path": os.path.relpath(path, os.path.dirname(_HERE)).replace("\\", "/"),
        "name": os.path.basename(path),
        "grip": round(float(grip), 1),              # 接地面積 mm²（プレート全体の合計）
        "grip_max": round(float(grip_max), 1),      # 1 枚あたりの接地（つながっている領域の最大）
        "long_mm": round(float(long_mm), 2),        # 一番長い辺
        "height": round(float(height), 3),          # 背
        "layers": int(math.ceil(float(height) / DZ)),
        "bbox": [round(float(v), 3) for v in (lo[0], lo[1], lo[2], hi[0], hi[1], hi[2])],
        "z0": round(float(lo[2]), 4),
        # 🔒 層ごとの断面積 mm²（層 0 = 接地）。出典の 30% は**断面**の話で、
        #   しかも土台がたわむ原因は剥離力なので、効くのは**その層に載っている合計**である。
        #   ⇒ 並べたときに層ごとに足し合わせるため、部品ごとの形をここで持つ。
        "profile": prof,
        "profile_max": round(float(max(prof)) if prof else 0.0, 1),
        "islands": len(isl),                        # 宙に浮いた欠片
        "island_mm2": round(float(sum(i[1] for i in isl)), 2),
        "ceilings": len(ceil),                      # 支えから離れた天井（層の数）
        "ceiling_mm2": round(float(sum(c[1] for c in ceil)), 2),
        # 🔴 「浮かせて刷る必要があるか」は**ここでは決めない。**
        #   幾何から推論すると、いま直置きで刷れている部品まで弾く（実際に弾いた）。
        #   置き方の判断は PRINT.md §3 のとおり人が決めるもので、server.py の
        #   lifted.json に宣言する。ここが返すのは観測だけ。
    }
    r["warn"] = _warn(r)

    cache[key] = r
    _save_cache(cache)
    return r


def _profile(tris, pitch):
    """層ごとの断面積 mm² の列を返す。層 0 が接地。"""
    col, zs, ze, us, vs, nu, nv = PF.zcolumns(tris, pitch)
    z0 = zs.min()
    n = int(np.ceil((ze.max() - z0) / DZ))
    if n <= 0:
        return []
    # 各レイの区間が覆う層を、差分配列で一気に数える
    s = np.clip(np.ceil((zs - z0) / DZ - 0.5).astype(int), 0, n)
    e = np.clip(np.ceil((ze - z0) / DZ - 0.5).astype(int), 0, n)
    d = np.zeros(n + 2)
    np.add.at(d, s, 1.0)
    np.add.at(d, e, -1.0)
    cnt = np.cumsum(d)[:n]
    return [round(float(v) * pitch * pitch, 2) for v in cnt]


def _warn(r):
    """PRINT.md の実績値と突き合わせる。⚠ ここで新しい基準を発明しない。"""
    w = []
    # 🔴 2026-08-31 判定を 1e-4（0.1µm）から**層の高さ**へ。0.1µm は層の 1/500 で、
    #    計算誤差ぶんの端数まで警告になっていた（v4_floor の 0.0043 が実例）。
    #    ⚠ 新しい基準ではない。_stl_preflight.py が既に使っている値（層 0.05・PRINT.md §1）。
    #    1 層目は 0〜0.05 を拾うので、それ未満の浮きは刷り上がりに現れない。
    LAYER = 0.05
    if r["z0"] < -1e-4:
        w.append("底がプレートより下にある（%.3f 沈んでいる）" % r["z0"])
    elif r["z0"] > LAYER:
        w.append("底が Z=0 にない（%.3f 浮いている）" % r["z0"])
    elif r["z0"] > 1e-4:
        w.append("🟡 底が %.4f 浮いているが層の高さ %.2f より小さい"
                 "（1 層目に入るので刷り上がりは変わらない）" % (r["z0"], LAYER))
    if r["islands"]:
        w.append("宙に浮いた欠片 %d か所（計 %.1fmm²）" % (r["islands"], r["island_mm2"]))
    if r["ceilings"]:
        # 🔴 2026-08-31 文面を直した。前は「支柱入りの knob_v5_deck で 19mm²」とだけ出ていて、
        #    無関係の部品の名前が理由なしに現れ、読む側に「なぜここで別の部品？」しか伝わらなかった
        #    （ユーザー「ノブデックが出てくるのも良く分かりませんし」「floor につまみってないですよね？」）。
        #    ⚠ 19.1mm² は同じ測り方で knob_v5_deck.stl を測った値で実在する（2026-08-31 に確認）。
        #    ただし**それが刷って無事だったという記録は無い。**実績値ではないので、
        #    「何 mm² までなら大丈夫か」の判断には使えない。⬜ その実績はまだ誰も取っていない
        w.append("持たれていない天井 %.0fmm²（%d 層）⬜ 何 mm² までなら大丈夫かの実績は無い"
                 "（比較: 同じ測り方で knob_v5_deck.stl が 19.1mm²。ただしその刷り上がりは未記録）"
                 % (r["ceiling_mm2"], r["ceilings"]))
    # 🔒 2026-09-01 比べるのは合計ではなく **1 枚あたり**（grip_max）。
    #   実績 585 / 1709 は 1 枚の大きな板で出た値で、小さい板が棒でつながった物には当たらない
    #   （ユーザー指摘「角が欠けるのは、それが 1 枚の大きな板だった場合でしょ？」）。
    #   ⚠ 合計（grip）は LCD 比＝土台のたわみの判定にそのまま使う。あちらは剥離力の総和なので
    if r.get("grip_max", r["grip"]) >= GRIP_BAD:
        w.append("1 枚あたりの接地 %.0fmm² ── 実績 %.0f で「剥がれず・プレートに傷」"
                 % (r.get("grip_max", r["grip"]), GRIP_BAD))
    elif r.get("grip_max", r["grip"]) >= GRIP_WARN:
        w.append("1 枚あたりの接地 %.0fmm² ── 実績 %.0f で「角が欠けた」"
                 % (r.get("grip_max", r["grip"]), GRIP_WARN))
    return w


# ---- STL の読み書き（結合して 1 つに出すため）----

def load_tris(path):
    return PF.read_stl(path)


def write_binary_stl(path, tris, header=b"surugo"):
    """三角形の配列を binary STL で書く。"""
    import struct
    n = len(tris)
    with open(path, "wb") as f:
        f.write(header.ljust(80, b" ")[:80])
        f.write(struct.pack("<I", n))
        v = tris.astype("<f4")
        # 法線は 0 で書く（スライサーは頂点順から求め直す）
        blank = np.zeros((n, 3), dtype="<f4")
        buf = np.concatenate([blank, v.reshape(n, 9)], axis=1).astype("<f4")
        for i in range(n):
            f.write(buf[i].tobytes())
            f.write(b"\0\0")
    return n
