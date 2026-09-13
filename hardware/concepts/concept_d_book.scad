// ============================================================
// 提案 D 「ブック」── 部品を 1 層に並べた、本を寝かせた形の板（2026-09-13）
//   🔒 ユーザー 2026-09-13「一旦 DuPont コネクタは無しでいい。出来る限り平らに並べると。Book タイプみたいな感じ」
//   コンセプトは docs/CONCEPTS-2026-09-13.md。ここは形だけ。
//   座標: X 0〜W（右が +X）・Y 0〜H（手前が 0・本の上が +Y）・Z 0〜T（顔が Z T・机が Z 0）
//   顔の上の並び（上から）: ReSpeaker（寝かせてマイク面を上・口は顔の両端）／ OLED（左）とつまみ（右）／ スピーカー（左）と会話ボタン（右）。
//   電池は OLED の下（板の裏）。トグルと充電の Type-C は手前の縁。XIAO の USB-C は左の縁・ジャックは右の縁（🔴 2026-09-13 まで逆に書き、穴も逆に開けていた）。
//   実行: "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o d.png -D "part=\"look\"" hardware/concepts/concept_d_book.scad
//   part: look ／ guts ／ shell ／ cut（X で半分）／ pair（-D A=\"knob\" -D B=\"rsp\"）
// ============================================================
part = "look";
A = "knob"; B = "rsp";
$fn = 48;
include <_cunits.scad>

WALL = 2.0;
T = 19.0;                                   // 厚み。🔒 2026-09-13 つまみを薄くした（u_knob_flat・底は会話ボタンと同じ 15.085）ので、決めているのは ReSpeaker の鎖 2 ＋ 2.6 ＋ 1.85 ＋ 9.9 ＋ 2 ＝ 18.35。それまで つまみ v5 の 22.4 で 25 だった
W = WALL + cu_rsp_jack_out() + cu_rsp_len() + cu_rsp_xiao_out() + WALL;   // 89.1 左右の縁でジャックと XIAO の USB-C が止まる
H = 112.0;                                  // 手前の帯 30（スピーカー・会話ボタン・トグル・Type-C）＋ 中の帯 42（OLED・つまみ）＋ ReSpeaker 34 ＋ 壁と逃げ
R_EDGE = 3.0;

// ---- 置き場 ----
RSP_X0 = WALL + cu_rsp_xiao_out();          // 3.5 板の左端（XIAO 側）
RSP_Y1 = H - WALL;                          // 110 板の +Y の縁
RSP_Z0 = T - WALL - 0.3 - cu_rsp_front() - cu_rsp_t();   // 18.25 板の下面。マイク面の部品の頭が顔の内面から 0.3
OLED_C = [24.0, 56.0];                      // 顔の上の芯（X, Y）。板 2.8〜45.2 × 37〜75（ReSpeaker の下の縁 76 の手前 1）
KNOB_C = [69.0, 56.0];                      // 顔の上の芯。皿 φ28.5・自作基板 30 × 30（仮）
SPK_C  = [22.0, 16.0];                      // 顔の上の芯
BTN_C  = [69.0, 18.0];                      // 顔の上の芯。バスタブ Y 13.35〜23.25
TGL_C  = [47.0, T / 2 + 1.0];                     // 手前の縁の芯（X, Z）。スピーカー（〜39）と会話ボタン（57〜）の間
BAT_AT = [2.5, 38.5, T - 2.85 - 0.65 - cu_bat()[2]];   // OLED の板の裏（22.15）の 0.65 下。X 2.5〜52.5（つまみの台座 53 の手前）
TC_AT  = [32.0, WALL + cu_tc_mouth_y(), 2.5];          // 手前の縁の左。板は寝かせて部品面を上（スピーカーのバスタブの底 T − 10.2 ＝ 8.8 の下。会話ボタンの底 3.9 の下には入らない）

module at_rsp()  translate([RSP_X0, RSP_Y1, RSP_Z0]) rotate([90, 0, 0]) children();   // 局所 y → +Z（マイク面が上）・z → −Y
module at_oled() translate([OLED_C[0], OLED_C[1], T - 0.2 - cu_oled_t()]) children();
module at_knob() translate([KNOB_C[0], KNOB_C[1], T]) children();   // 薄いつまみは丸いので向きは無い
module at_btn()  translate([BTN_C[0], BTN_C[1], T]) children();
module at_spk()  translate([SPK_C[0], SPK_C[1], T]) children();
module at_tgl()  translate([TGL_C[0], 0, TGL_C[1]]) rotate([90, 0, 0]) children();   // 手前の縁: 局所 +Z → −Y・x（13）→ X・y（8）→ Z
module at_bat()  translate(BAT_AT) children();
module at_tc()   translate(TC_AT) rotate([0, 0, 180]) children();                    // 口を −Y（手前の縁）へ

UNITS = ["rsp", "oled", "knob", "btn", "spk", "tgl", "bat", "tc"];
module one(n) {
    if (n == "rsp")  at_rsp()  u_rsp(dupont = false);
    if (n == "oled") at_oled() u_oled();
    if (n == "knob") at_knob() u_knob_flat(pcb_bot = -cu_btn_deep());   // 底を会話ボタンのバスタブの底に揃える
    if (n == "btn")  at_btn()  u_btn();
    if (n == "spk")  at_spk()  u_spk();
    if (n == "tgl")  at_tgl()  u_tgl();
    if (n == "bat")  at_bat()  u_bat();
    if (n == "tc")   at_tc()   u_tc();
}
module guts() for (n = UNITS) one(n);

// ---- 皮 ----
module rbox(sz, r) translate([r, r, r]) minkowski() { cube([sz[0] - 2 * r, sz[1] - 2 * r, sz[2] - 2 * r]); sphere(r = r, $fn = 24); }
module outer() rbox([W, H, T], R_EDGE);
module inner() translate([WALL, WALL, WALL]) rbox([W - 2 * WALL, H - 2 * WALL, T - 2 * WALL], R_EDGE - 1.0);
module openings() {
    at_oled() translate([0, 0, 0.2 + cu_oled_t()]) c_oled();
    at_knob() c_knob_flat();
    at_btn()  c_btn();
    at_spk()  c_spk();
    at_tgl()  c_tgl();
    for (mx = cu_rsp_mic_x()) translate([RSP_X0 + mx, RSP_Y1 - cu_rsp_h() / 2, T]) rotate([0, 0, 90]) c_mic();   // マイクの口: 顔の上の帯の両端 ⚠ Y は板の中央と仮定
    translate([0, RSP_Y1 - xiao_usb_yz()[1], RSP_Z0 - xiao_usb_yz()[0]]) rotate([0, 90, 0]) rotate([0, 0, 90]) c_usbc();   // XIAO の USB-C（左の縁。板の x 0 端が RSP_X0 ＝ 左）
    translate([W, RSP_Y1 - cu_rsp_jack_yz()[0], RSP_Z0 + cu_rsp_jack_yz()[1]]) rotate([0, 90, 0]) c_jack();               // ジャック（右の縁）
    translate([TC_AT[0] - cu_tc()[0] / 2, 0, TC_AT[2] + cu_tc_zc()]) rotate([90, 0, 0]) c_usbc();                         // 充電の Type-C（手前の縁）
}
module shell() difference() { outer(); inner(); openings(); }

module scene(sk = true, gt = true) { if (gt) guts(); if (sk) color("#c9d0d8", 0.35) shell(); }
if (part == "look")  scene();
if (part == "guts")  scene(sk = false);
if (part == "shell") color("#c9d0d8") shell();
if (part == "cut")   intersection() { scene(); translate([KNOB_C[0], -100, -100]) cube([200, 300, 200]); }
if (part == "pair")  intersection() { one(A); one(B); }

echo(str("D ブック 外形 W ", W, " × H ", H, " × T ", T, "・ReSpeaker の鎖 ", WALL + cu_rsp_front() + cu_rsp_t() + cu_rsp_back_pins() + WALL, "・つまみの底 ", T - cu_kflat_deep(-cu_btn_deep()), "・会話ボタンの底 ", T - cu_btn_deep()));
