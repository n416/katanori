// +X の耳の真下（1.085mm のスラブ）に、プレートまで下ろせる柱の場所が在るか。
//   形は本体のモジュールから取る（_btn_v3_fit.scad と同じ流儀・自分で描かない）。
//   MODE="slab" 障害物の実体 / "free" 全高すきとおる列（＝ここなら足を下ろせる）/ "obst" 障害物の影
include <btn_v3.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN3_SOLO = false;
MODE = "free";
I = 0;   // 0 = +X 側の耳

echo(str("PROBE 生存確認: BTN4=", BTN4, " Z_TOP=", Z_TOP,
         " ear_z0=", b3_ear_z0(I), " tub_b=", B3_Z_TUB_B, " 浮き=", b3_ear_z0(I) - B3_Z_TUB_B));

module ear_foot_2d() translate([0, B3_BLK_DY[I]])
    translate([B3_TUB_OX / 2 - 1, B3_TUB_CY - B3_BLK_W / 2])
        square([B3_EAR_XO - B3_TUB_OX / 2 + 1, B3_BLK_W]);
module ear_slab() translate([0, 0, B3_Z_TUB_B])
    linear_extrude(b3_ear_z0(I) - B3_Z_TUB_B) ear_foot_2d();

module at_world() translate([BTN4[0], BTN4[1], Z_TOP]) children();

module obstacles() intersection() { at_world() ear_slab(); innards4(); }

if (MODE == "slab") obstacles();
if (MODE == "obst") linear_extrude(1) projection() obstacles();
if (MODE == "free") linear_extrude(1) difference() {
    at_world() ear_foot_2d();
    projection() obstacles();
}

// ---- 絵（刷る向きの真上から。バスタブの輪郭＋耳の足あと＋塞がっている影）----
module unworld() translate([-BTN4[0], -BTN4[1], 0]) children();
if (MODE == "pic") {
    color("#c8ced6") linear_extrude(0.4) projection() btn3_tub();               // バスタブ（灰）
    color("#4c8f4c") translate([0, 0, 0.5]) linear_extrude(0.4) difference() {  // 足を下ろせる所（緑）
        ear_foot_2d(); unworld() projection() obstacles(); }
    color("#c04040") translate([0, 0, 1.0]) linear_extrude(0.4)                 // 電池／INA の影（赤）
        unworld() projection() obstacles();
}

// ---- 誰が塞いでいるか（相手ごと・0 が正）----
W = "none";
module one_target() {
    if (W == "bat") bat_v4();
    else if (W == "ina") ina_bat();
    else if (W == "pb") { pb_bat(); pbl_hous(); pbu_hous(); }
    else if (W == "brg") { brg_v4(); brg_front(); }
    else if (W == "straps") straps_v4();
    else if (W == "posts") posts_v4();
    else if (W == "wpwr") wires_pwr();
    else if (W == "wsig") wires_sig();
    else if (W == "oledh") oled_hous();
    else if (W == "oled") oled_at();
    else if (W == "hub") hub_unit();
    else if (W == "rsp") { respeaker_at(); xiao_hous(); rsp_j2_space(); }
    else if (W == "door") door4();
    else if (W == "core") core();
}
if (MODE == "who") intersection() { at_world() ear_slab(); one_target(); }
if (MODE == "slabonly") at_world() ear_slab();

// ---- 足そのものを innards4 の相手に 1 つずつ当てる（0 が正）----
//   ⚠ 相手の一覧は case_v4.scad の innards4() ＋ _v4_core.scad の core() を**数え直した物**。
//     あちらに部品が増えたらここも足す（漏れると「全部 0」が嘘になる・2026-08-30 の事故）
module one_target2() {
    if (W == "tgl") tgl_v4();
    else if (W == "tcb") tcb_v4();
    else if (W == "seat") tc_seat4();
    else if (W == "spk") translate([SPK4[0], SPK4[1], IN_Z - spk_th() - 0.2 + SPK_LIFT])
                             translate([-SPK_L / 2, -SPK_W / 2, 0]) speaker_112495();
    else if (W == "knob") translate([KNOB_DX, KNOB_DY, 0]) knob_at_v4();
    else if (W == "sw") btn3_at_switch();
    else if (W == "piston") btn3_at_piston();
    else if (W == "screws") btn3_at_screws();
    else if (W == "skin") { for (k = SKINS) skin1(k); }
    else if (W == "tub") btn3_at_tub();   // 🔒 これは当たって当然（検査が生きている確認）
    else one_target();
}
module ear_foot_solid() at_world() difference() {
    translate([B3_TUB_OX / 2 - 1, b3_ear_foot_y0(), B3_Z_TUB_B])
        cube([B3_EAR_XO - B3_TUB_OX / 2 + 1, B3_EAR_FOOT_Y1 - b3_ear_foot_y0(),
              b3_ear_z0(0) - B3_Z_TUB_B]);
    btn3_v_screw_cut();
}
if (MODE == "foot") intersection() { ear_foot_solid(); one_target2(); }
if (MODE == "footonly") ear_foot_solid();
