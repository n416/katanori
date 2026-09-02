// 🔴 自動生成。手で直さない。作り直しは `python hardware/_v4_post_props.py`
//    支柱（スペーサー）6 本を**傾けて浮かせて**刷るための、置き方と柱とラフト。
//    向きは 1 層あたりの断面積の増分がいちばん小さい所を毎回選び直している。
//    数字（胴 φ2.0・接触面 φ0.5・食い込み 0.1）は _v4_props.scad が持つ。
POST_LIFT = 5.00;
POST_TILT = [60, 60, 60, 30, 80, 30];
POST_AZ   = [270, 270, 90, 90, 90, 0];
POST_OFS  = [[-0.000, 2.617, 6.711], [-0.000, 2.617, 6.711], [-0.000, 2.667, 6.711], [-0.000, 2.267, 5.375], [-0.000, 3.298, 7.578], [0.000, 2.414, 5.375]];
module post_place(i) translate(POST_OFS[i]) rotate([POST_TILT[i], 0, 0]) rotate([0, 0, POST_AZ[i]]) children();
// 🔒 2026-09-01 ユーザー「柱＋球＋円錐で構成されるべきだよね」。
//   円錐の軸は**面の法線**で、両端とも軸に直角 ＝ 本物の円錐（回転体）。
//   向きの変わり目は球が受ける。柱は垂直（そうでないと刷れない）、円錐は法線向き。
//   ⚠ 球を挟まず「水平な円」と「傾いた円」を hull で繋ぐと、円錐の底が法線に直角にならない。
//   s=(sx,sy,sz) 球の中心＝柱の頭＝円錐の太い端／a=(ax,ay,az) 接触面の中心／hl 円錐の長さ
HEAD_D2 = 1.00;
module post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    translate([ax, ay, az]) rotate(a = ang, v = [vx, vy, vz])
        cylinder(d1 = PROP_TIP2, d2 = HEAD_D2, h = hl, $fn = 24);
}
// 柱（垂直）＋球へ絞るテーパー＋頭。
// px,py は**円錐の真下**（円錐の中点）。球の真下ではない ── 寝た円錐を柱に乗せるため。
//   🔴 柱は球の TAPER2 手前で止める。球まで上げると球が柱に埋まり、細い部分が
//      円錐のぶんしか残らずニッパーが入らない（2026-09-01・ユーザー指摘）。
TAPER2 = 1.00;
//   pz は柱の頭。球まで上げず、**部品の下面の手前**で止める（生成器が出す）。
module one_prop_free(px, py, pz, sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    translate([px, py, 0]) cylinder(d = PROP_D2, h = max(0.01, pz), $fn = 24);
    hull() {
        translate([px, py, pz]) cylinder(d = PROP_D2, h = 0.01, $fn = 24);
        translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    }
    post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl);
}
// 円錐から外へ降りて**自分の柱**を立てる（真下が部品の中のとき）。斜材は 45°。
module one_prop_strut(px, py, pz, sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    translate([px, py, 0]) cylinder(d = PROP_D2, h = max(0.01, pz), $fn = 24);
    hull() {
        translate([px, py, pz]) sphere(d = PROP_D2, $fn = 16);
        translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    }
    post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl);
}
// 隣の柱から出す**枝**（自分では降りられないとき）。頭は同じ。
//   出典の「支柱どうしを繋ぐと折れにくい」もこれ（docs/PRINT.md §3.9）。
module one_prop_branch(bx, by, bz, sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl) {
    hull() {
        translate([bx, by, bz]) sphere(d = PROP_D2, $fn = 16);
        translate([sx, sy, sz]) sphere(d = HEAD_D2, $fn = 24);
    }
    post_head(sx, sy, sz, ax, ay, az, ang, vx, vy, vz, hl);
}

module props_post_0() { one_prop_free(-0.091, -0.574, 2.812, -0.140, -0.948, 3.812, -0.042, -0.200, 5.108, 149.79, 0.9915, -0.1300, 0.0000, 1.500); one_prop_strut(-4.722, 0.247, 6.692, -4.222, 0.247, 7.192, -2.751, 0.394, 7.446, 99.73, 0.0990, -0.9951, 0.0000, 1.500); one_prop_strut(-0.349, 4.596, 5.915, -0.349, 4.096, 6.415, -0.349, 2.797, 7.165, 120.00, -1.0000, 0.0000, 0.0000, 1.500); }
module raft_post_0() hull() {
        linear_extrude(0.050) hull() { translate([-0.09, -0.57]) circle(d = 5.00, $fn = 32); translate([-4.72, 0.25]) circle(d = 5.00, $fn = 32); translate([-0.35, 4.60]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.09, -0.57]) circle(d = 6.20, $fn = 32); translate([-4.72, 0.25]) circle(d = 6.20, $fn = 32); translate([-0.35, 4.60]) circle(d = 6.20, $fn = 32); }
    }
module props_post_1() { one_prop_free(-0.091, -0.574, 2.812, -0.140, -0.948, 3.812, -0.042, -0.200, 5.108, 149.79, 0.9915, -0.1300, 0.0000, 1.500); one_prop_strut(-4.722, 0.247, 6.692, -4.222, 0.247, 7.192, -2.751, 0.394, 7.446, 99.73, 0.0990, -0.9951, 0.0000, 1.500); one_prop_strut(-0.349, 4.596, 5.915, -0.349, 4.096, 6.415, -0.349, 2.797, 7.165, 120.00, -1.0000, 0.0000, 0.0000, 1.500); }
module raft_post_1() hull() {
        linear_extrude(0.050) hull() { translate([-0.09, -0.57]) circle(d = 5.00, $fn = 32); translate([-4.72, 0.25]) circle(d = 5.00, $fn = 32); translate([-0.35, 4.60]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.09, -0.57]) circle(d = 6.20, $fn = 32); translate([-4.72, 0.25]) circle(d = 6.20, $fn = 32); translate([-0.35, 4.60]) circle(d = 6.20, $fn = 32); }
    }
module props_post_2() { one_prop_free(-0.091, -0.523, 2.811, -0.140, -0.898, 3.811, -0.042, -0.149, 5.108, 149.79, 0.9915, -0.1300, 0.0000, 1.500); one_prop_strut(-4.722, 0.198, 6.692, -4.222, 0.198, 7.192, -2.751, 0.344, 7.445, 99.73, 0.0990, -0.9951, 0.0000, 1.500); one_prop_strut(-0.349, 4.547, 5.744, -0.349, 4.047, 6.244, -0.349, 2.748, 6.994, 120.00, -1.0000, -0.0000, 0.0000, 1.500); }
module raft_post_2() hull() {
        linear_extrude(0.050) hull() { translate([-0.09, -0.52]) circle(d = 5.00, $fn = 32); translate([-4.72, 0.20]) circle(d = 5.00, $fn = 32); translate([-0.35, 4.55]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.09, -0.52]) circle(d = 6.20, $fn = 32); translate([-4.72, 0.20]) circle(d = 6.20, $fn = 32); translate([-0.35, 4.55]) circle(d = 6.20, $fn = 32); }
    }
module props_post_3() { one_prop_free(-0.249, 1.989, 2.815, -0.249, 2.364, 3.815, -0.249, 1.614, 5.114, 150.00, -1.0000, -0.0000, 0.0000, 1.500); one_prop_strut(3.557, -1.755, 5.569, 3.204, -1.402, 6.069, 2.076, -0.545, 6.564, 109.25, 0.6048, 0.7964, -0.0000, 1.500); one_prop_strut(-4.722, -0.839, 8.741, -4.222, -0.839, 9.241, -2.751, -0.585, 9.388, 95.60, 0.1698, -0.9855, 0.0000, 1.500); one_prop_free(-0.391, -3.664, 7.092, -0.440, -4.312, 8.279, -0.342, -3.016, 9.028, 119.93, 0.9971, -0.0755, 0.0000, 1.500); one_prop_strut(4.309, -4.826, 9.570, 3.956, -4.473, 10.070, 2.076, -3.045, 10.894, 109.25, 0.6048, 0.7964, -0.0000, 2.500); }
module raft_post_3() hull() {
        linear_extrude(0.050) hull() { translate([-0.25, 1.99]) circle(d = 5.00, $fn = 32); translate([-0.39, -3.66]) circle(d = 5.00, $fn = 32); translate([3.56, -1.76]) circle(d = 5.00, $fn = 32); translate([-4.72, -0.84]) circle(d = 5.00, $fn = 32); translate([4.31, -4.83]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.25, 1.99]) circle(d = 6.20, $fn = 32); translate([-0.39, -3.66]) circle(d = 6.20, $fn = 32); translate([3.56, -1.76]) circle(d = 6.20, $fn = 32); translate([-4.72, -0.84]) circle(d = 6.20, $fn = 32); translate([4.31, -4.83]) circle(d = 6.20, $fn = 32); }
    }
module props_post_4() { one_prop_free(-0.091, 1.102, 2.628, -0.140, 0.972, 3.628, -0.042, 1.232, 5.102, 169.33, 0.9356, -0.3531, 0.0000, 1.500); one_prop_strut(3.704, -1.046, 4.941, 3.204, -1.046, 5.441, 2.076, -0.874, 6.415, 130.49, 0.1505, 0.9886, -0.0000, 1.500); one_prop_free(-0.597, -3.490, 5.540, -0.884, -3.610, 6.540, -0.310, -3.369, 7.904, 155.48, 0.3866, -0.9222, 0.0000, 1.500); }
module raft_post_4() hull() {
        linear_extrude(0.050) hull() { translate([-0.09, 1.10]) circle(d = 5.00, $fn = 32); translate([-0.60, -3.49]) circle(d = 5.00, $fn = 32); translate([3.70, -1.05]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.09, 1.10]) circle(d = 6.20, $fn = 32); translate([-0.60, -3.49]) circle(d = 6.20, $fn = 32); translate([3.70, -1.05]) circle(d = 6.20, $fn = 32); }
    }
module props_post_5() { one_prop_free(-0.149, 2.142, 2.818, -0.149, 2.517, 3.818, -0.149, 1.767, 5.117, 150.00, -1.0000, -0.0000, 0.0000, 1.500); one_prop_strut(-0.440, -3.092, 4.998, -0.440, -2.592, 5.498, -0.342, -1.296, 6.246, 119.93, 0.9971, -0.0755, 0.0000, 1.500); one_prop_strut(-4.722, -1.619, 10.290, -4.222, -1.619, 10.790, -2.751, -1.366, 10.936, 95.60, 0.1698, -0.9855, 0.0000, 1.500); one_prop_strut(3.557, -2.535, 7.117, 3.204, -2.182, 7.617, 2.076, -1.325, 8.112, 109.25, 0.6048, 0.7964, -0.0000, 1.500); one_prop_strut(-0.506, -6.457, 8.829, -0.506, -5.957, 9.329, -0.342, -3.796, 10.576, 119.93, 0.9971, -0.0755, 0.0000, 2.500); }
module raft_post_5() hull() {
        linear_extrude(0.050) hull() { translate([-0.15, 2.14]) circle(d = 5.00, $fn = 32); translate([-0.44, -3.09]) circle(d = 5.00, $fn = 32); translate([-4.72, -1.62]) circle(d = 5.00, $fn = 32); translate([3.56, -2.54]) circle(d = 5.00, $fn = 32); translate([-0.51, -6.46]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.15, 2.14]) circle(d = 6.20, $fn = 32); translate([-0.44, -3.09]) circle(d = 6.20, $fn = 32); translate([-4.72, -1.62]) circle(d = 6.20, $fn = 32); translate([3.56, -2.54]) circle(d = 6.20, $fn = 32); translate([-0.51, -6.46]) circle(d = 6.20, $fn = 32); }
    }
