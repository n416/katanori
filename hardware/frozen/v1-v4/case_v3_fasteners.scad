// 筐体 v3 のビスとナットを全部実体で置く（当たりの検査用）。-D CHK= で選ぶ
include <case_v3.scad>
part = "none";
CHK = "list";
// ---- 1 本のビス: p = 頭の下面（座面）, v = 胴の向き（単位ベクトル）, len = 胴の長さ, d = 胴径, hd/hh = 頭
module rot_to(v) { // Z 軸を v に向ける
    if (v == [0, 0, 1]) children();
    else if (v == [0, 0, -1]) rotate([180, 0, 0]) children();
    else if (v == [0, -1, 0]) rotate([90, 0, 0]) children();
    else if (v == [0, 1, 0]) rotate([-90, 0, 0]) children();
    else if (v == [-1, 0, 0]) rotate([0, -90, 0]) children();
    else rotate([0, 90, 0]) children();
}
module shank(p, v, len, d) translate(p) rot_to(v) cylinder(d = d, h = len, $fn = 24);
module head(p, v, hd, hh) translate(p) rot_to(v) mirror([0, 0, 1]) cylinder(d = hd, h = hh, $fn = 32);
module nut(c, v, af, t) translate(c) rot_to(v) translate([0, 0, -t / 2]) cylinder(d = af / cos(30), h = t, $fn = 6);
// ---- 一覧 [名前, 頭の座面, 向き, 長さ, 胴径, 頭径, 頭高, ナット中心(undef で無し), ナット二面幅, ナット厚]
M2D = 2.0; M2HD = 3.0; M2HH = 1.3; M2AF = 4.0; M2T = 1.6;
SCREW_ANG_ = [0, 180]; OLED_PCB_Y_ = 3.0;   // knob_v5 の SCREW_ANG / parts.scad の OLED_PCB_Y（use<> では見えない）
M3D = 3.0; M3HD = 6.0; M3HH = 2.2; M3AF = 5.5; M3T = 2.4;
knob_scr = [for (a = SCREW_ANG_) let (p = KNOB_AT + [7.9 * cos(a), 7.9 * sin(a), 0]) ["KNOB", p + [0, 0, -2.5 - 1.8], [0, 0, -1], 6.0, M2D, M2HD, M2HH, p + [0, 0, -10.5 + 1.1], M2AF, M2T]];
oled_scr = [for (h = oled_top_holes()) ["OLED", [h[0], OLED_PCB_Y_, h[1]], [0, 1, 0], 6.0, M2D, M2HD, M2HH, [h[0], oled_back() + OLED_L_T - 0.9, h[1]], M2AF, M2T]];   // 前から・ナットは L の後ろのポケット
FAST = concat(
    [for (h = HUB_HOLES) ["HUB", [h[0], h[1], -FLOOR_T + M3_HEAD_H], [0, 0, 1], 8.0, M3D, M3HD, M3HH, [h[0], h[1], BOARD_Z + HUB_T + M3T / 2], M3AF, M3T]],
    [for (b = BOSSES_B) let (dy = (b[1] < IN_Y / 2) ? BOSS_B_DY_F : BOSS, c = [b[0] + BOSS / 2, b[1] + dy / 2])
        ["FLOORWALL", [c[0], c[1], -FLOOR_T + SCR_CBT], [0, 0, 1], 15.0, M2D, M2HD, M2HH, [c[0], c[1], BOSS_B_H - NUT_T + M2T / 2], M2AF, M2T]],
    [for (sc = concat(SCR_L, [SCR_R])) ["BRIDGE", [sc[0], sc[1], BR_ZT - SCR_CBT], [0, 0, -1], 15.0, M2D, M2HD, M2HH, [sc[0], sc[1], BR_ZB - NUT_T + M2T / 2], M2AF, M2T]],
    [for (b = BOSSES) let (c = [b[0] + BOSS / 2, b[1] + BOSS / 2]) ["TOP", [c[0], c[1], Z_TOP - SCR_CBT], [0, 0, -1], 6.0, M2D, M2HD, M2HH, [c[0], c[1], IN_Z - NUT_T + M2T / 2], M2AF, M2T]],
    [for (ex = EAR_X) let (c = [(ex[0] + ex[1]) / 2, (EAR_Y0 + EAR_Y1) / 2]) ["EAR", [c[0], c[1], Z_TOP - SCR_CBT], [0, 0, -1], 6.0, M2D, M2HD, M2HH, [c[0], c[1], IN_Z - EAR_T - NUT_T + M2T / 2], M2AF, M2T]],   // 耳を貫いて `ear_col` のナットへ
    oled_scr, knob_scr,
    [["LOCK", [shut_xl(), shut_lock_y(), shut_lock_z()], [1, 0, 0], 6.0, M2D, M2HD, M2HH, [shut_xg() + SHUT_LOCK_B - SHUT_LOCK_NT / 2, shut_lock_y(), shut_lock_z()], M2AF, M2T]],
    [["TCHOLD", tc_hold_scr() + [2.0, 0, 0], [-1, 0, 0], 6.0, M2D, M2HD, M2HH, [2.2 + (NUT_T + 0.2) / 2, tc_hold_scr()[1], tc_hold_scr()[2]], M2AF, M2T]]
);
module fastener(f, with_head = true, with_nut = true) {
    shank(f[1], f[2], f[3], f[4]);
    if (with_head) head(f[1], f[2], f[5], f[6]);
    if (with_nut && !is_undef(f[7])) nut(f[7], f[2], f[8], f[9]);
}
module all_fast() for (f = FAST) color("#222") fastener(f);
module shells_all() { floor_v3(); left_wall_v3(); right_wall_v3(); bridge_v3(); top_plate_raw(); front_plate_raw(); hatch_raw(); front_ears(); oled_brackets(); }
module parts_all() { hub_at(); respeaker_at(); oled_at(); pb_v3(); translate(LIPO_AT) lipo_1000mah();
    translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module();
    translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495(); translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch();
    for (id = PLUGGED_9) housing(id); left_wall_extras(); translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(0); }
if (CHK == "list") for (i = [0 : len(FAST) - 1]) echo(i, FAST[i][0], FAST[i][1], FAST[i][2]);
if (CHK == "show") { all_fast(); color("#b6c0cc", 0.3) shells_all(); }
// ビス同士: i 番と他の全部
if (CHK == "pair") intersection() { fastener(FAST[I]); union() for (j = [0 : len(FAST) - 1]) if (j != I) fastener(FAST[j]); }
// i 番 ↔ 外皮（穴やポケットが無ければ残る）
if (CHK == "shell") intersection() { fastener(FAST[I]); shells_all(); }
if (CHK == "shell_all") intersection() { all_fast(); shells_all(); }
if (CHK == "parts_all") intersection() { all_fast(); parts_all(); }
// i 番 ↔ 中身（自分の相手の部品も含む。OLED/ハブは自分の穴を通る）
if (CHK == "parts") intersection() { fastener(FAST[I]); parts_all(); }
I = 0;
