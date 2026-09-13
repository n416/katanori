// ============================================================
// 提案 A 「フレーム」── 12° 傾けて立つ薄い板（2026-09-13）
//   コンセプトは docs/CONCEPTS-2026-09-13.md。ここは形だけ。
//   板の座標: X 0〜W（右が +X）・Y 0〜T（顔が Y 0・奥が +Y）・Z 0〜H（上が +Z）。最後に全体を X 軸で LEAN 度だけ後ろへ倒す。
//   実行: "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o a.png -D "part=\"look\"" hardware/concepts/concept_a_frame.scad
//   part: look（皮を透かして中身）／ guts（中身だけ）／ shell（皮だけ）／ cut（Y で半分に切る）／ flat（傾けない）／ pair（A と B の重なり: -D A=\"knob\" -D B=\"rsp\"）
// ============================================================
part = "look";
A = "knob"; B = "rsp";
LEAN = 12;
$fn = 48;
include <_cunits.scad>

WALL = 2.0;
T = 30.0;                                   // 厚み: ReSpeaker 側の鎖 2 ＋ 0.2 ＋ 2.65 ＋ 1.3 ＋ 2.6 ＋ 1.85 ＋ 17.5 ＋ 2 ＝ 30.1 → 30（つまみ側は 2.5 ＋ 22.4 ＝ 24.9 で余る）
W = WALL + cu_rsp_jack_out() + cu_rsp_len() + cu_rsp_xiao_out() + WALL;   // 89.2 ジャックの筒と XIAO の USB-C が左右の壁の内面で止まる
H = 84.0;                                   // 下の帯 42（スピーカー・会話ボタン・トグル）＋ OLED 38 ＋ 壁 2 × 2
R_EDGE = 4.0;

// ---- 置き場（板の座標）----
RSP_X1 = W - WALL - cu_rsp_xiao_out();      // 85.6 板の右端（XIAO 側）
RSP_Y  = WALL + 0.2 + cu_oled_t() + 1.3 + cu_rsp_front() + cu_rsp_t();   // 10.6 板の奥の面（XIAO 面）。マイク面の部品の頭が OLED の板の裏から 1.3
RSP_Z0 = 46.0;                              // 板の下端
OLED_C = [W / 2, WALL + 0.2 + cu_oled_t(), RSP_Z0 + cu_rsp_h() / 2];   // 板の裏の Y 2.85・ReSpeaker の高さの中央
KNOB_C = [70.0, 23.0];                      // 顔の上の芯（X, Z）。台座 39 は X に寝かせる（X 47.7〜86.7）
BTN_C  = [18.0, 20.0];                      // 顔の上の芯（X, Z）
SPK_C  = [35.0, 13.0];                      // 底面の芯（X, Y）。下向きに鳴らす
TGL_C  = [13.0, 38.0];                      // 左の側面の芯（Y, Z）
BAT_AT = [8.0, 18.0, 46.0];                 // ReSpeaker の裏（XIAO の反対側）に立てて隠す。Y 18.0 は XIAO 面の部品の頭 10.6 ＋ 6.84（rsp × bat の重なりで測った）＋ 0.56
TC_AT  = [40.0, T - WALL - cu_tc_mouth_y(), 12.0];   // 奥の壁に口。板は YZ 面に立つ

module at_rsp()  translate([RSP_X1, RSP_Y, RSP_Z0]) rotate([0, 0, 180]) children();          // XIAO 端を右へ・マイク面を顔へ
module at_oled() translate(OLED_C) rotate([90, 0, 0]) children();                            // ガラスを −Y（顔）へ
module at_knob() translate([KNOB_C[0], 0, KNOB_C[1]]) rotate([90, 0, 0]) rotate([0, 0, 90]) children();   // 局所 y（台座の 39）→ −X・局所 z → −Y
module at_btn()  translate([BTN_C[0], 0, BTN_C[1]]) rotate([90, 0, 0]) children();
module at_spk()  translate([SPK_C[0], SPK_C[1], 0]) rotate([180, 0, 0]) children();          // 底面: 局所 +Z → −Z
module at_tgl()  translate([0, TGL_C[0], TGL_C[1]]) rotate([0, -90, 0]) children();          // 左の側面: 局所 +Z → −X
module at_bat()  translate(BAT_AT) rotate([90, 0, 0]) translate([0, 0, -cu_bat()[2]]) children();   // 50 を X・35 を Z・厚み 6 を +Y
module at_tc()   translate(TC_AT) rotate([0, -90, 0]) children();                            // 局所 x → +Z・局所 y → +Y（口が奥）・部品面 → −X

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

// ---- 皮 ----
module rbox(sz, r) translate([r, r, r]) minkowski() { cube([sz[0] - 2 * r, sz[1] - 2 * r, sz[2] - 2 * r]); sphere(r = r, $fn = 24); }
module outer() rbox([W, T, H], R_EDGE);
module inner() translate([WALL, WALL, WALL]) rbox([W - 2 * WALL, T - 2 * WALL, H - 2 * WALL], R_EDGE - 1.0);
module openings() {
    at_oled() c_oled();
    at_knob() c_knob();
    at_btn()  c_btn();
    at_spk()  c_spk();
    at_tgl()  c_tgl();
    // マイクの口: OLED の左右に 1 つずつ（ステレオの顔）
    for (mx = cu_rsp_mic_x()) translate([RSP_X1 - mx, 0, RSP_Z0 + cu_rsp_h() / 2]) rotate([90, 0, 0]) c_mic();
    // XIAO の USB-C（右の側面）・ジャック（左の側面）
    translate([W, RSP_Y + xiao_usb_yz()[0], RSP_Z0 + cu_rsp_usb_z()]) rotate([0, 90, 0]) rotate([0, 0, 90]) c_usbc();   // 局所 y −3.03（XIAO 面の奥）→ 世界 +Y
    translate([0, RSP_Y - cu_rsp_jack_yz()[1], RSP_Z0 + cu_rsp_jack_yz()[0]]) rotate([0, 90, 0]) c_jack();   // 局所 y −2.485 → 世界 +Y
    // 充電の Type-C（奥の壁）
    translate([TC_AT[0] - cu_tc()[2] - cu_tc_zc() + cu_tc()[2], T, TC_AT[2] + cu_tc()[0] / 2]) rotate([-90, 0, 0]) rotate([0, 0, 90]) c_usbc();
}
module feet() {   // 傾けたあと机に着く足 2 本（左右）。間はスピーカーの音の道
    c = cos(LEAN); s = sin(LEAN);
    for (x0 = [0, W - 16]) translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(16)
        polygon([[0, 0], [T * c + 12, 0], [T * c + 12, 4], [T * c + 1, 4], [T * c, 0.001], [0, T * s]]);
}
module shell() difference() { outer(); inner(); openings(); }
module lean() translate([0, 0, T * sin(LEAN)]) rotate([-LEAN, 0, 0]) children();   // 顔を上へ向けて後ろへ倒し、奥の下の縁を机（z 0）に

module scene(sk = true, gt = true) {
    lean() { if (gt) guts(); if (sk) color("#c9d0d8", 0.35) shell(); }
    if (sk) color("#c9d0d8", 0.35) feet();
}
if (part == "look")  scene();
if (part == "guts")  scene(sk = false);
if (part == "shell") { lean() color("#c9d0d8") shell(); color("#c9d0d8") feet(); }
if (part == "flat")  { guts(); color("#c9d0d8", 0.35) shell(); }
if (part == "cut")   intersection() { scene(); translate([-1, 5, -1]) cube([W + 2, 200, 200]); }   // OLED とつまみの芯の間（Y 5 より奥）を残す
if (part == "pair")  intersection() { one(A); one(B); }

echo(str("A フレーム 外形 W ", W, " × T ", T, " × H ", H, "・傾き ", LEAN, "°・机の上の高さ ", H * cos(LEAN) + T * sin(LEAN)));
