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

// 並べた全体は 247.8 x 362.4 mm（18 部品）
module plate_all() {
    color(PLATE_COLOR) translate([181.944, 234.400, 0]) import("stl/v4/v4_brgfront.stl");
    plate_label(199.444, 194.000, "brgfront", "23.0 x 29.4 x 8.0  08-28 09:23");
    color(PLATE_COLOR) translate([107.090, 192.100, 0]) import("stl/v4/v4_bridge.stl");
    plate_label(108.660, 194.000, "bridge", "82.8 x 50.0 x 6.0  08-28 09:23");
    color(PLATE_COLOR) translate([66.972, 326.450, 0]) import("stl/v4/v4_btn.stl");
    plate_label(57.972, 309.450, "btn", "18.0 x 12.0 x 10.0  08-28 09:23");
    color(PLATE_COLOR) translate([7.306, 114.000, 0]) import("stl/v4/v4_floor.stl");
    plate_label(0.000, 104.000, "floor", "100.7 x 71.0 x 8.5  08-28 09:23");
    color(PLATE_COLOR) translate([115.966, 165.094, 0]) import("stl/v4/v4_front.stl");
    plate_label(108.660, 104.000, "front", "100.7 x 52.1 x 11.0  08-28 09:23");
    color(PLATE_COLOR) translate([7.306, 206.996, 0]) import("stl/v4/v4_hatch.stl");
    plate_label(0.000, 194.000, "hatch", "100.7 x 50.4 x 6.6  08-28 09:23");
    color(PLATE_COLOR) translate([13.500, 287.950, 0]) import("stl/v4/v4_knob.stl");
    plate_label(0.000, 263.450, "knob", "27.0 x 27.0 x 21.4  08-28 09:32");
    color(PLATE_COLOR) translate([68.972, 285.450, 0]) import("stl/v4/v4_knobwall.stl");
    plate_label(57.972, 263.450, "knobwall", "22.0 x 24.0 x 3.9  08-28 09:23");
    color(PLATE_COLOR) translate([83.944, 299.950, 0]) import("stl/v4/v4_lock.stl");
    plate_label(115.944, 309.450, "lock", "28.7 x 11.8 x 3.0  08-28 09:23");
    color(PLATE_COLOR) translate([48.454, 17.000, 0]) import("stl/v4/v4_lwall.stl");
    plate_label(0.000, 0.000, "lwall", "48.5 x 85.0 x 9.0  08-28 09:23");
    color(PLATE_COLOR) translate([56.454, 17.000, 0]) import("stl/v4/v4_rwall.stl");
    plate_label(56.454, 0.000, "rwall", "48.5 x 85.0 x 9.0  08-28 09:23");
    color(PLATE_COLOR) translate([115.202, 218.500, 0]) import("stl/v4/v4_seat.stl");
    plate_label(114.332, 263.450, "seat", "21.6 x 16.0 x 4.2  08-28 09:23");
    color(PLATE_COLOR) translate([168.404, 299.950, 0]) import("stl/v4/v4_shutter.stl");
    plate_label(172.304, 309.450, "shutter", "50.2 x 11.8 x 2.8  08-28 09:23");
    color(PLATE_COLOR) translate([47.360, 337.362, 0]) import("stl/v4/v4_strap_a.stl");
    plate_label(56.360, 341.422, "strap_a", "40.0 x 8.4 x 9.0  08-28 09:23");
    color(PLATE_COLOR) translate([161.692, 243.250, 0]) import("stl/v4/v4_strap_b.stl");
    plate_label(170.692, 263.450, "strap_b", "40.0 x 13.0 x 12.2  08-28 09:23");
    color(PLATE_COLOR) translate([-9.000, 301.822, 0]) import("stl/v4/v4_strap_c.stl");
    plate_label(0.000, 341.422, "strap_c", "40.0 x 10.0 x 9.4  08-28 09:23");
    color(PLATE_COLOR) translate([6.486, 326.936, 0]) import("stl/v4/v4_tail.stl");
    plate_label(0.000, 309.450, "tail", "13.0 x 13.0 x 33.8  08-28 09:23");
    color(PLATE_COLOR) translate([120.214, 84.996, 0]) import("stl/v4/v4_top.stl");
    plate_label(112.908, 0.000, "top", "100.7 x 74.6 x 20.9  08-28 09:23");
}
