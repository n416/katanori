# -*- coding: utf-8 -*-
"""刷るぞー ── フィルムの摩耗マップ（真上から見たプレートのヒートマップ）。

🔒 **出どころは「実際に刷った結合 STL」**（result を積んだときに hardware/stl/term/archive/ へ
   移した物）。四隅のアンカー入りなので、その座標がそのまま刷った位置である
   （CHITUBOX は bbox の中心をプレート中央に置く。アンカーが原点対称なので何も動かない）。
   ⚠ アンカーが無い回（2026-09-02-1404 / 2026-09-03-0244）も、STL の中心が move と一致して
   いるか原点対称なので、同じ扱いでよい。人が CHITUBOX に move を打った前提（placed）。

   マスの値 … その 1mm² の上で**何層ぶん露光（＝剥離）が起きたか**の累計。
   ヘッダの「摩耗」（接地 × 層数の総和）と同じ考え方を、場所ごとに割ったもの。
   ⚠ 代理値。剥離仕事そのものではない。

   フィルム交換（film）より前の回は数えない（摩耗はそこで 0 に戻る・store.state と同じ）。

   🔴 ここは観測（STL）から導ける事実だけを出す。「どこが減っている」の判断はしない。
"""
import json, os
import numpy as np

import measure as M
import store as S

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

PLATE_X, PLATE_Y = 143.0, 89.0      # server.py と同じ（Mars 3・PRINT.md §4）
CELL = 1.0                          # マス 1mm
PITCH = 0.5                         # レイの間隔。1 マスに 4 本
CACHE_DIR = os.path.join(_HERE, ".heat_cache")

NX = int(round(PLATE_X / CELL))
NY = int(round(PLATE_Y / CELL))


def _grid_of(path):
    """1 つの結合 STL → (layers, hit)。どちらも NY×NX。
       layers … マスごとの露光層数（レイ 4 本の平均）
       hit    … その回の部品がそのマスに載っていたか（0/1）
       アンカー（プレートの外）は捨てる。"""
    st = os.stat(path)
    key = "v1_%s_%d_%d_%s_%s" % (os.path.basename(path), st.st_mtime_ns, st.st_size, CELL, PITCH)
    cpath = os.path.join(CACHE_DIR, key + ".npz")
    if os.path.exists(cpath):
        z = np.load(cpath)
        return z["layers"], z["hit"]
    tris = M.load_tris(path)
    col, zs, ze, us, vs, nu, nv = M.PF.zcolumns(tris, PITCH)
    # レイごとの層数（入りから出まで）。同じレイに区間が複数あれば足す
    lay = np.zeros(nu * nv)
    np.add.at(lay, col, (ze - zs) / M.DZ)
    ix = np.repeat(np.arange(nu), nv)
    iy = np.tile(np.arange(nv), nu)
    x = us[ix]; y = vs[iy]
    cx = np.floor((x + PLATE_X / 2) / CELL).astype(int)
    cy = np.floor((y + PLATE_Y / 2) / CELL).astype(int)
    ok = (cx >= 0) & (cx < NX) & (cy >= 0) & (cy < NY) & (lay > 0)
    per = (PITCH * PITCH) / (CELL * CELL)          # レイ 1 本がマスに占める割合
    layers = np.zeros((NY, NX))
    np.add.at(layers, (cy[ok], cx[ok]), lay[ok] * per)
    hit = (layers > 0).astype(np.uint8)
    os.makedirs(CACHE_DIR, exist_ok=True)
    np.savez(cpath, layers=layers, hit=hit)
    return layers, hit


def _term_stl(term, result):
    """その回の刷った STL の場所。result の archived が正。無ければ term の out。"""
    for p in ((result or {}).get("archived"), term.get("out")):
        if p:
            full = os.path.normpath(os.path.join(_ROOT, p))
            if os.path.exists(full):
                return p, full
    return None, None


def heat():
    evs = S.read_all()
    film_at = None
    film_ev = None
    order = []
    results = {}
    dropped = {}
    for i, e in enumerate(evs):
        k = e.get("t")
        if k == "film":
            film_at = i; film_ev = e
        elif k == "term":
            order.append((i, e))
        elif k == "result":
            results[e.get("term")] = e
        elif k == "drop":
            dropped[e.get("term")] = i
    last = {}
    for i, e in order:
        last[e.get("id")] = (i, e)
    live = [(i, e) for i, e in sorted(last.values()) if dropped.get(e.get("id"), -1) < i]

    layers = np.zeros((NY, NX))
    count = np.zeros((NY, NX), dtype=int)
    fail = np.zeros((NY, NX), dtype=int)
    terms = []
    skipped = []
    for i, e in live:
        tid = e.get("id")
        if film_at is not None and i < film_at:
            continue
        r = results.get(tid)
        if r is None:
            skipped.append({"id": tid, "why": "まだ刷っていない（結果が無い）"})
            continue
        rel, full = _term_stl(e, r)
        if full is None:
            skipped.append({"id": tid, "why": "刷った STL が残っていない（archive 以前の回）",
                            "parts": [p["name"] for p in e.get("parts", [])]})
            continue
        L, H = _grid_of(full)
        layers += L
        count += H
        if not r.get("ok"):
            fail += H
        terms.append({"id": tid, "ok": bool(r.get("ok")), "at": e.get("at"),
                      "result_at": r.get("at"), "detail": r.get("detail", ""),
                      "stl": rel, "parts": [p["name"] for p in e.get("parts", [])],
                      "layers_max": int(round(float(L.max())))})

    rnd = lambda a: [[int(round(float(v))) for v in row] for row in a]
    return {
        "cell": CELL, "nx": NX, "ny": NY,
        "plate": [PLATE_X, PLATE_Y],
        "x0": -PLATE_X / 2, "y0": -PLATE_Y / 2,     # マス [0][0] の左下（Front 側）の角
        "layers": rnd(layers),
        "count": count.tolist(),
        "fail": fail.tolist(),
        "layers_max": int(round(float(layers.max()))) if terms else 0,
        "count_max": int(count.max()) if terms else 0,
        "terms": terms,
        "skipped": skipped,
        "film_last_change": film_ev,
        "note": "マスの値＝その 1mm² の上で起きた露光（剥離）の層数の累計。⚠ 代理値。剥離仕事そのものではない",
    }


if __name__ == "__main__":
    h = heat()
    out = os.path.join(_HERE, "_heat_dump.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in h.items() if k not in ("layers", "count", "fail")},
                  f, ensure_ascii=False, indent=1)
    print("terms", len(h["terms"]), "skipped", len(h["skipped"]),
          "layers_max", h["layers_max"], "count_max", h["count_max"])
