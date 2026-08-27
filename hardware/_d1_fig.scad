// D-1 の絵（2026-08-27）: 充電基板の受け（tc_seat4）が床の背を決めている
//   形の定義は case_v4.scad の側にある。ここは色を塗って切り出すだけ
//   実行は python hardware/_d1_fig.py
include <case_v4.scad>
Q2 = "";
HOUS = true;
BOARD_ON = true;   // デュポンのハウジング（青）を描くか。false で受けと板が見える
module seat_red() color("#e53e3e") tc_seat4();
module floor_gray() color("#9aa5b1") floor_v4();
// ① 刷る向きの床。🔒 2026-08-27（D-1）で受けは床から出たので、床に残るのは枠（赤）だけ。
//    受け本体は 12mm 持ち上げて、落とし込む向きが分かるように置く
if (Q2 == "floor_now") translate([0, 0, FLOOR_T]) {
    color("#9aa5b1") difference() { p_one("floor"); seat_frame4(); }
    color("#e53e3e") seat_frame4();
    translate([0, 0, 18]) color("#2b6cb0") tc_seat4();
}
// ② 受けのまわり（壁は外して中を見せる。緑＝Type-C 基板・青＝デュポン・黄＝ハブ）
module cutbox2() translate([-2, 44, -3]) cube([16, 32, 30]);
if (Q2 == "near") intersection() {
    union() { floor_gray(); seat_red(); color("#2f855a") tcb_v4_bare(); if (HOUS) color("#4299e1") tcb_v4();
              color("#d69e2e") hub_unit(); color("#a0aec0") brg_tc_press(); }
    cutbox2();
}
// ③ 受け単体（別刷りにするなら、この 257mm3 が部品になる）
if (Q2 == "seat_only") seat_red();
// ④ 板を受けに入れる道（D-1 の追検査）。Z 4〜9（下の L 字コネクタの高さ）で切った**真上から**の断面。
//   灰＝左の壁／緑＝Type-C 基板と L 字コネクタ／赤＝受け（②③④⑤）／黄＝ハブの柱
module d1_slice() intersection() {
    union() { color("#8d99a6") difference() { lwall_v4(); tc_seat4(); } seat_red();
              color("#2f855a") tcb_v4_bare(); }
    translate([-1, 53, D1_SZ]) cube([8, 21, 1.0]);
}
D1_SZ = 6.0;   // 断面の高さ（6.0 = 下の L 字コネクタ／12.0 = 段の間／17.0 = 上の L 字）
if (Q2 == "slice") d1_slice();

// ⑤ 左の壁を**箱の内側から**（+X から）見た図。受けが壁の部品になったときの姿。
//   灰＝壁本体（棚・ボス込み）／赤＝受け（tc_seat4）／橙＝押さえ（brg_tc_press）／緑＝Type-C 基板
if (Q2 == "wall_in") {
    color("#8d99a6") difference() { lwall_v4(); tc_seat4(); brg_tc_press(); }
    seat_red();
    color("#dd6b20") brg_tc_press();
    if (BOARD_ON) color("#2f855a") tcb_v4_bare();
}

// ⑥ 受けの足元を真上から見た図（D-1・ストッパーの置き場を決めるため）。Z 0〜4 で切る。
//   灰＝床（受けを引いたもの）／赤＝受けの足（Z 0〜4 の断面）／橙＝ハブの柱と基板／緑＝Type-C 基板の足元
D1_TOPZ = 4.0;
module d1_top() intersection() {
    union() { color("#9aa5b1") difference() { floor_v4(); tc_seat4(); }
              seat_red();
              color("#d69e2e") hub_unit();
              if (BOARD_ON) color("#2f855a") tcb_v4_bare(); }
    translate([-1, 44, 0]) cube([14, 29, D1_TOPZ]);
}
if (Q2 == "top") d1_top();

// ⑦ 受けを真横（+X から）見た立面（D-1・ストッパーの当たり所を決めるため）。
//   赤＝受け／緑＝Type-C 基板／灰＝床。⑤ 前の三角は Y 52.2（Z 0）から Y 55.95（Z 12）へ斜めに立ち、
//   その上（Z 12〜20.5）だけ ② の前面が平らに出る。ケーブルの力は口の中心 Z 10.5 に効く。
if (Q2 == "side") intersection() {
    union() { seat_red(); if (BOARD_ON) color("#2f855a") tcb_v4_bare(); color("#9aa5b1") difference() { floor_v4(); tc_seat4(); } }
    translate([1.0, 46, -2.1]) cube([5.5, 29, 24]);
}
