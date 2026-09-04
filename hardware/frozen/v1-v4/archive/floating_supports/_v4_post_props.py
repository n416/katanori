# -*- coding: utf-8 -*-
"""留め帯 A/B/C（支柱と一体）を**傾けて浮かせて**刷るための、置き方・柱・ラフトを書き出す。

  python hardware/_v4_post_props.py     → hardware/_v4_post_props.scad

🔒 2026-09-03 ユーザー「スペーサーが上からひっぱると抜ける問題があり、帯と一体化に戻す事に
   なりました。ただ、印刷時に長いアーチになるので柱が必須です。浮かせるスペーサーを作る時に
   使った保持具を付けて欲しいです」「角度についても、最も印刷に適した極端な変化にならない角度を
   付けたいです」。⇒ この道具の相手を**支柱 6 本から帯 3 本へ**移した。作りは変えていない
   （柱＋球＋円錐・ラフト・向きの選び方は 2026-09-01〜02 に決めたまま）。
   「極端な変化にならない角度」＝ 1 層あたりの断面積の増分の最大値（_tilt_sweep.py の物差し）が
   いちばん小さい向き。ここで毎回選び直すので、形が変われば角度も追従する。

なぜ浮かせるか（docs/PRINT.md §3.9）:
  真っ直ぐ立てると断面が φ1.5＝1.74mm² から φ5.8＝26.37mm² へ **z 1.60 で一段に跳ぶ**。
  剥離力は断面積に比例するので、この跳ねが失敗の形そのものになる。傾けると跳ねは
  0.68〜0.79mm²/層（26〜30 倍まし）まで落ちるが、代わりに**接地が実質ゼロ**になるので、
  部品を浮かせて足で受ける仕組みが要る。それがこの生成器である。

サポート 1 本の作り（🔒 2026-09-01 ユーザー「柱＋球＋円錐で構成されるべきだよね」）:

    ラフト ── 柱（垂直・φ2.0）── 球（継ぎ手・φ1.0）── 円錐（軸＝面の法線）── 接触面 φ0.5

  ・**円錐の軸は面の法線**。両端とも軸に直角なので、これは本物の円錐（回転体）である。
  ・向きの変わり目は**球**が受ける。柱は垂直（そうでないと刷れない）、円錐は法線向きで、
    その間を球が繋ぐ。⚠ 球を挟まずに「水平な円」と「傾いた円」を hull で繋ぐと、
    円錐の底が法線に直角にならない（2026-09-01・ユーザー指摘で作り直した）。
  ・円錐は**球が接触面より上へ出ない長さ**まで伸ばす。急な面ほど長くなる。
  ・⚠ 柱が立つのは接触点の真下ではなく**球の真下**。円錐が法線に沿うぶん横へずれる。

数字を二重に持たない:
  ・柱の形（胴 φ2.0・接触面 φ0.5・食い込み 0.1）と間隔 2.4 は **_v4_props.py から読む**。
    🔒 2026-09-01 ユーザー「通常の柱の間隔と同じで良いと思うけど」
  ・傾きと方位は毎回 _tilt_sweep.py の物差し（1 層あたりの断面積の増分の最大値）で選び直す。
    ⇒ 部品の形が変われば向きも追従する。ここに角度を書かない。
  ・素の形は case_v4.scad の part="strap_bare_a/b/c"（傾ける前・組んだ姿勢）を焼いて読む。
  ・触ってはいけない面の座標（支柱の位置・座の高さ・帯の Y）も case_v4.scad の
    part="strap_nums" の echo から読む。**モデルが出どころ**で、ここには書き写さない。
"""
import io, math, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OPENSCAD = os.environ.get('OPENSCAD', r'C:\Program Files\OpenSCAD (Nightly)\openscad.exe')
TMP = os.path.join(HERE, '_pf'); os.makedirs(TMP, exist_ok=True)

sys.path.insert(0, HERE)
_saved = sys.argv
sys.argv = [sys.argv[0], '__no_match__*.stl', '0.30']
import _stl_preflight as PF          # noqa: E402  (import しただけで本体が走るので argv を逃がす)
sys.argv = _saved
import _tilt_sweep as TS             # noqa: E402

# ---- 柱の数字は _v4_props.py から読む（あちらが 🔒 の出どころ）----
_src = io.open(os.path.join(HERE, '_v4_props.py'), encoding='utf-8').read()


def _num(name):
    m = re.search(r'^%s\s*=\s*([0-9.]+)' % name, _src, re.M)
    if not m:
        raise SystemExit('_v4_props.py から %s を読めない' % name)
    return float(m.group(1))


PROP_D, PROP_TIP, PROP_BITE = _num('PROP_D'), _num('PROP_TIP'), _num('PROP_BITE')
PITCH, MIN_GAP = _num('PITCH'), _num('MIN_GAP')
# 🔴 接触点の間隔とニッパーの空きは**同じつまみ**である。間隔 2.4 なら隣り合う円錐の
#    隙間は最大 2.4 − 0.5 − 0.5 = 1.4mm にしかならない。刃がそれ以上要るなら間隔を広げる。
#   🔒 2026-09-02 既定は **間隔 3.2 / 先の空き 2.0**。刃が入らない支柱は失敗と同じなので、
#      6 本とも島が 0 になる範囲でいちばん空きの大きいこの組にした（4.0/2.5 は post_5 が島を出す）。
#   🔒 2026-09-02 ユーザーの案（角度・長さの自由度＋混んでいる順）を入れたら、
#      間隔を 3.2 → **2.5**（検算の下限）まで詰めても成立するようになった。
#      自由度が混雑を吸うので、支柱 3〜4 → 4〜6 本、接地 42〜74 → 65〜136mm² に戻っている。
PITCH = float(os.environ.get('POST_PITCH', '2.5'))


HEAD_D = 1.0      # 球（継ぎ手）の径 ＝ 円錐の太い方の端。柱 φ2.0 と接触面 φ0.5 の間
HEAD_L = 1.5      # 円錐の長さ（既定）
HEAD_MAX = 3.0    # 混んだときに伸ばせる上限
# 🔴 **円錐は法線から BETA_MAX まで振ってよい。** 根拠は接触面が浮かないこと:
#    面を法線から β 傾けると、円い面の縁で食い込みが ±(先の半径)·sinβ ずれる。
#    浅い側が 0 になるのが β = arcsin(食い込み / 先の半径) で、そこを超えると縁が浮いて
#    接触が三日月になる。⇒ 先 φ0.5・食い込み 0.1 なら **23.6°**。
#    🔒 2026-09-02 ユーザー「法線で取っていない円錐ができるということ。これが正しいとは
#      私も言えない」に対して出した数字。角度単独では球が 0.60mm しか動かないので、
#      **長さ（HEAD_MAX）と組にして初めて混雑を解く力になる**（3.0mm なら 1.20mm）。
HEAD_CLR = 0.2    # 球が接触面より下に居るための余裕
TAPER = 1.0       # 🔴 柱（φ2.0）は球の TAPER 手前で止め、そこから球へ絞る。
                  #   🔒 2026-09-01 ユーザー「円錐の下に球がない」「であれば柱の長さが
                  #   長すぎるのでは？」。柱を球まで上げると φ1.0 の球が φ2.0 の柱に
                  #   丸ごと埋まって継ぎ手として働かず、細い部分が円錐の 1.5mm しか
                  #   残らないのでニッパーが入らない。ここで止めると細い部分が 2.5mm になる。
# 🔴 **壁のような急な面にも当ててよい。** 円錐は常に法線どおり（曲げない）、長さも HEAD_L のまま。
#   ⚠ 一度「急な面には当てない」という規則を入れたが、それは私の思い違いだった
#     （2026-09-01・ユーザー「壁のような急な面には当てていいでしょ」「何言ってんの？」）。
#     水平に寝た 7.2mm の円錐ができたのは、**「球は接触面より下に居ること」を法線方向で
#     測っていた**私の規則のせいで、法線が水平に近づくと長さが発散していた。壁なら球は
#     横へ逃げるので、円錐は 1.5mm のままでよい。
#   ⇒ 本当に効く条件は**柱（と球）が部品にぶつからないこと**だけ。ぶつかるなら
#     🔒 ユーザー「刷れない円錐なのであれば柱の位置の方を変更すべきかと」のとおり、
#     近くで当てられる所を探して**柱の位置の方を動かす**。
BRANCH_MAX = 4.0   # 枝で届く距離（隣の柱まで）
MERGE = 0.5        # 🔴 これ以上**深く重なっていれば 1 本**とみなす（癒着ではなく融合）。
#   φ2.0 の柱どうしは「しっかり重なって 1 本になる」か「0.4mm 空ける」かのどちらかで、
#   **その中間（隙間 0〜0.4mm）だけが癒着して剥がせない塊**になる。禁じるのはその帯だけ。
BETA_MAX = math.degrees(math.asin(min(1.0, PROP_BITE / (PROP_TIP / 2))))
NIP_GAP = float(os.environ.get('NIP_GAP', '2.0'))
# 🔴 **先（円錐）のまわりに要る空き。ニッパーの刃が入る量。**
#   🔒 2026-09-02 ユーザー「ここニッパー入りませんし、多分くっ付いてしまう」。
#   GAP（0.4）は「癒着しない」だけの数字で、**刃が入る話ではない**。切るのは先なので、
#   先が絡む組み合わせにはこちらを要求する。環境変数 NIP_GAP で振れる。
# 🔴 **間隔は「先の径 ＋ 刃の空き」より広くなければならない。**
#    狭いと、格子が出した接触点のうち円錐どうしがぶつかるものが**黙って捨てられる**。
#    円錐の角度は点が決まった時点で確定し、逃げ道（真下・斜材・枝）はどれも降ろし方を
#    変えるだけで円錐は動かないので、ぶつかったら 3 つとも同じ理由で落ちるためである。
#    ⚠ 2026-09-02 間隔 2.4 に空き 2.0（＝要 3.0）を入れて、実際にそれをやっていた。
_NEED = PROP_TIP + NIP_GAP
if PITCH < _NEED:
    raise SystemExit('間隔 %.2f が「先の径 %.2f ＋ 刃の空き %.2f ＝ %.2f」より狭い。'
                     'このまま回すと接触点が黙って捨てられる。'
                     'POST_PITCH を %.2f 以上にするか NIP_GAP を下げること。'
                     % (PITCH, PROP_TIP, NIP_GAP, _NEED, _NEED))
GAP = 0.4          # 🔒 支柱どうしの最小の隙間。_v4_props.py の PITCH 2.4 の根拠と同じ値
                   #   （「隣との隙間 0.4 ＝ 癒着の実績 0.36 の外」）。
# 🔴 2026-09-01 これを**柱どうし以外に当てていなかった**。斜材と円錐が隣の支柱に触れるほど
#    近づき、癒着してニッパーの入らない塊になっていた（ユーザーのスクショ
#    「いずれにしてもこんなにちかいのはまずいでしょ」）。一度「空中で融合するのは無害」と
#    判断して当たり判定を外したのが誤り。**柱・斜材・円錐の全部の組み合わせで見る。**
# 🔒 2026-09-01 ユーザー「つまりだ。円錐から柱を作って行く感じなんだよね。」
#   ⇒ **円錐が先。柱は円錐から下ろす。** 接触点と法線が円錐を決め、柱はその真下へ降りる。
#     真下へ降りられない（部品に入る／隣の柱に当たる）ときも**円錐は動かさない**。
#     隣の柱へ**枝**で降ろす。それも無理なときだけ、その円錐をあきらめる。
LIFT = 5.0        # プレートから浮かせる量。CHITUBOX の既定（docs/PRINT.md §3.9）
# ---- ラフト（スケート型）----
# 🔒 2026-09-02 ユーザー「スケートなんとか型にできます？浮かせる時はこれにしておきたい」。
#   スケート型＝**底が狭く、上の縁が張り出した 1 枚の板**（スキーの先が反った形）。
#   その張り出しの下へヘラを差し込む。CHITUBOX の「ラフト形状: スケート」と同じ考え方で、
#   2026-08-10 に ✅ で通った設定（PRINT.md §3）でもこれを選んでいる。
RAFT_T = 0.6      # ラフトの高さ（出典 Make: の「台は 0.5〜2mm」の下寄り）
RAFT_SKIRT = 0.6  # 縁の反り。**上を底より広げる**量（45°）。
#   🔴 2026-09-02 最初は逆（底を広く・上を狭く）にした。ユーザー「スロープ・・・これじゃ
#      逆に入りづらいじゃん」。あれは縁が薄い刃先になるだけで、ヘラが乗り上げて刺さらない。
#      スケート（スキーの先）は**縁が上へ反っている**形で、その反りの下へヘラを差し込む。
RAFT_TOP = 0.05   # 上面の厚み（hull の種にする薄い板）
# 🔴 **足の球はラフトに触れてはいけない。** 球の底がラフト（0〜RAFT_T）に埋まると、
#    そこだけラフトが薄い板でなく塊になり、ヘラで曲げても逃げず力がプレートへ行く。
#    🔒 2026-09-02 ユーザー「支柱の足の球がプレートを割るって指摘が来たヨ」。
#    実際 post_3 の枝の足が球の底 z=+0.43（ラフトの中）だった。⇒ 球の中心の下限を
#    「ラフトの上面 ＋ 球の半径 ＋ 逃げ」にする。
FOOT_MIN_MARGIN = 0.1
RAFT_D = 5.0      # 🔒 ラフトの円の径。出典の「台は φ2〜5」の上限（docs/PRINT.md §3.9）。
                  #   ⚠ 直置きの部品と違い、**浮かせた部品ではラフトが唯一の接地**になる。
                  #   🔴 2026-09-02 刃の空きを 2.0 にして支柱が 3〜4 本に減ったぶん、接地が
                  #      31mm² まで落ちて検査の「点で立っている（38mm² 未満）」に触れた。
                  #      支柱を増やすと刃が入らなくなるので、**ラフトの方を大きくする**。
RAFT_MIN = 40.0   # 🔴 2026-09-02 ラフトはこの面積以上（検査の「点で立っている」38mm² の外）。
RAFT_DMAX = 9.0   #    柱が 1 本しか立たない部品（post_0/1・幹 1 本＋枝 3 本）は φ5 の円 1 つ＝19.6
                  #    になった。前回（31mm²）と同じ対処: 支柱を増やすと刃が入らないので**ラフトを
                  #    広げる**。RAFT_D から 0.5 刻みで RAFT_MIN に届くまで広げる（上限 RAFT_DMAX）。
RAFT_LINK = PITCH + 0.6   # この距離までは無条件で繋ぐ（_v4_props.py と同じ流儀）。
#   🔴 ただし**ラフトは必ず 1 枚**にする。柱は円錐が法線へ向くぶん横へずれるので、
#      固定の距離だけでは届かない対が出る（2026-09-01・post_4 で合計 60mm² のうち
#      1 枚が 23mm² に割れた）。浮かせた部品ではラフトが唯一の接地なので、
#      割れると小さい方が自分だけで剥離力を受けることになる。⇒ 最小全域木で必ず繋ぐ。
FOOT_MIN = RAFT_T + PROP_D / 2 + FOOT_MIN_MARGIN   # 1.70 足の球の中心はここより上
RAY = 0.1         # 下面を拾うレイの間隔

# ---- 触ってはいけない面（部品の素の向き ＝ 組んだ姿勢のまま z を BAT_Z ぶん下げた座標）----
# 数字は case_v4.scad の part="strap_nums" が出す。ここに書き写さない
def read_nums():
    r = subprocess.run([OPENSCAD, '--backend=manifold', '-o', os.path.join(TMP, 'nums.stl'),
                        '-D', 'PROPS_OFF=true', '-D', 'part="strap_nums"',
                        os.path.join(HERE, 'case_v4.scad')], capture_output=True)
    txt = r.stderr.decode('utf-8', 'replace')
    d = {'posts': [], 'bands': []}
    for line in txt.splitlines():
        if 'SNUM' in line:
            w = line.split('SNUM')[1].strip(' "').split()
            d.update({w[i]: float(w[i + 1]) for i in range(0, len(w) - 1, 2)})
        elif 'SPOST' in line:
            w = line.split('SPOST')[1].strip(' "').split()
            d['posts'].append([float(x) for x in w])       # i, x, y, 板の裏 z, 軸の先 z, 板の傾き°
        elif 'SBAND' in line:
            w = line.split('SBAND')[1].strip(' "').split()
            d['bands'].append([float(x) for x in w])       # k, y0, 幅, 胴込みの前端, 同 後端
    if len(d['posts']) != 6 or len(d['bands']) != 3:
        raise SystemExit('strap_nums を読めなかった: ' + txt[-2000:])
    return d


NUM = read_nums()
BAT_Z = NUM['bat_z']
PLATE_TOP = NUM['plate_top'] - BAT_Z          # 8.00 帯の天面（ここから支柱が生える）
SPACER_R = NUM['spacer_r']                    # 2.90 胴の半径
POST_D = NUM['post_d']                        # 2.00 軸の径
TAB_H = NUM['tab_h']                          # 2.00 ツバの高さ
SHAFT_KEEP = POST_D / 2 + PROP_TIP / 2 + MIN_GAP   # 1.55 先が軸と E リングの溝に触れない距離
SEAT_KEEP = SPACER_R + MIN_GAP                # 3.20 板が載る座（胴の天面）に触れない距離
END_FACE = 0.2    # 🔒 軸の**端面**（先の切り口）はこの逃げから外す。嵌合に効くのは軸の側面と溝で、
                  #   端面は軸方向。ここを塞ぐと、傾けたとき最下点になる先を誰も支えられない。
FOOT_FACE = 0.3   # 足の裏とツバの裏（皿に載る面）は**当ててよい**（紙やすりで落とす）。
                  #   🔒 2026-09-02 の提案どおり「支えは足の裏に立つ」。痕の実績 0.3mm。
TAB_KEEP = 0.3    # ツバの上面（45°）と側面は当てない。溝の逃げ TAB_CL が 0.2 しか無く、痕 0.3 が勝つ

POSTS = []
for _i, _x, _y, _bz, _tz, _th in NUM['posts']:
    POSTS.append(dict(x=_x, y=_y,
                      seat_lo=_bz - BAT_Z - SPACER_R * math.tan(math.radians(_th)),   # 座の面のいちばん低い所
                      tip=_tz - BAT_Z))
BAND = None       # build する帯（main が入れる）: (y0, y1)


def blocked(raw, raw_top):
    """そこへ先を当ててはいけないか（raw は素の向きの座標）"""
    x, y, z = float(raw[0]), float(raw[1]), float(raw[2])
    for q in POSTS:
        r2 = (x - q['x']) ** 2 + (y - q['y']) ** 2
        if z > PLATE_TOP - 0.01:
            if r2 < SHAFT_KEEP ** 2 and z < q['tip'] - END_FACE:
                return True                       # 軸の側面と E リングの溝
            if r2 < SEAT_KEEP ** 2 and z > q['seat_lo'] - MIN_GAP:
                return True                       # 板が載る座（胴の天面）
    if BAND is not None and FOOT_FACE < z < TAB_H + TAB_KEEP and (y < BAND[0] or y > BAND[1]):
        return True                               # ツバ（横差しの嵌合面）。裏（z < 0.3）は当ててよい
    return False


RISE_PITCH = (0.25, 0.15, 0.10)
RISE_WARN = PF.RISE_WARN      # 4.00 実績の較正値。数字はあちらが持つ
# 🔒 2026-09-02 ユーザー「もう島だのなんだの曖昧な話は無しにしました」
#    「面積は惑わせ、混乱させる元凶だから急な立ち上がりに統合だね」。
#    ⇒ 支柱を足す基準を**島の個数から「急な立ち上がり（mm）」へ**乗り換えた。
#    急な立ち上がり ＝ ある層で新しく出た肉が、直下の肉からどれだけ離れているか の最大値。
#    島（下に何も無い）も庇（下から離れている）も、これ 1 つの mm に入る。
#    ⚠ レイ間隔は 1 つにしない。刻み方で拾える所が変わるので、3 通りの**最大**を採る。


def bake(name):
    """素の形（傾ける前）を焼いて三角形を返す"""
    out = os.path.join(TMP, '%s.stl' % name)
    r = subprocess.run([OPENSCAD, '--backend=manifold', '-o', out,
                        '-D', 'PROPS_OFF=true', '-D', 'part="%s"' % name,
                        os.path.join(HERE, 'case_v4.scad')], capture_output=True)
    if not os.path.exists(out):
        raise SystemExit('%s を焼けなかった:\n%s'
                         % (name, r.stderr.decode('utf-8', 'replace')[-2000:]))
    return PF.read_stl(out)


def best_orientation(tris):
    """1 層あたりの断面積の増分がいちばん小さい向きを選ぶ"""
    best = None
    for tilt in range(0, 91, 5):
        for az in ([0] if tilt == 0 else [0, 45, 90, 135, 180, 225, 270, 315]):
            r = TS.score(tris, tilt, az, 0.1)
            if r and (best is None or r['max_step'] < best['max_step']):
                best = r
    return best


def place(tris, tilt, az):
    """傾けて、いちばん低い所が LIFT に来るよう浮かせる。送り（OFS）も返す"""
    v = TS.rotated(tris, tilt, az).reshape(-1, 3, 3)
    lo = v.reshape(-1, 3).min(axis=0); hi = v.reshape(-1, 3).max(axis=0)
    ofs = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, LIFT - lo[2]])
    return v + ofs, ofs


def rot_inv(tilt, az):
    a = np.radians(az); t = np.radians(tilt)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])
    return (Rx @ Rz).T


def normal_at(v, x, y, z):
    """(x,y) の垂直レイが z で当たる面の法線（外向き＝下を向いている側・単位）"""
    a, b, c = v[:, 0], v[:, 1], v[:, 2]
    e1 = b - a; e2 = c - a
    n = np.cross(e1, e2)
    d = np.array([0.0, 0.0, 1.0])
    den = n @ d
    ok = np.abs(den) > 1e-12
    t = np.zeros(len(v))
    o = np.array([x, y, -1e4])
    t[ok] = ((a[ok] - o) * n[ok]).sum(1) / den[ok]
    P = o + t[:, None] * d
    v0 = e1; v1 = e2; v2 = P - a
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
    d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den2 = d00 * d11 - d01 * d01
    safe = np.where(den2 == 0, 1.0, den2)
    with np.errstate(invalid='ignore', divide='ignore'):
        u = np.where(np.abs(den2) > 1e-15, (d11 * d20 - d01 * d21) / safe, np.nan)
        w = np.where(np.abs(den2) > 1e-15, (d00 * d21 - d01 * d20) / safe, np.nan)
        hit = (ok & np.isfinite(u) & np.isfinite(w)
               & (u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6))
    if not hit.any():
        return np.array([0.0, 0.0, -1.0])
    zs = np.where(hit, P[:, 2], np.inf)
    j = int(np.argmin(np.abs(zs - z)))
    nn = n[j] / np.linalg.norm(n[j])
    return nn if nn[2] < 0 else -nn


def axis_of(n0, beta, phi):
    """法線 n0 から beta[deg] だけ、方位 phi[deg] の向きへ振った軸"""
    if beta <= 1e-9:
        return n0
    t1 = np.cross(n0, [0.0, 0.0, 1.0])
    if np.linalg.norm(t1) < 1e-6:
        t1 = np.cross(n0, [1.0, 0.0, 0.0])
    t1 = t1 / np.linalg.norm(t1)
    t2 = np.cross(n0, t1)
    b = np.radians(beta); f = np.radians(phi)
    a = n0 * np.cos(b) + (t1 * np.cos(f) + t2 * np.sin(f)) * np.sin(b)
    return a / np.linalg.norm(a)


def head_at(v, x, y, z, beta=0.0, phi=0.0, hl=None):
    """接触点から「柱＋球＋円錐」の寸法を出す。

    A  = 接触面の中心（面から PROP_BITE だけ中へ入れた点。円錐の細い方の端）
    hl = 円錐の長さ（法線に沿って）。**球が接触面より上へ出ない長さ**まで伸ばす
    S  = 球の中心 ＝ 円錐の太い方の端 ＝ 柱の頭
    """
    n0 = normal_at(v, x, y, z)
    slope = float(np.degrees(np.arccos(np.clip(-n0[2], -1.0, 1.0))))
    n = axis_of(n0, beta, phi)
    A = np.array([x, y, z]) - n * PROP_BITE
    hl = HEAD_L if hl is None else hl
    S = A + n * hl
    axis = np.cross([0.0, 0.0, 1.0], n)
    ln = np.linalg.norm(axis)
    if ln < 1e-9:
        axis, ang = np.array([1.0, 0.0, 0.0]), (0.0 if n[2] > 0 else 180.0)
    else:
        axis = axis / ln
        ang = float(np.degrees(np.arccos(np.clip(n[2], -1.0, 1.0))))
    # 🔴 柱は**円錐の真下**に立てる（円錐の中点）。球の真下に立てると、寝た円錐が
    #    横へ張り出したまま誰にも持たれない（🔒 2026-09-01 ユーザー
    #    「その円錐を支えられる柱を作るべきです」）。円錐は hl=1.5 なので、中点から
    #    両端まで 0.75mm ＝ φ2.0 の柱の半径 1.0 の内側に収まり、footprint ごと乗る。
    M = (A + S) / 2
    return dict(A=A, n=n, hl=hl, S=S, M=M, ang=ang, axis=axis, slope=slope,
                beta=beta, phi=phi)


# ---- 部品の全表面（2026-09-02・胴の側面を見落としていた）----
# 🔴 当たり検査は lowest_surface（レイごとの最下面）だけで行っていた。それは下から見える面しか
#    持たないので、**胴の側面（壁）や上向きの面**の脇を通る斜材・枝を見落とす。
#    実際 post_0/1 の斜材が部品から 0.08mm の所を通り、首がその隙間に埋まってニッパーが
#    入らなかった（ユーザーのスクショ「ニッパー入りません」）。柱の頭のテーパーも部品から
#    0.30〜0.46 で「癒着しそう」。⇒ 三角形を SURF_STEP で点にして KD 木に入れ、胴・首の
#    検査はこちらで行う。lowest_surface は接触点を探すふるいにだけ使う。
# 🔒 2026-09-03 環境変数で落とせるようにした（速さのため）。逃げ（GAP 0.4）より細かければ用は足りる。
#    0.08 → 560 万点・0.15 → 160 万点。点の数は刻みの 2 乗で効き、以後の当たり判定が全部これに乗る。
SURF_STEP = float(os.environ.get('SURF_STEP', '0.08'))
_SURF = {}      # build_one が置く: tree（3D）・xy（2D）・z


def surface_samples(v, step=SURF_STEP):
    out = []
    for a, b, c in v:
        e1, e2 = b - a, c - a
        n = int(max(np.linalg.norm(e1), np.linalg.norm(e2)) / step) + 1
        ii, jj = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing='ij')
        m = (ii + jj) <= n
        out.append(a + np.outer(ii[m] / n, e1) + np.outer(jj[m] / n, e2))
    return np.vstack(out)


def set_surface(v):
    from scipy.spatial import cKDTree
    P = surface_samples(v)
    _SURF['tree'] = cKDTree(P); _SURF['xy'] = cKDTree(P[:, :2]); _SURF['z'] = P[:, 2]


def body_clear(P0, P1, r0, r1, need=None, skip=0.0):
    """胴（半径 r0→r1 の棒）が部品から need 以上離れているか。skip は P0 側で除く長さ"""
    need = GAP if need is None else need
    P0 = np.asarray(P0, float); P1 = np.asarray(P1, float)
    L = float(np.linalg.norm(P1 - P0))
    if L < 1e-6:
        return True
    ts = np.arange(skip, L + 1e-9, 0.1)
    if not len(ts):
        return True
    q = P0 + np.outer(ts / L, P1 - P0)
    r = r0 + (r1 - r0) * ts / L
    d = _SURF['tree'].query(q)[0]
    return bool(((d - r) >= need).all())


def neck_clear(h):
    """首（球〜円錐）のまわりに刃の入る空きがあるか。

    🔒 2026-09-02 ユーザー「ニッパー入りません」。軸から半径 NIP_GAP の筒の中、接触面の
       0.4 上から球の上までに部品の面が無いこと。接触面そのもの（軸方向 0 付近）と、
       凸に逃げていく面（軸方向が負）は入らない。壁の脇（凹）に当てると入って落ちる。
    """
    n = h['n']; A = np.asarray(h['A'], float); S = np.asarray(h['S'], float)
    top = float((S - A) @ n) + HEAD_D / 2 + 0.5
    for t in np.arange(0.4, top, 0.25):
        q = A + n * t
        for j in _SURF['tree'].query_ball_point(q, NIP_GAP):
            p = _SURF['tree'].data[j]
            ax = float((p - A) @ n)
            if 0.4 <= ax <= top:
                return False
    return True


def lowest_surface(v):
    """レイごとの最下面 (x, y, z, 面の傾き°)。

    傾きは最下面の高さの**勾配**から出す（下向きの外法線は (∂z/∂x, ∂z/∂y, -1)）。
    三角形を 1 点ずつ当たるより桁違いに速いので、**当てられる面を探す**ふるいに使う。
    採用した 1 点の法線は normal_at() で厳密に取り直す。
    """
    col, zs, ze, us, vs, nu, nv = PF.zcolumns(v, RAY)
    X = us[col // nv]; Y = vs[col % nv]
    low = {}
    for x, y, z in zip(X, Y, zs):
        k = (round(x / RAY), round(y / RAY))
        if k not in low or z < low[k][2]:
            low[k] = (x, y, z)
    P = np.array(list(low.values()))
    ix = np.round(P[:, 0] / RAY).astype(int); ix -= ix.min()
    iy = np.round(P[:, 1] / RAY).astype(int); iy -= iy.min()
    Z = np.full((ix.max() + 1, iy.max() + 1), np.nan)
    Z[ix, iy] = P[:, 2]
    gx, gy = np.gradient(np.nan_to_num(Z, nan=0.0), RAY)
    bad = ~np.isfinite(Z)
    g = np.hypot(gx, gy)
    g[bad] = np.inf
    # 欠けた隣（silhouette の縁）に触れる所は勾配が嘘になるので急な面として扱う
    nb = np.zeros_like(bad)
    nb[1:, :] |= bad[:-1, :]; nb[:-1, :] |= bad[1:, :]
    nb[:, 1:] |= bad[:, :-1]; nb[:, :-1] |= bad[:, 1:]
    g[nb] = np.inf
    slope = np.degrees(np.arctan(g[ix, iy]))
    return np.column_stack([P, slope])


def pillar_top(h, pts):
    """柱をどこまで上げられるか。**球まで上げる必要はない。**

    🔒 2026-09-01 ユーザー「真下ふさがってないよね」。柱の頭を球（S.z）に固定していたので、
    部品の下面まで 0.6mm しか足りないだけで「真下は部品の中」と判定し、斜材へ逃げていた。
    真下は部品の下面まで空いているのだから、**そこまで上げて残りをテーパーで繋ぐ**。
    """
    # 🔴 2026-09-02 全表面で見る。逃げは癒着の実績の外 GAP（0.4）
    idx = _SURF['xy'].query_ball_point([h['M'][0], h['M'][1]], PROP_D / 2 + GAP)
    low = float(_SURF['z'][idx].min()) if idx else np.inf
    return min(h['S'][2] - TAPER, low - GAP)


def pillar_clear(h, pts):
    """垂直な柱（φ2.0・0 から球の高さまで）が部品に入らないか。

    ⚠ **ここが「柱をどこに立てられるか」を決めている唯一の条件**である。
      面が急かどうかではない（2026-09-01・ユーザー指摘で入れ替えた）。
    ⚠ 球はここで見なくてよい。球の中心は接触面から**法線方向に hl（1.5mm）**離れていて、
      半径は 0.5 なので、面が平らな範囲では必ず 1.0mm 空いている。斜面で「真上の部品の
      高さ」と球の半径を足して比べると、垂直の高さと法線方向の距離を混ぜることになり、
      空いているのに落ちる（2026-09-01・それで柱が半分に減った）。
    """
    pz = pillar_top(h, pts)
    if pz < RAFT_T + 0.5:
        return False                             # 上げられる高さが無い
    # 柱の頭から球までのテーパー（φ2.0 → φ1.0）が部品から GAP 以上離れていること
    if not body_clear(np.array([h['M'][0], h['M'][1], pz]), h['S'], PROP_D / 2, HEAD_D / 2):
        return False
    h['PZ'] = float(pz)
    return True


def seg_clear(P0, P1, pts, skip=1.0):
    """斜材／枝の**通り道**が部品に入らないか。

    🔴 着地点の真下だけ調べても足りない。斜材そのものが部品を突き抜け、融着して
       **剥がせない**形になる（2026-09-01・ユーザーのスクショで発見）。
       頭の近く skip までは、円錐が部品へ向かうぶん除く。
    """
    # 🔴 2026-09-02 レイの最下面ではなく全表面で。半径は球 S 側 0.5 → 足側 1.0。
    #    skip は使わない: 頭の近くも部品から GAP 離れていなければ首が埋まる
    return body_clear(P0, P1, HEAD_D / 2, PROP_D / 2)


def members(h):
    """支柱を (端点0, 端点1, 半径) の棒の列で表す。柱・斜材・枝・円錐"""
    out = []
    S = np.asarray(h['S'], float)
    if h['mode'] == 'pillar':
        pz = h.get('PZ', S[2])
        out.append((np.array([h['M'][0], h['M'][1], RAFT_T]),
                    np.array([h['M'][0], h['M'][1], pz]), PROP_D / 2, 0))
        out.append((np.array([h['M'][0], h['M'][1], pz]), S, PROP_D / 2, 0))
    elif h['mode'] == 'strut':
        T = np.asarray(h['T'], float)
        out.append((np.array([T[0], T[1], RAFT_T]), T, PROP_D / 2, 0))
        out.append((T, S, PROP_D / 2, 0))
    else:
        out.append((np.asarray(h['base'], float), S, PROP_D / 2, 0))
    out.append((S, np.asarray(h['A'], float), HEAD_D / 2, 1))   # 1 = 先（ここを切る）
    return out


def seg_dist(p1, q1, p2, q2):
    """線分どうしの最短距離"""
    d1 = q1 - p1; d2 = q2 - p2; r = p1 - p2
    a = d1 @ d1; e = d2 @ d2; f = d2 @ r
    if a < 1e-12 and e < 1e-12:
        return float(np.linalg.norm(r))
    if a < 1e-12:
        sc, tc = 0.0, np.clip(f / e, 0, 1)
    else:
        c = d1 @ r
        if e < 1e-12:
            tc, sc = 0.0, np.clip(-c / a, 0, 1)
        else:
            b = d1 @ d2
            den = a * e - b * b
            sc = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-12 else 0.0
            tc = np.clip((b * sc + f) / e, 0, 1)
            sc = np.clip((b * tc - c) / a, 0, 1)
    return float(np.linalg.norm((p1 + d1 * sc) - (p2 + d2 * tc)))


def too_close(h, got, parent=None):
    """他の支柱と GAP より近づいていないか（親の柱へ意図的に繋ぐ枝は除く）"""
    mine = members(h)
    for g in got:
        for a0, a1, ra, ka in mine:
            for b0, b1, rb, kb in members(g):
                # 🔴 2026-09-02 親の柱は**胴だけ**除外する（枝は親の胴に繋ぐので）。
                #    親を丸ごと除外していたため、親の先の 0.28mm 隣に枝の先が立ち、
                #    1 本の柱の頭に首が 2 つ付いた（ユーザー「なんでここ２つ柱建ってるの？」）。
                if g is parent and not (ka or kb):
                    continue
                d = seg_dist(a0, a1, b0, b1) - ra - rb
                # 先が絡むならニッパーの刃のぶん、それ以外は癒着しないぶん
                need = NIP_GAP if (ka or kb) else GAP
                # 🔴 2026-09-02 「深く重なれば融合して 1 本」の例外（MERGE）は**柱どうしだけ**。
                #    先にも効かせていたので、最下点の先と格子の先が 0.3〜0.65mm 隣に立ち、
                #    ⚠ これだけでは直らなかった。本当の原因は上の「親を丸ごと除外」。
                if (ka or kb):
                    if d < need:
                        return True
                elif -MERGE < d < need:
                    return True
    return False


def _xy(h):
    return h['M'][0], h['M'][1]


def clash(h, got):
    """柱（＝球の真下）どうしが触るか"""
    return any((h['M'][0] - g['M'][0]) ** 2 + (h['M'][1] - g['M'][1]) ** 2
               < (PROP_D + MIN_GAP) ** 2 for g in got)


def cone_at(v, pts, x, y, z, Rinv, ofs, raw_top):
    """接触点から円錐を作る。**ここで円錐は決まり、以後動かさない。**"""
    if blocked(Rinv @ (np.array([x, y, z]) - ofs), raw_top):
        return None, '逃げ（軸の側面／D の面）の中'
    h = head_at(v, x, y, z)
    if h['S'][2] < RAFT_T + HEAD_D / 2 + HEAD_CLR:
        return None, '球がラフトに埋まる'
    if not neck_clear(h):
        return None, '首のまわりに刃が入らない'
    return h, None


def stand(h, pts, got):
    """円錐から柱を下ろす。真下が無理なときだけ隣の柱へ枝で降ろす。

    🔒 2026-09-01 ユーザー「円錐から柱を作って行く感じ」「その円錐を支えられる柱を作るべき」
    ⚠ **柱どうしが近いことは理由にならない。** 空中で φ2.0 の柱が融合しても無害で、
      出典の「支柱どうしを繋ぐと折れにくい」に沿う。近いだけで枝に回したら、
      プレートに届く柱が 2〜3 本まで減り、接地が 25〜33mm²（＝点で立っている判定）に落ち、
      post_2 は中身 2 個に割れた（2026-09-01・検査で発見）。
      間隔 2.4 の規則は**部品に当てる先の間隔**であって、柱どうしの話ではない。
    """
    # 🔴 「部品に当たる」と「隣の支柱に近い」を分ける。
    #    🔒 2026-09-01 ユーザー「真下ふさがってないよね」。どちらでも斜材へ逃げていたので、
    #    部品は何も邪魔していないのに柱が横へ飛んでいた。
    #    真下が部品に対して空いているなら、まず**隣の柱へ枝で相乗り**する。斜材は最後。
    under_ok = pillar_clear(h, pts)
    if under_ok:
        h['mode'] = 'pillar'
        if not too_close(h, got):
            return h, None
        h.pop('mode')
        # 真下は空いている（部品は邪魔していない）。隣の柱へ枝で繋ぐ
        for g in sorted(got, key=lambda g: (h['M'][0] - g['M'][0]) ** 2
                        + (h['M'][1] - g['M'][1]) ** 2):
            if g['mode'] != 'pillar':
                continue
            d = ((h['M'][0] - g['M'][0]) ** 2 + (h['M'][1] - g['M'][1]) ** 2) ** 0.5
            if d > BRANCH_MAX:
                break
            bz = max(FOOT_MIN, min(g['S'][2], h['S'][2] - max(d, 1.2)))
            if bz >= h['S'][2] - 0.3:
                continue
            if not seg_clear(h['S'], (g['M'][0], g['M'][1], bz), pts):
                continue
            h['mode'] = 'branch'; h['base'] = (g['M'][0], g['M'][1], bz)
            if too_close(h, got, parent=g):
                h.pop('mode'); h.pop('base'); continue
            return h, None
    # 🔴 真下が部品の中なら、**円錐から外へ降りて自分の柱を立てる**。
    #    急な面では円錐の真下も部品の中なので、垂直な柱は物理的に通せない。
    #    ⚠ 逃げる方角を**法線の方位に固定しない**。円錐が向いている方角しか探さないと、
    #      すぐ隣に空いている所があってもそこへ降りない
    #      （🔒 2026-09-01 ユーザー「この赤の柱はどうしてこんな位置なの？
    #        イメージ的にはオレンジの所に落ちると思うんだけど」）。
    #    ⇒ **全方位から探して、いちばん短く降りられる所**を採る。同じ長さなら法線に近い方角。
    n2 = h['n'][:2]
    nn = np.linalg.norm(n2)
    n2 = n2 / nn if nn > 1e-6 else np.array([1.0, 0.0])
    cands = []
    for a in np.arange(0, 360, 22.5):
        u = np.array([np.cos(np.radians(a)), np.sin(np.radians(a))])
        for t in np.arange(0.5, BRANCH_MAX + 0.01, 0.25):
            tx = h['S'][0] + u[0] * t; ty = h['S'][1] + u[1] * t
            tz = h['S'][2] - t                       # 斜材 45°
            if tz < FOOT_MIN:                        # 足の球がラフトに埋まる
                break
            idx = _SURF['xy'].query_ball_point([tx, ty], PROP_D / 2 + GAP)
            if idx and float(_SURF['z'][idx].min()) <= tz + GAP:
                continue                             # そこも部品の中（足の球の上に部品）
            if not seg_clear(h['S'], (tx, ty, tz), pts):
                continue                             # 斜材が部品を突き抜ける
            cands.append((t, -float(u @ n2), tx, ty, tz))
            break                                    # その方角では最短の 1 つでよい
    for t, _, tx, ty, tz in sorted(cands):
        h['mode'] = 'strut'; h['T'] = (tx, ty, tz)
        if too_close(h, got):
            h.pop('mode'); h.pop('T'); continue      # 隣の支柱に近すぎる（癒着する）
        return h, None
    near = sorted(got, key=lambda g: (h['M'][0] - g['M'][0]) ** 2 + (h['M'][1] - g['M'][1]) ** 2)
    for g in near:
        if g['mode'] != 'pillar':
            continue                              # 枝から枝は出さない
        d = ((h['M'][0] - g['M'][0]) ** 2 + (h['M'][1] - g['M'][1]) ** 2) ** 0.5
        if d > BRANCH_MAX:
            break
        bz = max(FOOT_MIN, min(g['S'][2], h['S'][2] - max(d, 1.2)))
        if bz >= h['S'][2] - 0.3:
            continue                              # 枝が寝すぎる
        if not seg_clear(h['S'], (g['M'][0], g['M'][1], bz), pts):
            continue                              # 枝が部品を突き抜ける
        h['mode'] = 'branch'; h['base'] = (g['M'][0], g['M'][1], bz)
        if too_close(h, got, parent=g):
            h.pop('mode'); h.pop('base'); continue
        return h, None
    return None, '柱も枝も降ろせない'


def heads(v, pts, ox, oy, Rinv, ofs, raw_top):
    """PITCH の格子で下面を拾い、混んでいる所から順に支柱を置く。

    🔒 2026-09-02 ユーザーの案（3 点）をそのまま実装したもの:
      ① 点が決まった時点で円錐の角度を固定しない（法線から BETA_MAX まで振れる）
      ② どの柱に落とすかの優先度は、**周りがいちばん混んでいる点から**
      ③ それでも混むときは円錐を細長くする（HEAD_L → HEAD_MAX）
    ⚠ ①は単独では球が 0.60mm しか動かない。③と組んで初めて効く（3.0mm で 1.20mm）。
    """
    # 🔴 **最下点は必ず最初の種にする。** 格子（間隔 2.5）の網目に最下点が落ちると、
    #    部品がいちばん低い層で何にも繋がらずに現れる。2026-09-02 ユーザーのスクショ
    #    「最下部にも関わらず、突然出現します」。6 本中 4 本で最下点から最寄りの接触点まで
    #    2.4〜3.2mm 離れていた。検査の急な立ち上がりは隣の柱まで XY で 2.4mm なので
    #    しきい値 4.0 の内側と判定し、島のまま通していた。
    j = int(np.argmin(pts[:, 2]))
    seeds = [(float(pts[j][0]), float(pts[j][1]), float(pts[j][2]))]
    gx = np.arange(pts[:, 0].min() - PITCH + ox, pts[:, 0].max() + PITCH, PITCH)
    gy = np.arange(pts[:, 1].min() - PITCH + oy, pts[:, 1].max() + PITCH, PITCH)
    for x0 in gx:
        for y0 in gy:
            d = (pts[:, 0] - x0) ** 2 + (pts[:, 1] - y0) ** 2
            j = int(np.argmin(d))
            # 🔴 レイは格子点の真下に無ければならない（無いと宙に立った柱になる）
            if d[j] > (RAY * 1.5) ** 2:
                continue
            seeds.append((x0, y0, float(pts[j][2])))
    if not seeds:
        return []
    # ② 混んでいる順（自分の周りに他の接触点が何個あるか）
    S = np.array(seeds)
    R = PROP_TIP + NIP_GAP
    crowd = [int((((S[:, 0] - p[0]) ** 2 + (S[:, 1] - p[1]) ** 2) <= R ** 2).sum()) - 1
             for p in S]
    order = [0] + sorted(range(1, len(seeds)),
                         key=lambda k: (-crowd[k], seeds[k][0], seeds[k][1]))

    got = []
    for k in order:
        x0, y0, z = seeds[k]
        h = try_place(v, pts, x0, y0, z, Rinv, ofs, raw_top, got)
        if h is not None:
            got.append(h)
    return got


# ①③ 振れる幅。理想（真っ直ぐ・短い）から順に試す
# 🔴 2026-09-02 角度の自由度①は**止めた**（0 だけ）。平らな面（傾き 0°）で 23.6° 振った
#    円錐が出て、ユーザー「円柱の先が法線になっていないところも見つかりました」。
#    円錐の軸は法線、が 🔒（2026-09-01）で、①はそれと両立しない。長さ③だけ残す。
#    戻すなら (0.0, 8.0, 16.0, BETA_MAX)。
BETA_STEPS = (0.0,)
PHI_STEPS = tuple(np.arange(0, 360, 30.0))
HL_STEPS = (HEAD_L, 2.0, 2.5, HEAD_MAX)


def try_place(v, pts, x0, y0, z, Rinv, ofs, raw_top, got):
    """1 つの接触点に支柱を置く。理想から始めて、詰まったら角度と長さを振る"""
    if blocked(Rinv @ (np.array([x0, y0, z]) - ofs), raw_top):
        return None
    for hl in HL_STEPS:
        for beta in BETA_STEPS:
            phis = (0.0,) if beta <= 1e-9 else PHI_STEPS
            for phi in phis:
                h = head_at(v, x0, y0, z, beta, phi, hl)
                if h['S'][2] < RAFT_T + HEAD_D / 2 + HEAD_CLR:
                    continue
                if not neck_clear(h):
                    continue
                g, _ = stand(h, pts, got)
                if g is not None:
                    return g
    return None


def raft_pts(hs):
    P = [[h['M'][0], h['M'][1]] for h in hs if h.get('mode') == 'pillar']
    P += [[h['T'][0], h['T'][1]] for h in hs if h.get('mode') == 'strut']
    return np.array(P) if P else np.zeros((0, 2))


def raft_links(P):
    """繋ぐ対を返す。近い対は全部＋最小全域木（必ず 1 枚になる）"""
    n = len(P)
    pairs = set()
    for i in range(n):
        for j in range(i + 1, n):
            if (P[i][0] - P[j][0]) ** 2 + (P[i][1] - P[j][1]) ** 2 <= RAFT_LINK ** 2:
                pairs.add((i, j))
    if n > 1:                                    # Prim の最小全域木
        inn = {0}
        while len(inn) < n:
            best = None
            for i in inn:
                for j in range(n):
                    if j in inn:
                        continue
                    d = (P[i][0] - P[j][0]) ** 2 + (P[i][1] - P[j][1]) ** 2
                    if best is None or d < best[0]:
                        best = (d, i, j)
            _, i, j = best
            pairs.add((min(i, j), max(i, j))); inn.add(j)
    return sorted(pairs)


def raft_d(P):
    """この部品のラフトの円の径。RAFT_MIN に届くまで広げる"""
    d = RAFT_D
    while d < RAFT_DMAX - 1e-9 and raft_area(P, d) < RAFT_MIN:
        d += 0.5
    return d


def raft_src(P, d=None):
    """スケート型のラフト。底（広い）と上（狭い）の 2 枚を hull で繋いでスロープにする"""
    if not len(P):
        return ''
    d = raft_d(P) if d is None else d
    def outline(extra):
        body = ' '.join('translate([%.2f, %.2f]) circle(d = %.2f, $fn = 32);'
                        % (p[0], p[1], d + 2 * extra) for p in P)
        return body if len(P) < 2 else 'hull() { %s }' % body
    # 底（狭い＝プレートに着く面）→ 上（広い＝反った縁）。ヘラはこの反りの下に入る
    lines = ['hull() {',
             '        linear_extrude(%.3f) %s' % (RAFT_TOP, outline(0.0)),
             '        translate([0, 0, %.3f]) linear_extrude(%.3f) %s'
             % (RAFT_T - RAFT_TOP, RAFT_TOP, outline(RAFT_SKIRT)),
             '    }']
    return chr(10).join(lines)


def raft_area(P, d=None):
    """ラフトの面積（重なりを二重に数えないよう 0.05mm の格子で塗る）。d 省略時は広げた後の径"""
    if not len(P):
        return 0.0
    d = raft_d(P) if d is None else d
    c = 0.05
    xs = np.arange(P[:, 0].min() - d - 2, P[:, 0].max() + d + 2, c)
    ys = np.arange(P[:, 1].min() - d - 2, P[:, 1].max() + d + 2, c)
    XX, YY = np.meshgrid(xs, ys, indexing='ij')
    m = np.zeros(XX.shape, bool)
    rr = d / 2                             # 底（プレートに着く側）。反りは上なので広がらない
    for p in P:
        m |= (XX - p[0]) ** 2 + (YY - p[1]) ** 2 <= rr ** 2
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            p, q = P[i], P[j]
            d2 = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
            if d2 < 1e-9:
                continue
            vx, vy = q[0] - p[0], q[1] - p[1]
            s = np.clip(((XX - p[0]) * vx + (YY - p[1]) * vy) / d2, 0, 1)
            m |= (XX - (p[0] + s * vx)) ** 2 + (YY - (p[1] + s * vy)) ** 2 <= rr ** 2
    return float(m.sum()) * c * c


_TIP_SRC = """// 🔒 2026-09-01 ユーザー「柱＋球＋円錐で構成されるべきだよね」。
//   円錐の軸は**面の法線**で、両端とも軸に直角 ＝ 本物の円錐（回転体）。
//   向きの変わり目は球が受ける。柱は垂直（そうでないと刷れない）、円錐は法線向き。
//   ⚠ 球を挟まず「水平な円」と「傾いた円」を hull で繋ぐと、円錐の底が法線に直角にならない。
//   s=(sx,sy,sz) 球の中心＝柱の頭＝円錐の太い端／a=(ax,ay,az) 接触面の中心／hl 円錐の長さ
HEAD_D2 = %.2f;
module post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    translate([ax, ay, az]) rotate(a = ang, v = [vx, vy, vz])
        cylinder(d1 = PROP_TIP2, d2 = HEAD_D2, h = hl, $fn = 24);
}
// 柱（垂直）＋球へ絞るテーパー＋頭。
// px,py は**円錐の真下**（円錐の中点）。球の真下ではない ── 寝た円錐を柱に乗せるため。
//   🔴 柱は球の TAPER2 手前で止める。球まで上げると球が柱に埋まり、細い部分が
//      円錐のぶんしか残らずニッパーが入らない（2026-09-01・ユーザー指摘）。
TAPER2 = %.2f;
//   pz は柱の頭。球まで上げず、**部品の下面の手前**で止める（生成器が出す）。
module one_prop_free(px, py, pz, sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    translate([px, py, 0]) cylinder(d = PROP_D2, h = max(0.01, pz), $fn = 24);
    hull() {
        translate([px, py, pz]) cylinder(d = PROP_D2, h = 0.01, $fn = 24);
        translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    }
    post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl);
}
// 円錐から外へ降りて**自分の柱**を立てる（真下が部品の中のとき）。斜材は 45°。
module one_prop_strut(px, py, pz, sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    translate([px, py, 0]) cylinder(d = PROP_D2, h = max(0.01, pz), $fn = 24);
    hull() {
        translate([px, py, pz]) sphere(d = PROP_D2, $fn = 16);
        translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    }
    post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl);
}
// 隣の柱から出す**枝**（自分では降りられないとき）。頭は同じ。
//   出典の「支柱どうしを繋ぐと折れにくい」もこれ（docs/PRINT.md §3.9）。
module one_prop_branch(bx, by, bz, sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    hull() {
        translate([bx, by, bz]) sphere(d = PROP_D2, $fn = 16);
        translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    }
    post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl);
}
"""


def head_call(name, h, pre=''):
    return ('%s(%s%.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.2f, %.4f, %.4f, %.4f, %.3f);'
            % (name, pre, h['S'][0], h['S'][1], h['S'][2], h['A'][0], h['A'][1], h['A'][2],
               h['ang'], h['axis'][0], h['axis'][1], h['axis'][2], h['hl']))


def write_scad(state):
    tilts, azs, ofss, headlist = state['tilt'], state['az'], state['ofs'], state['hs']
    L = ['// 🔴 自動生成。手で直さない。作り直しは `python hardware/_v4_post_props.py`',
         '//    留め帯 A/B/C（支柱と一体）を**傾けて浮かせて**刷るための、置き方と柱とラフト。',
         '//    向きは 1 層あたりの断面積の増分（＝極端な変化）がいちばん小さい所を毎回選び直している。',
         '//    数字（胴 φ2.0・接触面 φ0.5・食い込み 0.1）は _v4_props.scad が持つ。',
         'STRAP_LIFT = %.2f;' % LIFT,
         'STRAP_TILT = [%s];' % ', '.join('%d' % t for t in tilts),
         'STRAP_AZ   = [%s];' % ', '.join('%d' % a for a in azs),
         'STRAP_OFS  = [%s];' % ', '.join('[%.3f, %.3f, %.3f]' % tuple(o) for o in ofss),
         'module strap_place(k) translate(STRAP_OFS[k]) rotate([STRAP_TILT[k], 0, 0]) '
         'rotate([0, 0, STRAP_AZ[k]]) children();',
         _TIP_SRC % (HEAD_D, TAPER)]
    for i in range(3):
        src = []
        for h in headlist[i]:
            if h['mode'] == 'pillar':
                src.append(head_call('one_prop_free', h, '%.3f, %.3f, %.3f, '
                                     % (h['M'][0], h['M'][1], h['PZ'])))
            elif h['mode'] == 'strut':
                src.append(head_call('one_prop_strut', h, '%.3f, %.3f, %.3f, ' % h['T']))
            else:
                src.append(head_call('one_prop_branch', h, '%.3f, %.3f, %.3f, ' % h['base']))
        L.append('module props_strap_%s() { %s }' % (STRAPS[i], ' '.join(src)))
        L.append('module raft_strap_%s() %s' % (STRAPS[i], raft_src(raft_pts(headlist[i]))))
    io.open(os.path.join(HERE, '_v4_post_props.scad'), 'w',
            encoding='utf-8').write('\n'.join(L) + '\n')


def rise_of(i):
    """刷る向きの STL を焼いて、**急な立ち上がり**（mm）と、それが出た場所を返す。

    判定は検査器（_stl_preflight.steep_rise）に任せる。
    戻り: (立ち上がり mm, Z, X0, X1, Y0, Y1)。測れないときは None。
    """
    out = os.path.join(TMP, 'strap_chk_%s.stl' % STRAPS[i])
    subprocess.run([OPENSCAD, '--backend=manifold', '-o', out,
                    '-D', 'part="print_strap_%s"' % STRAPS[i],
                    os.path.join(HERE, 'case_v4.scad')], capture_output=True)
    tris = PF.read_stl(out)
    best = None
    for q in RISE_PITCH:
        rs = PF.steep_rise(tris, q)
        if rs is None:
            continue
        if best is None or rs[0] > best[0]:
            best = (rs[0], rs[1], rs[3], rs[4], rs[5], rs[6])
    return best


# 開始点のレイ間隔。刻みで拾える所が変わるので既定は 2 通りの和。速さが要るときは 1 通りに落とす
START_PITCH = tuple(float(x) for x in os.environ.get('START_PITCH', '0.15,0.10').split(','))


def starts_of(i):
    """刷る向きの STL を焼いて、**宙から始まる肉（開始点）**を全部返す。

    🔴 2026-09-03 ユーザー「これは急な立ち上がりというよりも、開始点ですね」
       「差分という意味なら無限大です」。⇒ しきい値のある「立ち上がり」ではなく、
       **0 でなければならない個数**として扱う。判定は検査器（_stl_preflight.layer_starts）に任せる。
    """
    out = os.path.join(TMP, 'strap_chk_%s.stl' % STRAPS[i])
    subprocess.run([OPENSCAD, '--backend=manifold', '-o', out,
                    '-D', 'part="print_strap_%s"' % STRAPS[i],
                    os.path.join(HERE, 'case_v4.scad')], capture_output=True)
    if not os.path.exists(out):
        return []
    tris = PF.read_stl(out)
    got = []
    for q in START_PITCH:
        r = PF.layer_starts(tris, q)
        if r:
            got.extend(r)
    uniq = []
    for z, x, y, a in sorted(got):
        if all(abs(z - u[0]) > 0.6 or (x - u[1]) ** 2 + (y - u[2]) ** 2 > 0.4 ** 2 for u in uniq):
            uniq.append((z, x, y, a))
    return uniq


def weld_mm3(i):
    """支柱と部品が食い込んでいる体積 mm³。**剥がせるかの物差し**。

    円錐の先が PROP_BITE だけ食い込むぶん（φ0.5 の面 × 0.1 ＝ 0.0196mm³）× 本数が
    見込み値。これより大きければ、斜材か枝が部品を突き抜けて融着している
    （2026-09-01・ユーザーのスクショで発見。斜材の通り道を検査していなかった）。
    """
    out = os.path.join(TMP, 'weld_%s.stl' % STRAPS[i])
    subprocess.run([OPENSCAD, '--backend=manifold', '-o', out,
                    '-D', 'part="strap_weld_%s"' % STRAPS[i],
                    os.path.join(HERE, 'case_v4.scad')], capture_output=True)
    if not os.path.exists(out):
        return 0.0
    t = PF.read_stl(out)
    if not len(t):
        return 0.0
    return float(abs(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0))


STRAPS = ['a', 'b', 'c']
GRID_N = int(os.environ.get('GRID_N', '6'))   # 格子をずらして試す回数（GRID_N × GRID_N 通り）
# 向きを動かしたくないとき（支柱だけ作り直す）: KEEP_ORIENT="30/315,45/135,45/225"
KEEP_ORIENT = [tuple(int(v) for v in t.split('/'))
               for t in os.environ['KEEP_ORIENT'].split(',')] if os.environ.get('KEEP_ORIENT') else None
ORIENT_TRY = int(os.environ.get('ORIENT_TRY', '6'))
# 🔴 向きは「立ち上がりの緩やかさ」だけで選ばない。**島が残らない向きを優先し、
#    同点なら跳ねで選ぶ**。どちらもユーザーが出した基準である。
#    ⚠ 2026-09-01 跳ねだけで選んでいたため post_5 が 30°/90 になり、0.38mm² の島が
#      1 つ消せなくなっていた。接触点 2 つの軸間距離が 0.6mm しかなく、支柱をどう細くしても
#      隙間 0.4 を作れない（隣を外しても島が移るだけだと実験で確認）。
#      35°/0 なら跳ねが 0.77 → 0.85（10% 悪い）で島 0・支柱 7 → 10・接地 84 → 94mm²。


def build_one(tris, tilt, az):
    """1 つの向きで支柱を組む（島潰しは呼び側）"""
    v, ofs = place(tris, tilt, az)
    raw_top = float(tris.reshape(-1, 3)[:, 2].max())
    Rinv = rot_inv(tilt, az)
    pts = lowest_surface(v)
    set_surface(v)
    # 🔴 最下点に先を当てられるか（格子の位相とは無関係に決まる）。
    #    当てられない向きは main() が捨てる。2026-09-02、60°/135 では最下点が D の足の角
    #    （平らな面から 0.06）に来て、逃げの中なので当てられず、島で現れていた。
    j = int(np.argmin(pts[:, 2]))
    low_ok = try_place(v, pts, float(pts[j][0]), float(pts[j][1]), float(pts[j][2]),
                       Rinv, ofs, raw_top, []) is not None
    best = None
    for ox in np.linspace(0, PITCH, GRID_N + 1)[:-1]:
        for oy in np.linspace(0, PITCH, GRID_N + 1)[:-1]:
            g = heads(v, pts, ox, oy, Rinv, ofs, raw_top)
            if best is None or len(g) > len(best):
                best = g
    return dict(v=v, ofs=ofs, raw_top=raw_top, Rinv=Rinv, pts=pts, hs=list(best), low_ok=low_ok)


def place_island(st, x, y, z, got):
    """開始点に 1 本立てる。まず通常の規則で、駄目なら**隙間の規則だけ緩めて**もう一度。

    🔒 2026-09-03 順序: **宙から始まる肉は必ず落ちる**。それに比べれば「柱どうしが近い」
       「ニッパーの刃が入りにくい」は軽い（切りにくいだけで、刷れる）。⇒ 島に限って緩める。
       ⚠ 緩めてよいのは**支柱どうしの隙間と刃の空き**だけ。触ってはいけない面（軸・E リングの溝・
         板が載る座・ツバ）は緩めない ── あれは部品が使えなくなる。
    """
    global NIP_GAP, GAP
    keep = (NIP_GAP, GAP)
    try:
        for nip, gap in ((keep[0], keep[1]), (1.0, 0.2), (0.5, 0.1)):
            NIP_GAP, GAP = nip, gap
            for dz in (0.0, 0.05, -0.05, 0.1, -0.1, 0.2, -0.2):
                h, _ = cone_at(st['v'], st['pts'], x, y, z + dz,
                               st['Rinv'], st['ofs'], st['raw_top'])
                if h is None:
                    continue
                if any(abs(g['A'][0] - h['A'][0]) < 0.05 and abs(g['A'][1] - h['A'][1]) < 0.05
                       for g in got):
                    return None, 'すでに同じ場所に立っている'
                g, why = stand(h, st['pts'], got)
                if g is not None:
                    g['relax'] = (nip, gap) if (nip, gap) != keep else None
                    return g, None
            last = why if h is not None else '円錐が作れない'
        return None, last
    finally:
        NIP_GAP, GAP = keep


def cut_starts(i, st, state, rounds=10):
    """**宙から始まる肉が無くなるまで**柱を足す。残ったものを返す。

    🔴 2026-09-03 それまでは検査器の「急な立ち上がり」が RISE_WARN（4.00）を切ったら止めていた。
       あの数字は**直下の肉ではなく平面上でいちばん近い肉**までの距離だったので、下に何も無い島でも
       1.95mm のような有限の値が出て、そのまま通っていた（CHITUBOX のスライスでユーザーが発見）。
       ⇒ 止める条件を「開始点 0」にした。しきい値は無い。
    """
    for _ in range(rounds):
        write_scad(state)
        isl = starts_of(i)
        if not isl:
            return []
        grew = False
        st['why'] = []
        for z, x, y, a in sorted(isl):
            g, why = place_island(st, x, y, z, st['hs'])
            if g is None:
                st['why'].append((z, x, y, a, why))
                continue
            st['hs'].append(g); grew = True
        if not grew:
            break
    write_scad(state)
    return starts_of(i)


def main():
    global BAND
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')   # ファイルへ流すと cp932 で mm² が落ちる
    n = len(STRAPS)
    state = dict(tilt=[0] * n, az=[0] * n, ofs=[np.zeros(3)] * n, hs=[[] for _ in range(n)])
    report = []
    for i in range(n):
        # ツバは帯そのものの Y の外に出ている部分（BAND の外・低い所）
        BAND = (NUM['bands'][i][1], NUM['bands'][i][1] + NUM['bands'][i][2])
        tris = bake('strap_bare_%s' % STRAPS[i])
        cand = []
        for tilt in range(0, 91, 5):
            for az in ([0] if tilt == 0 else [0, 45, 90, 135, 180, 225, 270, 315]):
                r = TS.score(tris, tilt, az, 0.1)
                if r:
                    cand.append(r)
        cand.sort(key=lambda r: r['max_step'])
        if KEEP_ORIENT:
            cand = [c for c in cand if c['tilt'] == KEEP_ORIENT[i][0]
                    and c['az'] == KEEP_ORIENT[i][1]] or cand
        # 🔴 2026-09-02 先に「最下点に先を当てられるか」で候補をふるう（安い検査）。しきい値は変えない。
        ok = []
        for r in cand:
            v, ofs = place(tris, r['tilt'], r['az'])
            set_surface(v); pts = lowest_surface(v)
            j = int(np.argmin(pts[:, 2]))
            if try_place(v, pts, float(pts[j][0]), float(pts[j][1]), float(pts[j][2]),
                         rot_inv(r['tilt'], r['az']), ofs,
                         float(tris.reshape(-1, 3)[:, 2].max()), []) is not None:
                ok.append(r)
                if len(ok) >= ORIENT_TRY:
                    break
        picked = None
        for r in (ok or cand[:ORIENT_TRY]):
            st = build_one(tris, r['tilt'], r['az'])
            state['tilt'][i] = r['tilt']; state['az'][i] = r['az']
            state['ofs'][i] = st['ofs']; state['hs'][i] = st['hs']
            left = cut_starts(i, st, state)
            rise = rise_of(i)
            rv = rise[0] if rise else float('inf')
            # 🔴 2026-09-03 選ぶ順は ①最下点に先を当てられるか ②**宙から始まる肉の数**
            #    ③つながった庇の出（mm）。②が 0 でない向きは、何本足しても刷れない。
            key = (0 if st['low_ok'] else 1, len(left), rv)
            if picked is None or key < picked[4]:
                picked = (r, st, (rise, left), rv, key)
            if st['low_ok'] and not left:
                break
        r, st, (rise, left), rv, _ = picked
        state['tilt'][i] = r['tilt']; state['az'][i] = r['az']
        state['ofs'][i] = st['ofs']; state['hs'][i] = st['hs']
        write_scad(state)
        report.append((i, r, st, rise, left))
        print('帯 %s: %d°/%d  支柱 %d 本  宙から始まる肉 %d か所  庇の出 %s'
              % (STRAPS[i].upper(), r['tilt'], r['az'], len(st['hs']), len(left),
                 ('%.2fmm' % rise[0]) if rise else '測れない'), flush=True)
    write_scad(state)

    print()
    print('部品   向き       真下 斜め  枝  接触面の合計   ラフト   急な立ち上がり  面の傾き   食い込み(見込み)  最下点から最寄りの先')
    for i, r, st, rise, left in report:
        hs = state['hs'][i]
        npil = sum(1 for h in hs if h['mode'] == 'pillar')
        nst = sum(1 for h in hs if h['mode'] == 'strut')
        tips = len(hs) * np.pi * (PROP_TIP / 2) ** 2
        sl = sorted(h['slope'] for h in hs)
        want = len(hs) * np.pi * (PROP_TIP / 2) ** 2 * PROP_BITE
        got_w = weld_mm3(i)
        flag = '' if got_w <= want * 1.6 + 0.01 else '  🔴 突き抜けている'
        rv = rise[0] if rise else float('nan')
        rmark = '' if (rise and rv <= RISE_WARN) else '  🔴 しきい値 %.2f 超' % RISE_WARN
        smark = '' if not left else '  🔴 宙から始まる肉が %d か所残っている' % len(left)
        allv = st['v'].reshape(-1, 3); lowpt = allv[np.argmin(allv[:, 2])]
        dlow = min(float(np.linalg.norm(h['A'] + h['n'] * PROP_BITE - lowpt)) for h in hs) if hs else float('inf')
        lmark = '' if dlow <= PROP_TIP else '  🔴 最下点に先が無い'
        for z, x, y, a, why in st.get('why', []):
            print('   🔴 帯 %s の開始点が残った: Z %.2f (%.2f, %.2f) %.2fmm² ── %s'
                  % (STRAPS[i].upper(), z, x, y, a, why))
        print('帯 %s  %2d°/%-3d  %3d %3d %3d  %7.2fmm²  %6.1fmm²  %6.2fmm%s  %3.0f〜%2.0f°  '
              '%.4f(%.4f)mm³%s  %.2fmm%s%s'
              % (STRAPS[i].upper(), r['tilt'], r['az'], npil, nst, len(hs) - npil - nst, tips,
                 raft_area(raft_pts(hs)), rv, rmark, sl[0], sl[-1], got_w, want, flag, dlow, lmark, smark))
    # 支柱どうしの隙間（枝と親の繋ぎ目は除く）
    print()
    for i in range(n):
        hs = state['hs'][i]
        m = 1e9
        for a in range(len(hs)):
            for b in range(a + 1, len(hs)):
                if joined(hs[a], hs[b]):
                    continue
                for p0, p1, ra, ka in members(hs[a]):
                    for q0, q1, rb, kb in members(hs[b]):
                        d = seg_dist(p0, p1, q0, q1) - ra - rb
                        if d > -MERGE:          # 融合しているものは「隙間」ではない
                            m = min(m, d)
        mc = 1e9
        for a in range(len(hs)):
            for b in range(a + 1, len(hs)):
                if joined(hs[a], hs[b]):
                    continue
                for p0, p1, ra, ka in members(hs[a]):
                    for q0, q1, rb, kb in members(hs[b]):
                        if ka or kb:
                            d = seg_dist(p0, p1, q0, q1) - ra - rb
                            if d > -MERGE:
                                mc = min(mc, d)
        foot = [h['T'][2] if h['mode'] == 'strut' else h['base'][2]
                for h in hs if h['mode'] != 'pillar']
        fb = (min(foot) - PROP_D / 2) if foot else float('inf')
        fmark = '' if fb >= RAFT_T else '  🔴 足の球がラフトに埋まっている'
        bt = sorted(h['beta'] for h in hs); hh = sorted(h['hl'] for h in hs)
        print('帯 %s  支柱どうし %.2fmm（要 %.2f）／**先まわり %.2fmm（要 %.2f）**'
              '  振った角度 %.0f〜%.0f°  円錐の長さ %.1f〜%.1fmm  足の球の底 %s%s'
              % (STRAPS[i].upper(), m, GAP, mc if mc < 1e8 else float('nan'), NIP_GAP,
                 bt[0], bt[-1], hh[0], hh[-1],
                 ('z%+.2f' % fb) if foot else '足の球なし', fmark))
    print('→ hardware/_v4_post_props.scad')


def joined(a, b):
    """枝と、その親の柱か（意図して繋いでいる所）"""
    for x, y in ((a, b), (b, a)):
        if x['mode'] == 'branch':
            m = y.get('M') if y['mode'] == 'pillar' else y.get('T')
            if m is not None and abs(x['base'][0] - m[0]) < 0.01 and abs(x['base'][1] - m[1]) < 0.01:
                return True
    return False


if __name__ == '__main__':
    main()
