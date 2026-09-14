// ============================================================
// v6 外形の案（2026-09-13）── ユーザー「ただ四角い箱で、面白みもありません」
//   🔴 中身は 1 つも動かさない。**外形だけ**を替えて並べる。
//   容れ物の条件（動かせない）: 内寸 X 2〜46・Y 2〜86・Z 2〜21 を全部飲むこと。
//   ⇒ 削れるのは「その外側」だけ。いま胴は 48 × 88 × 23 で、内寸の外に片側 2.0 しかない。
//   ⇒ **削れるのは角と稜だけ。面そのものは動かせない。**
//   実行: openscad --backend=manifold -o x.png -D "shape=1" hardware/frozen/v6/_v6_shape.scad
// ============================================================
include <_v6_portrait.scad>
part  = "none";
shape = 0;   // 0 いま ／ 1 背だけ面取り ／ 2 上へ絞る ／ 3 スピーカーを胴へ取り込む ／ 4 前面に段

CH = 6.0;    // 面取りの大きさ
module body() {
    if (shape == 0) cube([BODY_X, BODY_Y, BODY_Z]);

    // ① 背だけ大きく面取り。顔は平らのまま・持つと薄く感じる側を作る
    else if (shape == 1) hull() {
        translate([0, 0, BODY_Z - 0.01]) cube([BODY_X, BODY_Y, 0.01]);          // 顔は 48 × 88 のまま
        translate([CH, CH, 0]) cube([BODY_X - 2 * CH, BODY_Y - 2 * CH, 0.01]);  // 背は 36 × 76
    }

    // ② 上へ絞る。下（つまみ側）48 ・上（口の並ぶ側）42。画面のガラス 40.04 は飲む
    else if (shape == 2) hull() {
        cube([BODY_X, 0.01, BODY_Z]);
        translate([(BODY_X - 42) / 2, BODY_Y - 0.01, 0]) cube([42, 0.01, BODY_Z]);
    }

    // ③ スピーカーの膨らみを胴へ取り込む。いまは 48 の胴に 8.2 のコブが付いて総幅 56.2
    else if (shape == 3) hull() {
        cube([BODY_X, BODY_Y, BODY_Z]);
        translate([-8.2, SPK_CY - 17, BODY_Z / 2 - 9]) cube([8.2, 34, 18]);
    }

    // ④ 顔に段。画面とつまみの帯だけ 1.5 落として、縁を残す
    else if (shape == 4) difference() {
        cube([BODY_X, BODY_Y, BODY_Z]);
        translate([3.0, 12.0, BODY_Z - 1.5]) cube([BODY_X - 6.0, BODY_Y - 24.0, 2]);
    }
}
if (shape >= 0) { shell(); screen(); knob(); side_parts(); }
