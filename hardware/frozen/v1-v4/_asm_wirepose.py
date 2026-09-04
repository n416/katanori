# -*- coding: utf-8 -*-
# 「天面を横に置いた姿勢」で線が何 mm 余分に要るかの計算（2026-08-26）。
#
#   python hardware/_asm_wirepose.py
#
# 手順 10 で天面側につながる 4 束（AS5600 / BTN2 / PHOUT / REED）だけが、この姿勢で引っ張られる。
# 模型の端点は端子の手前で切ってあるので**絶対値は当てにならない**。同じ端点で 2 つの姿勢を比べた
# **差**（＝置いた分の増し）だけを見る。
#
#   組んだ姿勢  : _v4_core.scad の w_*() の折れ線長（＋ AS5600 だけコネクタまでの引き伸ばし）
#   置いた姿勢  : ハブの口 → 箱の縁（そこで垂れる）→ 倒した天面の端子、の直線 2 本。
#                 直線なので**下限**（実際はもう少し要る）。
#
# 置き方は 5 通り。「真上」は裏返して箱の真上で持つ（机に置かない）姿勢で、左右に返すか前後に返すかで
# 分けてある。残る「左・手前・右」は、箱の縁から 10mm の線を軸に外へ 180° 倒して机（Z=0）に置く姿勢。
# 🔴 天面を机に置くと、どの向きでも +85〜120mm 要る（裏返しは横の 1 軸を鏡にするので、
#    軸から遠い部品ほど 2 倍の距離を動く）。マニュアルの見込み +15 は「真上で持つ」姿勢の数字。
import io, sys
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

Z_TOP = 50.954      # 天面の外の面（case_v4.scad）
WALL  = 2.0
IN_X  = 84.354
IN_Y  = 72.0
GAP   = 10.0        # 箱の縁から蝶番の線までの距離（置く隙間）

# 束ごとの [ハブの口 → … → 天面側の端子]。点列は _v4_core.scad の w_*() をそのまま写す。
#   AS5600 だけ、模型が逃げの下（Z 13.3）で切れているので**コネクタの入口**（Z 31.25）まで足した。
BUNDLES = {
    'AS5600': [[[38.05, 29.2, 19], [54.0, 29.2, 19], [54.0, 29.2, 13.3], [54.0, 36.8, 13.3],
                [72.4, 36.8, 13.3], [72.4, 38.8, 31.25]]],
    'BTN2': [[[11.75, 54.85, 19], [11.75, 41.4, 19], [11.75, 41.4, 15.9], [11.75, 28.0, 15.9],
              [11.75, 28.0, 19], [5.5, 28.0, 19], [5.5, 28.0, 39.7], [5.5, 14.3, 39.7],
              [11.75, 14.3, 39.7], [11.75, 12.0, 39.7], [16.6, 12.0, 39.7]],
             [[11.75, 54.85, 19], [11.75, 41.4, 19], [11.75, 41.4, 15.9], [11.75, 28.0, 15.9],
              [11.75, 28.0, 19], [5.5, 28.0, 19], [5.5, 28.0, 39.7], [5.5, 14.3, 39.7],
              [11.75, 14.3, 39.7], [11.75, 16.6, 39.7], [16.6, 16.6, 39.7]]],
    'PHOUT': [[[79.1, 55.87, 19.5], [83.3, 55.87, 19.5], [83.3, 47.9, 19.5], [83.3, 47.9, 46.6],
               [83.3, 20.6, 46.6], [83.3, 20.6, 41.6], [54.7, 20.6, 41.6], [54.7, 20.6, 41.9]],
              [[79.1, 55.87, 19.5], [83.3, 55.87, 19.5], [83.3, 49.4, 19.5], [83.3, 49.4, 45.1],
               [83.3, 20.6, 45.1], [83.3, 20.6, 40.1], [56.7, 20.6, 40.1], [56.7, 20.6, 41.9]]],
    'REED': [[[56.97, 64.76, 22.3], [55.35, 64.76, 22.3], [55.35, 64.76, 42.6], [55.35, 61.5, 42.6],
              [55.35, 61.5, 41.0], [55.35, 57.4, 41.0]],
             [[56.97, 64.76, 22.3], [56.97, 64.76, 44.6], [71.05, 64.76, 44.6], [71.05, 61.5, 44.6],
              [71.05, 61.5, 41.0], [71.05, 57.4, 41.0]]],
}


def plen(pts):
    P = np.asarray(pts, float)
    return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())


HOLD = Z_TOP + 4.0   # 「真上で持つ」ときの、裏返した天面の外の面の高さ


def flip(p, where):
    """箱の縁から GAP の線を軸に外へ 180° 倒し、外の面を机（Z=0）に着ける。
       '真上' だけは机に置かず、箱の中心の線を軸に裏返して箱の真上で持つ"""
    x, y, z = p
    if where == '左':   return np.array([2 * (-WALL - GAP) - x, y, Z_TOP - z])
    if where == '右':   return np.array([2 * (IN_X + WALL + GAP) - x, y, Z_TOP - z])
    if where == '手前': return np.array([x, 2 * (-WALL - GAP) - y, Z_TOP - z])
    if where == '真上左右': return np.array([IN_X - x, y, 2 * HOLD - z])
    if where == '真上前後': return np.array([x, IN_Y - y, 2 * HOLD - z])
    raise ValueError(where)


def edge(p0, where):
    """線が箱から出る所（その向きの壁の外の上の角）。'真上' は箱から出ない"""
    x, y, _ = p0
    if where == '左':   return np.array([-WALL, y, Z_TOP])
    if where == '右':   return np.array([IN_X + WALL, y, Z_TOP])
    if where == '手前': return np.array([x, -WALL, Z_TOP])
    if where in ('真上左右', '真上前後'): return np.array([x, y, Z_TOP])
    raise ValueError(where)


def main():
    places = ['真上左右', '真上前後', '左', '手前', '右']
    print('%-8s %8s   %s' % ('束', '組んだ', '   '.join('%s置き（増し）' % w for w in places)))
    print('-' * 64)
    worst = {w: (0.0, '') for w in places}
    for name, wires in BUNDLES.items():
        built = max(plen(w) for w in wires)
        cells = []
        for w in places:
            need = max(float(np.linalg.norm(edge(x[0], w) - np.asarray(x[0], float))
                             + np.linalg.norm(flip(x[-1], w) - edge(x[0], w))) for x in wires)
            d = need - built
            cells.append('%6.1f (%+5.1f)' % (need, d))
            if d > worst[w][0]:
                worst[w] = (d, name)
        print('%-8s %8.1f   %s' % (name, built, '   '.join(cells)))
    print()
    for w in places:
        print('%s置き: 一番要るのは %s の +%.1f mm' % (w, worst[w][1], worst[w][0]))


if __name__ == '__main__':
    main()


# ---- 置き方の最小値を探す（2026-08-26 追記）------------------------------------
# 裏返した天面は、水平に何度でも回してよい（裏返し＝横 1 軸の鏡、そのあとの回転は自由）。
# 「縁を軸にそのまま倒す」は 1 通りにすぎないので、角度と位置を掃いて**一番要らない置き方**を探す。
#   置く条件: 箱の外形（角丸は無視した長方形）と重ならない・机の上（Z=0）・外の面が下。
#   線が箱から出る所は、端子に一番近い箱の縁の点にした（そこで垂れる）。
BOX = (-WALL, IN_X + WALL, -WALL, IN_Y + WALL)   # 箱の外形（x0, x1, y0, y1）
CLR = 3.0                                        # 箱と天面のすきま


def _refl(theta):
    """水平面の角度 theta の線についての鏡（裏返し＋水平回転の合わせ技）"""
    c, s = np.cos(2 * theta), np.sin(2 * theta)
    return np.array([[c, s], [s, -c]])


def _corners():
    x0, x1, y0, y1 = BOX
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)


def _overlap(P, Q):
    """凸多角形どうしの重なり（分離軸法）"""
    for A, B in ((P, Q), (Q, P)):
        for i in range(len(A)):
            e = A[(i + 1) % len(A)] - A[i]
            n = np.array([-e[1], e[0]])
            a, b = A @ n, B @ n
            if a.max() < b.min() - 1e-9 or b.max() < a.min() - 1e-9:
                return False
    return True


def _rim(T):
    """箱の縁（上の口の周り）で、端子に一番近い点"""
    x0, x1, y0, y1 = BOX
    x = min(max(T[0], x0), x1)
    y = min(max(T[1], y0), y1)
    if x0 < x < x1 and y0 < y < y1:      # 箱の真上なら一番近い辺へ寄せる
        d = [(x - x0, (x0, y)), (x1 - x, (x1, y)), (y - y0, (x, y0)), (y1 - y, (x, y1))]
        x, y = min(d)[1]
    return np.array([x, y, Z_TOP])


def best():
    box = _corners()
    rows = [(n, w, plen(w)) for n, ws in BUNDLES.items() for w in ws]
    built = {n: max(plen(w) for w in ws) for n, ws in BUNDLES.items()}
    out = None
    for deg in range(0, 180, 2):
        M = _refl(np.radians(deg))
        top = box @ M.T
        for side in range(4):
            for slide in range(-70, 71, 5):
                if side == 0:   t = np.array([BOX[0] - CLR - top[:, 0].max(), slide])
                elif side == 1: t = np.array([BOX[1] + CLR - top[:, 0].min(), slide])
                elif side == 2: t = np.array([slide, BOX[2] - CLR - top[:, 1].max()])
                else:           t = np.array([slide, BOX[3] + CLR - top[:, 1].min()])
                if _overlap(box, top + t):
                    continue
                worst, who = -1e9, ''
                for n, w, L in rows:
                    P0 = np.asarray(w[0], float)
                    T = np.asarray(w[-1], float)
                    T2 = np.append(M @ T[:2] + t, Z_TOP - T[2])
                    A = _rim(T2)
                    d = np.linalg.norm(A - P0) + np.linalg.norm(T2 - A) - built[n]
                    if d > worst: worst, who = d, n
                if out is None or worst < out[0]:
                    out = (worst, who, deg, side, slide)
    w, who, deg, side, slide = out
    print('一番要らない置き方: 裏返して水平に %d° 回し、箱の%sへ %+d mm ずらして置く'
          % (deg, ['左', '右', '手前', '奥'][side], slide))
    print('  そのとき一番要るのは %s の +%.1f mm' % (who, w))


if __name__ != '__main__':
    pass


# ---- 手順 12（ハッチを手に持ったままトグルへ繋ぐ）の姿勢（2026-08-27 追記）------
# 天面（手順 10）と違って、ハッチに付く物は**箱を閉じた後**につながる。天面もフロントも既に載って
# いるので中から手は入らず、トグルの 2 本は**ハッチを箱から離したまま**繋ぐしかない。
# 上の best() は天面の置き場の話なので、ハッチのぶんはここで別に測る。
#
#   固定点   : 線が後ろの縦穴の頭で前へ折れる角（TGL_FIX）。ここから先は後ろの口へ引き出せる
#   置いた姿勢: ハッチを机（Z=0）に**外の面を下**にして置く。トグルは上を向き、端子の先は
#              板の厚み ＋ 箱の中へ出ていた分（72 − 54）＝ 20.0mm の高さに立つ
HATCH_T2 = 2.0
BOX_OUT  = (-2.0, 86.354, -1.0, 74.0)          # 箱の外形（x0, x1, y0, y1）
PLATE_W, PLATE_H = 86.65, 52.954               # ハッチの板（世界の X と Z）
TGL_TERM = [(40.0, 43.5), (44.7, 43.5)]        # 端子（板の中での位置。w_tgl の終点）
PLATE_ORG = (-1.15, -2.0)                      # 板の左下（世界 X, Z）
TERM_UP  = HATCH_T2 + (72.0 - 54.0)            # 机に置いたときの端子の先の高さ = 20.0
TGL_ROUTE = [[49.35, 64.76, 21.9], [49.35, 64.76, 22.3], [55.2, 64.76, 22.3],
             [55.2, 64.76, 46.8], [55.2, 55.4, 46.8], [40, 55.4, 46.8], [40, 55.4, 44.75]]
FIX_I = 3                                      # 縦穴の頭の角（ここまでは動かない）


def _plate_corners(deg, tx, ty):
    """机に置いた板の四隅（外の面が下・水平に deg 回して置く）"""
    th = np.radians(deg)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    c = np.array([PLATE_W / 2, PLATE_H / 2])
    P = np.array([[0, 0], [PLATE_W, 0], [PLATE_W, PLATE_H], [0, PLATE_H]], float)
    return (P - c) @ R.T + np.array([tx, ty]), R, c


def _term_on_desk(deg, tx, ty, t):
    P, R, c = _plate_corners(deg, tx, ty)
    u = np.array([t[0] - PLATE_ORG[0], t[1] - PLATE_ORG[1]])
    xy = (u - c) @ R.T + np.array([tx, ty])
    return np.array([xy[0], xy[1], TERM_UP])


def hatch():
    fix = np.asarray(TGL_ROUTE[FIX_I], float)
    to_fix = plen(TGL_ROUTE[:FIX_I + 1])           # 口 → 縦穴の頭（動かない分）
    built = plen(TGL_ROUTE)                        # 組んだ姿勢の全長
    box = np.array([[BOX_OUT[0], BOX_OUT[2]], [BOX_OUT[1], BOX_OUT[2]],
                    [BOX_OUT[1], BOX_OUT[3]], [BOX_OUT[0], BOX_OUT[3]]], float)
    CLR2 = 10.0                                    # 箱とハッチのすきま
    CX = (BOX_OUT[0] + BOX_OUT[1]) / 2             # 箱の X の真ん中（ずらし 0 = 箱の後ろの真ん中）
    best = None
    for deg in range(0, 360, 5):
        P0, _, _ = _plate_corners(deg, 0, 0)
        for slide in range(-60, 61, 5):
            ty = BOX_OUT[3] + CLR2 - P0[:, 1].min()   # 箱の後ろへ置く
            P, _, _ = _plate_corners(deg, CX + slide, ty)
            if _overlap(box, P):
                continue
            need = max(to_fix + float(np.linalg.norm(_term_on_desk(deg, CX + slide, ty, t) - fix))
                       for t in TGL_TERM)
            if best is None or need < best[0]:
                best = (need, deg, slide)
    need, deg, slide = best
    print('TOGGLE 2 本（手順 12・ハッチを机に置いて繋ぐ）')
    print('  組んだ姿勢 %.1f mm／固定点まで %.1f mm' % (built, to_fix))
    print('  一番要らない置き方: 外の面を下にして水平に %d° 回し、箱の後ろへ %+d mm ずらして置く'
          % (deg, slide))
    print('    そのとき要る長さ %.1f mm（組んだ姿勢との差 %+.1f mm）' % (need, need - built))
    for nm, d in (('そのまま置く（レバーが奥）', 0), ('上下を返して置く（トグルが箱側）', 180)):
        P0, _, _ = _plate_corners(d, 0, 0)
        ty = BOX_OUT[3] + CLR2 - P0[:, 1].min()
        n = max(to_fix + float(np.linalg.norm(_term_on_desk(d, CX, ty, t) - fix)) for t in TGL_TERM)
        print('  %-24s %6.1f mm（%+.1f）' % (nm, n, n - built))


if __name__ == '__main__':
    print()
    hatch()
