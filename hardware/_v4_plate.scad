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

// 並べた全体は 253.4 x 310.5 mm（18 部品）
module plate_all() {
    color(PLATE_COLOR) translate([73.160, 224.036, 0]) import("stl/v4/v4_brgfront.stl");
    plate_label(90.660, 183.636, "brgfront", "23.0 x 29.4 x 8.0  08-29 22:22");
    color(PLATE_COLOR) translate([-1.694, 181.736, 0]) import("stl/v4/v4_bridge.stl");
    plate_label(0.000, 183.636, "bridge", "82.7 x 50.0 x 6.0  08-29 22:22");
    color(PLATE_COLOR) translate([94.953, 10.000, 0]) import("stl/v4/v4_floor.stl");
    plate_label(94.651, 0.000, "floor", "86.7 x 71.0 x 8.5  08-29 22:22");
    color(PLATE_COLOR) translate([56.756, 154.731, 0]) import("stl/v4/v4_front.stl");
    plate_label(56.454, 93.636, "front", "86.7 x 52.1 x 11.0  08-29 22:22");
    color(PLATE_COLOR) translate([151.407, 106.632, 0]) import("stl/v4/v4_hatch.stl");
    plate_label(151.105, 93.636, "hatch", "86.7 x 50.4 x 6.6  08-29 22:22");
    color(PLATE_COLOR) translate([160.520, 208.136, 0]) import("stl/v4/v4_knob.stl");
    plate_label(147.020, 183.636, "knob", "27.0 x 27.0 x 21.4  08-29 22:22");
    color(PLATE_COLOR) translate([215.992, 205.636, 0]) import("stl/v4/v4_knobwall.stl");
    plate_label(204.992, 183.636, "knobwall", "22.0 x 24.0 x 3.9  08-29 22:22");
    color(PLATE_COLOR) translate([-32.000, 278.186, 0]) import("stl/v4/v4_lock.stl");
    plate_label(0.000, 287.686, "lock", "28.7 x 11.8 x 3.0  08-29 22:22");
    color(PLATE_COLOR) translate([237.757, 10.000, 0]) import("stl/v4/v4_lwall.stl");
    plate_label(189.303, 0.000, "lwall", "48.5 x 71.0 x 9.0  08-29 22:22");
    color(PLATE_COLOR) translate([181.304, 269.636, 0]) import("stl/v4/v4_piston.stl");
    plate_label(172.304, 252.636, "piston", "18.0 x 12.0 x 9.4  08-29 22:22");
    color(PLATE_COLOR) translate([0.000, 103.636, 0]) import("stl/v4/v4_rwall.stl");
    plate_label(0.000, 93.636, "rwall", "48.5 x 71.0 x 9.0  08-29 22:22");
    color(PLATE_COLOR) translate([0.870, 207.686, 0]) import("stl/v4/v4_seat.stl");
    plate_label(0.000, 252.636, "seat", "21.6 x 16.0 x 4.2  08-29 22:22");
    color(PLATE_COLOR) translate([52.460, 278.186, 0]) import("stl/v4/v4_shutter.stl");
    plate_label(56.360, 287.686, "shutter", "50.2 x 11.8 x 2.8  08-29 22:22");
    color(PLATE_COLOR) translate([105.560, 283.236, 0]) import("stl/v4/v4_strap_a.stl");
    plate_label(114.560, 287.686, "strap_a", "40.0 x 11.0 x 9.0  08-29 22:22");
    color(PLATE_COLOR) translate([47.360, 232.436, 0]) import("stl/v4/v4_strap_b.stl");
    plate_label(56.360, 252.636, "strap_b", "40.0 x 13.0 x 13.7  08-29 22:22");
    color(PLATE_COLOR) translate([161.920, 248.086, 0]) import("stl/v4/v4_strap_c.stl");
    plate_label(170.920, 287.686, "strap_c", "40.0 x 10.0 x 10.0  08-29 22:22");
    color(PLATE_COLOR) translate([120.818, 270.122, 0]) import("stl/v4/v4_tail.stl");
    plate_label(114.332, 252.636, "tail", "13.0 x 13.0 x 33.8  08-29 22:22");
    color(PLATE_COLOR) translate([0.302, 84.996, 0]) import("stl/v4/v4_top.stl");
    plate_label(0.000, 0.000, "top", "86.7 x 74.6 x 20.9  08-29 22:22");
}
