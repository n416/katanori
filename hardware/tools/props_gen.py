# -*- coding: utf-8 -*-
"""刷る向きの STL から支柱の位置を決めて hardware/parts/props_v5_gen.scad を書き出す（v5。frozen/v1-v4/_v4_props.py の移植・2026-09-05）。
   いま相手にするのは帯 A/B/C だけ（PARTS）。ほかの部品の刷る向きが決まったら PARTS と BARE に足す。
   🔒 2026-08-27 ユーザー「柱は輪郭に立てる。距離は近似」。つまみの deck_props と同じ形:
      天井の**輪郭**（外周・穴の縁）から 1.3mm の輪を 1 本目に、内側へ 3.0mm ずつ輪を重ねる。
      輪の上は約 3.0mm 間隔。距離は 8 近傍の近似でよい。
   🔴 2026-08-27 に 2 度作り直し、3 度目（この版・1 から書き直し）:
      ① 「深い順に置く」に勝手に置き換えて散らばった詰め物にした（指示違反）
      ② 柱を「真下がプレートまで空いている所」にしか立てられず、下に肉のある区間で
         輪が欠けた（座の左の弧・ユーザーが丸で指摘）。柱は**下の肉の上からも立てる**
      ③ 覆い残りで柱を間引く判定が置いた順に効いて、輪に穴が開いた。判定は置く前に固定する
   使い方: python hardware/tools/props_gen.py   （素の形は -D PROPS_OFF=true で焼く）
"""
import bisect, io, math, os, subprocess, sys
from scipy.ndimage import label as ndimage_label, maximum_filter as ndimage_maxfilt, minimum_filter as ndimage_minfilt
from scipy.ndimage import distance_transform_edt as ndimage_edt
import numpy as np

OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.com')
HERE = os.path.dirname(os.path.abspath(__file__))          # hardware/tools
HW = os.path.dirname(HERE)                                   # hardware
SCAD = os.path.join(HW, 'case_v5.scad')
OUT = os.path.join(HW, 'parts', 'props_v5_gen.scad')
TMP = os.path.join(HW, '_tmp_v5', 'props'); os.makedirs(TMP, exist_ok=True)

# ---- 検査と同じ read_stl / zcolumns を**別の名前空間**へ読む ----
# 🔴 exec を自分のグローバルへ流すと、あちらの PITCH = 0.25 がこちらの 3.0 を上書きする
#    （ピッチ 0.25mm ＝ 全セルに柱・ブリッジで 23,917 本の事故）。ns 辞書に隔離する。
_ns = {}
_src = io.open(os.path.join(HERE, '_stl_preflight.py'), encoding='utf-8').read()
_argv = sys.argv; sys.argv = sys.argv[:1]   # あちらは sys.argv[2] を薄肉のしきい値として読む。こちらの部品名を渡さない
exec(_src[:_src.index("for p in sorted(glob.glob(")], _ns)
sys.argv = _argv
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
# 🔴 2026-08-30 輪と輪の刻み。ユーザー指摘「外周が壁から 2mm 開けるのは分かるんですが、
#   4mm もあけたら部分的にこうなるのは当たり前では」（天板の CHITUBOX の絵・外周に柱が
#   ばらばらに 10 本だけ立っていた）。それまで 1 本目を縁から 2*REACH（4.0）に置き、
#   2*REACH ごとに重ねていた。根拠は「輪 1 本が [r−REACH, r+REACH] を持つ」で、これは
#   **輪が切れ目のない線なら**正しい。実際の輪は PITCH（2.4）おきの**点の列**で、
#   隣り合う柱のちょうど中間では、外向きに √(REACH² − (PITCH/2)²) = 1.6mm しか届かない。
#   その結果、壁の受け持ち（縁から 2.0）との間に 0.4mm の帯が空き、そこを「埋め」が
#   ばらばらに拾っていた（天板では斜め 45°付近だけに 10 本。dil() が十字なので斜めの
#   受け持ちが √2 分短く出るため、残りも斜めに寄る）。
#   ⇒ 1 本目は縁から REACH（2.0）ちょうど、輪と輪は 2*REACH_EFF（3.2）刻み。
REACH_EFF = (REACH ** 2 - (PITCH / 2) ** 2) ** 0.5   # 1.60 点で並べた輪が外へ実際に届く量
FILL_PITCH = 2.4  # 埋めの最小間隔（隣との隙間 0.4 ＝ 癒着の実績 0.36 の外）
RAFT_LINK = PITCH + 0.6   # ラフトで繋ぐ柱どうしの上限距離
# 🔴 2026-08-29 ラフトは「その層の柱を全部 1 つの hull() で包む」だった。輪の上の 2 本だけが
#   ラフト側に分類されると、**その 2 点を結ぶ棒**になり、部品の footprint を引いた残りが
#   会話ボタンの首の口を横切る膜として残った（ユーザー「なんか変な事になってませんか」）。
#   ⇒ 各柱の下に円を置き、**RAFT_LINK より近い柱どうしだけ**を繋ぐ。輪ならラフトも輪になる。
# 🔒 2026-09-03 ユーザー案「柱を口の内側へ寄せ、円錐で保持する」「内側の何もない所にラフトを置いて、
#    そこから伸ばすしかない」。⇒ この部品では**接触点と柱の足を切り離す**。
#    接触点は天井のふちのまま、柱は肉から MIN_GAP 逃げてプレートまで降りる所にだけ立て、
#    間を 球（継ぎ手）＋円錐（先 φPROP_TIP）＋枝（斜材）で渡す。作りは
#    archive/floating_supports/_v4_post_props.py から借りた（浮かせも傾けもしない）。
CONE_PARTS = {'hatch'}
HEAD_D = 1.0        # 球（継ぎ手）＝円錐の太い端
HEAD_L = 0.6        # 円錐の長さ。天井は水平＝法線は真下なので、球が接触面より上へ出ない最短でよい
BRANCH_SLOPE = 1.0  # 枝の傾き（1.0 ＝ 45°）。横へ 1 行くのに縦へ 1 落ちる
POST_MIN_TOP = 0.5  # 枝の付け根がこれより低くなるなら、その接触点はあきらめる（天井は持たれずに残る）
GAP2 = 0.4          # 🔒 支えどうしの最小の隙間（癒着の実績 0.36 の外。PITCH 2.4 の根拠と同じ値）
POST_MIN_D2 = (PROP_D + GAP2) ** 2   # 柱の足どうしの最小の間隔の 2 乗
n_branch = {}       # 枝で振った柱の数
d_branch = {}       # 振った横の距離の最大
DBG = os.environ.get('PROPDBG') == '1'
# 🔒 2026-09-03 帯 A/B/C は**この道具（立てる柱）に戻した**。ユーザー「帯については浮かすのも
#    傾けるのもやめましょう。この帯については柱を立てる方のパイプラインで作りましょう」。
#    同日いったん「傾けて浮かせる」側（_v4_post_props.py）へ移したが、その道具は凍結した。
PARTS_ALL = ['strap_a', 'strap_b', 'strap_c', 'floor', 'top', 'lwall', 'rwall', 'front', 'hatch', 'bridge']   # case_v5 の print_<部品> がある物
PARTS = ['strap_a', 'strap_b', 'strap_c', 'top']   # 既定で支柱を書く部品。top はつまみのへこみ（keepout_top で軸・ねじ・リードの穴を避ける）。v5: まず帯 3 本（ユーザー 2026-09-05「帯の柱を立てないといけませんね」）
# 引数に部品名を並べるとその部品だけ。--report を付けると調べるだけで props_v5_gen.scad を書かない（どの部品に柱が要るかを見る用）
_args = [a for a in sys.argv[1:] if not a.startswith('--')]
REPORT = '--report' in sys.argv[1:]
if _args: PARTS = _args
for _a in PARTS: assert _a in PARTS_ALL, ('知らない部品', _a, PARTS_ALL)
# 🔒 2026-08-28 ユーザー「その支柱はいらない。過去にノブでその形状はなにも無くても印刷できるの分かってる」。
#    ここに挙げた（部品, 天井の高さ）には柱もヒレも立てない。**実機の実績が検査の判定より優先する。**
#    🔴 2026-08-28 **この SKIP は空に戻した。** 外して刷ったら皿の底に穴が開いた（実機・ユーザー）。
#       私が「無くていい」と言った判断が外れ。皿の底は 0.25mm しかなく、82mm² を渡れなかった。
#       つまみの皿の実績はここには効かない（あちらの底はここより厚い）。
SKIP = {('floor', 3.5),   # 床: ハッチの爪のバー（幅 8・奥行き 2・厚み 1.0・両端が帯に載る橋）。🔒 ユーザー 2026-09-05「要らないんじゃないですか」「v4 で付けてませんでしたよ」。中央は支えから 4.0 で較正 4.00 の内側
        ('top', 8.7),      # 天板: 会話ボタンの耳のブロック 2 個の中のナットの溝の天井（溝は幅 5.0・上の肉 = ナットの床 0.8）。中央は壁から 2.5。同じブロックを v4 で柱なしで刷っている（2026-09-05）
        ('bridge', 1.1)}   # ブリッジ: 皿の裏の前板のフランジの掘り込み（幅 23・奥行き 6・上の肉 1.0・3 辺が壁につながる棚）。柱を立てると溝の中に立つ。爪のバーと同じ扱い（2026-09-05・AI の勧め）


def bake(part):
    p = os.path.join(TMP, 'bare_%s.stl' % part)
    subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', p,
                    '-D', 'PROPS_OFF=true', '-D', 'part="print_%s"' % part,
                    SCAD], check=True, capture_output=True)
    return p


def bake_keepout(part):
    """空いていなければならない体積（case_v5.scad の keepout_<部品>）を刷る向きで焼く。
       中身が空の部品は OpenSCAD が STL を書かないので None を返す。"""
    p = os.path.join(TMP, 'ko_%s.stl' % part)
    if os.path.exists(p): os.remove(p)
    subprocess.run([OPENSCAD, '--backend=manifold', '--export-format=binstl', '-o', p,
                    '-D', 'part="keepout_%s"' % part,
                    SCAD], capture_output=True)   # 空なら OpenSCAD は 1 で終わる（v5 の帯には keepout_strap_* が無い ＝ 軸は上向きで穴が無い）
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


out = ['// 🔴 自動生成。手で直さない。作り直しは `python hardware/tools/props_gen.py`',
       '//    位置は刷る向きの素の STL（PROPS_OFF=true）の天井の輪郭から決めている。',
       'PROP_D2 = %.2f; PROP_TIP2 = %.2f; PROP_NECK2 = 0.8; PROP_BITE2 = %.2f;' % (PROP_D, PROP_TIP, PROP_BITE),
       'module one_prop(x, y, base, h) translate([x, y, base]) {',
       '    cylinder(d = PROP_D2, h = max(0.01, h - base - PROP_NECK2), $fn = 16);',
       '    translate([0, 0, max(0, h - base - PROP_NECK2)])',
       '        cylinder(d = PROP_TIP2, h = min(PROP_NECK2, h - base) + PROP_BITE2, $fn = 12);',
       '}',
       'HEAD_D2 = %.2f; HEAD_L2 = %.2f;' % (HEAD_D, HEAD_L),
       '// 柱（垂直）― 球（継ぎ手）― 枝（斜材）― 円錐（先 PROP_TIP2）。柱の足 (px,py) と接触点 (cx,cy) は別',
       'module one_cone(cx, cy, h, px, py, ptop) {',
       '    translate([px, py, 0]) cylinder(d = PROP_D2, h = max(0.01, ptop), $fn = 16);',
       '    hull() {',
       '        translate([px, py, ptop]) sphere(d = HEAD_D2, $fn = 16);',
       '        translate([cx, cy, h - HEAD_L2]) sphere(d = HEAD_D2, $fn = 16);',
       '    }',
       '    translate([cx, cy, h - HEAD_L2]) cylinder(d1 = HEAD_D2, d2 = PROP_TIP2, h = HEAD_L2, $fn = 16);',
       '    translate([cx, cy, h]) cylinder(d = PROP_TIP2, h = PROP_BITE2, $fn = 12);',
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
n_brush = {}    # 足元が段差をまたぎ、胴が段差の側面をかすめる柱の数
d_brush = {}    # そのかすめる深さの最大
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
        # 🔴 2026-09-03 上の basemax だけでは**空中から生える柱**が出る。ハッチで 20 本出た
        #   （ユーザー ChituBox「柱が地面に置かれていない」「柱そのものが印刷不能」）。
        #   胴 φ2.0 の円の**端**を高さ 0.70 の段差がかすめただけで円全体が 0.70 まで持ち上がり、
        #   円の中心の真下は空のまま底面が宙に浮いていた（例: 柱 (11.55, 22.11)・肉は 0.70 から）。
        #   ⇒ 足元は「**胴の底面全部の下にある肉**」（basemin）で取る。段差をまたぐ升には立てない。
        #   段差をまたぐ升に**立てない**ようにすると、ハッチは天井 252.1mm2 のうち 114.9mm2 が
        #   持たれないまま残った（柱 49 → 32 本）。段差の縁の帯 2mm がまるごと禁止になるため。
        #   ⇒ 立てないのではなく**下（プレート側）まで下ろす**。胴が段差の側面をかすめて癒着するが、
        #     宙に浮いた底面や無支持の天井より軽い（かすめる深さは下の brush で数える）。
        basemin = ndimage_minfilt(basegrid, footprint=_disc, mode='nearest')
        brush = basemax - basemin                # 胴が段差の側面をかすめる深さ
        # 🔴 2026-09-03 足元を下ろしただけでは**胴が部品の肉に食い込む**。ハッチで 20 本、
        #   足 φ2.0 の 18〜50% が蓋の鞘の床（Z 0〜0.70）に埋まっていた（ユーザー ChituBox「重なってる」）。
        #   折れば跡が蓋の入口に残る。⇒ 胴の半径に逃げ MIN_GAP を足した円の中に、
        #   足元より高い肉が 1 つでもあれば**そこには立てない**（＝肉から 0.3 離れた所にしか立たない）。
        _rr3 = int(np.ceil((PROP_D / 2 + MIN_GAP) / P))
        _yy3, _xx3 = np.ogrid[-_rr3:_rr3 + 1, -_rr3:_rr3 + 1]
        _disc3 = (_yy3 ** 2 + _xx3 ** 2) <= _rr3 ** 2
        side_hit = ndimage_maxfilt(basegrid, footprint=_disc3, mode='nearest') > basemin + 0.05
        # 🔒 2026-09-03 柱を降ろせる升 ＝ 肉から MIN_GAP 逃げていて、足がプレートに着く所（＝ラフトを敷く所）
        CONE = part in CONE_PARTS
        stand = (~side_hit) & (basemin < 0.01)
        _dstand = _istand = None
        if CONE and stand.any():
            _dstand, _istand = ndimage_edt(~stand, sampling=P, return_indices=True)

        _sx = _sy = None
        if CONE and stand.any():
            _si = np.argwhere(stand); _sx = us[_si[:, 0]]; _sy = vs[_si[:, 1]]
        post_pts = []          # この層で出した柱の足（間隔を守るための帳簿）
        _reach = (h - HEAD_L - POST_MIN_TOP) * BRANCH_SLOPE    # 枝で振れる横の量

        def choose_post(i, j, cx, cy, reserve=False):
            """接触点 (cx, cy) を持つ柱の足を選ぶ。(x, y, 枝の付け根の高さ)／降ろせないなら None。
               🔴 足どうしは PROP_D + GAP2 だけ離す（離さないと柱が互いに食い込む・2026-09-03 に実測 -0.845mm）"""
            if not CONE:
                return None if side_hit[i, j] else (cx, cy, 0.0)
            def far(x, y):
                return all((x - a) ** 2 + (y - b) ** 2 >= POST_MIN_D2 - 1e-9 for a, b in post_pts)
            r = None
            if stand[i, j] and far(cx, cy):
                r = (cx, cy, h - HEAD_L)
            elif _sx is not None:
                d = np.hypot(_sx - cx, _sy - cy)
                for k in np.argsort(d):
                    if d[k] > _reach: break
                    if far(float(_sx[k]), float(_sy[k])):
                        r = (float(_sx[k]), float(_sy[k]), h - HEAD_L - float(d[k]) / BRANCH_SLOPE)
                        break
            if r is None: return None
            if reserve: post_pts.append((r[0], r[1]))
            return r
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
            if choose_post(i, j, us[i], vs[j]) is None: return False   # 🔴 柱を降ろせない（肉に食い込む／枝が届かない／足の間隔）
            if h - basemin[i, j] < 0.4: return False            # 下の肉がほぼ届いている
            if blocked(i, j, basemin[i, j], h): return False     # ネジ・ナット・軸・回る物
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
            #   🔴 2026-08-30 上の「2*REACH ごと」は**輪を切れ目のない線と見た**計算だった。
            #     点の列では外向きに REACH_EFF（1.6）しか届かない。1 本目は縁から REACH に置き
            #     （壁の受け持ち 2.0 の境目ちょうど）、以降は 2*REACH_EFF 刻みにする。定義は冒頭。
            else:
                rads = []
                rr = REACH
                while rr <= dmax_k:
                    rads.append(rr); rr += 2 * REACH_EFF
                if not rads or dmax_k - rads[-1] > REACH_EFF:
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
                    else:
                        n = max(2, int(L // PITCH) + 1)
                        if L / (n - 1) > 2 * REACH: n = int(math.ceil(L / (2 * REACH))) + 1
                    # 🔴 2026-08-29 本数は**弧長**で決めていたが、胴が接するかどうかを決めるのは**弦**。
                    #   曲がった輪では弦のほうが短いので、弧で 2.4 でも実距離が 2.12 まで詰まっていた。
                    #   ⇒ 実際に置く点の**いちばん近い弦**が PITCH を割るなら、本数を 1 減らす。
                    def _step_of(nn):
                        return L / nn if closed else L / max(1, nn - 1)

                    while n > 1:
                        st = _step_of(n)
                        pi = [at_arc_f(k * st) for k in range(n)]
                        mind = min((_d(pi[a], pi[b]) for a in range(len(pi)) for b in range(a + 1, len(pi))),
                                   default=1e9)
                        if mind >= PITCH - 1e-9: break
                        n -= 1
                    step = _step_of(n)
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
                        # 🔴 2026-08-29 ここで「輪の中の点どうしが step 以上離れているか」を
                        #   **直線距離**で見ていた。位置は**弧長**で等間隔に作ってあり、曲がった輪では
                        #   弦は必ず弧より短いので、**構造的に必ず不合格**になる。18 点中 15 点が
                        #   「近すぎる」と判定されてずらされ、輪が 2.4 の狙いに対し 2.4〜3.7 に歪んだ
                        #   （ユーザー「先祖返りしてます？」で発覚）。
                        #   ⇒ 理想の位置は等間隔だと分かっているので比べない。**他の輪・他の天井の柱
                        #     （placed）とだけ**比べる。ずらした候補は輪の中の点とも比べる。
                        def _farf(cf, nudged=False):
                            if nudged and any(_d(cf, f[1]) < step * 0.9 for f in laid): return False
                            if any(_d(cf, pp) < PITCH - 1e-9 for pp in placed): return False
                            return True

                        if DBG and part == 'top' and abs(h - 2.25) < 0.01 and 13 <= us[0] + qf[0] * P <= 35:
                            print('  k=%2d (%6.2f,%7.2f) usable=%s far=%s' % (
                                k, us[0] + qf[0] * P, vs[0] + qf[1] * P, usable(*q), _farf(qf)))
                        if not (usable(*q) and _farf(qf)):       # 弧の上で ±step/2 だけ探す
                            alt = None
                            for dt in np.arange(P, step / 2 + 1e-9, P):
                                for sgn in (1, -1):
                                    c = at_arc(t + sgn * dt); cf = at_arc_f(t + sgn * dt)
                                    if usable(*c) and _farf(cf, True): alt = (c, cf); break
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
                        # 🔒 2026-08-29 出す直前の最後の門。ずらした柱は輪の中で step×0.9 まで
                        #   許していたので、1 組だけ 1.57mm（φ2.0 の胴が食い込む）が残っていた。
                        #   ここで placed（＝既に出した柱すべて）と PITCH で比べて落とす。
                        if any(_d((fx, fy), pp) < PITCH - 1e-9 for pp in placed): continue
                        # 🔒 2026-08-29 ユーザー「そしてこの外周の柱には絶対ラフトをつけてはいけない」。
                        #   🔴 距離の値（dist <= CLEAR + P）で見ていたので、同じ輪の上でも歩きで 1.80mm まで
                        #     振れた 2 本がラフト側に落ちていた。**輪の番号**で決める。0 番＝外周。
                        is_outer = (ring_idx == 0)
                        on_raft = (not is_outer) and basemin[i2, j2] < 0.01
                        _cx, _cy = us[0] + fx * P, vs[0] + fy * P
                        _po = choose_post(i2, j2, _cx, _cy, reserve=True)
                        if _po is not None:                          # 帳簿は柱の足の升で取る
                            i2 = int(np.clip(np.searchsorted(us, _po[0]) - 1, 0, nu - 1))
                            j2 = int(np.clip(np.searchsorted(vs, _po[1]) - 1, 0, nv - 1))
                        if not CONE: _po = None
                        n_brush[part] = n_brush.get(part, 0) + (1 if brush[i2, j2] > 0.05 else 0)
                        d_brush[part] = max(d_brush.get(part, 0.0), float(brush[i2, j2]))
                        if _po is not None and (_po[0] != _cx or _po[1] != _cy):
                            n_branch[part] = n_branch.get(part, 0) + 1
                            d_branch[part] = max(d_branch.get(part, 0.0),
                                                 ((_po[0] - _cx) ** 2 + (_po[1] - _cy) ** 2) ** 0.5)
                        picks.append((_cx, _cy, basemin[i2, j2], h, on_raft, _po))
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
            if choose_post(i, j, us[i], vs[j]) is None: continue     # 🔴 柱を降ろせない（同上）
            if h - basemin[i, j] < 0.4: continue
            if blocked(i, j, basemin[i, j], h):                     # 持たれないまま残す（残りの面積に出る）
                n_dropped[part] = n_dropped.get(part, 0) + 1; continue
            if any((i - a) ** 2 + (j - b) ** 2 < fs2 for a, b in placed): continue
            # 🔒 2026-08-29 埋めの柱にも同じ規則。外周の輪の帯に居る柱にはラフトを付けない
            #   （ユーザー「この外周の柱には絶対ラフトをつけてはいけない」）
            #   2 本目の輪が入らない幅（＝外周の輪しか無い天井）なら、その柱は全部「外周」扱い。
            _outer = dist[i, j] < CLEAR + P + PITCH / 2
            _cx, _cy = us[i], vs[j]
            _po = choose_post(i, j, _cx, _cy, reserve=True)
            _bi, _bj = (i, j)
            if _po is not None:                                          # 帳簿は**柱の足**の升で取る
                _bi = int(np.clip(np.searchsorted(us, _po[0]) - 1, 0, nu - 1))
                _bj = int(np.clip(np.searchsorted(vs, _po[1]) - 1, 0, nv - 1))
            if not CONE: _po = None
            n_brush[part] = n_brush.get(part, 0) + (1 if brush[_bi, _bj] > 0.05 else 0)
            d_brush[part] = max(d_brush.get(part, 0.0), float(brush[_bi, _bj]))
            if _po is not None and (_po[0] != _cx or _po[1] != _cy):
                n_branch[part] = n_branch.get(part, 0) + 1
                d_branch[part] = max(d_branch.get(part, 0.0),
                                     ((_po[0] - _cx) ** 2 + (_po[1] - _cy) ** 2) ** 0.5)
            picks.append((_cx, _cy, basemin[i, j], h,
                          (not _outer) and basemin[i, j] < 0.01, _po)); placed.append((i, j))
            rem[max(0, i - nr):min(nu, i + nr + 1), max(0, j - nr):min(nv, j + nr + 1)] = False
            n_fill += 1
        thin_rem = rem & (above < THIN_ABOVE)
        if thin_rem.sum() * cell >= 1.0:
            dsup = edt_mm(~(S.reshape(nu, nv)), P)
            _tj = np.argwhere(thin_rem)
            alerts.append((part, h, thin_rem.sum() * cell, float(above[thin_rem].max()), float(dsup[thin_rem].max()),
                           us[_tj[:, 0].min()], us[_tj[:, 0].max()], vs[_tj[:, 1].min()], vs[_tj[:, 1].max()]))
        _ij = np.argwhere(Ng)
        rep.append((part, h, need.sum() * cell, n_ring, n_fill, rem.sum() * cell,
                    us[_ij[:, 0].min()], us[_ij[:, 0].max()], vs[_ij[:, 1].min()], vs[_ij[:, 1].max()]))
    BARE = ({'strap_a': 'strap_print(0)', 'strap_b': 'strap_print(1)', 'strap_c': 'strap_print(2)'}.get(part) or 'print_%s()' % part)   # case_v5 の print_<部品> と同じ素の形
    # 🔴 2026-08-29 同じ座標に 2 本出ることがある（開いた道の端と埋めが重なる等）。
    #   union では消えるが、ラフトの点も二重になるので、出す直前に落とす。
    seen_xy = set(); uniq = []
    for pk in picks:
        key = (round(pk[0], 2), round(pk[1], 2), round(pk[3], 2))
        if key in seen_xy: continue
        seen_xy.add(key); uniq.append(pk)
    picks = uniq
    def _emit(p):
        po = p[5] if len(p) > 5 else None
        if po is None: return 'one_prop(%.2f, %.2f, %.2f, %.2f);' % p[:4]
        return 'one_cone(%.2f, %.2f, %.2f, %.2f, %.2f, %.2f);' % (p[0], p[1], p[3], po[0], po[1], po[2])
    out.append('module props_%s() { %s }' % (part, ' '.join(_emit(p) for p in picks)))
    layers = {}
    for p in picks:
        x, y, b, h, on_raft = p[:5]
        po = p[5] if len(p) > 5 else None
        if po is not None:
            layers.setdefault(h, []).append((po[0], po[1]))   # ラフトは**柱の足**の下に敷く
        elif on_raft:
            layers.setdefault(h, []).append((x, y))
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
for _p in PARTS_ALL:   # 回していない部品は空の受け口（case_v5 の print_<部品> が呼ぶ）
    if _p not in PARTS: out.append('module props_%s() {} module raft_%s() {}   // 未生成' % (_p, _p))
if REPORT: print('--report: %s は書いていない' % OUT)
else: io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
if not REPORT: print('wrote', OUT)
print('%-9s %7s %12s %6s %6s %12s   %s' % ('部品', '天井Z', '要る面積', '輪', '埋め', '残り', '天井の場所（刷る向きの X / Y）'))
for r in rep: print('%-9s %7.2f %9.1f mm2 %6d %6d %9.1f mm2   X %.1f..%.1f  Y %.1f..%.1f' % r)
if alerts:
    print()
    print('🔴 **浮いていて薄い天井**（柱を立てると破るので立てていない。設計側で直す所）')
    print('%-9s %7s %11s %10s %10s   %s' % ('部品', '天井Z', '面積', '上の肉', '渡る距離', '場所（刷る向きの X / Y）'))
    for a in alerts:
        print('%-9s %7.2f %8.1f mm2 %7.2f mm %7.2f mm   X %.1f..%.1f  Y %.1f..%.1f' % a)
    print()
print('天井が狭くて置けなかった柱:',
      ' '.join('%s %d' % kv for kv in sorted(n_narrow.items())) or 'なし')
print('keepout（ネジ・ナット・軸・回る物）で落とした柱:',
      ' '.join('%s %d' % kv for kv in sorted(n_dropped.items())) or 'なし')
print('枝で口の内側へ振った柱（本数 / 振った横の距離の最大）:',
      ' '.join('%s %d本 %.2fmm' % (k, v, d_branch.get(k, 0.0))
               for k, v in sorted(n_branch.items()) if v) or 'なし')
print('段差の縁に立ち、胴が側面をかすめる柱（本数 / 最大の深さ）:',
      ' '.join('%s %d本 %.2fmm' % (k, v, d_brush.get(k, 0.0))
               for k, v in sorted(n_brush.items()) if v) or 'なし')
