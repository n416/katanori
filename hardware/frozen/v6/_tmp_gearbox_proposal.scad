// 【提案・未実装】ギアボックスの形を見るためだけのファイル（機構担当・2026-09-13）
//   🔴 _v6_gear.scad / _v6_portrait.scad は 1 文字も触っていない。ここから読むだけ。
//   形が通ったら _v6_gear.scad へ 1 回で入れて、このファイルは消す。
part = "gbox";
include <_v6_gear.scad>

BOX_TOP   = WALL_IN;          // 21.00 天井＝前の壁の内面（そのまま使う）
BOX_IN    = 2.00;             // 内のり（中継 1.70 ＋ 遊び 0.30）
BOX_FLOOR = BOX_TOP - BOX_IN; // 19.00 床の上面
BOX_FT    = 1.50;             // 床の肉
BOX_BOT   = BOX_FLOOR - BOX_FT;   // 17.50 床の下面
BOX_WALL  = 1.00;             // 側壁の肉
CL_SHELL  = 0.30;             // 歯先 ↔ 壁（前の殻と同じ鎖）
CL_STACK  = 0.85;             // 歯先 ↔ 壁（スタックの鎖 0.55 ＋ 逃げ 0.30）
SG_HOLE   = 15.70;            // 読み取りの下は開ける（歯先 φ14.85 が通る）

module box_hull(extra) hull() {
    translate([KN_C[0],  KN_C[1]])  circle(r = g_ra(GEAR_N)  + CL_SHELL + extra);
    translate([IDLER[0], IDLER[1]]) circle(r = g_ra(GEAR_NI) + CL_SHELL + extra);
    translate([SENS[0],  SENS[1]])  circle(r = g_ra(GEAR_N)  + CL_STACK + extra);
}
module gearbox() color("#8a9ba8", 0.55) difference() {
    union() {
        linear_extrude(BOX_FLOOR - BOX_BOT) box_hull(BOX_WALL);                    // 床
        translate([0, 0, BOX_BOT]) linear_extrude(BOX_TOP - BOX_BOT) box_hull(BOX_WALL);
    }
    translate([0, 0, BOX_FLOOR]) linear_extrude(BOX_IN + 1) box_hull(0);           // 中の空
    translate([SENS[0], SENS[1], BOX_BOT - 1])
        cylinder(d = SG_HOLE, h = BOX_FLOOR - BOX_BOT + 2);                        // 読み取りの下は開ける
    translate([KN_C[0], KN_C[1], BOX_TOP - 1]) cylinder(d = KN_BORE, h = 3);
}
if (part == "gbox") {
    translate([0, 0, BOX_BOT]) {}
    gearbox();
    knob_hub(); idler(); sgear(); rotor(); rotor_magnet(); idler_pin(); brk();
    color("#c9c2a8", 0.30) translate([-2, -2, WALL_IN]) cube([BODY_X + 4, BODY_Y + 4, WALL]);
    color("#c9d3c9", 0.35) translate([RS_X, RS_Y, BOX_BOT - 0.95 - 1.85]) cube([34.007, 82.024, 1.85]);
}

// ---- 提案の当たり検査（実体は空 or 0 が正・対照は反応が正）----
module rs_new() translate([RS_X, RS_Y, BOX_BOT - 0.95 - 1.85]) cube([34.007, 82.024, 1.85]);
module mic_u4() translate([RS_X + 15.25, RS_Y + 4.16, BOX_BOT - 0.95]) cube([3.50, 2.65, 1.28]);
module mic_u5() translate([RS_X + 15.25, RS_Y + 75.16, BOX_BOT - 0.95]) cube([3.50, 2.65, 1.28]);
module sw_k1()  translate([RS_X + 4.11, RS_Y + 1.23, BOX_BOT - 0.95]) cube([3.20, 4.60, 2.58]);
module sw_k2()  translate([RS_X + 4.16, RS_Y + 8.92, BOX_BOT - 0.95]) cube([3.20, 4.60, 2.58]);
if (part == "bx_khub")  intersection() { gearbox(); knob_hub(); }
if (part == "bx_idler") intersection() { gearbox(); idler(); }
if (part == "bx_sgear") intersection() { gearbox(); sgear(); }
if (part == "bx_rotor") intersection() { gearbox(); union() { rotor(); brk(); } }
if (part == "bx_rs")    intersection() { gearbox(); rs_new(); }
if (part == "bx_mic")   intersection() { gearbox(); union() { mic_u4(); mic_u5(); sw_k1(); sw_k2(); } }
if (part == "bx_ceil")  intersection() { gearbox();
    translate([-2, -2, WALL_IN]) cube([BODY_X + 4, BODY_Y + 4, WALL]); }
// 対照
if (part == "bx_c1") intersection() { translate([-2, -2, WALL_IN]) cube([BODY_X + 4, BODY_Y + 4, WALL]);
                                     translate([0, 0, 0.30]) idler(); }   // 中継を 0.30 上げ→天井に食い込むはず
if (part == "bx_c2") intersection() { gearbox(); translate([0, 0, -0.30]) idler(); }  // 中継を 0.30 下げ→床に当たるはず
if (part == "bx_c3") intersection() { gearbox(); translate([1.20, 0, 0]) sgear(); }    // 読み取りを X へ 1.20→側壁に当たるはず
if (part == "bx_c4") intersection() { gearbox(); translate([0, 0, 1.20]) rs_new(); }  // 板を 1.20 上げ→床に当たるはず
if (part == "bx_c5") intersection() { gearbox(); translate([0, 16, 0]) mic_u4(); }     // マイクを Y へ 16 寄せ→つまみの下へ入るはず
