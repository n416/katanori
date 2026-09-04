// 筐体の天板（gap版 = case_pack_front2_gap.scad の箱に載る実物）
//
//   openscad -o top.stl -D 'part="panel"' hardware/case_top.scad
//   （part 未指定なら、つまみ一式を載せた組み立てビュー）
//
// 🔒 **つまみステーションは「入れる」部品ではない。この天板と一体で印刷される。**
//    knob_top.scad の knob_station_add()/cut() を、この板に union/difference して
//    穴・柱・ねじ台ごと1回で焼く。deck STL は卓上テスト用の切れ端で、本番には存在しない。
//
// ---- 座標系 ----
//   X/Y は箱の内寸座標そのまま（case_pack_front2 と同じ）。板は壁の上まで覆う。
//   Z: 天板の上面 = 0、下面 = -DECK_T（knob_top.scad の Z と一致）
//
// ---- ⚠ まだ決まっていないもの（この初版の限界）----
//   ・筐体本体（壁・ねじ受けボス）が未設計。四隅の M2 は**本体側に同じ位置の
//     ボスを作る前提**の先行穴
//   ・スピーカーは前面向きに置いたので、この天板に音穴は無い
//   ・リード用磁石の座 … 距離の実測待ち（A-3）

part = "all";
$fn = 64;

use <knob_top.scad>

// ---- 箱（gap版）から ----
IN_X   = 86;
IN_Y   = 69.1;
WALL   = 2.0;
DECK_T = 2.5;

// ---- つまみの位置（✅ 2026-08-15 ユーザー承認「そこでいいです」）----
KNOB_AT = [IN_X - knob_bay_x() / 2 - 2, 16.1];   // 右寄り・帯の上

// ---- 縁 ----
LIP_W  = 1.2;    // 内側に落ちるスカート（位置決め）
LIP_H  = 2.0;
LIP_CL = 0.25;   // 壁との遊び（穴の縮み0.1込みで現物合わせの初期値）

// ---- 本体との固定 M2×4（⚠ 本体側ボスは未設計。同じ座標で作ること）----
SCREW_AT = [[5, 5], [IN_X - 5, 5], [5, IN_Y - 5], [IN_X - 5, IN_Y - 5]];

module case_top() {
    difference() {
        union() {
            // 板（壁の上まで覆う）
            translate([-WALL, -WALL, -DECK_T])
                cube([IN_X + WALL * 2, IN_Y + WALL * 2, DECK_T]);
            // スカート（内側に落ちて位置を決める）
            difference() {
                translate([LIP_CL, LIP_CL, -DECK_T - LIP_H])
                    cube([IN_X - LIP_CL * 2, IN_Y - LIP_CL * 2, LIP_H]);
                translate([LIP_CL + LIP_W, LIP_CL + LIP_W, -DECK_T - LIP_H - 1])
                    cube([IN_X - (LIP_CL + LIP_W) * 2, IN_Y - (LIP_CL + LIP_W) * 2,
                          LIP_H + 2]);
                // ⚠ スカートはつまみの柱・ねじ台と干渉しない位置関係だが、
                //    本体の壁の内側の物（基板の縁など）とは本体設計時に照合すること
            }
            // つまみステーション（柱・ねじ台）
            translate([KNOB_AT[0], KNOB_AT[1], 0]) knob_station_add();
        }
        // つまみの落とし込み穴
        translate([KNOB_AT[0], KNOB_AT[1], 0]) knob_station_cut();
        // 本体固定の M2（皿もみ無し・なべ頭のザグリ）
        for (p = SCREW_AT) translate([p[0], p[1], 0]) {
            translate([0, 0, -DECK_T - LIP_H - 1]) cylinder(d = 2.4, h = DECK_T + LIP_H + 2);
            translate([0, 0, -1.2]) cylinder(d = 4.6, h = 1.3);   // 頭 φ3.8 + 遊び
        }
    }
}

module top_assembly() {
    color("#9aa5b1", 0.85) case_top();
    translate([KNOB_AT[0], KNOB_AT[1], 0]) {
        assembly();   // knob_top.scad のつまみ・リング・球・AS5600
    }
}

if (part == "panel") rotate([180, 0, 0]) case_top();   // 反転で最下点が Z=0
else                 top_assembly();

echo(str("天板 ", IN_X + WALL * 2, " × ", IN_Y + WALL * 2, " × ", DECK_T,
         "（＋スカート", LIP_H, "）  つまみ中心 ", KNOB_AT));
