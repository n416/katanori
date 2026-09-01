# -*- coding: utf-8 -*-
"""検算が出した**1 か所**に、後から支柱を付ける。

  python hardware/_spot_props.py     → hardware/_spot_props.scad

なぜ別の道具か:
  ・_v4_props.py      … 部品全体の**平らな天井**に、輪郭に沿った輪で柱を置く
  ・_v4_post_props.py … 部品ごと**傾けて浮かせて**、法線に沿った支柱で受ける
  ・これ（_spot_props）… **部品も向きも変えずに、指定した 1 か所だけ**に支柱を足す
    使い道は「刷る前の検算が『急な立ち上がり』を出したが、部品は直せない」とき。

🔒 数字も形も自分で作らない。支柱 1 本の形（ラフト・柱 φ2.0・球 φ1.0・円錐 φ1.0→φ0.5・
   軸＝面の法線）と、置き方の判断（stand / pillar_clear / too_close / raft）は
   **_v4_post_props.py の関数をそのまま呼ぶ**。あちらが 🔒 の出どころ。

⚠ 触ってはいけない所（SPOTS の keep）は**ここに書く**。あちらの blocked() は
   スペーサーの軸と D 面と E リングの溝に固定されていて、他の部品には使えない。
"""
import io, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _v4_post_props as PP        # noqa: E402  （if __name__ で守られているので走らない）

STL = os.path.join(HERE, 'stl', 'v4')

# ---- 直す場所。検算の「🔴 急な立ち上がり ◯mm（Z ◯・X ◯..◯ Y ◯..◯）」から写す ----
SPOTS = [
    dict(
        name='bridge',
        stl='v4_bridge.stl',
        # 🔴 検算: 急な立ち上がり 5.00mm（Z 3.03・X 2.3..4.1 Y 45.5..45.5）
        #    実体は箱へ留める M2 のボス。下面 22.50mm² が Z 3.00 で宙に始まる。
        box=(1.5, 7.0, 44.8, 53.5),
        # 🔴 真下に φ2.0 の柱は立たない（実測 0.00mm²・どんなに細くしても 0）。
        #    当てるのは**縁を回る 45° の面取りの帯**（先 φ0.5 が乗れる所 2.40mm²）。
        slope=(20.0, 70.0),        # 当ててよい面の傾き（°）。平ら 0° は避け、斜めだけ拾う
        keep=[dict(x=4.2, y=47.7, d=2.49)],   # ネジの通し穴（φ2.49）
    ),
]


def seeds_in(pts, box, slope):
    """箱の中の、傾きが範囲に入っている点を PITCH の格子で間引いて返す"""
    x0, x1, y0, y1 = box
    m = ((pts[:, 0] >= x0) & (pts[:, 0] <= x1)
         & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
         & (pts[:, 3] >= slope[0]) & (pts[:, 3] <= slope[1]))
    P = pts[m]
    if not len(P):
        return []
    out = []
    for x in np.arange(x0, x1 + PP.PITCH, PP.PITCH):
        for y in np.arange(y0, y1 + PP.PITCH, PP.PITCH):
            d = (P[:, 0] - x) ** 2 + (P[:, 1] - y) ** 2
            j = int(np.argmin(d))
            if d[j] > (PP.PITCH / 2) ** 2:
                continue
            out.append((float(P[j][0]), float(P[j][1]), float(P[j][2])))
    # 同じ点を二度拾わない
    uniq = []
    for p in out:
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 1e-6 for q in uniq):
            uniq.append(p)
    return uniq


def in_keep(x, y, keep):
    """先（φPROP_TIP）＋逃げが、触ってはいけない所に掛かるか"""
    r = PP.PROP_TIP / 2 + PP.MIN_GAP
    for k in keep:
        if (x - k['x']) ** 2 + (y - k['y']) ** 2 <= (k['d'] / 2 + r) ** 2:
            return True
    return False


def place_one(v, pts, x, y, z, keep, got):
    """1 点に支柱を置く。理想（法線どおり・短い）から始めて、詰まったら振る"""
    if in_keep(x, y, keep):
        return None
    for hl in PP.HL_STEPS:
        for beta in PP.BETA_STEPS:
            phis = (0.0,) if beta <= 1e-9 else PP.PHI_STEPS
            for phi in phis:
                h = PP.head_at(v, x, y, z, beta, phi, hl)
                if h['S'][2] < PP.RAFT_T + PP.HEAD_D / 2 + PP.HEAD_CLR:
                    continue
                g, _ = PP.stand(h, pts, got)
                if g is not None:
                    return g
    return None


# 🔴 2026-09-02 足の球がプレートより下へ出る。one_prop_strut / one_prop_branch は足に
#   φPROP_D の球を置くが、stand() はその足を RAFT_T（0.6）まで下げてよいことにしている。
#   球の下端は 0.6 − 1.0 = **−0.4**。浮かせる仕組み（_v4_post_props）では部品が 5mm 上がって
#   いるので足がそこまで下がらず、表に出ていなかった。**部品を浮かせないこの道具で初めて出る。**
#   ⇒ 置く間だけ床を球の半径ぶん上げる。ラフト自身の高さは元のまま（0.6）。
#   ⬜ 本来は stand() 側で「足の球がプレートを割らない」を条件にするのが筋。あちらは別セッションの
#      持ち物なので、ここで受けている。
def build(spot):
    tris = PP.PF.read_stl(os.path.join(STL, spot['stl']))
    v = tris
    pts = PP.lowest_surface(v)
    seeds = seeds_in(pts, spot['box'], spot['slope'])
    got = []
    floor0 = PP.RAFT_T
    PP.RAFT_T = floor0 + PP.PROP_D / 2          # 置く間だけ床を上げる（足の球のぶん）
    try:
        for x, y, z in seeds:
            h = place_one(v, pts, x, y, z, spot['keep'], got)
            if h is not None:
                got.append(h)
    finally:
        PP.RAFT_T = floor0                       # ラフトの高さは元に戻す
    return seeds, got


def write(results):
    L = ['// 🔴 自動生成。手で直さない。作り直しは `python hardware/_spot_props.py`',
         '//    検算が出した 1 か所にだけ足す支柱。支柱の形（one_prop_free / _strut / _branch）は',
         '//    _v4_post_props.scad が持っているので、使う側でそちらも include すること。']
    for name, spot, seeds, got in results:
        src = []
        for h in got:
            if h['mode'] == 'pillar':
                src.append(PP.head_call('one_prop_free', h, '%.3f, %.3f, %.3f, '
                                        % (h['M'][0], h['M'][1], h['PZ'])))
            elif h['mode'] == 'strut':
                src.append(PP.head_call('one_prop_strut', h, '%.3f, %.3f, %.3f, ' % h['T']))
            else:
                src.append(PP.head_call('one_prop_branch', h, '%.3f, %.3f, %.3f, ' % h['base']))
        L.append('// %s: 接触点の候補 %d / 置けた %d' % (name, len(seeds), len(got)))
        L.append('module spot_props_%s() { %s }' % (name, ' '.join(src)))
        L.append('module spot_raft_%s() %s' % (name, PP.raft_src(PP.raft_pts(got)) or '{}'))
    io.open(os.path.join(HERE, '_spot_props.scad'), 'w',
            encoding='utf-8').write('\n'.join(L) + '\n')


def main():
    results = []
    print('%-10s %8s %8s %10s' % ('場所', '候補', '置けた', 'ラフト'))
    for spot in SPOTS:
        seeds, got = build(spot)
        area = PP.raft_area(PP.raft_pts(got)) if got else 0.0
        print('%-10s %8d %8d %8.1f mm2' % (spot['name'], len(seeds), len(got), area))
        results.append((spot['name'], spot, seeds, got))
    write(results)
    print('⇒ hardware/_spot_props.scad')


if __name__ == '__main__':
    main()
