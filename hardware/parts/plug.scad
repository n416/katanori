// 線の口（DuPont のメスを挿した状態）— **全部の口がこれ 1 つを読む**
//
//   use <plug.scad>
//   plug(n, exit)        // n 本・線が抜ける向き exit=[dx,dy]（局所 XY・単位ベクトル）
//   plug_env(n, exit)    // 当たり検査用の包絡（ハウジング＋曲がり＋線の出だし）
//
// 原点: 1 本目のピンの中心・ヘッダの樹脂の上面（z=0）。ピンは +X へ 2.54 ピッチ。
// 高さの鎖（出どころ: ユーザー 2026-09-05「ピンヘッダは 10、ハウジングは 14」「17 はコネクタまで。曲がりを考慮するなら 20」）
//   樹脂の上面 0 → ハウジングの頭 dupont_h()=14 → 線が横を向く dupont_bend()=3.0 上 = 17
//   （部品面から数えると 2.5 + 14 = 16.5 ≈ 17 が頭、20 が曲がりの頭）
// 曲がりの形は「半径 3.0 の 1/4 円」で置く（AI の模型。数字はユーザーの 3.0）。線の太さは wires.scad と同じ 1.55（✅ 2026-08-20 実測から）。
// 🔴 部品ごとに別の描き方（10 の直書き・3.6 の角箱）を残さない。ここ以外に DuPont を描かない。

use <parts.scad>

PITCH = 2.54;
WIRE_D = 1.55;
STUB  = 4.0;     // 曲がった後、向きを見せるための線の長さ

function _arc(r, ex, n = 6) = [for (i = [0 : n]) let (a = 90 * i / n) [ex[0], ex[1], 0] * (r - r * cos(a)) + [0, 0, r * sin(a)]];

module plug(n, exit = [0, 1], h = dupont_h(), bend = dupont_bend()) {
    e = exit / norm(exit);
    // ハウジング n 個（1 列）
    color("#63b3ed", 0.85) translate([-PITCH / 2, -PITCH / 2, 0]) cube([n * PITCH, PITCH, h]);
    // 線: 頭から真上に出て、半径 bend で exit の向きへ曲がり、STUB だけ進む
    color("#e0b060") for (i = [0 : n - 1]) translate([i * PITCH, 0, h]) {
        pts = concat(_arc(bend, e), [[e[0], e[1], 0] * (bend + STUB) + [0, 0, bend]]);
        for (k = [0 : len(pts) - 2]) hull() { translate(pts[k]) sphere(d = WIRE_D, $fn = 10); translate(pts[k + 1]) sphere(d = WIRE_D, $fn = 10); }
    }
}
// 包絡（塊）。ハウジング＋曲がりの箱＋線の出だし
module plug_env(n, exit = [0, 1], h = dupont_h(), bend = dupont_bend()) {
    e = exit / norm(exit);
    translate([-PITCH / 2, -PITCH / 2, 0]) cube([n * PITCH, PITCH, h + bend + WIRE_D / 2]);
    hull() for (i = [0, n - 1]) translate([i * PITCH, 0, h + bend]) {
        sphere(d = WIRE_D, $fn = 10);
        translate([e[0], e[1], 0] * (bend + STUB)) sphere(d = WIRE_D, $fn = 10);
    }
}
function plug_top() = dupont_h() + dupont_bend();   // 樹脂の上面から曲がりの頭まで（17.0）

if ($preview && is_undef(PLUG_EMBEDDED)) { plug(4, [0, 1]); translate([15, 0, 0]) plug(2, [-1, 0]); }
