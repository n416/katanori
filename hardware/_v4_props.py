# -*- coding: utf-8 -*-
"""刷る向きの STL から支柱の位置を決めて hardware/_v4_props.scad を書き出す。
   🔒 2026-08-27 ユーザー「柱は輪郭に立てる。距離は近似」。つまみの deck_props と同じ形:
      天井の**輪郭**（外周・穴の縁）から 1.3mm の輪を 1 本目に、内側へ 3.0mm ずつ輪を重ねる。
      輪の上は約 3.0mm 間隔。距離は 8 近傍の近似でよい。
   🔴 2026-08-27 に 2 度作り直し、3 度目（この版・1 から書き直し）:
      ① 「深い順に置く」に勝手に置き換えて散らばった詰め物にした（指示違反）
      ② 柱を「真下がプレートまで空いている所」にしか立てられず、下に肉のある区間で
         輪が欠けた（座の左の弧・ユーザーが丸で指摘）。柱は**下の肉の上からも立てる**
      ③ 覆い残りで柱を間引く判定が置いた順に効いて、輪に穴が開いた。判定は置く前に固定する
   使い方: python hardware/_v4_props.py   （素の形は -D PROPS_OFF=true で焼く）
"""
import bisect, io, math, os, subprocess, sys
from scipy.ndimage import label as ndimage_label, maximum_filter as ndimage_maxfilt
import numpy as np

OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, '_pf'); os.makedirs(TMP, exist_ok=True)

# ---- 検査と同じ read_stl / zcolumns を**別の名前空間**へ読む ----
# 🔴 exec を自分のグローバルへ流すと、あちらの PITCH = 0.25 がこちらの 3.0 を上書きする
#    （ピッチ 0.25mm ＝ 全セルに柱・ブリッジで 23,917 本の事故）。ns 辞書に隔離する。
_ns = {}
_src = io.open(os.path.join(HERE, '_stl_preflight.py'), encoding='utf-8').read()
exec(_src[:_src.index("for p in sorted(glob.glob(")], _ns)
read_stl = _ns['read_stl']; zcolumns = _ns['zcolumns']

P = 0.25          # レイの間隔
DZ = 0.05         # 層の高さ（PRINT.md §1）
REACH = 2.0       # 支えからこれ以上離れた天井は持たれていない（ピッチ 3.0 の半分＋α）
PROP_D = 2.0      # 柱の**胴**の径（knob_v5 実績。φ1.4 は薄皮のまま面ごと剥がれた）
PROP_TIP = 0.5    # 🔒 2026-08-29 先の径。1.2 → 0.5。樹脂の常識は 0.3〜0.5 で、1.2 は太すぎた。
                  #   太い先は「保持は強いが折ったときの跡がでかい」。薄い天井では皮ごとえぐれる。
PROP_BITE = 0.1   # 🔒 同 食い込み。0.3 → 0.1。0.25mm の皮に 0.3 食い込ませて穴を開けた前科がある
MIN_GAP = 0.3     # 逃げ
PITCH = 2.4       # 🔒 2026-08-29 3.0 → 2.4。先を細くしたぶん本数で支える。
                  #   ⚠ 2.0 にはできない（胴 φ2.0 が接する）。2.4 なら隙間 0.4 で癒着の実績 0.36 の外
TIP_CLEAR = PROP_TIP / 2 + MIN_GAP   # 先が天井の縁から離れているべき量（0.55）
# 🔴 2026-08-29 それまで「胴の半径＋逃げ（1.3mm）だけ天井の輪郭から離れていること」を条件にしていた。
#   これは**胴を天井の輪郭で測っていた**もので、間違い。胴は天井の外へはみ出してよい（そこは空）。
#   効くのは ①先が天井に乗るか ②胴が部品にぶつからないか の 2 つ。②は柱の足元を
#   「胴の footprint の中でいちばん高い肉の上」に置くことで満たす（basemax）。
FILL_PITCH = 2.4  # 埋めの最小間隔（隣との隙間 0.4 ＝ 癒着の実績 0.36 の外）
RAFT_LINK = PITCH + 0.6   # ラフトで繋ぐ柱どうしの上限距離
# 🔴 2026-08-29 ラフトは「その層の柱を全部 1 つの hull() で包む」だった。輪の上の 2 本だけが
#   ラフト側に分類されると、**その 2 点を結ぶ棒**になり、部品の footprint を引いた残りが
#   会話ボタンの首の口を横切る膜として残った（ユーザー「なんか変な事になってませんか」）。
#   ⇒ 各柱の下に円を置き、**RAFT_LINK より近い柱どうしだけ**を繋ぐ。輪ならラフトも輪になる。
PARTS = ['top', 'hatch', 'bridge', 'strap_a', 'strap_b', 'strap_c', 'seat']
# 🔒 2026-08-28 ユーザー「その支柱はいらない。過去にノブでその形状はなにも無くても印刷できるの分かってる」。
#    ここに挙げた（部品, 天井の高さ）には柱もヒレも立てない。**実機の実績が検査の判定より優先する。**
#    🔴 2026-08-28 **この SKIP は空に戻した。** 外して刷ったら皿の底に穴が開いた（実機・ユーザー）。
#       私が「無くていい」と言った判断が外れ。皿の底は 0.25mm しかなく、82mm² を渡れなかった。
#       つまみの皿の実績はここには効かない（あちらの底はここより厚い）。
SKIP = set()   # seat = 充電基板の受け（2026-08-27・D-1 で独立した部品になった）


def bake(part):
    p = os.path.join(TMP, 'bare_%s.stl' % part)
    subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', p,
                    '-D', 'PROPS_OFF=true', '-D', 'part="print_%s"' % part,
                    os.path.join(HERE, 'case_v4.scad')], check=True, capture_output=True)
    return p


def bake_keepout(part):
    """空いていなければならない体積（case_v4.scad の keepout_<部品>）を刷る向きで焼く。
       中身が空の部品は OpenSCAD が STL を書かないので None を返す。"""
    p = os.path.join(TMP, 'ko_%s.stl' % part)
    if os.path.exists(p): os.remove(p)
    subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', p,
                    '-D', 'part="keepout_%s"' % part,
                    os.path.join(HERE, 'case_v4.scad')], capture_output=True)   # 空なら OpenSCAD は 1 で終わる
    return p if os.path.exists(p) else None


def dil(a):
    o = a.copy()
    o[1:, :] |= a[:-1, :]; o[:-1, :] |= a[1:, :]
    o[:, 1:] |= a[:, :-1]; o[:, :-1] |= a[:, 1:]
    return o


def band_chain(cells):
    """帯の升を**1 本の道**の順に並べる（開いた帯用）。
       🔒 2026-08-29 ユーザー「開いた図形の場合は…のループだと思います」。
       角度順は閉じた輪でしか使えない（重心のまわりを 1 周しない帯では順序が壊れる）。
       ⇒ 8 連結のグラフで BFS を 2 回。任意の升から最も遠い升 A を取り、A から最も遠い升 B を取ると
         A〜B が帯の両端になる（グラフの直径を取る定石）。A からの歩数で並べれば道の順になる。"""
    S = set(map(tuple, cells))

    def bfs(src):
        seen = {src: 0}; q = [src]
        while q:
            nxt = []
            for (a, b) in q:
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        c = (a + da, b + db)
                        if c in S and c not in seen:
                            seen[c] = seen[(a, b)] + 1; nxt.append(c)
            q = nxt
        return seen

    d0 = bfs(next(iter(S)))
    A = max(d0, key=d0.get)
    dA = bfs(A)
    return dA   # 升 → A からの歩数


def edt_mm(mask, p):
    """輪郭からの**本当の距離**（mm）。8 近傍のチェビシェフは対角で最大 √2 倍短く出るので使わない。
       🔒 2026-08-29 ユーザー「置けないなら置かないで良い」。置ける／置けないの判定に効く値なので
       近似では駄目。scipy があれば厳密、無ければ (1, √2) のチャンファ（誤差 4% 程度）。"""
    try:
        from scipy import ndimage
        return ndimage.distance_transform_edt(mask) * p
    except Exception:
        INF = 1e9
        d = np.where(mask, INF, 0.0)
        a, b = 1.0, 2 ** 0.5
        nu_, nv_ = d.shape
        for i in range(nu_):
            for j in range(nv_):
                if not mask[i, j]: continue
                v = d[i, j]
                if i > 0: v = min(v, d[i - 1, j] + a)
                if j > 0: v = min(v, d[i, j - 1] + a)
                if i > 0 and j > 0: v = min(v, d[i - 1, j - 1] + b)
                if i > 0 and j < nv_ - 1: v = min(v, d[i - 1, j + 1] + b)
                d[i, j] = v
        for i in range(nu_ - 1, -1, -1):
            for j in range(nv_ - 1, -1, -1):
                if not mask[i, j]: continue
                v = d[i, j]
                if i < nu_ - 1: v = min(v, d[i + 1, j] + a)
                if j < nv_ - 1: v = min(v, d[i, j + 1] + a)
                if i < nu_ - 1 and j < nv_ - 1: v = min(v, d[i + 1, j + 1] + b)
                if i < nu_ - 1 and j > 0: v = min(v, d[i + 1, j - 1] + b)
                d[i, j] = v
        return d * p


def erode8(m):
    o = m.copy()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == dy == 0: continue
            t = np.zeros_like(m)
            xs = slice(max(0, dx), m.shape[0] + min(0, dx)); xd = slice(max(0, -dx), m.shape[0] + min(0, -dx))
            ys = slice(max(0, dy), m.shape[1] + min(0, dy)); yd = slice(max(0, -dy), m.shape[1] + min(0, -dy))
            t[xd, yd] = m[xs, ys]
            o &= t
    return o


out = ['// 🔴 自動生成。手で直さない。作り直しは `python hardware/_v4_props.py`',
       '//    位置は刷る向きの素の STL（PROPS_OFF=true）の天井の輪郭から決めている。',
       'PROP_D2 = %.2f; PROP_TIP2 = %.2f; PROP_NECK2 = 0.8; PROP_BITE2 = %.2f;' % (PROP_D, PROP_TIP, PROP_BITE),
       'module one_prop(x, y, base, h) translate([x, y, base]) {',
       '    cylinder(d = PROP_D2, h = max(0.01, h - base - PROP_NECK2), $fn = 16);',
       '    translate([0, 0, max(0, h - base - PROP_NECK2)])',
       '        cylinder(d = PROP_TIP2, h = min(PROP_NECK2, h - base) + PROP_BITE2, $fn = 12);',
       '}', '']
rep = []
def sq_dilate(a, r):
    o = a.copy()
    for _ in range(r):
        n = o.copy()
        n[1:, :] |= o[:-1, :]; n[:-1, :] |= o[1:, :]
        n[:, 1:] |= o[:, :-1]; n[:, :-1] |= o[:, 1:]
        o = n
    return o


n_dropped = {}
n_narrow = {}   # 天井が狭すぎて柱が縁からはみ出すので置かなかった数
THIN_ABOVE = 0.8   # 🔒 2026-08-29 ユーザー「柱には弱さ、強さがある。特定の柱の強さが上の構造物を
                   #   破壊するようなものなら立てちゃいけない」。柱の先は φPROP_TIP で 0.1 食い込む。
                   #   その上の肉がこれより薄いと、剥離の力と折るときの力で皮が抜ける（2026-08-28 に
                   #   0.25mm の皿の底で実際に穴が開いた）。⇒ **立てない。そして警告する。**
alerts = []     # （部品, 天井 Z, 面積 mm2, 上の肉 mm, 渡る距離 mm）浮いていて薄い所
CLEAR = TIP_CLEAR   # 柱の芯が天井の縁から離れていなければならない量（先の半径＋逃げ）
for part in PARTS:
    tris = read_stl(bake(part))
    col, zs, ze, us, vs, nu, nv = zcolumns(tris, P)
    z0 = zs.min(); cell = P * P
    # 🔴 2026-08-27 ユーザー「ネジ穴や回転部分にサポートが立っている。これはまずい」。
    #    空いていなければならない体積（keepout）に柱の胴（φPROP_D）＋逃げ MIN_GAP が
    #    1mm³ でも入るなら、その柱は**立てない**。天井は持たれないまま残る（＝短いブリッジになる）。
    kp = bake_keepout(part)
    KR = int(np.ceil((PROP_D / 2 + MIN_GAP) / P))     # 柱の胴＋逃げ（セル）
    if kp is None:
        kcol = kzs = kze = None
    else:
        ktris = read_stl(kp)
        kcol, kzs, kze, kus, kvs, knu, knv = zcolumns(ktris, P)
        # keepout の格子は部品の格子と原点が違う → 部品の格子の座標へ載せ替える
        ki = np.clip(np.searchsorted(us, kus[kcol // knv]) - 1, 0, nu - 1)
        kj = np.clip(np.searchsorted(vs, kvs[kcol % knv]) - 1, 0, nv - 1)
        kcol = ki * nv + kj
    kcache = {}

    def keepout_at(z):
        """高さ z で「柱を立てられない」セルの地図（keepout を柱の太さ分ふくらませた物）"""
        if kcol is None: return None
        key = round(z, 3)
        if key not in kcache:
            m = np.zeros(nu * nv, bool)
            m[kcol[(kzs <= z) & (kze > z)]] = True
            kcache[key] = sq_dilate(m.reshape(nu, nv), KR)
        return kcache[key]

    def blocked(i, j, base, h):
        """base〜h のどこかで keepout に触るなら True"""
        if kcol is None: return False
        z = base + 0.05
        while z < h:
            m = keepout_at(round(z, 2))
            if m is not None and m[i, j]: return True
            z += 0.2
        return False
    nr = int(round(REACH / P))
    picks = []
    # 🔴 間隔と覆いの帳簿は**層ごと**に取る。全層で 1 つの帳簿にすると、会話ボタンの受け（天井 6.20）の真下に
    #    皿（天井 2.25）の柱が居るだけで「もう近くに柱がある」と間引かれ、6.20 の天井が丸ごと持たれないまま
    #    「残り 0.0」と報告された（2026-08-27）。別の層の柱は別の高さの物で、同じ xy に重なってよい（積み重なるだけ）。
    ps2 = (PITCH / P) ** 2; fs2 = (FILL_PITCH / P) ** 2
    for lay in np.unique(np.round((zs - z0) / DZ).astype(int)):
        if lay <= 0: continue
        h = z0 + lay * DZ; z = h + DZ * 0.5
        if (part, round(h, 2)) in SKIP: continue
        O = np.zeros(nu * nv, bool); O[col[(zs <= z) & (ze > z)]] = True
        S = np.zeros(nu * nv, bool); S[col[(zs <= z - DZ) & (ze > z - DZ)]] = True
        Ngf = O & ~S
        if Ngf.sum() * cell < 1.0: continue
        Og = O.reshape(nu, nv); Ng = Ngf.reshape(nu, nv)
        reach = (S & O).reshape(nu, nv)
        for _ in range(nr): reach = dil(reach) & Og
        need = Ng & ~reach
        if need.sum() * cell < 0.5: continue
        # 柱の足元 = その柱の真下にある一番高い肉の上面（無ければプレート 0）
        sel = ze <= h - 0.02
        tmp = np.zeros(nu * nv)
        np.maximum.at(tmp, col[sel], ze[sel])
        basegrid = tmp.reshape(nu, nv)
        # 🔒 2026-08-29 柱の足元は「**胴の footprint の中でいちばん高い肉**の上」に置く。
        #   こうすると胴（φPROP_D）が部品に食い込まない。天井の輪郭で胴の太さを測る必要が無くなり、
        #   胴が天井の外へはみ出しても（そこが空なら）柱を立てられる。
        _rr = int(np.ceil((PROP_D / 2) / P))
        _yy, _xx = np.ogrid[-_rr:_rr + 1, -_rr:_rr + 1]
        _disc = (_yy ** 2 + _xx ** 2) <= _rr ** 2
        basemax = ndimage_maxfilt(basegrid, footprint=_disc, mode='nearest')
        # 天井の上に乗っている肉の厚み（その升で z から上へ続く塊の高さ）
        tmp2 = np.zeros(nu * nv)
        sel2 = (zs <= z) & (ze > z)
        np.maximum.at(tmp2, col[sel2], ze[sel2])
        above = (tmp2 - h).reshape(nu, nv)
        # 🔴 2026-08-29 距離は**2 つ**要る（ユーザー「この 2 本が外周側に行ってないのが変です」）。
        #   輪を刻むのは **外周（壁になる側）からの距離**。1 つの距離で測ると、皿の床のような
        #   輪の天井では「外周から 1.3」と「穴の縁から 1.3」が同じ輪に混ざり、柱が内外に散った。
        #   柱が入るかの判定は **どの縁からも** の距離（穴の縁からはみ出させないため）。
        comp_outer0 = ~Ng
        edge0 = np.zeros_like(comp_outer0); edge0[0, :] = edge0[-1, :] = edge0[:, 0] = edge0[:, -1] = True
        seed0 = comp_outer0 & edge0
        while True:
            nxt0 = dil(seed0) & comp_outer0
            if (nxt0 == seed0).all(): break
            seed0 = nxt0
        comp_outer = seed0
        dist = edt_mm(~comp_outer, P)      # 外周からの距離
        clr = edt_mm(Ng, P)                # どの縁からも（＝柱が入るか）
        dmax = dist[Ng].max() if Ng.any() else 0.0
        # 判定は**置く前に固定**: 「持たれない天井が届く範囲に在るか」を静的な地図で見る
        needD = need.copy()
        for _ in range(nr + int(round(PITCH / P))): needD = dil(needD)
        # 🔒 2026-08-27 ユーザー「最も外の輪郭以外にはラフトを貼って」= 手本の deck_props と同じ:
        #    内側の支柱は 0.3mm のラフトに載せて 1 枚で剥がす。プレート直立ちは**外周の輪郭の輪**だけ
        #    （穴の縁の輪は「外周」ではないのでラフト側）。外周かどうかは、天井の外の空白のうち
        #    グリッドの縁とつながっている領域（comp_outer）に近いかで見分ける。
        # comp_outer は上で作ってある
        n_ring = n_fill = 0
        placed = []

        def usable(i, j):
            """その升に柱を立てられるか（立てる意味があるか）"""
            if not needD[i, j]: return False                    # この辺りの天井は縁が持っている
            if clr[i, j] < CLEAR: return False                  # 縁からはみ出す ＝ 置けない
            if above[i, j] < THIN_ABOVE: return False           # 🔒 上が薄い＝柱が破る。立てない
            if h - basemax[i, j] < 0.4: return False            # 下の肉がほぼ届いている
            if blocked(i, j, basemax[i, j], h): return False     # ネジ・ナット・軸・回る物
            if any((i - a) ** 2 + (j - b) ** 2 < ps2 for a, b in placed): return False
            return True

        # 🔴 2026-08-29 天井は 1 つの層に**複数**あることがある（ハッチ・帯）。それを 1 枚の絵として
        #   まとめて帯にすると、角度順は別々の天井の点を交互に拾い、BFS の鎖は 1 つの天井しか歩かない。
        #   結果、弧長が滅茶苦茶になって柱どうしが 1.16mm（φ2.0 が食い込む）まで詰まった。
        #   ⇒ **繋がっている天井ごとに**分けて輪を作る。placed は共通なので天井をまたいだ間隔も守られる。
        _lab, _nlab = ndimage_label(Ng)
        for _k in range(1, _nlab + 1):
            Nk = (_lab == _k)
            if Nk.sum() * cell < 0.5: continue
            if not (need & Nk).any(): continue
            ci, cj = np.argwhere(Nk).mean(axis=0)
            dmax_k = dist[Nk].max()
            # 🔴 2026-08-29 1 本目の輪の位置。先を細くして CLEAR が 1.3 → 0.55 になった結果、
            #   輪が縁から 0.80mm の所に来て**壁がもともと支えている帯**と重なり、
            #   皿の残りが 0.8 → 6.4mm² に悪化した。壁は縁から REACH（2.0mm）まで持つので、
            #   1 本目はその境目あたりに置く。ただし細い天井ではそこまで入らないので、
            #   その天井の最大距離の 7 割で頭打ちにする。
            # 🔒 2026-08-29 ユーザー「広い天井なのか、狭い天井なのか判断させたら？」。
            #   柱 1 本が面倒を見られるのは半径 REACH（2.0mm）。縁も内側 REACH までは自分で持つ。
            #   ⇒ 縁からの最大距離 dmax で場を分ける:
            #     ・dmax ≤ REACH        … 縁だけで届く。輪は要らない
            #     ・dmax ≤ 2*REACH      … **狭い天井**。真ん中に輪 1 本で端から端まで届く
            #     ・それ以上            … **広い天井**。縁から 2*REACH ごとに輪を重ねる
            #       （輪 1 本が [r−REACH, r+REACH] を持つので、2*REACH 刻みで隙間なく繋がる）
            #   🔴 前は広い/狭いを見ずに同じ刻み方をしていたので、広い天井で輪が足りず
            #     （天板 21mm² 残り）、狭い天井では縁に寄りすぎていた（皿 6.4mm² 残り）。
            if dmax_k <= REACH:
                rads = []
            elif dmax_k <= 2 * REACH:
                rads = [dmax_k / 2]
            else:
                rads = []
                rr = 2 * REACH
                while rr <= dmax_k:
                    rads.append(rr); rr += 2 * REACH
                if not rads or dmax_k - rads[-1] > REACH:
                    rads.append(dmax_k * 0.98)
            rads = [max(CLEAR + P, x) for x in rads]
            for ring_idx, r in enumerate(rads):
                band = np.argwhere(Nk & (np.abs(dist - r) <= P))
                if len(band) >= 3:
                    # ---- 輪郭を 1 本の閉じた折れ線にする（角度で刻んで代表点を 1 つずつ）----
                    # ---- 閉じた輪か、開いた道か ----
                    #   重心のまわりを 1 周しているか（角度の隙間が 30° 以下か）で見分ける。
                    degs = np.degrees(np.arctan2(band[:, 1] - cj, band[:, 0] - ci)) % 360
                    occ = sorted(set((degs // 2).astype(int)))
                    gapdeg = max((occ[(k + 1) % len(occ)] - occ[k]) % 180 for k in range(len(occ))) * 2
                    closed = gapdeg <= 30
                    if closed:
                        ang = np.arctan2(band[:, 1] - cj, band[:, 0] - ci)
                        NB = 720
                        bins = ((ang + np.pi) / (2 * np.pi) * NB).astype(int) % NB
                        best = {}
                        for k in range(len(band)):
                            i2, j2 = int(band[k][0]), int(band[k][1]); b = int(bins[k])
                            e = abs(dist[i2, j2] - r)
                            if b not in best or e < best[b][0]: best[b] = (e, (i2, j2))
                        ring = [best[b][1] for b in sorted(best)]
                    else:
                        steps = band_chain(band)          # 升 → 端 A からの歩数
                        best = {}
                        for c, d0 in steps.items():
                            e = abs(dist[c[0], c[1]] - r)
                            if d0 not in best or e < best[d0][0]: best[d0] = (e, c)
                        ring = [best[d0][1] for d0 in sorted(best)]
                    # 🔒 2026-08-29 ユーザーの手順どおりに置く:
                    #   ①壁のある外周を調べ ②その長さを調べ ③等間隔の計算をし ④実際に置いてみて
                    #   ⑤**最後の柱と最初の柱の距離**を測って何本足りない／要らないかを出し ⑥繰り返す。
                    #   🔴 前は「弧長 ÷ ピッチ」で本数を決めて減らすだけだった。帯の折れ線は階段状で
                    #     弧長が実長の約 2 倍に出るため、本数が倍になり柱が癒着した（隣まで 1.25mm）。
                    #     置いてから閉じ目を測れば、折れ線の長さが不正確でも収束する。
                    def _d(a, b):
                        return P * math.hypot(a[0] - b[0], a[1] - b[1])

                    # ---- 周長は輪郭から**一度だけ**測る（置いた柱の間隔からは測らない）----
                    # 🔴 2026-08-29 前は「歩幅 s で歩いて置く → 置いた点の間隔を足して L を出す →
                    #   s = L/n を作り直す」だった。階段状の折れ線では歩くたびに s を少し行き過ぎるので、
                    #   その行き過ぎが次の s に足し込まれ、3.0 → 4.05 → 4.5 と**離れていった**。
                    #   ⇒ L を固定し、**n を 1 ずつ増やして L/n が狙いのピッチ以下になった所で止める**
                    #     （ユーザー「逆に 1 個ずつ増やして近似に近くなるまで置いて行きますか？」）。
                    #     位置は弧長 t = k・L/n を折れ線の**辺の途中まで補間**して取るので、
                    #     閉じ目は定義から L/n になり、余りも不足も出ない。
                    # 🔴 2026-08-29 折れ線をそのまま足すと、升の階段のギザギザで**周長が実長の約 2 倍**に
                    #   出る（角度 720 刻みの点を 1 つずつ結ぶと、1 歩ごとに 0/0.25mm の段が入るため）。
                    #   ⇒ 1 周が 72 点くらいになるまで間引いてから測る。5° の弦は弧の 0.03% 短いだけ。
                    if len(ring) > 96:
                        ring = ring[::max(1, len(ring) // 72)]
                    # 閉じた輪は最後から最初へ戻る辺を足す。開いた道は足さない
                    segs = ([_d(a, c) for a, c in zip(ring, ring[1:] + ring[:1])] if closed
                            else [_d(a, c) for a, c in zip(ring, ring[1:])] + [0.0])
                    cum = [0.0]
                    for t in segs: cum.append(cum[-1] + t)
                    L = cum[-1]

                    def at_arc_f(t):
                        """弧長 t の点（辺の途中は線形補間）。升の番号のまま**小数で**返す"""
                        t %= L
                        k = min(bisect.bisect_right(cum, t) - 1, len(ring) - 1)
                        a = ring[k]; c = ring[(k + 1) % len(ring)]
                        f = 0.0 if segs[k] <= 0 else (t - cum[k]) / segs[k]
                        return (a[0] + (c[0] - a[0]) * f, a[1] + (c[1] - a[1]) * f)

                    def at_arc(t):
                        fx, fy = at_arc_f(t)
                        return (int(round(fx)), int(round(fy)))

                    # 🔒 2026-08-29 開いた道は**両端に柱を置く**ので、間隔は L/(n−1)。
                    #   終点の余り／不足は定義から 0 になる（閉じた輪の閉じ目と同じ考え方）。
                    # 🔴 2026-08-29 本数は「L/n が PITCH **以下**になるまで増やす」だった。これだと
                    #   間隔が PITCH を下回る（L=8.0・PITCH=2.4 → n=4 → 2.0mm）。φ2.0 の胴が接する。
                    #   ⇒ **PITCH を下回らない側**で取る。ただし空きすぎると天井が持たれないので、
                    #     間隔が 2*REACH（4.0mm＝隣の柱の受け持ちが繋がる限界）を超えたら増やす。
                    if closed:
                        n = max(1, int(L // PITCH))
                        if L / n > 2 * REACH: n = int(math.ceil(L / (2 * REACH)))
                        step = L / n
                    else:
                        n = max(2, int(L // PITCH) + 1)
                        if L / (n - 1) > 2 * REACH: n = int(math.ceil(L / (2 * REACH))) + 1
                        step = L / (n - 1)
                    laid = []
                    for k in range(n):
                        t = k * step
                        q = at_arc(t); qf = at_arc_f(t)
                        # ずらした先が隣に寄らないように、**この輪の間隔 step**を基準に見る。
                        #   🔴 2026-08-29 ここを一度 PITCH 基準にしたら、閉じ目の 1 対（ちょうど step）が
                        #     誤爆して穴が開いた。逆に条件を全部外したら、ずらしで 0.42mm まで詰まった。
                        #     正しい基準は PITCH ではなく step。等間隔の点（1.0×step）は必ず通る。
                        # 🔴 2026-08-29 間隔の判定を**候補のマス**でしていた。柱は補間した実座標で
                        #   出すので、両側で最大 0.35mm ずつずれて 2.4 の狙いが 2.04 まで詰まっていた。
                        #   ⇒ 判定も**実座標どうし**で行う。laid はこの輪の中、placed は他の輪と埋め。
                        def _farf(cf):
                            # 輪の中の点はちょうど step 間隔で作ってあるので、掛け率は要らない。
                            #   0.9 を掛けていたぶん（2.4 → 2.16）が最後まで残っていた。
                            if any(_d(cf, f[1]) < step - 1e-6 for f in laid): return False
                            if any(_d(cf, pp) < PITCH - 1e-9 for pp in placed): return False
                            return True

                        if not (usable(*q) and _farf(qf)):       # 弧の上で ±step/2 だけ探す
                            alt = None
                            for dt in np.arange(P, step / 2 + 1e-9, P):
                                for sgn in (1, -1):
                                    c = at_arc(t + sgn * dt); cf = at_arc_f(t + sgn * dt)
                                    if usable(*c) and _farf(cf): alt = (c, cf); break
                                if alt: break
                            if alt is None:
                                n_narrow[part] = n_narrow.get(part, 0) + 1
                                continue                        # 置けない所は空けたまま（輪全体は崩さない）
                            q, qf = alt
                        # 🔴 2026-08-29 ここで「既存の柱から PITCH*0.9 以上」を要求していた。位置は
                        #   L/n で**等間隔に作ってある**のに、n は L/n ≤ PITCH になるまで増やすので
                        #   間隔はちょうど 2.7mm 付近。最後の 1 本と最初の 1 本がその値ちょうどになり、
                        #   丸めで落ちて**閉じ目だけ 4.93mm の穴**が開いていた（ユーザー「絶対おかしい」）。
                        #   等間隔に作った点を距離で篩い直さない。見るのは「立てられるか」だけ。
                        # 🔒 2026-08-29 ユーザー「2 個置く、3 個置く、4 個置く。すべてのタイミングで
                        #   間隔は均等になるアルゴリズムでは」→ そのとおりで、位置は t = k・L/n。
                        #   🔴 ただし柱の座標を升（0.25mm）に丸めていたので、間隔が 2.47〜3.01 に散っていた。
                        #     柱は升に乗る必要が無い（升は「立てられるか」を見るためだけ）ので、
                        #     **丸めずに補間した実座標で出す**。
                        laid.append((q, qf))
                    for (i2, j2), (fx, fy) in laid:
                        # 🔒 2026-08-29 ユーザー「そしてこの外周の柱には絶対ラフトをつけてはいけない」。
                        #   🔴 距離の値（dist <= CLEAR + P）で見ていたので、同じ輪の上でも歩きで 1.80mm まで
                        #     振れた 2 本がラフト側に落ちていた。**輪の番号**で決める。0 番＝外周。
                        is_outer = (ring_idx == 0)
                        on_raft = (not is_outer) and basemax[i2, j2] < 0.01
                        picks.append((us[0] + fx * P, vs[0] + fy * P, basemax[i2, j2], h, on_raft))
                        # 🔴 2026-08-29 間隔の判定に**丸めたマスの番号**を入れていた。柱は補間した
                        #   実座標で出すので、最大 0.35mm ぶん詰まって出ていた（2.4 の狙いに対し 1.97）。
                        #   判定にも実座標（小数のマス番号）を入れる。
                        placed.append((fx, fy))
                        n_ring += 1
                pass
        # 覆い残りを埋める（深い所から・間隔 2.4 まで詰めてよい）
        cov = reach.copy()
        for _pi, _pj in placed:
            i = int(round(_pi)); j = int(round(_pj))
            cov[max(0, i - nr):min(nu, i + nr + 1), max(0, j - nr):min(nv, j + nr + 1)] = True
        rem = need & ~cov
        for i, j in sorted(np.argwhere(rem).tolist(), key=lambda c: -dist[c[0], c[1]]):
            if not rem[i, j]: continue
            if clr[i, j] < CLEAR:                                   # 🔒 同上。埋めにも同じ門を付ける
                n_narrow[part] = n_narrow.get(part, 0) + 1; continue
            if above[i, j] < THIN_ABOVE: continue                   # 🔒 上が薄い＝柱が破る
            if h - basemax[i, j] < 0.4: continue
            if blocked(i, j, basemax[i, j], h):                     # 持たれないまま残す（残りの面積に出る）
                n_dropped[part] = n_dropped.get(part, 0) + 1; continue
            if any((i - a) ** 2 + (j - b) ** 2 < fs2 for a, b in placed): continue
            # 🔒 2026-08-29 埋めの柱にも同じ規則。外周の輪の帯に居る柱にはラフトを付けない
            #   （ユーザー「この外周の柱には絶対ラフトをつけてはいけない」）
            #   2 本目の輪が入らない幅（＝外周の輪しか無い天井）なら、その柱は全部「外周」扱い。
            _outer = dist[i, j] < CLEAR + P + PITCH / 2
            picks.append((us[i], vs[j], basemax[i, j], h, (not _outer) and basemax[i, j] < 0.01)); placed.append((i, j))
            rem[max(0, i - nr):min(nu, i + nr + 1), max(0, j - nr):min(nv, j + nr + 1)] = False
            n_fill += 1
        thin_rem = rem & (above < THIN_ABOVE)
        if thin_rem.sum() * cell >= 1.0:
            dsup = edt_mm(~(S.reshape(nu, nv)), P)
            alerts.append((part, h, thin_rem.sum() * cell, float(above[thin_rem].max()), float(dsup[thin_rem].max())))
        rep.append((part, h, need.sum() * cell, n_ring, n_fill, rem.sum() * cell))
    BARE = {'top': 'top_print()', 'hatch': 'hatch_print()',
            'bridge': 'translate([0, 0, -(BAT_Z - BRG_T)]) brg_v4()',
            'strap_a': 'strap_print(STRAP_BANDS[0])', 'strap_b': 'strap_print(STRAP_BANDS[1])',
            'strap_c': 'strap_print(STRAP_BANDS[2])',
            'seat': 'translate([TC4_ZT, 0, -LW_X]) rotate([0, -90, 0]) tc_seat4()'}[part]
    # 🔴 2026-08-29 同じ座標に 2 本出ることがある（開いた道の端と埋めが重なる等）。
    #   union では消えるが、ラフトの点も二重になるので、出す直前に落とす。
    seen_xy = set(); uniq = []
    for pk in picks:
        key = (round(pk[0], 2), round(pk[1], 2), round(pk[3], 2))
        if key in seen_xy: continue
        seen_xy.add(key); uniq.append(pk)
    picks = uniq
    out.append('module props_%s() { %s }' % (part, ' '.join(
        'one_prop(%.2f, %.2f, %.2f, %.2f);' % p[:4] for p in picks)))
    layers = {}
    for x, y, b, h, on_raft in picks:
        if on_raft: layers.setdefault(h, []).append((x, y))
    if layers:
        _c = lambda x, y: 'translate([%.2f, %.2f]) circle(d = PROP_D2, $fn = 16);' % (x, y)
        shapes = []
        for pts in layers.values():
            for k, (x, y) in enumerate(pts):
                shapes.append(_c(x, y))
                for x2, y2 in pts[k + 1:]:
                    if (x - x2) ** 2 + (y - y2) ** 2 <= RAFT_LINK ** 2:
                        shapes.append('hull() { %s %s }' % (_c(x, y), _c(x2, y2)))
        hulls = ' '.join(shapes)
        out.append('module raft_%s() difference() {' % part)
        out.append('    linear_extrude(0.3) union() { %s }' % hulls)
        out.append('    // 部品がプレートに着く足の周り 0.5 を空ける（手本のラフト ↔ ピンの隙間 0.4 と同等）')
        out.append('    translate([0, 0, -0.1]) linear_extrude(0.6) offset(r = 0.5) projection(cut = true) translate([0, 0, -0.15]) %s;' % BARE)
        out.append('}')
    else:
        out.append('module raft_%s() {}' % part)
io.open(os.path.join(HERE, '_v4_props.scad'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('%-9s %7s %12s %6s %6s %12s' % ('部品', '天井Z', '要る面積', '輪', '埋め', '残り'))
for r in rep: print('%-9s %7.2f %9.1f mm2 %6d %6d %9.1f mm2' % r)
if alerts:
    print()
    print('🔴 **浮いていて薄い天井**（柱を立てると破るので立てていない。設計側で直す所）')
    print('%-9s %7s %11s %10s %10s' % ('部品', '天井Z', '面積', '上の肉', '渡る距離'))
    for a in alerts:
        print('%-9s %7.2f %8.1f mm2 %7.2f mm %7.2f mm' % a)
    print()
print('天井が狭くて置けなかった柱:',
      ' '.join('%s %d' % kv for kv in sorted(n_narrow.items())) or 'なし')
print('keepout（ネジ・ナット・軸・回る物）で落とした柱:',
      ' '.join('%s %d' % kv for kv in sorted(n_dropped.items())) or 'なし')
