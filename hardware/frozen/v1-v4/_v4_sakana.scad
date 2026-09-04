// ============================================================
// 🐟 魚の開き（2026-08-24 ユーザー発案・完成版）
//   中継基板を中心に、各部品を口の方向へ、ケーブル長無限として開いた上面図。線は直線。
//   図の下＝前（OLED・ReSpeaker の面）。図の左＝OLED から見て右（つまみ・電池の蓋の側）。
//   口の役割は 🔒 実配線（ユーザーの補正・POWER.md 4章）を反映済み: つまみの線は OLED から見て右の口から出る。
//   灰色の点 ＝ 平面図でだけ重なる点。線を引く工程で高さと道順を割り付けて 0 にする（v3 は 13 本全部で重なり 0 の実績）。
// ============================================================
use <parts.scad>
use <respeaker_lite.scad>
use <hub_board.scad>
include <hub_board_parts.scad>
$fn = 24;
function bport(id) = [for (h = HUB_HEADERS) if (h[0] == id) [(h[4] + h[6]) / 2, (h[5] + h[7]) / 2]][0];
module lbl(t, s = 4.5, c = "#1a1a1a") color(c) translate([0, 0, 16]) linear_extrude(0.6) text(t, size = s, halign = "center", font = "Meiryo", $fn = 16);
module wire(a, b, c) color(c) hull() { translate([a[0], a[1], 10]) cylinder(d = 1.7, h = 0.8); translate([b[0], b[1], 10]) cylinder(d = 1.7, h = 0.8); }
module xmark(p) color("#cc0000") { translate([p[0], p[1], 12]) cylinder(d = 8, h = 0.5); }

// ---- 中央: 中継基板（箱に載る向きのまま） ----
hub_board(false);
translate([37, 30, 0]) lbl("中継基板", 6);

// ---- 前（図の下）: ReSpeaker を手前へ開く（XIAO 面が上を向く） ----
translate([84, -6, 0]) rotate([0, 0, 180]) rotate([-90, 0, 0]) respeaker_lite();
translate([40, -47, 0]) lbl("ReSpeaker（前・手前へ開いた姿）", 5);
STK = [73, -20];  J2P = [7.5, -20];
wire(bport("XIAO"), STK, "#e67e22"); translate([56, -4, 0]) lbl("XIAO 7本", 4, "#e67e22");
wire(bport("PHIN"), J2P, "#16a085"); translate([86, 37, 0]) lbl("PHIN 2本", 4, "#16a085");

// ---- 前・さらに手前: OLED（裏を上に向けて開く。ヘッダの辺が板側） ----
translate([78, -100, 0]) rotate([0, 180, 0]) oled_242();
OLH = [42.95, -53.5];
translate([43, -110, 0]) lbl("OLED（裏が上）", 5);
wire(bport("OLED"), OLH, "#2980b9");
translate([-14, 20, 0]) lbl("OLED 4本", 4, "#2980b9");

// ---- 左: つまみ（🔒 ご指定「つまみは左」）と会話ボタン ----
KN = [-28, 30];
translate([KN[0], KN[1], 0]) { color("#8e44ad", 0.5) cylinder(d = 27, h = 5); color("#6c3483") translate([0, 0, 2]) cube([12, 12, 4], center = true); }
translate([KN[0] + 2, KN[1] - 22, 0]) lbl("つまみ（OLEDから見て右）", 4.6);
wire(bport("AS5600"), [KN[0] + 14, KN[1]], "#8e44ad");
translate([-14, 40, 0]) lbl("AS5600 4本", 4, "#8e44ad");
BT = [-26, 54];
translate([BT[0], BT[1], 0]) color("#c0392b") cylinder(d = 14, h = 4);
translate([BT[0], BT[1] + 11, 0]) lbl("会話ボタン", 5);
wire(bport("BTN2"), [BT[0] + 8, BT[1]], "#c0392b");

// ---- 右: スピーカー ----
SP = [102, 40];
translate([SP[0] - 11.5, SP[1] - 7.5, 0]) color("#555") cube([23, 15, 4]);
translate([SP[0], SP[1] - 14, 0]) lbl("スピーカー", 5);
wire(bport("PHOUT"), [SP[0] - 12, SP[1]], "#27ae60"); translate([90, 48, 0]) lbl("PHOUT 2本", 4, "#27ae60");

// ---- 後ろ（図の上）: 電源の列 ----
translate([43, 76, 0]) powerboost_1000c(hdr = "none");
translate([61, 104, 0]) lbl("PowerBoost", 5);
wire(bport("PWR"), [61.1, 77.5], "#d35400"); translate([74, 57, 0]) lbl("PWR 3本", 4, "#d35400");
translate([38, 74, 0]) rotate([0, 0, 90]) ina226_module();
translate([8, 104, 0]) lbl("INA226", 5);
wire(bport("INA"), [28, 77], "#7f8c8d"); translate([20, 58, 0]) lbl("INA 4本", 4, "#7f8c8d");
translate([49.4, 68, 0]) rotate([0, 0, 90]) mts102(0);
translate([36, 64, 0]) lbl("トグル", 4);
wire(bport("TOGGLE"), [49.4, 64], "#2c3e50");
translate([57 - 7, 62, 0]) color("#2c3e50") cube([14, 3, 3]);
translate([66, 63, 0]) lbl("リード", 4);
wire(bport("REED"), [57, 62], "#95a5a6");
translate([2, 112, 0]) lipo_1000mah();
translate([56, 128, 0]) lbl("電池", 5);
wire([27, 112], [35.75, 91], "#111"); translate([16, 94, 0]) lbl("電池線", 4, "#111");
wire([20.15, 91], [53.7, 100], "#111");

// ---- 平面図でだけ重なる点（灰色）。線を引く工程で高さと道順を割り付けて 0 にする ----
module gdot(p) color("#808080") translate([p[0], p[1], 12]) cylinder(d = 6, h = 0.5);
gdot([33.7, 0.9]);    // XIAO と PHIN
gdot([10.7, 18.5]);   // つまみの線と OLED の口のそば
gdot([22.6, -8.0]);   // PHIN と OLED
color("#00600f") {
    translate([-30, -22, 12]) lbl("←この側＝OLEDから見て右", 4.4, "#00600f");
    translate([-30, -29, 12]) lbl("（つまみ・電池の蓋）", 4.0, "#00600f");
    translate([112, 84, 12]) lbl("この側＝OLEDから見て左→", 4.4, "#00600f");
    translate([112, 77, 12]) lbl("（XIAOのUSB・スピーカー）", 4.0, "#00600f");
}
translate([37, -122, 0]) lbl("魚の開き — 下＝前・上＝後ろ。口の役割は実配線（入れ替え済み）を反映", 4.8);
translate([37, -130, 0]) lbl("灰色の点＝平面図でだけ重なる点（線を引く工程で高さと道順を割り付けて0にする）", 4.5, "#808080");
