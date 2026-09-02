// 🔴 自動生成。手で直さない。並べ直しは `python hardware/_v4_plate.py`
//    中身は stl/v4/*.stl そのもの（支柱・ラフト・犠牲タブ込みで焼いたもの）。
//    支柱とラフトは部品の下に付くので、真上からは見えない。回して下から見ること。
//    X と Y だけ動かしてある。**Z は動かしていない**ので、浮いている部品は浮いたまま出る。
//    🔒 色分けはしない（2026-08-27 ユーザー「全部白くていいです」）。焼いた時刻は名札に出ている。
PLATE_COLOR = "#b6c0cc";
PLATE_NAME_H = 4.5; PLATE_SUB_H = 2.6;
module plate_label(x, y, name, sub) color("#8a8a8a") translate([x, y, 0]) {
    linear_extrude(0.2) text(sub, size = PLATE_SUB_H);
    translate([0, PLATE_SUB_H * 1.7, 0]) linear_extrude(0.2) text(name, size = PLATE_NAME_H);
}

// 並べた全体は 253.4 x 374.9 mm（25 部品）
module plate_all() {
    color(PLATE_COLOR) translate([73.160, 224.040, 0]) import("stl/v4/v4_brgfront.stl");
    plate_label(90.660, 183.640, "brgfront", "23.0 x 29.4 x 8.0  09-02 13:49");
    color(PLATE_COLOR) translate([-1.694, 181.740, 0]) import("stl/v4/v4_bridge.stl");
    plate_label(0.000, 183.640, "bridge", "82.7 x 50.0 x 6.0  09-02 13:49");
    color(PLATE_COLOR) translate([94.966, 10.000, 0]) import("stl/v4/v4_floor.stl");
    plate_label(94.660, 0.000, "floor", "86.7 x 71.0 x 8.5  09-02 13:49");
    color(PLATE_COLOR) translate([56.760, 154.735, 0]) import("stl/v4/v4_front.stl");
    plate_label(56.454, 93.640, "front", "86.7 x 52.1 x 11.0  09-02 13:49");
    color(PLATE_COLOR) translate([151.420, 106.640, 0]) import("stl/v4/v4_hatch.stl");
    plate_label(151.114, 93.640, "hatch", "86.7 x 50.5 x 6.6  09-02 13:49");
    color(PLATE_COLOR) translate([160.520, 208.140, 0]) import("stl/v4/v4_knob.stl");
    plate_label(147.020, 183.640, "knob", "27.0 x 27.0 x 21.4  09-02 13:49");
    color(PLATE_COLOR) translate([215.992, 205.640, 0]) import("stl/v4/v4_knobwall.stl");
    plate_label(204.992, 183.640, "knobwall", "22.0 x 24.0 x 3.9  09-02 13:49");
    color(PLATE_COLOR) translate([140.304, 311.480, 0]) import("stl/v4/v4_lock.stl");
    plate_label(172.304, 320.980, "lock", "29.3 x 11.8 x 3.0  09-02 13:49");
    color(PLATE_COLOR) translate([237.774, 10.000, 0]) import("stl/v4/v4_lwall.stl");
    plate_label(189.320, 0.000, "lwall", "48.5 x 71.0 x 9.0  09-02 13:49");
    color(PLATE_COLOR) translate([67.872, 337.980, 0]) import("stl/v4/v4_piston.stl");
    plate_label(57.972, 320.980, "piston", "19.8 x 12.0 x 8.3  09-02 13:49");
    color(PLATE_COLOR) translate([5.760, 306.120, 0]) import("stl/v4/v4_post_0.stl");
    plate_label(0.000, 288.770, "post_0", "11.5 x 13.2 x 10.7  09-02 13:49");
    color(PLATE_COLOR) translate([63.732, 306.120, 0]) import("stl/v4/v4_post_1.stl");
    plate_label(57.972, 288.770, "post_1", "11.5 x 13.2 x 10.7  09-02 13:49");
    color(PLATE_COLOR) translate([5.530, 338.400, 0]) import("stl/v4/v4_post_2.stl");
    plate_label(0.000, 320.980, "post_2", "11.8 x 12.1 x 11.0  09-02 13:49");
    color(PLATE_COLOR) translate([122.152, 339.890, 0]) import("stl/v4/v4_post_3.stl");
    plate_label(114.332, 320.980, "post_3", "14.6 x 11.9 x 14.8  09-02 13:49");
    color(PLATE_COLOR) translate([120.282, 271.770, 0]) import("stl/v4/v4_post_4.stl");
    plate_label(114.332, 252.640, "post_4", "9.6 x 13.5 x 11.4  09-02 13:49");
    color(PLATE_COLOR) translate([7.160, 272.780, 0]) import("stl/v4/v4_post_5.stl");
    plate_label(0.000, 252.640, "post_5", "14.5 x 17.1 x 14.4  09-02 13:49");
    color(PLATE_COLOR) translate([0.000, 103.640, 0]) import("stl/v4/v4_rwall.stl");
    plate_label(0.000, 93.640, "rwall", "48.5 x 71.0 x 9.0  09-02 13:49");
    color(PLATE_COLOR) translate([58.842, 207.690, 0]) import("stl/v4/v4_seat.stl");
    plate_label(57.972, 252.640, "seat", "21.6 x 16.0 x 4.2  09-02 13:49");
    color(PLATE_COLOR) translate([-3.400, 342.560, 0]) import("stl/v4/v4_shutter.stl");
    plate_label(0.000, 352.060, "shutter", "51.2 x 11.8 x 2.8  09-02 13:49");
    color(PLATE_COLOR) translate([50.200, 389.510, 0]) import("stl/v4/v4_strap_a.stl");
    plate_label(59.200, 352.060, "strap_a", "40.0 x 11.0 x 8.0  09-02 13:49");
    color(PLATE_COLOR) translate([106.944, 343.970, 0]) import("stl/v4/v4_strap_b.stl");
    plate_label(115.944, 288.770, "strap_b", "40.0 x 13.0 x 8.0  09-02 13:49");
    color(PLATE_COLOR) translate([106.560, 423.660, 0]) import("stl/v4/v4_strap_c.stl");
    plate_label(115.560, 352.060, "strap_c", "40.0 x 10.0 x 8.0  09-02 13:49");
    color(PLATE_COLOR) translate([178.790, 306.257, 0]) import("stl/v4/v4_tail.stl");
    plate_label(172.304, 288.770, "tail", "13.0 x 13.0 x 33.7  09-02 13:49");
    color(PLATE_COLOR) translate([0.306, 85.000, 0]) import("stl/v4/v4_top.stl");
    plate_label(0.000, 0.000, "top", "86.7 x 74.6 x 20.9  09-02 13:49");
    color(PLATE_COLOR) translate([186.042, 269.540, 0]) import("stl/v4/v4_tub.stl");
    plate_label(170.692, 252.640, "tub", "30.7 x 13.5 x 9.3  09-02 13:49");
}
