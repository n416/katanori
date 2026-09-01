// 🔴 自動生成。手で直さない。作り直しは `python hardware/_v4_post_props.py`
//    支柱（スペーサー）6 本を**傾けて浮かせて**刷るための、置き方と柱とラフト。
//    向きは 1 層あたりの断面積の増分がいちばん小さい所を毎回選び直している。
//    数字（胴 φ2.0・接触面 φ0.5・食い込み 0.1）は _v4_props.scad が持つ。
POST_LIFT = 5.00;
POST_TILT = [60, 60, 60, 30, 60, 30];
POST_AZ   = [135, 135, 135, 90, 135, 90];
POST_OFS  = [[-0.000, 2.617, 6.708], [-0.000, 2.617, 6.708], [-0.000, 2.667, 6.708], [-0.000, 2.267, 5.375], [-0.000, 2.943, 6.708], [-0.000, 2.146, 5.375]];
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

module props_post_0() { one_prop_free(2.640, -0.664, 4.444, 3.204, -0.911, 5.444, 2.076, -0.417, 6.300, 124.82, 0.4016, 0.9158, -0.0000, 1.500); one_prop_strut(2.151, 3.763, 7.726, 2.151, 3.263, 8.226, 2.151, 1.964, 8.976, 120.00, -1.0000, -0.0000, 0.0000, 1.500); one_prop_strut(-2.657, -0.912, 5.475, -2.849, -0.450, 5.975, -2.849, -0.450, 7.475, 180.00, 1.0000, 0.0000, 0.0000, 1.500); one_prop_free(-0.597, -3.250, 6.729, -0.884, -3.596, 7.729, -0.310, -2.903, 8.929, 143.14, 0.7701, -0.6380, 0.0000, 1.500); }
module raft_post_0() hull() {
        linear_extrude(0.050) hull() { translate([2.64, -0.66]) circle(d = 5.00, $fn = 32); translate([-0.60, -3.25]) circle(d = 5.00, $fn = 32); translate([2.15, 3.76]) circle(d = 5.00, $fn = 32); translate([-2.66, -0.91]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([2.64, -0.66]) circle(d = 6.20, $fn = 32); translate([-0.60, -3.25]) circle(d = 6.20, $fn = 32); translate([2.15, 3.76]) circle(d = 6.20, $fn = 32); translate([-2.66, -0.91]) circle(d = 6.20, $fn = 32); }
    }
module props_post_1() { one_prop_free(2.640, -0.664, 4.444, 3.204, -0.911, 5.444, 2.076, -0.417, 6.300, 124.82, 0.4016, 0.9158, -0.0000, 1.500); one_prop_strut(2.151, 3.763, 7.726, 2.151, 3.263, 8.226, 2.151, 1.964, 8.976, 120.00, -1.0000, -0.0000, 0.0000, 1.500); one_prop_strut(-2.657, -0.912, 5.475, -2.849, -0.450, 5.975, -2.849, -0.450, 7.475, 180.00, 1.0000, 0.0000, 0.0000, 1.500); one_prop_free(-0.597, -3.250, 6.729, -0.884, -3.596, 7.729, -0.310, -2.903, 8.929, 143.14, 0.7701, -0.6380, 0.0000, 1.500); }
module raft_post_1() hull() {
        linear_extrude(0.050) hull() { translate([2.64, -0.66]) circle(d = 5.00, $fn = 32); translate([-0.60, -3.25]) circle(d = 5.00, $fn = 32); translate([2.15, 3.76]) circle(d = 5.00, $fn = 32); translate([-2.66, -0.91]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([2.64, -0.66]) circle(d = 6.20, $fn = 32); translate([-0.60, -3.25]) circle(d = 6.20, $fn = 32); translate([2.15, 3.76]) circle(d = 6.20, $fn = 32); translate([-2.66, -0.91]) circle(d = 6.20, $fn = 32); }
    }
module props_post_2() { one_prop_free(3.151, -0.643, 5.418, 3.824, -0.809, 6.418, 2.478, -0.477, 6.993, 112.52, 0.2394, 0.9709, -0.0000, 1.500); one_prop_branch(3.151, -0.643, 3.857, 2.948, 2.659, 6.840, 2.548, 1.966, 8.673, 156.42, -0.8660, 0.5000, 0.0000, 2.000); one_prop_free(-2.432, 2.564, 7.054, -2.432, 3.213, 8.054, -2.432, 1.914, 8.804, 120.00, -1.0000, 0.0000, 0.0000, 1.500); one_prop_free(0.153, -3.321, 6.630, 0.251, -3.693, 7.630, 0.055, -2.950, 8.918, 149.16, 0.9670, 0.2546, -0.0000, 1.500); }
module raft_post_2() hull() {
        linear_extrude(0.050) hull() { translate([3.15, -0.64]) circle(d = 5.00, $fn = 32); translate([-2.43, 2.56]) circle(d = 5.00, $fn = 32); translate([0.15, -3.32]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([3.15, -0.64]) circle(d = 6.20, $fn = 32); translate([-2.43, 2.56]) circle(d = 6.20, $fn = 32); translate([0.15, -3.32]) circle(d = 6.20, $fn = 32); }
    }
module props_post_3() { one_prop_free(-0.349, -0.277, 3.334, -0.349, 0.098, 4.334, -0.349, -0.652, 5.633, 150.00, -1.0000, 0.0000, 0.0000, 1.500); one_prop_branch(-0.349, -0.277, 1.700, -0.349, 2.598, 3.930, -0.349, 1.848, 5.229, 150.00, -1.0000, 0.0000, 0.0000, 1.500); one_prop_branch(-0.349, -0.277, 1.903, 3.535, -2.069, 5.229, 2.094, -0.541, 6.585, 122.84, 0.7273, 0.6864, -0.0000, 2.500); one_prop_strut(-4.722, -0.839, 8.741, -4.222, -0.839, 9.241, -2.751, -0.585, 9.388, 95.60, 0.1698, -0.9855, 0.0000, 1.500); one_prop_strut(-0.440, -4.812, 7.779, -0.440, -4.312, 8.279, -0.342, -3.016, 9.028, 119.93, 0.9971, -0.0755, 0.0000, 1.500); one_prop_strut(3.689, -3.039, 9.673, 3.336, -3.393, 10.173, 2.067, -3.081, 10.910, 119.40, 0.2383, 0.9712, -0.0000, 1.500); }
module raft_post_3() hull() {
        linear_extrude(0.050) hull() { translate([-0.35, -0.28]) circle(d = 5.00, $fn = 32); translate([-4.72, -0.84]) circle(d = 5.00, $fn = 32); translate([-0.44, -4.81]) circle(d = 5.00, $fn = 32); translate([3.69, -3.04]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.35, -0.28]) circle(d = 6.20, $fn = 32); translate([-4.72, -0.84]) circle(d = 6.20, $fn = 32); translate([-0.44, -4.81]) circle(d = 6.20, $fn = 32); translate([3.69, -3.04]) circle(d = 6.20, $fn = 32); }
    }
module props_post_4() { one_prop_free(-0.391, -1.100, 3.323, -0.440, -1.474, 4.323, -0.342, -0.726, 5.619, 149.79, 0.9915, -0.1300, 0.0000, 1.500); one_prop_branch(-0.391, -1.100, 2.787, 3.204, -1.237, 5.820, 2.076, -0.743, 6.677, 124.82, 0.4016, 0.9158, -0.0000, 1.500); one_prop_free(-2.849, 2.287, 6.096, -2.849, 2.937, 7.096, -2.849, 1.638, 7.846, 120.00, -1.0000, 0.0000, 0.0000, 1.500); one_prop_strut(-1.023, -5.032, 7.422, -0.832, -4.570, 7.922, -0.323, -3.208, 9.294, 133.35, 0.9368, -0.3498, 0.0000, 2.000); }
module raft_post_4() hull() {
        linear_extrude(0.050) hull() { translate([-0.39, -1.10]) circle(d = 5.00, $fn = 32); translate([-2.85, 2.29]) circle(d = 5.00, $fn = 32); translate([-1.02, -5.03]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([-0.39, -1.10]) circle(d = 6.20, $fn = 32); translate([-2.85, 2.29]) circle(d = 6.20, $fn = 32); translate([-1.02, -5.03]) circle(d = 6.20, $fn = 32); }
    }
module props_post_5() { one_prop_free(0.111, -1.876, 3.877, 0.160, -2.524, 4.877, 0.061, -1.228, 5.625, 119.93, 0.9971, 0.0755, -0.0000, 1.500); one_prop_strut(-4.058, -2.180, 7.392, -3.596, -1.988, 7.892, -2.349, -1.267, 8.308, 106.13, 0.5008, -0.8655, 0.0000, 1.500); one_prop_strut(4.286, -2.042, 7.821, 3.824, -1.851, 8.321, 2.478, -1.276, 8.653, 102.78, 0.3928, 0.9196, -0.0000, 1.500); one_prop_free(2.568, 1.510, 4.456, 2.568, 1.885, 5.456, 2.568, 1.135, 6.755, 150.00, -1.0000, 0.0000, 0.0000, 1.500); one_prop_strut(0.332, -6.045, 8.665, 0.332, -5.545, 9.165, 0.054, -3.724, 9.945, 112.93, 0.9886, 0.1506, -0.0000, 2.000); one_prop_strut(0.068, 4.885, 6.399, 0.068, 4.385, 6.899, 0.068, 3.635, 8.198, 150.00, -1.0000, -0.0000, 0.0000, 1.500); }
module raft_post_5() hull() {
        linear_extrude(0.050) hull() { translate([0.11, -1.88]) circle(d = 5.00, $fn = 32); translate([2.57, 1.51]) circle(d = 5.00, $fn = 32); translate([-4.06, -2.18]) circle(d = 5.00, $fn = 32); translate([4.29, -2.04]) circle(d = 5.00, $fn = 32); translate([0.33, -6.04]) circle(d = 5.00, $fn = 32); translate([0.07, 4.89]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([0.11, -1.88]) circle(d = 6.20, $fn = 32); translate([2.57, 1.51]) circle(d = 6.20, $fn = 32); translate([-4.06, -2.18]) circle(d = 6.20, $fn = 32); translate([4.29, -2.04]) circle(d = 6.20, $fn = 32); translate([0.33, -6.04]) circle(d = 6.20, $fn = 32); translate([0.07, 4.89]) circle(d = 6.20, $fn = 32); }
    }
