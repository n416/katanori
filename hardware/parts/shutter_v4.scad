// ============================================================
// 電池の蓋（後ろ抜き・横（右へ）スライド）—— v4 の形（frozen/v1-v4/case_v4_shutter.scad ＋ case_v3_shutter.scad の定数）を v5 用に写した（2026-09-05）
//   🔒 実機で確かめた数字はそのまま: 磁石 φ6.00 圧入（ELEGOO 透明・2026-09-02）、ロック ⇔ 蓋 0.20、ナット二面幅 4.10、六角の床 0.80、レール 6mm 以外は塞いでよい
//   case_v5.scad から include する。要る変数: BAT_X0・BAT_Z（電池の下面）・lipo_size()・IN_Y・HATCH_T・WALL
//   刷る物: 蓋（battery_shutter4）・ロック（battery_lock4）・床の板（sw4_floor_plate）。ハッチ側の縁（sw4_hatch_rim）はハッチと一体
//   v5 で外した物: 電源の線（w_pwr3）での削り（v5 は線の模型が無い）、ハッチのリブとの検算（v5 はリブ未設計）
// ============================================================
SHUT_T     = 2.75;  // 板厚。磁石 2.0 ＋ 外面の肉 0.75
SHUT_EAR_T = 0.75;  // 耳の厚み。🔒 電池の押しはここが受ける
SHUT_LIP   = 0.70;  // リップの厚み（外面から）
SHUT_EAR   = 1.60;  // 耳の掛かり（片側）
SHUT_EAR_H = 4.50;  // 耳の丈
SHUT_SLIDE = 5.50;  // 逃がすためにずらす量（耳の丈 + 1.0）
SHUT_CL    = 0.25;  // 隙間
SHUT_MARG  = 0.80;  // 開口を被る量
SHUT_BACK  = 2.20;  // 壁の内面から裏へ足す肉
SHUT_R     = 2.50;  // 角丸
SHUT_EXT   = 6.80;  // 蓋を口の外へ伸ばす量（磁石の部屋・🔒 2026-09-02）
SHUT_MAG_D = 6.00;  // 磁石の穴 ✅ 2026-09-02 実機（ELEGOO）
SHUT_MAG_H = 2.00;  // 磁石の厚み（📄 φ6 × 2.0）
SHUT_LK_T   = 1.20; // 舌（中央の半円）の厚み
SHUT_LK_R   = 5.00; // 半円の半径
SHUT_LK_DIP = 2.50; // 半円が蓋へ下りる量
SHUT_LK_RF  = 0.50; // 脚の足先・外側の角丸
SHUT_LK_CL  = 0.20; // ロック ⇔ 蓋 ✅ 2026-09-02 実機
SHUT_LOCK_D   = 2.50;  // M2 の通し
SHUT_LOCK_NAF = 4.10;  // M2 ナットの二面幅 ✅ 2026-09-02
SHUT_LOCK_NT  = 1.80;  // 同 厚み
SHUT_LOCK_B   = 3.60;  // 彫り込みの床から内側へ立てるボスの厚み
SHUT_LOCK_FLR = 0.80;  // ナットを載せる床の厚み
SHUT_LOCK_CB  = 4.40;  // ネジ頭のザグリ径
SHUT_LOCK_CBT = 1.60;  // 同 深さ

SW4_X0 = BAT_X0 - 0.5;                        // 口（電池の断面 35 × 6 ＋ 逃げ 0.5）
SW4_X1 = BAT_X0 + lipo_size()[1] + 0.5;
SW4_Z0 = BAT_Z - 0.5;
SW4_Z1 = BAT_Z + lipo_size()[2] + 0.5;
SW4_YOUT = IN_Y + HATCH_T;                    // ハッチの外面
SW4_NOSE_R = 4.3;    // 🔒 ロックの外端の半円（ビスが中心）
SW4_FILLET = 0.8;    // 🔒 舌が枠に刺さる 2 か所の入り隅の角

// ---- Y の面（外面から中へ）----
function sw4_yb() = SW4_YOUT - SHUT_T;        // 蓋の裏面
function sw4_yl() = SW4_YOUT - SHUT_LIP;      // リップの裏面
function sw4_yg() = sw4_yb() - SHUT_CL;       // 彫り込み（溝）の床
function sw4_ye() = sw4_yl() - SHUT_CL;       // 耳の外面側

// ---- 蓋（X の両端に磁石の部屋・右だけ 1.8 広い 🔒 2026-09-04）----
SW4_EXT_L = SHUT_EXT;
SW4_EXT_R = SHUT_EXT + 1.8;
function sw4_lx0() = SW4_X0 - SHUT_MARG - SW4_EXT_L;
function sw4_lx1() = SW4_X1 + SHUT_MARG + SW4_EXT_R;
function sw4_lz0() = SW4_Z0 - SHUT_MARG;
function sw4_lz1() = SW4_Z1 + SHUT_MARG;
function sw4_lw()  = sw4_lx1() - sw4_lx0();
// ---- 帯（彫り込み）----
function sw4_bx0() = sw4_lx0() - SHUT_CL;
function sw4_bx1() = sw4_lx1() + SHUT_SLIDE + SHUT_CL;
function sw4_bz0() = sw4_lz0() - SHUT_EAR - SHUT_CL;
function sw4_bz1() = sw4_lz1() + SHUT_EAR + SHUT_CL;
// ---- 耳（上下 1 個ずつ・X の中央）----
function sw4_ex0()  = sw4_lx0() + (sw4_lw() - SHUT_EAR_H) / 2;
function sw4_lend() = sw4_ex0() + SHUT_EAR_H + 0.5;   // リップの右端（閉の耳の先 +0.5）＝逃がし口の左端
// ---- 磁石（🔒 芯は蓋の外周から数える。左は蓋の端から、右は電池の口から）----
SW4_MAG_WALL = 1.00;
SW4_MAG_IN   = 0.60;
function sw4_mag_z()  = (sw4_lz0() + sw4_lz1()) / 2;
function sw4_mag_xs() = [sw4_lx0() + SW4_MAG_WALL + SHUT_MAG_D / 2, SW4_X1 + SW4_MAG_IN + SHUT_MAG_D / 2];
function sw4_mag_inner_l() = SW4_X0 - (sw4_mag_xs()[0] + SHUT_MAG_D / 2);
function sw4_mag_inner_r() = (sw4_mag_xs()[1] - SHUT_MAG_D / 2) - SW4_X1;
function sw4_mag_outer_r() = sw4_lx1() - (sw4_mag_xs()[1] + SHUT_MAG_D / 2);
assert(sw4_mag_inner_l() >= 0.42 && sw4_mag_inner_r() >= 0.42, "磁石の座と電池の口の間の壁が 0.42 を切る");
assert(sw4_mag_outer_r() >= SW4_MAG_WALL, "右の磁石と蓋の端の肉が SW4_MAG_WALL を切る");
assert(sw4_lk_xr() - SHUT_LK_DIP >= sw4_mag_xs()[1] + SHUT_MAG_D / 2 + 0.4, "ロックの舌が右の磁石に掛かる");
// ---- ロック（門形を右へ回したもの: 帯の右端に縦棒・脚は左・舌は蓋の右端に乗る）----
function sw4_lk_xr()   = sw4_lx1() + SHUT_LK_CL;
function sw4_lock_x()  = sw4_lk_xr() + SHUT_LOCK_CB / 2;
function sw4_lock_z()  = (sw4_lz0() + sw4_lz1()) / 2;
function sw4_lk_x1()   = sw4_bx1() - SHUT_CL;
function sw4_lk_x0()   = sw4_lend() + SHUT_CL;
function sw4_lk_z0()   = sw4_bz0() + SHUT_CL;
function sw4_lk_z1()   = sw4_bz1() - SHUT_CL;
function sw4_lk_boss_z1() = sw4_lz1() + 3.0;

// ---- 道具 ----
module sw4_ext(y0, ylen) translate([0, y0 + ylen, 0]) rotate([90, 0, 0]) linear_extrude(ylen) children();
module sw4_fillet(f) offset(r = -f) offset(r = f) children();
module sw4_rrect(y0, ylen, x0, x1, z0, z1, r) {
    hull() for (x = [x0 + r, x1 - r], z = [z0 + r, z1 - r])
        translate([x, y0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = ylen, $fn = 48);
}
module sw4_magnets(y0, h) { for (x = sw4_mag_xs()) translate([x, y0, sw4_mag_z()]) rotate([-90, 0, 0]) cylinder(d = SHUT_MAG_D, h = h, $fn = 48); }
module sw4_lock_bore(y0, h, d) { translate([sw4_lock_x(), y0, sw4_lock_z()]) rotate([-90, 0, 0]) cylinder(d = d, h = h, $fn = 32); }

// ---- ロックの 2D 輪郭 ----
module sw4_nose_2d() translate([sw4_lock_x(), sw4_lock_z()]) circle(r = SW4_NOSE_R, $fn = 64);
module sw4_lk_end_2d() { r = SHUT_LK_RF; for (z = [sw4_lk_z0() + r, sw4_lk_z1() - r]) translate([sw4_lk_x1() - r, z]) circle(r = r, $fn = 32); }
module sw4_lk_leg_2d() { rf = SHUT_LK_RF; for (z = [sw4_lk_z0() + rf, sw4_lk_z1() - rf]) translate([sw4_lk_x0() + rf, z]) circle(r = rf, $fn = 32); }
module sw4_lk_frame_2d() hull() { sw4_lk_end_2d(); sw4_lk_leg_2d(); }
module sw4_lk_out_2d()   union() { sw4_lk_frame_2d(); sw4_nose_2d(); }
module sw4_lk_hole_2d() {
    ri = SHUT_R - SHUT_CL + SHUT_LK_CL;
    hull() {
        for (z = [sw4_lz0() - SHUT_LK_CL + ri, sw4_lz1() + SHUT_LK_CL - ri]) translate([sw4_lk_xr() - ri, z]) circle(r = ri, $fn = 64);
        translate([sw4_lk_x0() - 3, sw4_lz0() - SHUT_LK_CL]) square([3, sw4_lz1() - sw4_lz0() + 2 * SHUT_LK_CL]);
    }
}
module sw4_lk_tongue_2d() {
    intersection() {
        translate([sw4_lk_xr() + SHUT_LK_R - SHUT_LK_DIP, sw4_lock_z()]) circle(r = SHUT_LK_R, $fn = 64);
        translate([sw4_lk_xr() - SHUT_LK_DIP, sw4_lock_z() - SHUT_LK_R - 1]) square([SHUT_LK_DIP, (SHUT_LK_R + 1) * 2]);
    }
}
module sw4_lk_body_2d() difference() { sw4_lk_out_2d(); sw4_lk_hole_2d(); }
module sw4_lk_face_2d() union() {
    sw4_fillet(SW4_FILLET) union() { difference() { sw4_lk_frame_2d(); sw4_lk_hole_2d(); } sw4_lk_tongue_2d(); }
    sw4_lk_body_2d();
}
module sw4_lk_lap_2d() intersection() { sw4_lk_face_2d(); sw4_lk_hole_2d(); }

// ---- 刷る部品 ----
module battery_shutter4(open = 0) {   // 蓋。open = 0 で閉、1 で右へ SHUT_SLIDE ずらし切った状態
    translate([open * SHUT_SLIDE, 0, 0]) difference() {
        union() {
            sw4_rrect(sw4_yb(), SHUT_T, sw4_lx0(), sw4_lx1(), sw4_lz0(), sw4_lz1(), SHUT_R - SHUT_CL);
            for (z = [sw4_lz0() - SHUT_EAR, sw4_lz1()]) translate([sw4_ex0(), sw4_ye() - SHUT_EAR_T, z]) cube([SHUT_EAR_H, SHUT_EAR_T, SHUT_EAR]);   // 上下の耳
        }
        sw4_magnets(sw4_yb() - 0.01, SHUT_MAG_H + 0.01);                                            // 磁石は裏面から埋める（外面に 0.75 残る）
        sw4_ext(SW4_YOUT - SHUT_LK_T - SHUT_LK_CL, SHUT_LK_T + SHUT_LK_CL + 0.01) offset(r = SHUT_LK_CL) sw4_lk_lap_2d();   // 舌の逃げ
    }
}
module battery_lock4() {   // ロック
    difference() {
        union() {
            sw4_ext(sw4_yg(), SW4_YOUT - sw4_yg() - SHUT_LK_T) sw4_lk_body_2d();
            sw4_ext(SW4_YOUT - SHUT_LK_T, SHUT_LK_T) sw4_lk_face_2d();
        }
        sw4_lock_bore(sw4_yg() - 2, SW4_YOUT - sw4_yg() + 4, SHUT_LOCK_D);
        sw4_lock_bore(SW4_YOUT - SHUT_LOCK_CBT, SHUT_LOCK_CBT + 0.01, SHUT_LOCK_CB);
    }
}

// ---- ハッチから引くもの ----
module battery_port_cut4() translate([SW4_X0, sw4_yg() - SHUT_BACK - 1, SW4_Z0]) cube([SW4_X1 - SW4_X0, SHUT_BACK + SHUT_T + 2, SW4_Z1 - SW4_Z0]);   // 口（蓋が塞ぐのでベベル無し）
SW4_RAIL_LEAD = SHUT_R + SHUT_CL;
function sw4_rail_x0() = sw4_ex0() - SW4_RAIL_LEAD;
module sw4_band_cut(u = 1.0) {   // 彫り込み（🔒 レールは耳が届く所だけ・2026-09-04）
    y0 = sw4_yg() - u;
    sw4_rrect(y0, sw4_yl() - y0, sw4_bx0(), sw4_bx1(), sw4_lz0() - SHUT_CL, sw4_lz1() + SHUT_CL, SHUT_R);      // 蓋の本体が走る溝
    sw4_rrect(y0, sw4_yl() - y0, sw4_rail_x0(), sw4_bx1(), sw4_bz0(), sw4_bz1(), SHUT_R);                      // 耳が走るレール
    sw4_rrect(sw4_yl() - 0.01, SHUT_LIP + 0.02, sw4_bx0(), sw4_bx1(), sw4_lz0() - SHUT_CL, sw4_lz1() + SHUT_CL, SHUT_R);   // 蓋の本体が出る窓
    sw4_ext(y0, SW4_YOUT - y0 + 0.01) offset(r = SHUT_CL) sw4_lk_out_2d();                                      // ロックが座る所（耳の逃がし口を兼ねる）
    sw4_magnets(sw4_yg() - SHUT_MAG_H, SHUT_MAG_H + 0.01);                                                      // 相手側の磁石の座
}
SW4_MAG_WIN_D = 4.1;   // 磁石の芯の窓（🔒 2026-08-29 蓋で見えなくなるので枠だけ残す）
module sw4_mag_window() for (x = sw4_mag_xs()) translate([x, sw4_yg() - 4.0, sw4_mag_z()]) rotate([-90, 0, 0]) cylinder(d = SW4_MAG_WIN_D, h = 6.0, $fn = 48);
module sw4_lock_cut() {
    sw4_lock_bore(sw4_yg() - SHUT_LOCK_B - 2, SHUT_LOCK_B + SHUT_T + 4, SHUT_LOCK_D);
    translate([sw4_lock_x(), sw4_yg() - SHUT_LOCK_B - 0.01, sw4_lock_z()]) rotate([-90, 0, 0]) rotate([0, 0, 30]) cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT + 0.02, $fn = 6);   // ナットの六角ポケット
    translate([sw4_lock_x() - SHUT_LOCK_NAF / 2, sw4_yg() - SHUT_LOCK_B - 0.01, sw4_lock_z()]) cube([SHUT_LOCK_NAF, SHUT_LOCK_NT + 0.02, sw4_lk_boss_z1() - sw4_lock_z() + 0.01]);   // 落とす溝
}
// ---- 彫ったぶんハッチの裏へ足す肉（🔒 2026-09-04 溝の床 Y = IN_Y − 1.0 で 2 部品に割る: ハッチの縁と床の板）----
function sw4_lock_boss_z0() = sw4_lock_z() - SHUT_LOCK_NAF / cos(30) / 2 - SHUT_LOCK_FLR;
SW4_BOSS_W = 7.0;
module sw4_lock_boss() translate([sw4_lock_x() - SW4_BOSS_W / 2, sw4_yg() - SHUT_LOCK_B, sw4_lock_boss_z0()]) cube([SW4_BOSS_W, SHUT_LOCK_B, sw4_lk_boss_z1() - sw4_lock_boss_z0()]);
assert(SW4_BOSS_W / 2 - SHUT_LOCK_NAF / cos(30) / 2 >= 0.42, "ロックのナットのボスの壁が 0.42 を切る");
SW4_BACK_FL = 1.0;   // つばの出
SW4_BACK_CL = 0.3;   // 当たる部品との隙間
module sw4_dilate(cl) for (d = [[0, 0, 0], [cl, 0, 0], [-cl, 0, 0], [0, cl, 0], [0, -cl, 0], [0, 0, cl], [0, 0, -cl]]) translate(d) children();
module sw4_backing_carve(cl) sw4_dilate(cl) sw4_carve_targets();   // 当たる相手は case_v5 の sw4_carve_targets() が持つ（v5: Type-C 基板）
// 位置決めの爪 2 個（ハッチの縁に立ち、床の板の欠きに入る。貼るとき磁石とねじ無しで位置が決まる。🔒 ユーザー 2026-09-05「なら戻そう」）
//   爪はハッチ側（板側に立てると寝かせて刷るとき爪が最下層になり板の本体が一度に現れる）
SW4_REG_H  = 1.0;  SW4_REG_W  = 3.0;  SW4_REG_L  = 1.0;  SW4_REG_CL = 0.25;
SW4_REG_BX = 30.0;   // ② の X の中心
module sw4_reg_2d(g) {
    translate([sw4_bx0() - SW4_BACK_FL - g, sw4_mag_z() - SW4_REG_W / 2 - g]) square([SW4_REG_L + 2 * g, SW4_REG_W + 2 * g]);   // ① 左の端
    translate([SW4_REG_BX - SW4_REG_W / 2 - g, sw4_bz0() - SW4_BACK_FL - g]) square([SW4_REG_W + 2 * g, SW4_REG_L + 2 * g]);   // ② 下の帯
}
module sw4_rrect2d(x0, x1, z0, z1, r) hull() for (x = [x0 + r, x1 - r], z = [z0 + r, z1 - r]) translate([x, z]) circle(r = r, $fn = 48);
module sw4_flange_2d() difference() {
    union() {
        sw4_rrect2d(sw4_bx0() - SW4_BACK_FL, sw4_bx1() + SW4_BACK_FL, sw4_bz0() - SW4_BACK_FL, sw4_bz1() + SW4_BACK_FL, SHUT_R + SW4_BACK_FL);
        offset(r = SHUT_CL + 1.0) sw4_lk_out_2d();
        sw4_tabs_2d();
    }
    sw4_flange_notch_2d();   // つばを欠く所（case_v5 が持つ。v5: トグルの胴の真下・上の縁を 1.0）
}
// のりしろ（🔒 2026-09-05 ユーザー「接着用ののりしろをいくつか」）。v4 の X はハッチのリブの間。v5 はリブ未設計なので同じ X をそのまま
SW4_TAB_XS = [8.1, 25.694, 41.694, 57.694]; SW4_TAB_W = 5.6; SW4_TAB_H = 3.0; SW4_TAB_TOP = false;   // 上ののりしろ 4 個は無し（🔒 ユーザー 2026-09-05「のりしろが減る。別に構わない」: トグルの胴の席を空ける）。下の 4 個だけ
function sw4_tab_rects() = concat(
    [for (x = SW4_TAB_XS) [x - SW4_TAB_W / 2, x + SW4_TAB_W / 2, sw4_bz0() - SW4_BACK_FL - SW4_TAB_H, sw4_bz0() - SW4_BACK_FL + 0.5]],
    SW4_TAB_TOP ? [for (x = SW4_TAB_XS) [x - SW4_TAB_W / 2, x + SW4_TAB_W / 2, sw4_bz1() + SW4_BACK_FL - 0.5, sw4_bz1() + SW4_BACK_FL + 2.5]] : []);
module sw4_tabs_2d() for (r = sw4_tab_rects()) translate([r[0], r[2]]) square([r[1] - r[0], r[3] - r[2]]);
module sw4_floor_plate() difference() {   // 床の板（別部品）: 溝の床から内へ 1.2 ＋ 磁石の座 ＋ ロックのナットのボス
    union() {
        sw4_ext(IN_Y - SHUT_BACK, SHUT_BACK - (IN_Y - sw4_yg())) sw4_flange_2d();
        sw4_lock_boss();
        for (x = sw4_mag_xs()) translate([x, sw4_yg() - SHUT_MAG_H - 0.4, sw4_mag_z()]) rotate([-90, 0, 0]) cylinder(d = SHUT_MAG_D + 2.0, h = SHUT_MAG_H + 0.4 - 0.01, $fn = 48);
    }
    sw4_ext(IN_Y - SHUT_BACK - 1, SHUT_BACK + 2) sw4_reg_2d(SW4_REG_CL);   // 爪が入る欠き（貫通）
    sw4_backing_carve(SW4_BACK_CL);
    battery_port_cut4(); sw4_lock_cut(); sw4_mag_window();   // 電池の口・ロックのねじとナット・磁石の窓（ハッチと同じ物を床の板にも）
}
module sw4_hatch_rim() difference() {   // ハッチ側の縁（溝の床 〜 内面）＋ 位置決めの爪 2 個
    union() {
        sw4_ext(sw4_yg(), IN_Y - sw4_yg()) sw4_flange_2d();
        sw4_ext(sw4_yg() - SW4_REG_H, SW4_REG_H) sw4_reg_2d(0);   // 位置決めの爪 2 個（溝の床から板の側へ 1.0）
    }
    sw4_backing_carve(SW4_BACK_CL);
}
// ---- 絵にだけ出す実体 ----
module sw4_lock_screw() color("#e8e8e8") translate([sw4_lock_x(), sw4_yl(), sw4_lock_z()]) rotate([90, 0, 0]) { cylinder(d = 2.0, h = 6.0, $fn = 24); translate([0, 0, -1.3]) cylinder(d = 3.0, h = 1.3, $fn = 32); }
module sw4_lock_nut() color("#888") translate([sw4_lock_x(), sw4_yg() - SHUT_LOCK_B, sw4_lock_z()]) rotate([-90, 0, 0]) rotate([0, 0, 30]) cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT, $fn = 6);
module sw4_magnets_wall()    color("#c0c0c0") sw4_magnets(sw4_yg() - SHUT_MAG_H, SHUT_MAG_H);
module sw4_magnets_shutter() color("#c0c0c0") sw4_magnets(sw4_yb(), SHUT_MAG_H);   // 蓋の中（裏面から 2.0・外面に 0.75 残る）。🔴 v4 は yb − H（ハッチの座の中）に描いていた
