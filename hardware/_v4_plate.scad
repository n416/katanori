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

// 並べた全体は 253.4 x 349.8 mm（20 部品）
module plate_all() {
    color(PLATE_COLOR) translate([73.160, 228.454, 0]) import("stl/v4/v4_brgfront.stl");
    plate_label(90.660, 188.054, "brgfront", "23.0 x 29.4 x 8.0  09-05 03:55");
    color(PLATE_COLOR) translate([-1.694, 186.154, 0]) import("stl/v4/v4_bridge.stl");
    plate_label(0.000, 188.054, "bridge", "82.7 x 50.0 x 6.0  09-05 03:55");
    color(PLATE_COLOR) translate([94.966, 10.000, 0]) import("stl/v4/v4_floor.stl");
    plate_label(94.660, 0.000, "floor", "86.7 x 73.0 x 8.5  09-05 03:55");
    color(PLATE_COLOR) translate([56.760, 157.561, 0]) import("stl/v4/v4_front.stl");
    plate_label(56.454, 96.054, "front", "86.7 x 52.5 x 11.8  09-05 03:55");
    color(PLATE_COLOR) translate([151.420, 109.054, 0]) import("stl/v4/v4_hatch.stl");
    plate_label(151.114, 96.054, "hatch", "86.7 x 50.5 x 5.8  09-05 03:55");
    color(PLATE_COLOR) translate([160.520, 212.554, 0]) import("stl/v4/v4_knob.stl");
    plate_label(147.020, 188.054, "knob", "27.0 x 27.0 x 21.4  09-05 03:55");
    color(PLATE_COLOR) translate([215.992, 210.054, 0]) import("stl/v4/v4_knobwall.stl");
    plate_label(204.992, 188.054, "knobwall", "22.0 x 24.0 x 3.9  09-05 03:55");
    color(PLATE_COLOR) translate([81.432, 286.354, 0]) import("stl/v4/v4_lock.stl");
    plate_label(114.332, 295.854, "lock", "30.2 x 11.8 x 3.0  09-05 03:55");
    color(PLATE_COLOR) translate([237.774, 10.000, 0]) import("stl/v4/v4_lwall.stl");
    plate_label(189.320, 0.000, "lwall", "48.5 x 73.0 x 9.0  09-05 03:55");
    color(PLATE_COLOR) translate([67.872, 312.854, 0]) import("stl/v4/v4_piston.stl");
    plate_label(57.972, 295.854, "piston", "19.8 x 12.0 x 8.3  09-05 03:55");
    color(PLATE_COLOR) translate([0.000, 106.054, 0]) import("stl/v4/v4_rwall.stl");
    plate_label(0.000, 96.054, "rwall", "48.5 x 73.0 x 9.0  09-05 03:55");
    color(PLATE_COLOR) translate([71.068, 210.104, 0]) import("stl/v4/v4_seat.stl");
    plate_label(70.198, 257.054, "seat", "21.6 x 16.0 x 4.2  09-05 03:55");
    color(PLATE_COLOR) translate([-2.150, 251.804, 0]) import("stl/v4/v4_shutfloor.stl");
    plate_label(0.000, 257.054, "shutfloor", "62.2 x 19.8 x 3.6  09-05 03:55");
    color(PLATE_COLOR) translate([167.292, 286.354, 0]) import("stl/v4/v4_shutter.stl");
    plate_label(170.692, 295.854, "shutter", "53.0 x 11.8 x 2.8  09-05 03:55");
    color(PLATE_COLOR) translate([-9.000, 323.376, 0]) import("stl/v4/v4_strap_a.stl");
    plate_label(0.000, 327.826, "strap_a", "40.0 x 11.0 x 11.9  09-05 03:55");
    color(PLATE_COLOR) translate([117.558, 236.854, 0]) import("stl/v4/v4_strap_b.stl");
    plate_label(126.558, 257.054, "strap_b", "40.0 x 15.6 x 16.3  09-05 03:55");
    color(PLATE_COLOR) translate([48.972, 289.126, 0]) import("stl/v4/v4_strap_c.stl");
    plate_label(57.972, 327.826, "strap_c", "40.0 x 10.9 x 12.7  09-05 03:55");
    color(PLATE_COLOR) translate([6.486, 313.340, 0]) import("stl/v4/v4_tail.stl");
    plate_label(0.000, 295.854, "tail", "13.0 x 13.0 x 33.7  09-05 03:55");
    color(PLATE_COLOR) translate([0.306, 87.000, 0]) import("stl/v4/v4_top.stl");
    plate_label(0.000, 0.000, "top", "86.7 x 77.1 x 20.9  09-05 03:55");
    color(PLATE_COLOR) translate([199.880, 273.954, 0]) import("stl/v4/v4_tub.stl");
    plate_label(184.530, 257.054, "tub", "30.7 x 13.5 x 9.3  09-05 03:55");
}
