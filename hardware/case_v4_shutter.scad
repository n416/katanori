// ============================================================
// 📦 v4 電池の入れ替え口（後ろ抜き）—— v3 の蓋の型（case_v3_shutter.scad）をハッチ面へ写す（2026-08-25）
//   🔒 ユーザー GO「後ろから出すのは配置を指定した時から分かっていた事」。
//   レール＋留め帯＝ +Y にだけ開いた鞘・タブは後ろ向き 🔒 → 口はハッチ。抜く接続は電池の JST 1 本。
//   型は v3 のまま: 蓋（板＋耳＋磁石 2）＋外面の彫り込み帯＋門形ロック（M2＋ナット・外せば磁石だけで開閉）。
//   寸法の定数（SHUT_*・磁石 ✅ゲージ確定 φ6.1）は case_v3_shutter.scad のを共有する。
//   🔴 v3 と違う点 1 つ: **スライドは下（−Z）**。上だと ①帯の裏の増し肉（上端 36.45）が PB の
//      L ピンの線の通り道（Z 35.8）を塞ぐ ②ロックのボス（口の上・中央）が 5V の DuPont（X 30.9〜33.5・
//      Z 34.5〜37.1）に刺さる。下なら増し肉の上端 30.95 で線の下を空け、ロックは口の下（ハブの上の空き）に立つ。
//   軸の写像: v3 左壁（外面 x=-WALL・スライド +Z・耳 ±Y）→ v4 ハッチ（外面 y=74・スライド −Z・耳 ±X）。
//   ⚠ 蓋の裏 ↔ 電池の尻は 8.35 空く（電池は前ガードとこの蓋の間で Y に遊ぶ）。
//      ⬜ 詰め物（v3 のスポンジ TUN_SPG の流儀）はユーザー。
// ============================================================
SW4_X0 = BAT_X0 - 0.5;                        // 口 15.0〜51.0（電池の断面 35 × 6 ＋ 逃げ 0.5）
SW4_X1 = BAT_X0 + lipo_size()[1] + 0.5;
SW4_Z0 = BAT_Z - 0.5;                         // 22.9〜29.9
SW4_Z1 = BAT_Z + lipo_size()[2] + 0.5;
SW4_YOUT = IN_Y + HATCH_T;                    // 外面 74
// Y の面（v3 の X の関数の写し・外面から中へ）
function sw4_yb() = SW4_YOUT - SHUT_T;                 // 71.25 蓋の裏面
function sw4_yl() = SW4_YOUT - SHUT_LIP;               // 73.3  リップの裏面
function sw4_yg() = sw4_yb() - SHUT_CL;                // 71.0  彫り込み（溝）の床
function sw4_ye() = sw4_yl() - SHUT_CL;                // 73.05 耳の前面（リップのすぐ裏・v3 の 🔴 と同じ取り方）
// X（v3 の Y の写し）
function sw4_lx0() = SW4_X0 - SHUT_MARG;               // 14.2 蓋の端
function sw4_lx1() = SW4_X1 + SHUT_MARG;               // 51.8
function sw4_bx0() = sw4_lx0() - SHUT_EAR - SHUT_CL;   // 12.35 帯の端
function sw4_bx1() = sw4_lx1() + SHUT_EAR + SHUT_CL;   // 53.65
// Z（v3 の上下反転。EXT＝磁石の部屋は口の下・スライドも下）
function sw4_lz1() = SW4_Z1 + SHUT_MARG;               // 30.7 蓋の上端
function sw4_lz0() = SW4_Z0 - SHUT_MARG - SHUT_EXT;    // 15.8 蓋の下端（EXT 込み）
function sw4_h()   = sw4_lz1() - sw4_lz0();
function sw4_ez0() = sw4_lz0() + (sw4_h() - SHUT_EAR_H) / 2;   // 21.0 耳の下端（閉）
function sw4_bz1() = sw4_lz1() + SHUT_CL;              // 30.95 帯の上端
function sw4_bz0() = sw4_lz0() - SHUT_SLIDE - SHUT_CL; // 10.05 帯の下端
// 🔒 リップの下端（v3 の shut_ltop の反転）: 閉の耳の足（−0.5）と、ずらし切った耳の頭（+0.5）の間
function sw4_lbot() = sw4_ez0() - 0.5;                 // 20.5
SW4_LK_X = (SW4_X0 + SW4_X1) / 2;             // ロックの中心 X 33（🔒 v3「中央だけ半円」のまま。
                                              //   下スライドなので 5V の DuPont と取り合わない）
function sw4_lk_zb() = sw4_lz0() - SHUT_LK_CL;         // 15.7 蓋の下端（ロックの半円が乗る所）
function sw4_lock_z() = sw4_lk_zb() - SHUT_LOCK_CB / 2;   // 13.5 ネジの高さ（v3 の規則の反転: 頭のザグリが蓋の縁に触れる位置）
// ロックの門形の外形（v3 の反転: 帯の下端側に横棒・脚は上へ・足先は上）
function sw4_lk_x0() = sw4_bx0() + SHUT_CL;
function sw4_lk_x1() = sw4_bx1() - SHUT_CL;
function sw4_lk_z1() = sw4_lbot() - SHUT_CL;           // 20.25 脚の足先（上）
function sw4_lk_z0() = sw4_bz0() + SHUT_CL;            // 10.3  横棒の下端
// 磁石: EXT の部屋の中・蓋の中心から X ±12（v3 の ±Y の写し）
SW4_MAG_Z = 0;   // （下で式。変数の前方参照を避ける）
function sw4_mag_z() = sw4_lz0() + SHUT_EXT / 2;       // 18.95
function sw4_mag_xs() = [SW4_LK_X - SHUT_MAG_DY, SW4_LK_X + SHUT_MAG_DY];   // X 21 / 45

// X-Z 面の角丸長方形を Y 方向へ伸ばす（v3 rrect_x の写し）
module rrect_y(y0, ylen, x0, x1, z0, z1, r) {
    hull() for (x = [x0 + r, x1 - r], z = [z0 + r, z1 - r])
        translate([x, y0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = ylen, $fn = 48);
}
module sw4_magnets(y0, h) {
    for (x = sw4_mag_xs()) translate([x, y0, sw4_mag_z()]) rotate([-90, 0, 0]) cylinder(d = SHUT_MAG_D, h = h, $fn = 48);
}
module sw4_lock_bore(y0, h, d) {
    translate([SW4_LK_X, y0, sw4_lock_z()]) rotate([-90, 0, 0]) cylinder(d = d, h = h, $fn = 32);
}
// 中央の半円（ロックが蓋へ**上に**乗る部分。v3 の反転）
module sw4_lk_tongue(y0, ylen, gap = 0) {
    intersection() {
        translate([SW4_LK_X, y0, sw4_lk_zb() - SHUT_LK_R + SHUT_LK_DIP]) rotate([-90, 0, 0]) cylinder(r = SHUT_LK_R + gap, h = ylen, $fn = 64);
        translate([SW4_LK_X - SHUT_LK_R - 1, y0 - 1, sw4_lk_zb() - gap]) cube([(SHUT_LK_R + 1) * 2, ylen + 2, SHUT_LK_DIP + gap * 2]);
    }
}
// 蓋そのもの（刷る部品）。open = 0 で閉、1 でずらし切った（下へ SHUT_SLIDE）
module battery_shutter4(open = 0) {
    translate([0, 0, -open * SHUT_SLIDE]) difference() {
        union() {
            rrect_y(sw4_yb(), SHUT_T, sw4_lx0(), sw4_lx1(), sw4_lz0(), sw4_lz1(), SHUT_R - SHUT_CL);
            for (x = [sw4_lx0() - SHUT_EAR, sw4_lx1()])
                translate([x, sw4_ye() - SHUT_EAR_T, sw4_ez0()]) cube([SHUT_EAR, SHUT_EAR_T, SHUT_EAR_H]);
        }
        sw4_magnets(sw4_yb() - 0.01, SHUT_MAG_H + 0.01);                       // 磁石は裏面から埋める（外面に 0.75 残る）
        sw4_lk_tongue(SW4_YOUT - SHUT_LK_T - SHUT_LK_CL, SHUT_LK_T + SHUT_LK_CL + 0.01, SHUT_LK_CL);   // 半円の逃げ（外面側）
    }
}
// ロック（刷る部品）。門形（下の横棒＋両端の脚・足先は上）＋中央の半円
module sw4_lk_frame(y0, ylen) {
    r = SHUT_R - SHUT_CL;
    difference() {
        hull() {
            for (x = [sw4_lk_x0() + r, sw4_lk_x1() - r])
                translate([x, y0, sw4_lk_z0() + r]) rotate([-90, 0, 0]) cylinder(r = r, h = ylen, $fn = 48);
            rf = SHUT_LK_RF;
            for (x = [sw4_lk_x0() + rf, sw4_lk_x1() - rf])
                translate([x, y0, sw4_lk_z1() - rf]) rotate([-90, 0, 0]) cylinder(r = rf, h = ylen, $fn = 32);
        }
        ri = SHUT_R - SHUT_CL + SHUT_LK_CL;   // 蓋の角丸と同心
        hull() {
            for (x = [sw4_lx0() - SHUT_LK_CL + ri, sw4_lx1() + SHUT_LK_CL - ri])
                translate([x, y0 - 1, sw4_lk_zb() + ri]) rotate([-90, 0, 0]) cylinder(r = ri, h = ylen + 2, $fn = 64);
            translate([sw4_lx0() - SHUT_LK_CL, y0 - 1, sw4_lk_z1()]) cube([sw4_lx1() - sw4_lx0() + 2 * SHUT_LK_CL, ylen + 2, 1]);
        }
    }
}
module battery_lock4() {
    difference() {
        union() {
            sw4_lk_frame(sw4_yg(), SW4_YOUT - sw4_yg());
            sw4_lk_tongue(SW4_YOUT - SHUT_LK_T, SHUT_LK_T);
        }
        sw4_lock_bore(sw4_yg() - 2, SW4_YOUT - sw4_yg() + 4, SHUT_LOCK_D);
        sw4_lock_bore(SW4_YOUT - SHUT_LOCK_CBT, SHUT_LOCK_CBT + 0.01, SHUT_LOCK_CB);
    }
}
// 口（ハッチ＋増し肉から抜く）
module battery_port_cut4() { translate([SW4_X0, sw4_yg() - SHUT_BACK - 1, SW4_Z0]) cube([SW4_X1 - SW4_X0, SHUT_BACK + SHUT_T + 2, SW4_Z1 - SW4_Z0]); }
// 彫り込み（ハッチから引く）
module sw4_band_cut() {
    rrect_y(sw4_yg(), sw4_yl() - sw4_yg(), sw4_bx0(), sw4_bx1(), sw4_bz0(), sw4_bz1(), SHUT_R);        // 耳が走る溝（リップの裏・全幅・全高）
    rrect_y(sw4_yl() - 0.01, SHUT_LIP + 0.02, sw4_lx0() - SHUT_CL, sw4_lx1() + SHUT_CL, sw4_bz0(), sw4_bz1(), SHUT_R);   // 中央は外面まで抜く（蓋の本体）
    rrect_y(sw4_yl() - 0.01, SHUT_LIP + 0.02, sw4_bx0(), sw4_bx1(), sw4_bz0(), sw4_lbot(), SHUT_R);    // 🔒 リップの下端より下は全幅で抜く（ロックの門形）
    // 🔴 角丸のせいで X の両端だけリップが下に残る（v3 と同じ）。耳の幅だけ角丸なしで抜く。外の上の角は r 0.75
    for (sgn = [0, 1]) {
        rp = SHUT_LK_RF + SHUT_CL;
        w  = SHUT_EAR + SHUT_CL;
        h  = SHUT_R + 1;
        x  = sgn == 0 ? sw4_bx0() : sw4_lx1();
        xc = sgn == 0 ? x + rp : x + w - rp;
        xs = sgn == 0 ? x + rp : x;
        hull() {
            translate([xc, sw4_yl() - 0.01, sw4_lbot() - rp]) rotate([-90, 0, 0]) cylinder(r = rp, h = SHUT_LIP + 0.02, $fn = 32);
            translate([x, sw4_yl() - 0.01, sw4_lbot() - h + rp]) cube([w, SHUT_LIP + 0.02, h - rp]);
            translate([xs, sw4_yl() - 0.01, sw4_lbot() - h]) cube([w - rp, SHUT_LIP + 0.02, h]);
        }
    }
    sw4_magnets(sw4_yg() - SHUT_MAG_H, SHUT_MAG_H + 0.01);   // 相手側の磁石の座（増し肉＋パッドの中へ）
}
// ロックのネジ穴とナットの座（ハッチから引く）
module sw4_lock_cut() {
    sw4_lock_bore(sw4_yg() - SHUT_LOCK_B - 2, SHUT_LOCK_B + SHUT_T + 4, SHUT_LOCK_D);
    translate([SW4_LK_X, sw4_yg() - SHUT_LOCK_B, sw4_lock_z()]) rotate([-90, 0, 0]) rotate([0, 0, 30])
        cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT + 0.01, $fn = 6);                        // ナットの六角ポケット（🔒 上から落とし込む）
    translate([SW4_LK_X - SHUT_LOCK_NAF / 2, sw4_yg() - SHUT_LOCK_B, sw4_lock_z()])
        cube([SHUT_LOCK_NAF, SHUT_LOCK_NT + 0.01, sw4_lk_boss_z1() - sw4_lock_z() + 0.01]);             // 落とす溝（ボスの頭まで）
}
// 彫ったぶんハッチの裏へ足す肉＋ロックのボス＋磁石のパッド
function sw4_lk_boss_z1() = 18.2;   // ⚠ ボスの下端 12.7 はハブのジャンパの被覆線（頭 12.2）の上 0.5
module sw4_backing() {
    translate([sw4_bx0(), IN_Y - SHUT_BACK, sw4_bz0()]) cube([sw4_bx1() - sw4_bx0(), SHUT_BACK, sw4_bz1() - sw4_bz0()]);
    translate([SW4_LK_X - 4.5, sw4_yg() - SHUT_LOCK_B, 12.7]) cube([9.0, SHUT_LOCK_B, sw4_lk_boss_z1() - 12.7]);   // ロックのナットのボス（溝の床から中へ 3.6。帯の中はロックの門形の場所）
    for (x = sw4_mag_xs()) translate([x, sw4_yg() - SHUT_MAG_H - 0.4, sw4_mag_z()])                     // 磁石の座の増し
        rotate([-90, 0, 0]) cylinder(d = SHUT_MAG_D + 2.0, h = SHUT_MAG_H + 0.4 + 0.01, $fn = 48);
    // ⚠ 穴の底 0.4（0.8 だと座の前面 68.2 が INA の I2C の束（Y 〜68.6）に 0.4 入る。磁石は接着が持つ前提）
}
// ---- 絵にだけ出す実体 ----
module sw4_lock_screw() color("#e8e8e8") translate([SW4_LK_X, sw4_yl(), sw4_lock_z()]) rotate([90, 0, 0]) {
    cylinder(d = 2.0, h = 6.0, $fn = 24);                                  // 胴（リップの裏からボスのナットへ）
    translate([0, 0, -1.3]) cylinder(d = 3.0, h = 1.3, $fn = 32);          // 頭（外面のザグリの中）
}
module sw4_lock_nut() color("#888") translate([SW4_LK_X, sw4_yg() - SHUT_LOCK_B, sw4_lock_z()]) rotate([-90, 0, 0]) rotate([0, 0, 30])
    cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT, $fn = 6);
module sw4_magnets_wall()    color("#c0c0c0") sw4_magnets(sw4_yg() - SHUT_MAG_H, SHUT_MAG_H);
module sw4_magnets_shutter() color("#c0c0c0") sw4_magnets(sw4_yb() - SHUT_MAG_H, SHUT_MAG_H);
