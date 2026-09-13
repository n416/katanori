// ============================================================
// 提案 B 「ハンド」── 片手で持つ縦型（2026-09-13）
//   コンセプトは docs/CONCEPTS-2026-09-13.md。ここは形だけ。
//   座標: X 0〜W（右が +X）・Y 0〜T（顔が Y 0・背が +Y）・Z 0〜H（上が +Z）
//   左の列: ReSpeaker を縦に（XIAO の USB-C が上の縁・ジャックが下の縁）・その顔に OLED。右の列: つまみ（上）・会話ボタン（下）。
//   実行: "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o b.png -D "part=\"look\"" hardware/concepts/concept_b_hand.scad
//   part: look ／ guts ／ shell ／ cut ／ back（背から見る向きに回す）／ pair（-D A=\"knob\" -D B=\"rsp\"）
// ============================================================
part = "look";
A = "knob"; B = "rsp";
$fn = 48;
include <_cunits.scad>

WALL = 2.0;
T = 30.0;                                   // 厚み: ReSpeaker 側の鎖 2 ＋ 0.2 ＋ 2.65 ＋ 1.3 ＋ 2.6 ＋ 1.85 ＋ 17.5 ＋ 2 ＝ 30.1 → 30（つまみ側は 2.5 ＋ 22.4 ＝ 24.9）
H = WALL + cu_rsp_jack_out() + cu_rsp_len() + cu_rsp_xiao_out() + WALL;   // 89.2 上下の縁で XIAO の USB-C とジャックが止まる
COL_L = WALL + 0.5 + cu_rsp_h() + 0.5;      // 37.0 左の列の右端（ReSpeaker の幅 34 に逃げ 0.5 ずつ）
KNOB_X = 64.5;                              // 右の列の芯。台座 32 は X 48.5〜80.5（OLED の窓を左の丸い角から離すため 61.5 → 64.5・2026-09-13）
W = KNOB_X + cu_knob_pad()[0] / 2 + 0.5 + WALL;   // 80.0
R_EDGE = 4.0;

// ---- 置き場 ----
RSP_Y  = WALL + 0.2 + cu_oled_t() + 1.3 + cu_rsp_front() + cu_rsp_t();   // 10.6 板の背の面（XIAO 面）
RSP_X1 = WALL + 0.5 + cu_rsp_h();           // 36.5 板の右端
RSP_Z1 = H - WALL - cu_rsp_xiao_out();      // 87.1 板の上端（XIAO 側）
OLED_C = [RSP_X1 - cu_rsp_h() / 2 + 7.5, WALL + 0.2 + cu_oled_t(), RSP_Z1 - cu_rsp_len() / 2];   // 板の裏 Y 2.85・ReSpeaker の長さの中央。X は右へ 7.5 寄せる: 板 5.8〜48.2（つまみの台座 48.5 の手前 0.3）・ガラスの窓 6.7〜47.3（角の丸め 4 の外）
KNOB_Z = 60.0;                              // 台座 y −16.7〜22.3 → Z 43.3〜82.3
BTN_C  = [KNOB_X, 26.0];                    // 顔の上（X, Z）。バスタブ Z 18〜34
SPK_C  = [KNOB_X, 24.0];                    // 背の上（X, Z）。会話ボタンの真裏（バスタブ 15.1 ＋ 10.2 ＜ 25）
TGL_C  = [12.5, 36.5];                      // 右の側面（Y, Z）。胴 Y 6〜19・Z 32.5〜40.5: 会話ボタンのバスタブ 31.25 の上・つまみの吊り 41.0 の下・背のスピーカーのバスタブ 19.8 の手前（2026-09-13 pairs.py で当たった 2 件を直した）
BAT_AT = [WALL + 0.5, 18.0, 8.0];           // ReSpeaker の背（XIAO の反対＝下半分）。50 を Z に。Y 18.0 は XIAO 面の部品の頭 10.6 ＋ 6.84（A 案の rsp × bat で測った）＋ 0.56
TC_C   = [52.0, 6.0];                       // 下の縁（X 52〜72）。口は −Z・部品面は +Y

module at_rsp()  translate([RSP_X1, RSP_Y, RSP_Z1]) rotate([0, 0, 180]) rotate([0, 90, 0]) children();   // 局所 x → −Z（XIAO を上へ）・y → −Y（マイク面を顔へ）・z → −X
module at_oled() translate(OLED_C) rotate([90, 0, 0]) children();
module at_knob() translate([KNOB_X, 0, KNOB_Z]) rotate([90, 0, 0]) children();               // 局所 y（39）→ +Z
module at_btn()  translate([BTN_C[0], 0, BTN_C[1]]) rotate([90, 0, 0]) children();
module at_spk()  translate([SPK_C[0], T, SPK_C[1]]) rotate([-90, 0, 0]) children();          // 背: 局所 +Z → +Y
module at_tgl()  translate([W, TGL_C[0], TGL_C[1]]) rotate([0, 90, 0]) rotate([0, 0, 90]) children();   // 右の側面: 局所 z → +X・x（13）→ Y・y（8）→ Z
module at_bat()  translate(BAT_AT) multmatrix([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]]) children();   // 局所 x（50）→ Z・y（35）→ X・z（6）→ +Y（巡回なので回転）
module at_tc()   translate([TC_C[0], TC_C[1], WALL + cu_tc_mouth_y()]) rotate([-90, 0, 0]) children();   // 局所 y → −Z（口が下）・z → +Y

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

// ---- 皮（縦長・四隅と厚みの角を大きく丸める）----
module rslab(sz, r) hull() for (x = [r, sz[0] - r], z = [r, sz[2] - r]) translate([x, 0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = sz[1]);
module rbox(sz, r) translate([r, r, r]) minkowski() { cube([sz[0] - 2 * r, sz[1] - 2 * r, sz[2] - 2 * r]); sphere(r = r, $fn = 24); }
module outer() rbox([W, T, H], R_EDGE);
module inner() translate([WALL, WALL, WALL]) rbox([W - 2 * WALL, T - 2 * WALL, H - 2 * WALL], R_EDGE - 1.0);
module openings() {
    at_oled() c_oled();
    at_knob() c_knob();
    at_btn()  c_btn();
    at_spk()  c_spk();
    at_tgl()  c_tgl();
    for (mx = cu_rsp_mic_x()) translate([RSP_X1 - cu_rsp_h() / 2, 0, RSP_Z1 - mx]) rotate([90, 0, 0]) rotate([0, 0, 90]) c_mic();   // マイクの口: 上と下（顔）
    translate([RSP_X1 - cu_rsp_usb_z(), RSP_Y + xiao_usb_yz()[0], H]) rotate([0, 0, 90]) c_usbc();   // 局所 y −3.03 → 世界 +Y   // XIAO の USB-C（上の縁）
    translate([RSP_X1 - cu_rsp_jack_yz()[0], RSP_Y - cu_rsp_jack_yz()[1], 0]) c_jack();   // 局所 y −2.485 → 世界 +Y                      // ジャック（下の縁）
    translate([TC_C[0] + cu_tc()[0] / 2, TC_C[1] + cu_tc_zc(), 0]) c_usbc();                                  // 充電の Type-C（下の縁）
}
module shell() difference() { outer(); inner(); openings(); }

module scene(sk = true, gt = true) { if (gt) guts(); if (sk) color("#c9d0d8", 0.35) shell(); }
if (part == "look")  scene();
if (part == "guts")  scene(sk = false);
if (part == "shell") color("#c9d0d8") shell();
if (part == "back")  translate([W, T, 0]) rotate([0, 0, 180]) scene();
if (part == "cut")   intersection() { scene(); translate([-1, 4, -1]) cube([W + 2, 200, 200]); }
if (part == "pair")  intersection() { one(A); one(B); }

echo(str("B ハンド 外形 W ", W, " × T ", T, " × H ", H));
