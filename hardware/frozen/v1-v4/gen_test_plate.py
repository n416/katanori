#!/usr/bin/env python3
"""Mars 3 の1回目のテスト用モデルを生成する。

目的は3つ:
  1. ビルドプレートへの食いつきが出るか（20mm角の板）
  2. どこまで細い形が出るか（ピンと薄壁）
  3. 穴が設計寸法どおりに出るか（リング）

3 が本命。AS5600ホルダーは磁石とネジの穴の寸法で決まるので、
光造形の「穴は縮む」量をここで実測しておく。ID6.0 は磁石の径そのもの。

サポート無し・全部プレート直置きで刷れるように、
どの部品も底が平らで、互いに重なっていない（各パーツが独立した閉じた立体）。

使い方:
    python hardware/gen_test_plate.py
"""

import struct
import math
from pathlib import Path

SEG = 64  # 円の分割数


def _tri(a, b, c):
    """3頂点から法線を計算して1枚の三角形にする。"""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length > 0:
        nx, ny, nz = nx / length, ny / length, nz / length
    return ((nx, ny, nz), a, b, c)


def box(x0, y0, z0, dx, dy, dz):
    """底面が (x0,y0,z0) の直方体。"""
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    p = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 3, 2), (0, 2, 1),  # 底
        (4, 5, 6), (4, 6, 7),  # 天
        (0, 1, 5), (0, 5, 4),  # 手前
        (1, 2, 6), (1, 6, 5),  # 右
        (2, 3, 7), (2, 7, 6),  # 奥
        (3, 0, 4), (3, 4, 7),  # 左
    ]
    return [_tri(p[i], p[j], p[k]) for i, j, k in faces]


def _ring_points(cx, cy, r, z):
    return [
        (cx + r * math.cos(2 * math.pi * i / SEG),
         cy + r * math.sin(2 * math.pi * i / SEG),
         z)
        for i in range(SEG)
    ]


def cylinder(cx, cy, z0, d, h):
    """直径 d の円柱。"""
    r = d / 2.0
    bot, top = _ring_points(cx, cy, r, z0), _ring_points(cx, cy, r, z0 + h)
    cb, ct = (cx, cy, z0), (cx, cy, z0 + h)
    tris = []
    for i in range(SEG):
        j = (i + 1) % SEG
        tris.append(_tri(cb, bot[j], bot[i]))          # 底
        tris.append(_tri(ct, top[i], top[j]))          # 天
        tris.append(_tri(bot[i], bot[j], top[j]))      # 側面
        tris.append(_tri(bot[i], top[j], top[i]))
    return tris


def tube(cx, cy, z0, d_in, d_out, h):
    """内径 d_in・外径 d_out の筒。穴の縮みを測るための形。"""
    ri, ro = d_in / 2.0, d_out / 2.0
    ib, it = _ring_points(cx, cy, ri, z0), _ring_points(cx, cy, ri, z0 + h)
    ob, ot = _ring_points(cx, cy, ro, z0), _ring_points(cx, cy, ro, z0 + h)
    tris = []
    for i in range(SEG):
        j = (i + 1) % SEG
        tris.append(_tri(ib[i], ob[j], ob[i]))         # 底の輪
        tris.append(_tri(ib[i], ib[j], ob[j]))
        tris.append(_tri(it[i], ot[i], ot[j]))         # 天の輪
        tris.append(_tri(it[i], ot[j], it[j]))
        tris.append(_tri(ob[i], ob[j], ot[j]))         # 外壁（外向き）
        tris.append(_tri(ob[i], ot[j], ot[i]))
        tris.append(_tri(ib[j], ib[i], it[i]))         # 内壁（内向き）
        tris.append(_tri(ib[j], it[i], it[j]))
    return tris


def build():
    tris = []

    # 1. 食いつきと寸法の基準。この20.00mmをノギスで測ってXYの縮みを見る
    tris += box(-10.0, -10.0, 0.0, 20.0, 20.0, 2.0)

    # 2. ピン: どこまで細い出っ張りが出るか（Φ1.0 が出れば十分すぎる）
    for i, d in enumerate((1.0, 1.5, 2.0, 3.0)):
        tris += cylinder(16.0 + i * 6.0, -6.0, 0.0, d, 4.0)

    # 3. 薄壁: 筐体の壁厚を決めるときの下限
    for i, t in enumerate((0.3, 0.5, 1.0)):
        tris += box(14.0 + i * 5.0, 2.0, 0.0, t, 8.0, 3.0)

    # 4. 穴（本命）: 設計値に対して実物が何mm細るか。ID6.0は磁石の径
    for i, d_in in enumerate((2.0, 3.0, 6.0)):
        tris += tube(-16.0 - i * 10.0, 0.0, 0.0, d_in, d_in + 3.0, 3.0)

    return tris


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"katanori first print test (mm)".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for n, a, b, c in tris:
            f.write(struct.pack("<12fH", *n, *a, *b, *c, 0))


if __name__ == "__main__":
    tris = build()
    out = Path(__file__).with_name("first-print-test.stl")
    write_stl(out, tris)

    xs = [v[0] for _, *vs in tris for v in vs]
    ys = [v[1] for _, *vs in tris for v in vs]
    zs = [v[2] for _, *vs in tris for v in vs]
    print(f"{out.name}: {len(tris)} triangles")
    print(f"  X {min(xs):7.2f} .. {max(xs):7.2f}  ({max(xs)-min(xs):.2f} mm)")
    print(f"  Y {min(ys):7.2f} .. {max(ys):7.2f}  ({max(ys)-min(ys):.2f} mm)")
    print(f"  Z {min(zs):7.2f} .. {max(zs):7.2f}  ({max(zs)-min(zs):.2f} mm)")
