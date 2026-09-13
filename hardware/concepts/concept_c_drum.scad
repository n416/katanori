// ============================================================
// 提案 C 「ドラム」── 横に寝た筒。天面につまみ、顔は 15° 上を向いた平面（2026-09-13）
//   コンセプトは docs/CONCEPTS-2026-09-13.md。ここは形だけ。
//   座標: X 0〜L（筒の軸・右が +X）・筒の軸が Y 0・Z 0。顔は −Y（斜めの平面）・天面は Z TOP の平面・机は Z BOT の平面。
//   ReSpeaker は軸に沿って寝かせ、マイク面を上へ（マイクの口は天面の両端）。XIAO の USB-C は左の端面・ジャックは右の端面。
//   実行: "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o c.png -D "part=\"look\"" hardware/concepts/concept_c_drum.scad
//   part: look ／ guts ／ shell ／ cut（X で半分に切る）／ pair（-D A=\"knob\" -D B=\"rsp\"）
// ============================================================
part = "look";
A = "knob"; B = "rsp";
$fn = 96;
include <_cunits.scad>

WALL = 2.0;
R    = 36.0;                                // 筒の半径
TOP  = 28.0;                                // 天面の平面（Z）。弦の幅 2 × √(36² − 28²) ＝ 45.2 に台座 39 ＋ 逃げ
BOT  = -30.0;                               // 机に着く平面（Z）。弦の幅 39.8
FACE_TILT = 15;                             // 顔の平面が上を向く角度
FACE_D = 27.0;                              // 顔の平面の軸からの距離。弦の高さ 2 × √(36² − 27²) ＝ 47.6（OLED のガラス 27.2 と スピーカー 15 が縦に並ぶ）
L = WALL + cu_rsp_xiao_out() + cu_rsp_len() + cu_rsp_jack_out() + WALL;   // 89.2 両端の壁の内面で XIAO の USB-C とジャックが止まる
N_FACE = [0, -cos(FACE_TILT), sin(FACE_TILT)];   // 顔の法線（外向き）
V_FACE = [0, sin(FACE_TILT), cos(FACE_TILT)];    // 顔の面内の上向き
P_FACE = FACE_D * N_FACE;                        // 顔の平面が軸に一番近い点 (0, −26.08, 6.99)

// ---- 置き場 ----
KNOB_C = [50.0, -0.5];                      // 天面の芯（X, Y）。台座 y −16.7〜22.3 → Y −17.2〜21.8（弦 ±22.6 の中）。−2.8 だと吊りの壁が OLED の板の角とスピーカーの手に触れた（pairs.py）
BTN_C  = [23.0, 0.0];                       // 天面の芯（X, Y）。つまみの左
TGL_C  = [70.0, 4.0];                       // 天面の芯（X, Y）。つまみの右。胴 13 は Y に
OLED_X = 26.0;                              // 顔の上の芯の X。顔の面内の上下は 0（平面が軸に一番近い高さ）
SPK_X  = 71.0; SPK_V = -12.0;               // 顔の上の芯の X と、面内で下へ 12
RSP_X0 = WALL + cu_rsp_xiao_out();          // 3.6 板の左端（XIAO 側）
RSP_Y1 = 17.0;                              // 板の +Y の縁（局所 z 0 → Y 17・z 34 → Y −17）
RSP_Z0 = TOP - 2.5 - cu_knob_deep() - 2.2 - cu_rsp_front() - cu_rsp_t();   // −3.55 板の下面。マイク面の部品の頭 0.9 が吊りの板の裏 3.1 から 2.2（1.0 だと AS5600 のピンの先が部品に 0.04mm³ 触れた・pairs.py）
BAT_AT = [30.0, -cu_bat()[1] / 2, -27.0];   // 底。XIAO 面の DuPont（左端・Z −20.9 まで）と X で分ける
TC_AT  = [L - WALL - cu_tc_mouth_y(), 0.0, -16.0];   // 右の端面に口（Y −20〜0・Z −16〜−11）。ジャック（Y 10.5・Z −4.8）の下

module at_face(x, v) translate([x, 0, 0] + P_FACE + v * V_FACE) rotate([90 - FACE_TILT, 0, 0]) children();   // 顔の平面: 局所 +Z → N_FACE・局所 +Y → V_FACE
module at_rsp()  translate([RSP_X0, RSP_Y1, RSP_Z0]) rotate([90, 0, 0]) children();          // 局所 y → +Z（マイク面が上）・z → −Y
module at_oled() at_face(OLED_X, 0) translate([0, 0, -(0.2 + cu_oled_t())]) children();      // ガラスの面が顔の 0.2 裏
module at_knob() translate([KNOB_C[0], KNOB_C[1], TOP]) children();
module at_btn()  translate([BTN_C[0], BTN_C[1], TOP]) children();
module at_tgl()  translate([TGL_C[0], TGL_C[1], TOP]) rotate([0, 0, 90]) children();
module at_spk()  at_face(SPK_X, SPK_V) children();
module at_bat()  translate(BAT_AT) children();                                               // 50 を X・35 を Y・6 を Z
module at_tc()   translate(TC_AT) rotate([0, 0, -90]) children();                            // 局所 y → +X（口が右の端面）・x → −Y・部品面 → +Z

UNITS = ["rsp", "oled", "knob", "btn", "spk", "tgl", "bat", "tc"];
module one(n) {
    if (n == "rsp")  at_rsp()  u_rsp();
    if (n == "oled") at_oled() u_oled();
    if (n == "knob") at_knob() u_knob();
    if (n == "btn")  at_btn()  u_btn();
    if (n == "spk")  at_spk()  u_spk();
    if (n == "tgl")  at_tgl()  u_tgl();
    if (n == "bat")  at_bat()  u_bat();
    if (n == "tc")   at_tc()   u_tc();
}
module guts() for (n = UNITS) one(n);

// ---- 皮（筒 ∩ 天面の平面 ∩ 机の平面 ∩ 顔の平面）----
module drum(r, x0, x1, top, bot, fd) intersection() {
    translate([x0, 0, 0]) rotate([0, 90, 0]) cylinder(r = r, h = x1 - x0);
    translate([x0 - 1, -r - 1, bot]) cube([x1 - x0 + 2, 2 * r + 2, top - bot]);
    translate(fd * N_FACE) rotate([90 - FACE_TILT, 0, 0]) translate([-100, -100, -200]) cube([200, 200, 200]);   // 顔の平面より内側
}
module outer() drum(R, 0, L, TOP, BOT, FACE_D);
module inner() drum(R - WALL, WALL, L - WALL, TOP - WALL, BOT + WALL, FACE_D - WALL);
module openings() {
    at_oled() c_oled();
    at_knob() c_knob();
    at_btn()  c_btn();
    at_spk()  c_spk();
    at_tgl()  c_tgl();
    for (mx = cu_rsp_mic_x()) translate([RSP_X0 + mx, 0, TOP]) c_mic();                                   // マイクの口: 天面の両端 ⚠ Y は板の中央と仮定
    translate([0, RSP_Y1 - xiao_usb_yz()[1], RSP_Z0 - xiao_usb_yz()[0]]) rotate([0, 90, 0]) rotate([0, 0, 90]) c_usbc();   // 局所 z 17 → 世界 Y 0・局所 y −3.03 → 世界 Z   // XIAO の USB-C（左の端面）
    translate([L, RSP_Y1 - cu_rsp_jack_yz()[0], RSP_Z0 + cu_rsp_jack_yz()[1]]) rotate([0, 90, 0]) c_jack();            // ジャック（右の端面）
    translate([L, TC_AT[1] - cu_tc()[0] / 2, TC_AT[2] + cu_tc_zc()]) rotate([0, 90, 0]) rotate([0, 0, 90]) c_usbc();   // 充電の Type-C（右の端面）
}
module shell() difference() { outer(); inner(); openings(); }

module scene(sk = true, gt = true) { if (gt) guts(); if (sk) color("#c9d0d8", 0.35) shell(); }
if (part == "look")  scene();
if (part == "guts")  scene(sk = false);
if (part == "shell") color("#c9d0d8") shell();
if (part == "cut")   intersection() { scene(); translate([KNOB_C[0], -100, -100]) cube([200, 200, 200]); }
if (part == "pair")  intersection() { one(A); one(B); }

echo(str("C ドラム 長さ ", L, " × 幅 ", 2 * R, " × 高さ ", TOP - BOT, "（机から天面）・顔の傾き ", FACE_TILT, "°・ReSpeaker の板の下面 Z ", RSP_Z0));
