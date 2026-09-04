#!/usr/bin/env python3
"""2回目に刷るもの。1枚のSTLに2つのゲージを入れてある。

  1. 磁石ポケットのゲージ（gen_magnet_gauge.py と同じもの）
  2. 板バネ（片持ち梁）のゲージ ← ここで追加

2 を足した理由: 1回目の薄壁（長さ8mmの短冊）が、0.3mm でも 0.5mm でも
「折れないが戻らない」だった。原因の候補が2つあり、

  - 材料: レジン①（水洗い）の弾性回復が弱い
  - 形状: 梁が短すぎた（表面ひずみは長さの2乗で効く）

**今回もレジン①なので、切り分けられるのは形状（長さ）だけ。** それでも
「長くすれば戻るのか」に答えが出るので、材料へ進む前にやる価値がある。

前回との違いは支持条件。前回はただの短冊を指で曲げただけで、根元が固定されて
いなかった。今回は**根元を桟に固定した本物の片持ち梁**にしてある。

向き: 刃はプレートに寝かせず「立てて」ある（厚みが水平方向）。厚みをZに取ると
ボトム層（35秒露光の5層＝0.25mm）が刃の大部分を占めてしまい、過硬化した層の
硬さを測ることになる。立てれば刃はどの高さも同じ露光で焼かれる。

使い方:
    python hardware/gen_run2.py
"""

from pathlib import Path

from gen_test_plate import box, write_stl
from gen_magnet_gauge import build as build_magnet_gauge

THICKNESS = (0.4, 0.6, 0.8)     # 刃の厚み（水平方向）
LENGTH = (12.0, 18.0, 24.0)     # 刃の長さ（根元から先端まで）
BLADE_H = 3.0                   # 刃の高さ。1回目の薄壁と同じにして比較できるように
PITCH = 9.0                     # 刃の間隔。指を入れてしならせるので広めに取る

BASE_Y = 6.0                    # 桟の手前側。磁石ゲージ（y≤4.8）と当たらない位置
BASE_D = 4.0                    # 桟の奥行き
BASE_MARGIN = 4.0               # 桟を刃の両端より外へ伸ばす量


def build_spring_gauge():
    """厚み3種 × 長さ3種 = 9枚の片持ち梁を、1本の桟に生やした櫛。

    並びは左から「厚み0.4の短中長 / 0.6の短中長 / 0.8の短中長」。
    長さの短中長が3回くり返すので、その切れ目が厚みの境目になる。
    """
    tris = []
    blades = [(t, l) for t in THICKNESS for l in LENGTH]
    x0 = -PITCH * (len(blades) - 1) / 2

    for i, (t, length) in enumerate(blades):
        x = x0 + PITCH * i
        tris += box(x - t / 2, BASE_Y + BASE_D, 0.0, t, length, BLADE_H)

    # 桟。9枚の根元をつないで1枚にする（バラバラの小部品にしない）
    tris += box(x0 - BASE_MARGIN, BASE_Y, 0.0,
                PITCH * (len(blades) - 1) + BASE_MARGIN * 2, BASE_D, BLADE_H)

    return tris


if __name__ == "__main__":
    tris = build_magnet_gauge() + build_spring_gauge()
    out = Path(__file__).with_name("print-run-2.stl")
    write_stl(out, tris)

    xs = [v[0] for _, *vs in tris for v in vs]
    ys = [v[1] for _, *vs in tris for v in vs]
    zs = [v[2] for _, *vs in tris for v in vs]
    print(f"{out.name}: {len(tris)} triangles")
    print(f"  刃: 厚み {THICKNESS} × 長さ {LENGTH} = {len(THICKNESS) * len(LENGTH)}枚")
    print(f"  X {min(xs):7.2f} .. {max(xs):7.2f}  ({max(xs)-min(xs):.2f} mm)")
    print(f"  Y {min(ys):7.2f} .. {max(ys):7.2f}  ({max(ys)-min(ys):.2f} mm)")
    print(f"  Z {min(zs):7.2f} .. {max(zs):7.2f}  ({max(zs)-min(zs):.2f} mm)")
