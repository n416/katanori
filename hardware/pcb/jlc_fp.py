# -*- coding: utf-8 -*-
"""JLCPCB が実装に使う足形（LCSC の品番ごとの EasyEDA の足形）を読んで、KiCad の足形と重ねる。

JLCPCB は CPL の角度を **自分の足形の 0 度** に足し、CPL の座標に **自分の足形の原点** を置く。
KiCad の足形と 0 度の向きや原点が違えば、その差だけ回って・ずれて載る。
差は足形の名前ではなく **品番ごと** に決まる（同じ SOT-23 でも品番で足形が違う）。

⭐ 2026-09-18: それまでは公開の補正表（JLCKicadTools の cpl_rotations_db.csv）を足形の名前で当てていたが、
   いまの JLCPCB の足形と重ねると U1・Q2・Q31・K31・J13 の 5 個が 90° / 180° 回って載る値だった
   （SOT-23 は表の −90 ではなく 180、HRO の USB-C は表の 180 ではなく 0）。表は足形が作り直される前の値とみる。
   ⇒ 表はやめて、品番の足形そのものから角度と原点のずれを出す。

足形は jlc_fp/<LCSC>.json に取っておく（一次の値。取り直すときはファイルを消して回す）。
"""
import json
import math
import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "jlc_fp"
URL = "https://easyeda.com/api/products/{}/components?version=6.4.19.5"

# 極性のある 2 本足: KiCad の LED・ダイオードの足形は 1 = K（カソード）・2 = A。
# EasyEDA は品番ごとに番号の振り方が違う（LED2〜4 は 1 = A）ので、**番号ではなく記号のピン名**で合わせる
KICAD_POLAR = {"LED_": {"1": "K", "2": "A"}, "D_": {"1": "K", "2": "A"}}
EASY_POLAR = {"K": "K", "-": "K", "A": "A", "+": "A"}


def fetch(lcsc):
    """品番の EasyEDA の部品を読む。無ければ取ってきて取っておく。足形が無い品番は None。
    ⚠ Python の urllib からは名乗りを変えても 403 で断られる（2026-09-18）。curl そのものなら通るので curl で取る"""
    CACHE.mkdir(exist_ok=True)
    p = CACHE / f"{lcsc}.json"
    if not p.exists():
        subprocess.run(["curl", "-sf", "-m", "30", "-o", str(p), URL.format(lcsc)], check=True)
    j = json.loads(p.read_text(encoding="utf-8"))
    return j["result"] if j.get("result") else None


def easy_pads(res):
    """→ (足形の名前, {パッド番号: [(x, y), …]}, {パッド番号: 記号のピン名})。mm・Y は下向き・原点は足形の原点。"""
    ds = res["packageDetail"]["dataStr"]
    ox, oy = float(ds["head"]["x"]), float(ds["head"]["y"])
    pads = {}
    for s in ds["shape"]:
        if s.startswith("PAD~"):
            f = s.split("~")               # PAD~形~x~y~幅~高さ~層~ネット~番号~…（単位は 10 mil）
            pads.setdefault(f[8], []).append(((float(f[2]) - ox) * 0.254, (float(f[3]) - oy) * 0.254))
    names = {}
    for s in res["dataStr"]["shape"]:
        if s.startswith("P~"):
            seg = s.split("^^")
            try:
                names[seg[0].split("~")[3]] = seg[3].split("~")[4]
            except IndexError:
                pass
    return res["packageDetail"]["title"], pads, names


def rot(p, a):
    """Y 下向きの座標で、画面の上で反時計回りに a 度（KiCad の足形の回転と同じ向き）。"""
    a = math.radians(a)
    x, y = p
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def pair(fp, kpads, epads, names):
    """KiCad のパッド番号 → EasyEDA のパッド番号。極性のある 2 本足はピン名で、ほかは同じ番号で。"""
    for pre, kfun in KICAD_POLAR.items():
        if fp.startswith(pre):
            efun = {EASY_POLAR.get(names.get(n, ""), ""): n for n in epads}
            if set(kfun.values()) <= set(efun):
                return {k: efun[f] for k, f in kfun.items()}
            raise SystemExit(f"{fp}: EasyEDA のピン名 {names} から K／A が決まらない")
    return {k: k for k in kpads if k in epads}


def solve(fp, kpads, lcsc):
    """KiCad の足形（{番号: [(x, y), …]}・Y 下向き・回転前）を品番の足形に重ねる。

    → dict(corr=CPL に足す角度, d=(dx, dy) KiCad の足形を回した後の EasyEDA の原点の位置（Y 下向き）,
           err=重ねたときの最大の食い違い mm, n=重ねたパッド数, title=EasyEDA の足形名)
    足形が無い品番は None。向きが 1 つに決まらなければ止める。
    """
    res = fetch(lcsc)
    if res is None:
        return None
    title, epads, names = easy_pads(res)
    m = pair(fp, kpads, epads, names)
    if len(m) < 2:
        raise SystemExit(f"{lcsc} {fp}: 重ねられるパッドが {len(m)} 個しか無い")
    tries = []
    for th in (0, 90, 180, 270):
        # 対応するパッドどうしの差の平均を原点のずれにして、残りの食い違いを測る
        ks = [(k, e) for k, e in m.items()]
        diffs = []
        for k, e in ks:
            kr = [rot(p, th) for p in kpads[k]]
            ep = epads[e]
            # 同じ番号が複数あるとき（シェルの足など）は、最も近い組を取る
            best = min(((a, b) for a in kr for b in ep), key=lambda ab: math.dist(*ab))
            diffs.append((best[1][0] - best[0][0], best[1][1] - best[0][1]))
        dx = sum(d[0] for d in diffs) / len(diffs)
        dy = sum(d[1] for d in diffs) / len(diffs)
        err = max(math.hypot(d[0] - dx, d[1] - dy) for d in diffs)
        tries.append((err, th, (dx, dy)))
    tries.sort()
    err, th, d = tries[0]
    # 食い違いは足形どうしのパッドの置き方の違い（ランドの外への伸び）で出る。
    #   onsemi C86182 の SOT-23（Q1 の候補だった品）は KiCad よりパッドの中心が 0.30 外で 0.40・
    #   この板の品では 0.28 まで（2026-09-18）。
    #   向きを 90° 間違えると SOT-23 でも 2.07 になるので、「0.5 以下」かつ「次の向きより 1.0 以上よく合う」で決める
    if err > 0.5 or tries[1][0] - err < 1.0:
        raise SystemExit(f"{lcsc} {fp}: 向きが 1 つに決まらない（{[(round(e, 2), t) for e, t, _ in tries]}）")
    return dict(corr=(-th) % 360, d=d, err=err, n=len(m), title=title)


def place_holes(cpl_x, cpl_y, cpl_rot, lcsc):
    """CPL の 1 行どおりに置いたときの、JLCPCB の足形の穴（HOLE・位置決めの突起）の位置 → [(x, y), …]"""
    ds = fetch(lcsc)["packageDetail"]["dataStr"]
    ox, oy = float(ds["head"]["x"]), float(ds["head"]["y"])
    out = []
    for s in ds["shape"]:
        if s.startswith("HOLE~"):
            f = s.split("~")               # HOLE~x~y~半径~…
            out.append(_up(((float(f[1]) - ox) * 0.254, (float(f[2]) - oy) * 0.254), cpl_x, cpl_y, cpl_rot))
    return out


def _up(p, cpl_x, cpl_y, cpl_rot):
    # EasyEDA の Y 下向きを Y 上向きへ（y → −y）。Y 上向きでの反時計回り
    u, v = p[0], -p[1]
    a = math.radians(cpl_rot)
    return (cpl_x + u * math.cos(a) - v * math.sin(a), cpl_y + u * math.sin(a) + v * math.cos(a))


def place(cpl_x, cpl_y, cpl_rot, lcsc):
    """CPL の 1 行どおりに JLCPCB の足形を置いたときの、パッドの板の上の位置（CPL の座標・Y 上向き）。
    → {EasyEDA のパッド番号: [(x, y), …]}"""
    _, epads, _ = easy_pads(fetch(lcsc))
    out = {}
    for n, ps in epads.items():
        for p in ps:
            out.setdefault(n, []).append(_up(p, cpl_x, cpl_y, cpl_rot))
    return out
