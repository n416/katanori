#!/usr/bin/env python3
"""AS5600の磁石ポケット寸法を「現物合わせ」で決めるゲージ。

磁石の絶対径は分かっていない（2026-08-02 時点で 4.0〜5.0mm、硬貨での判定では
φ4.0mm が濃厚）。だが、ホルダーの設計に本当に要るのは絶対径ではなく
**「どの設計値で穴を作れば、刷ったときにこの磁石がぴったり入るか」**で、
これは磁石の公差と樹脂の縮みの両方を含んだ値でなければ意味がない。

そこで内径を 0.1mm 刻みで並べて刷り、入るものを探す。
答えはノギスを介さず直接、設計値として得られる。

**8個は桟（さん）で1枚につながっている。** 1回目でピンを1本紛失したので、
バラバラの小部品にしない。桟は穴を塞がない位置（穴の縁より外）に通してある。

見分け方: 桟に並んだ順が内径の順。**外径も内径と一緒に大きくなる**ので、
桟を切り離したあとでも大小に並べ直せば順番が復元できる。

使い方:
    python hardware/gen_magnet_gauge.py
"""

from pathlib import Path

from gen_test_plate import box, tube, write_stl

ID_START = 3.8   # 一番小さい内径
ID_STEP = 0.1
COUNT = 8        # 3.8 .. 4.5
HEIGHT = 3.0     # 磁石の厚みより高くしない（押し込んだとき底が見えるように）
PITCH = 12.0     # 中心間の距離

RAIL_Y0 = 2.6    # 桟の内側の縁。一番大きい穴の半径 2.25 に対して 0.35mm 逃げてある
RAIL_W = 2.0     # 桟の幅
RAIL_H = 1.5     # 桟の高さ。リング(3.0)より低くして、切り離しやすくしておく


def _center(i):
    return -PITCH * (COUNT - 1) / 2 + PITCH * i


def _outer(i):
    # 一番小さいリングでも外半径が桟(2.6)より十分外に出るよう、底上げしてある
    return ID_START + ID_STEP * i + 3.0 + 0.3 * i


def build():
    tris = []
    for i in range(COUNT):
        d_in = ID_START + ID_STEP * i
        # 外径も一緒に育てて、切り離したあとでも順番を見た目で復元できるように
        tris += tube(_center(i), 0.0, 0.0, d_in, _outer(i), HEIGHT)

    # 桟。全リングの外壁に食い込ませて1枚につなぐ。
    # 一番小さいリングでも外半径 3.4 > RAIL_Y0(2.6) なので、8個すべてに 0.8mm 掛かる。
    x0 = _center(0) - _outer(0) / 2
    x1 = _center(COUNT - 1) + _outer(COUNT - 1) / 2
    tris += box(x0, RAIL_Y0, 0.0, x1 - x0, RAIL_W, RAIL_H)

    return tris


if __name__ == "__main__":
    tris = build()
    out = Path(__file__).with_name("magnet-fit-gauge.stl")
    write_stl(out, tris)

    xs = [v[0] for _, *vs in tris for v in vs]
    ys = [v[1] for _, *vs in tris for v in vs]
    zs = [v[2] for _, *vs in tris for v in vs]
    print(f"{out.name}: {len(tris)} triangles")
    print("  内径: " + " / ".join(f"{ID_START + ID_STEP * i:.1f}" for i in range(COUNT)))
    print(f"  X {min(xs):7.2f} .. {max(xs):7.2f}  ({max(xs)-min(xs):.2f} mm)")
    print(f"  Y {min(ys):7.2f} .. {max(ys):7.2f}  ({max(ys)-min(ys):.2f} mm)")
    print(f"  Z {min(zs):7.2f} .. {max(zs):7.2f}  ({max(zs)-min(zs):.2f} mm)")
