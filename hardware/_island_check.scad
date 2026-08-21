// 島（ねじ止めする内側の輪）を厚み 3.9mm にしたとき、その座がリードスイッチの溝へ
// 抜けるかどうかを見るためだけの図。数字は knob_v4.scad から読んだもの。
//   島の上面    z -2.5   （へこみの底）
//   島の底      z -6.4   （ザグリ 3.5 ＋ 底 0.4 ＝ 厚み 3.9）
//   リードの溝  z -7.7 〜 -4.45 ／ x ±7.15 ／ y 9.0〜12.25
//
// view = "cut" … +Y 方向の断面（横から見る。上下関係が見える）
//        "top" … 真上から（平面で重なる場所が見える）
//        "hit" … ぶつかっている体積だけ
view = "cut";
$fn = 120;

R_HOLE  = 5.5;    // 落とし込み穴の半径
R_ISL   = 9.8;    // 島の外の縁（＝溝の内側）
R_GRV   = 12.0;   // ツメの通り道の外側
R_DISH  = 13.1;   // へこみの壁
Z_TOP   = -2.5;   // 島の上面＝へこみの底
T_ISL   = 3.9;    // 島の厚み（ザグリ 3.5 ＋ 底 0.4）
Z_BOT   = Z_TOP - T_ISL;    // -6.4  島の底＝座の面
T_NOW   = 1.2;              // いまの輪の厚み（比較用）

REED_X  = 7.15;
REED_Y0 = 9.0;
REED_Y1 = 12.25;
REED_Z0 = -7.7;
REED_Z1 = -4.45;

SCR_R   = 7.6;    // ねじの半径位置
SCR_CB  = 5.0;    // ザグリの径
SCR_CBT = 3.5;    // ザグリの深さ
SCR_D   = 3.0;    // ねじの通し穴

module island() {
    difference() {
        translate([0, 0, Z_BOT]) cylinder(r = R_ISL, h = T_ISL);
        translate([0, 0, Z_BOT - 1]) cylinder(r = R_HOLE, h = T_ISL + 2);
    }
}
module island_now() {       // いまの厚み 1.2 の輪（比較）
    difference() {
        translate([0, 0, Z_TOP - T_NOW]) cylinder(r = R_ISL, h = T_NOW);
        translate([0, 0, Z_TOP - T_NOW - 1]) cylinder(r = R_HOLE, h = T_NOW + 2);
    }
}
module reed() {
    translate([-REED_X, REED_Y0, REED_Z0])
        cube([REED_X * 2, REED_Y1 - REED_Y0, REED_Z1 - REED_Z0]);
}
module screw() {            // ザグリ＋通し穴
    for (a = [0, 120, 210]) rotate([0, 0, a]) translate([SCR_R, 0, 0]) {
        translate([0, 0, Z_TOP - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT);
        translate([0, 0, Z_TOP - 8]) cylinder(d = SCR_D, h = 8);
    }
}
module rail() {             // ツメが通る溝
    difference() {
        translate([0, 0, Z_TOP - 1.5]) cylinder(r = R_GRV, h = 1.6);
        translate([0, 0, Z_TOP - 2.6]) cylinder(r = R_ISL, h = 4);
    }
}
module hit() { intersection() { island(); reed(); } }

module slab() { translate([-0.6, -2, -14]) cube([1.2, 20, 16]); }   // x ±0.6 の薄板

module scene() {
    color("#adb5bd") island();
    color("#1c7ed6") screw();
    color("#37b24d") rail();
    color("#f08c00") reed();
    color("#e03131") hit();
}

if (view == "hit") {
    color("#e03131") hit();
} else if (view == "cut") {
    intersection() { scene(); slab(); }
    // 目盛り（1mm ごと・+Y 側の外に立てる）
    for (k = [0 : 8]) color("#868e96")
        translate([-0.6, R_DISH + 1.5, -k]) cube([1.2, 1.2, 0.06]);
} else {
    scene();
}

echo(str("島 z ", Z_BOT, " 〜 ", Z_TOP, " / リードの溝 z ", REED_Z0, " 〜 ", REED_Z1));
echo(str("重なる z ", max(Z_BOT, REED_Z0), " 〜 ", min(Z_TOP, REED_Z1),
         " → 高さ ", min(Z_TOP, REED_Z1) - max(Z_BOT, REED_Z0), "mm"));
echo(str("重なる y ", REED_Y0, " 〜 ", R_ISL, " → 幅 ", R_ISL - REED_Y0, "mm"));
echo(str("いまの輪の底 z ", Z_TOP - T_NOW, " → リードの溝の天面 ", REED_Z1,
         " まで ", (Z_TOP - T_NOW) - REED_Z1, "mm"));
