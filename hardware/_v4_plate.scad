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

// 並べた全体は 253.4 x 342.1 mm（20 部品）
module plate_all() {
    color(PLATE_COLOR) translate([73.160, 224.454, 0]) import("stl/v4/v4_brgfront.stl");
    plate_label(90.660, 184.054, "brgfront", "23.0 x 29.4 x 8.0  09-04 12:42");
    color(PLATE_COLOR) translate([-1.694, 182.154, 0]) import("stl/v4/v4_bridge.stl");
    plate_label(0.000, 184.054, "bridge", "82.7 x 50.0 x 6.0  09-04 12:42");
    color(PLATE_COLOR) translate([94.966, 10.000, 0]) import("stl/v4/v4_floor.stl");
    plate_label(94.660, 0.000, "floor", "86.7 x 71.0 x 8.5  09-04 12:42");
    color(PLATE_COLOR) translate([56.760, 155.561, 0]) import("stl/v4/v4_front.stl");
    plate_label(56.454, 94.054, "front", "86.7 x 52.5 x 11.8  09-04 12:42");
    color(PLATE_COLOR) translate([151.420, 107.054, 0]) import("stl/v4/v4_hatch.stl");
    plate_label(151.114, 94.054, "hatch", "86.7 x 50.5 x 5.8  09-04 12:42");
    color(PLATE_COLOR) translate([160.520, 208.554, 0]) import("stl/v4/v4_knob.stl");
    plate_label(147.020, 184.054, "knob", "27.0 x 27.0 x 21.4  09-04 12:42");
    color(PLATE_COLOR) translate([215.992, 206.054, 0]) import("stl/v4/v4_knobwall.stl");
    plate_label(204.992, 184.054, "knobwall", "22.0 x 24.0 x 3.9  09-04 12:42");
    color(PLATE_COLOR) translate([81.432, 278.604, 0]) import("stl/v4/v4_lock.stl");
    plate_label(114.332, 288.104, "lock", "30.2 x 11.8 x 3.0  09-04 12:42");
    color(PLATE_COLOR) translate([237.774, 10.000, 0]) import("stl/v4/v4_lwall.stl");
    plate_label(189.320, 0.000, "lwall", "48.5 x 71.0 x 9.0  09-04 12:42");
    color(PLATE_COLOR) translate([67.872, 305.104, 0]) import("stl/v4/v4_piston.stl");
    plate_label(57.972, 288.104, "piston", "19.8 x 12.0 x 8.3  09-04 12:42");
    color(PLATE_COLOR) translate([0.000, 104.054, 0]) import("stl/v4/v4_rwall.stl");
    plate_label(0.000, 94.054, "rwall", "48.5 x 71.0 x 9.0  09-04 12:42");
    color(PLATE_COLOR) translate([0.870, 208.104, 0]) import("stl/v4/v4_seat.stl");
    plate_label(0.000, 253.054, "seat", "21.6 x 16.0 x 4.2  09-04 12:42");
    color(PLATE_COLOR) translate([112.182, 244.804, 0]) import("stl/v4/v4_shutfloor.stl");
    plate_label(114.332, 253.054, "shutfloor", "61.1 x 14.5 x 3.6  09-04 12:42");
    color(PLATE_COLOR) translate([167.292, 278.604, 0]) import("stl/v4/v4_shutter.stl");
    plate_label(170.692, 288.104, "shutter", "53.0 x 11.8 x 2.8  09-04 12:42");
    color(PLATE_COLOR) translate([-9.000, 315.626, 0]) import("stl/v4/v4_strap_a.stl");
    plate_label(0.000, 320.076, "strap_a", "40.0 x 11.0 x 11.9  09-04 12:42");
    color(PLATE_COLOR) translate([47.360, 232.854, 0]) import("stl/v4/v4_strap_b.stl");
    plate_label(56.360, 253.054, "strap_b", "40.0 x 15.6 x 16.3  09-04 12:42");
    color(PLATE_COLOR) translate([48.972, 281.376, 0]) import("stl/v4/v4_strap_c.stl");
    plate_label(57.972, 320.076, "strap_c", "40.0 x 10.9 x 12.7  09-04 12:42");
    color(PLATE_COLOR) translate([6.486, 305.590, 0]) import("stl/v4/v4_tail.stl");
    plate_label(0.000, 288.104, "tail", "13.0 x 13.0 x 33.7  09-04 12:42");
    color(PLATE_COLOR) translate([0.306, 85.000, 0]) import("stl/v4/v4_top.stl");
    plate_label(0.000, 0.000, "top", "86.7 x 75.1 x 20.9  09-04 12:42");
    color(PLATE_COLOR) translate([198.782, 269.954, 0]) import("stl/v4/v4_tub.stl");
    plate_label(183.432, 253.054, "tub", "30.7 x 13.5 x 9.3  09-04 12:42");
}
