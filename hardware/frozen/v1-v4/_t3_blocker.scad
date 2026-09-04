// T-3: OLED の左のナットが入らない（2026-08-26）。
//   断面は X 9.5〜10.5（左の L のビス穴 X 10.002 を通る 1mm のスラブ）を、左（−X）から見た Y-Z 面。
//   画面の左が奥（+Y・ハッチ側）、右が手前（−Y・OLED 側）。
//   実行: python hardware/_t3_fig.py（レンダーと文字入れをまとめてやる）
include <case_v4.scad>
part = "none";

XC = 10.002;        // 左の L のビス穴
SL = 0.5;           // 断面のスラブの半分の厚み
Z0 = 41; Z1 = 51;   // 見る高さ
Y0 = -1; Y1 = 14;   // 見る奥行き

module win() translate([XC - SL, Y0, Z0]) cube([SL * 2, Y1 - Y0, Z1 - Z0]);
module cut() intersection() { children(); win(); }
// 会話ボタンの受けの板（X 9.5〜34.5・Y 6.8〜21.8・Z 47.104〜48.454）
module pad_raw() translate([BTN4[0] - BTN_PAD_X / 2, BTN4[1] - BTN_PAD_Y / 2, Z_BTN_PAD]) cube([BTN_PAD_X, BTN_PAD_Y, IN_Z - Z_BTN_PAD]);
// 🔒 この図は**直す前**の姿で描く。2026-08-26 に case_v4.scad で受けの手前左の角を欠いて解決したので、
//    いまの天面をそのまま切ると「なぜ入らなかったか」が消えてしまう。欠いた分を埋め戻してから切る。
//    埋め戻すのは**受けから削った分だけ**（欠きの箱は受けの外へ 0.1〜0.2 はみ出しているので、
//    そのまま足すと受けの前面が Y 6.8 → 6.7 になって、隙間 0.19 が図の上で 0.09 に見えてしまう）。
module notch() translate([9.3, 6.7, Z_BTN_PAD - 0.01]) cube([12.4 - 9.3, 10.0 - 6.7, IN_Z - Z_BTN_PAD + 0.01]);
module pad()  pad_raw();
module top_b(){ top_v4(); intersection() { notch(); pad_raw(); } }

// ---- 天面の断面（受けだけ色を分ける）----
color("#b9c2cc") difference()   { cut() top_b(); pad(); }
//    当たっている所は**赤にだけ**描く（同じ場所に橙と赤の 2 つの実体を置くと、どちらが手前か決まらず
//    レンダーのたびに絵が変わる）。
color("#e08a2e") difference() { intersection() { cut() top_b(); pad(); } nut(6.61); }
color("#3d566e") cut() oled_at();

// ---- ナット（二面幅 4.0 の現物・厚み 1.6）----
module nut(y) translate([XC, y, 46.1]) rotate([-90, 0, 0]) hex_pocket_af(4.0, 1.6);
//   🔴 ナットも断面で切る。切らずに描くと、ナットの手前半分（X 7.85〜9.5・受けより手前）が
//      当たっている角（X 9.5〜12.15）を隠してしまう（−X から見るので手前が勝つ）。
color("#2f6f4f") cut() nut(4.8);                              // 座った位置（ポケットの中 Y 4.8〜6.4）
color("#eab6ad") cut() difference()   { nut(6.61); pad(); }   // 差し込む直前の位置（L の裏から 0.01）
color("#e6231a") cut() intersection() { nut(6.61); pad(); }   // 🔴 通れない角（受けの中に入っている）

// ---- L の裏面（Y 6.6）と 受けの前面（Y 6.8）の隙間 0.19 ----
color("#d81b60") translate([XC - SL - 0.2, 6.61, 47.104]) cube([(SL + 0.2) * 2, 0.19, 48.454 - 47.104]);
