// 卓上スタンドの「形」の検討（2026-08-08）
//
// これは**見た目だけを振る**ためのファイル。機能はv17で確定しているので触らない。
//   include <stand_seat_test.scad> で v17 の modules と変数をそのまま持ってくる
//   → 外側の肉を union で足す → **cuts() をもう一度引く**
// これで、溝・後ろ壁(z16)・前壁(z13.5・内面y1.0)・レール(z2.5)・舳先・スロープ床・
// 水抜き・抜き文字は、どの形を選んでも v17 と同一のまま残る。
//
//   openscad -o form.png --render -D 'FORM=1' stand_form_study.scad
//
// FORM = 0 … v17そのまま（比較用）
//        1 … 舟：土台を木の葉形にして、クレードルを抜き勾配の台座にする
//        2 … 1 ＋ 背面に一枚の帆（後ろへ抜ける線を作る）
//        3 … 刃：土台を薄いまま全周を大きく斜めに削ぐ

include <stand_seat_test.scad>
show = "none";      // include先の描画を止める（このファイルが描く）

FORM = 1;
BEVEL = 1.5;    // 土台の下の縁の削ぎ

// ---- 共通の道具 ----
// 2Dの輪郭を、上下に面取りを付けて押し出す
module chamfered(h, ch, top = true, bot = true) {
    hull() {
        translate([0, 0, bot ? ch : 0]) linear_extrude(0.01) children();
        translate([0, 0, bot ? ch : 0]) linear_extrude(0.01) children();
        if (bot) linear_extrude(0.01) offset(r = -ch) children();
        translate([0, 0, h - (top ? ch : 0) - 0.01]) linear_extrude(0.01) children();
        if (top) translate([0, 0, h - 0.01]) linear_extrude(0.01) offset(r = -ch) children();
    }
}

// 木の葉形の土台の輪郭。両端は細く、クレードルのあたりで一番広い
module hull_plan() {
    hull() {
        translate([ -1,   0]) circle(r = 7);
        translate([ 48, -20]) circle(r = 6);
        translate([ 48,  12]) circle(r = 6);
        translate([ 87,   0]) circle(r = 7);
    }
}

// クレードルの外側を抜き勾配の台座にする。天面は v17 の塊と同じなので機能に触らない
module plinth() {
    hull() {
        translate([27, -18, 0])          cube([44, 30, 0.01]);
        translate([GRIP_X0, CR_Y0, CR_H - 0.01]) cube([GRIP_X1 - GRIP_X0, CR_Y1 - CR_Y0, 0.01]);
    }
}

// 背面の帆。クレードルの後ろから土台の後ろ縁へ、一枚の面で抜ける
module sail() {
    hull() {
        translate([GRIP_X0 + 2, CR_Y0 + 1, CR_H - 6]) cube([GRIP_X1 - GRIP_X0 - 4, 2, 6]);
        translate([18, -25, 0]) cube([58, 2, 0.01]);
    }
}

module form_shell() {
    if (FORM == 1 || FORM == 2) {
        chamfered(BASE_T + 1.5, 1.2) hull_plan();
        plinth();
        if (FORM == 2) sail();
    } else if (FORM == 3) {
        chamfered(BASE_T + 1.0, 2.6) hull_plan();
        // クレードルは箱のまま、天面と側面の角だけ大きく削ぐ
        intersection() {
            translate([GRIP_X0 - 3, CR_Y0 - 3, 0]) cube([GRIP_X1 - GRIP_X0 + 6, CR_Y1 - CR_Y0 + 6, CR_H]);
            hull() {
                translate([GRIP_X0 - 2, CR_Y0 - 2, 0]) cube([GRIP_X1 - GRIP_X0 + 4, CR_Y1 - CR_Y0 + 4, 0.01]);
                translate([GRIP_X0 + 2, CR_Y0 + 2, CR_H - 0.01]) cube([GRIP_X1 - GRIP_X0 - 4, CR_Y1 - CR_Y0 - 4, 0.01]);
            }
        }
    }
}

// 平面形は「足す」ではなく「削る」で決める。足すだけだと元の長方形と合わさって
// 長方形のまま残る（2026-08-08にそれをやった）
module stand_formed() {
    if (FORM == 0) stand();
    else difference() {
        intersection() {
            union() { stand(); form_shell(); }
            linear_extrude(80) hull_plan();            // ← 輪郭はここで決まる
        }
        cuts();                                        // 機能面を必ず引き直す
        // 土台の下の縁を全周45°で削ぐ（薄く見せる／剥がしの刃の入口も兼ねる）
        difference() {
            linear_extrude(BEVEL) offset(delta = 2) hull_plan();
            hull() {
                linear_extrude(0.01) offset(delta = -BEVEL) hull_plan();
                translate([0, 0, BEVEL - 0.01]) linear_extrude(0.01) hull_plan();
            }
        }
        translate([-60, -60, -50]) cube([300, 200, 50]);   // 底より下
        import("katanori_logo_cutter.stl");            // 抜き文字も引き直す
    }
}

stand_formed();
