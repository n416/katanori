// ============================================================
// 提案 E 「文庫本」── D の本体（幅 89・両端の口が壁に出る）の左に木のクレードル（幅 16）を足して文庫本 105 × 148 にした物（2026-09-13）
//   🔒 ユーザー 2026-09-13「USB を両方出させる為に、文庫本サイズの横は別の木製パーツで埋める。充電器も兼ねる」
//   🔒 同「逆。左につけて。メンテナンス用の USB はいつも使う訳ではないから。この木はいわばクレードルなんで、USB 基板は本体側。USB のオスだけがついてる」
//   本体の幅は ReSpeaker で決まる 89.13（左の壁に XIAO の USB-C・右の壁にジャック）。充電の Type-C 基板は本体の左の壁に口を出す。
//   木は左に付き、充電の口へ挿さる USB-C のオスだけを持つ（木の中に基板は無い）。木を付けている間、XIAO の USB-C は木の裏に隠れる。
//   ⚠ 木と本体の留め方・オスの線の出口・クレードルとして本体を受ける形（溝など）は描いていない。木は Y 0〜148 の板 1 枚
//   コンセプトは docs/CONCEPTS-2026-09-13.md。ここは形だけ。
//   座標: X 0〜W（右が +X）・Y 0〜H（手前が 0・本の上が +Y）・Z 0〜T（顔が Z T・机が Z 0）
//   顔の上の並び（上から）: ReSpeaker（寝かせてマイク面を上・口は顔の両端）／ OLED（左）とつまみ（右）／ スピーカー（左）と会話ボタン（右）。
//   電池は OLED の下（板の裏）。充電の Type-C は本体の左の壁（スピーカーと電池の間の Y）。
//   🔒 ユーザー 2026-09-13「トグルスイッチは無くす。リードスイッチに変更。しおり型の磁石が付いた板を外すと ON になるようにする。上から斜めに刺さるように。
//      このリードスイッチは表面近くにしておいて、後ほど作るカバーを閉じても電源が切れるようにする」
//   🔒 同「斜めはやめる。イメージしてたのは Z 軸を中心に時計回りに 10 度くらい」
//   ⇒ 電源はリードスイッチ（N/O・磁石が近いと閉）。しおり（板 20 × 45 × 2.2・先から 3 に φ6 の磁石）は皮の裏に平らに寝て、上の縁（Y 148）の口から
//      上から見て時計回りに 10° 振った向きで 16 刺さり（🔒 ユーザー「しおりはもっと押し込む想定。ちょっと出てるくらいのがしおり」「長さは短く。つまり磁石の位置はもっと上」: 板 20 で出るのは 4）、磁石がリードの真下に来る。リードは天面の皮のすぐ裏（芯 Z 15.4・上面が皮の裏 17.0 に着く）に X 向きで寝かせ、
//      後で作るカバーがこの真上（X 45・Y 138.6）に磁石を持てば、閉じたときも閉になる。回路は「閉 ＝ OFF」と読む（しおりを外す／カバーを開ける ＝ ON）。
//      しおりは皮の裏を平らに走るので、その下に高い物は置けない（板の下面 11.4）。上の縁の 19（Y 129〜148）がしおりのレーン。
//   🔒 ユーザー 2026-09-13「それならボタンとスピーカーを上に。バッテリーは下にしましょ」「下が重い方が持ちやすいので」⇒ 上から: レーン／会話ボタンとスピーカー（Y 108〜128）／ReSpeaker（Y 71〜105）／OLED とつまみ（Y 32〜70）／電池（Y 3〜38・OLED の下に 6 潜る）
//      ⚠ 板の寸法（20 × 20 × 2.2）・出る長さ 4・板の高さは私の仮の数字
//   実行: "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o d.png -D "part=\"look\"" hardware/concepts/concept_e_bunko.scad
//   part: look ／ guts ／ shell ／ cut（X で半分）／ pair（-D A=\"knob\" -D B=\"rsp\"）
// ============================================================
part = "look";
A = "knob"; B = "rsp";
$fn = 48;
include <_cunits.scad>

WALL = 2.0;
T = 19.0;                                   // 厚み。🔒 2026-09-13 つまみを薄くした（u_knob_flat・底は会話ボタンと同じ 15.085）ので、決めているのは ReSpeaker の鎖 2 ＋ 2.6 ＋ 1.85 ＋ 9.9 ＋ 2 ＝ 18.35。それまで つまみ v5 の 22.4 で 25 だった
W = WALL + cu_rsp_jack_out() + cu_rsp_len() + cu_rsp_xiao_out() + WALL;   // 89.1 左右の縁でジャックと XIAO の USB-C が止まる
H = 148.0;                                  // 文庫本（A6）の長辺
W_ALL = 105.0;                              // 文庫本の短辺（本体 ＋ 木）
WOOD_W = W_ALL - W; WOOD_X0 = -WOOD_W;      // 木のクレードル X −15.87〜0（幅 15.87）・Y 0〜148（本体は X 0〜89.13 のまま）
PLUG_SHELL = [6.5, 8.94, 3.26];             // USB-C オスの金属の殻（挿さる長さ 6.5 ⚠ 規格の概数・幅 8.94・厚み 3.26）
PLUG_BODY  = [10.0, 12.0, 6.5];             // オスの樹脂の胴（木の中）⚠ 概数
R_EDGE = 3.0;

// ---- 置き場 ----
RSP_X0 = WALL + cu_rsp_xiao_out();          // 3.5 板の左端（XIAO 側）
RSP_Y1 = 105.0;                             // 板の +Y の縁（Y 71〜105）。上は会話ボタンとスピーカーの帯（スピーカーの手が Y 105.5 まで下りる。106 だと 0.37mm³ 当たった）
RSP_Z0 = T - WALL - 0.3 - cu_rsp_front() - cu_rsp_t();   // 18.25 板の下面。マイク面の部品の頭が顔の内面から 0.3
OLED_C = [24.0, 51.0];                      // 顔の上の芯（X, Y）。板 2.8〜45.2 × 32〜70（ReSpeaker 72 の手前 2）
KNOB_C = [69.0, 51.0];                      // 顔の上の芯。皿 φ28.5・自作基板 30 × 30（仮）
SPK_C  = [22.0, 118.0];                     // 顔の上の芯（足 Y 108〜128・しおりのレーン 129 の手前）
BTN_C  = [69.0, 118.0];                     // 顔の上の芯（バスタブ Y 113.35〜123.25）
MARK_X = 45.0; MARK_ANG = 10; MARK_Z = 12.5;   // しおりの芯の X・上から見て時計回りに振る角度（🔒 ユーザー「Z 軸を中心に時計回りに 10 度くらい」）・板の芯の Z（板の上面 13.6 がリードの下面 13.8 の 0.2 下）
MARK_PL = [20.0, 20.0, 2.2]; MARK_IN = 16.0; MARK_MAG_FROM_TIP = 3.0;   // 板の幅・全長・厚み／刺さる深さ／先から磁石の芯まで ⚠ 仮
MARK_SLOT = [MARK_PL[0] + 2.0, MARK_PL[2] + 0.4];   // 通り道の幅と高さ（片側 1.0・上下 0.2）
MAG_W = [MARK_X + (MARK_IN - MARK_MAG_FROM_TIP) * sin(MARK_ANG), H - (MARK_IN - MARK_MAG_FROM_TIP) * cos(MARK_ANG)];   // 刺し切った磁石の芯（X 47.3・Y 135.2）。時計回りなので中へ行くほど +X
REED_Z = T - WALL - reed_body_sec() / 2;    // 15.4 リードの芯。上面が皮の裏に着く
BAT_AT = [2.5, 3.0, T - 2.85 - 0.65 - cu_bat()[2]];   // いちばん手前の帯。Y 3〜38 で OLED（32〜）の板の裏の 0.65 下に 6 潜る。X 2.5〜52.5
TC_AT  = [WALL + cu_tc_mouth_y(), 40.0, 2.5];   // 本体の左の壁。板は寝かせて部品面を上・口は左（X 2 ＝ 壁の内面。壁の穴を通って外へ）。局所 x（20）は +Y へ（Y 40〜60: スピーカーの足 36 と電池 60.5 の間）

module at_rsp()  translate([RSP_X0, RSP_Y1, RSP_Z0]) rotate([90, 0, 0]) children();   // 局所 y → +Z（マイク面が上）・z → −Y
module at_oled() translate([OLED_C[0], OLED_C[1], T - 0.2 - cu_oled_t()]) children();
module at_knob() translate([KNOB_C[0], KNOB_C[1], T]) children();   // 薄いつまみは丸いので向きは無い
module at_btn()  translate([BTN_C[0], BTN_C[1], T]) children();
module at_spk()  translate([SPK_C[0], SPK_C[1], T]) children();
module at_mark() translate([MARK_X, H, MARK_Z]) rotate([0, 0, -MARK_ANG]) children();   // しおりの局所: 原点 ＝ 上の縁の口の板の芯・+Y が外・−Y が中へ・Z が板の厚み。上から見て時計回りに 10°（OpenSCAD の Z 回転は反時計が正なので −）
module mark() {   // しおり（刺し切った姿勢）。磁石は板に埋め、平らな面をリードへ向ける
    color("#8fb8a0") difference() {
        translate([-MARK_PL[0] / 2, -MARK_IN, -MARK_PL[2] / 2]) cube(MARK_PL);
        translate([0, -(MARK_IN - MARK_MAG_FROM_TIP), -2]) cylinder(d = 6.1, h = 5);
    }
    color("#bbb") translate([0, -(MARK_IN - MARK_MAG_FROM_TIP), -magnet_reed_t() / 2]) magnet_reed();
}
module at_reed() translate([MAG_W[0], MAG_W[1], REED_Z]) children();   // 磁石の真上・X 向き
module c_mark(t = 10) translate([-MARK_SLOT[0] / 2, -MARK_IN - 1.0, -MARK_SLOT[1] / 2]) cube([MARK_SLOT[0], MARK_IN + 1.0 + t, MARK_SLOT[1]]);   // しおりの通り道（口から中へ）
module at_bat()  translate(BAT_AT) children();
module at_tc()   translate(TC_AT) rotate([0, 0, 90]) children();                     // 局所 y（口）→ −X・局所 x → +Y
PLUG_C = [TC_AT[1] + cu_tc()[0] / 2, TC_AT[2] + cu_tc_zc()];   // オスの芯（Y, Z）＝ 本体の充電の口の芯
module plug() {   // 木のクレードルが持つ USB-C のオス。殻は本体の壁を抜けて基板の口に 6.5 挿さる（tc との重なりは挿している分・意図した重なり）
    color("#aab") translate([-0.5, PLUG_C[0] - PLUG_SHELL[1] / 2, PLUG_C[1] - PLUG_SHELL[2] / 2]) cube([PLUG_SHELL[0] + 0.5 + WALL, PLUG_SHELL[1], PLUG_SHELL[2]]);
    color("#333") translate([-0.5 - PLUG_BODY[0], PLUG_C[0] - PLUG_BODY[1] / 2, PLUG_C[1] - PLUG_BODY[2] / 2]) cube([PLUG_BODY[0], PLUG_BODY[1], PLUG_BODY[2]]);
}
module wood_pocket() translate([-0.5 - PLUG_BODY[0] - 0.3, PLUG_C[0] - PLUG_BODY[1] / 2 - 0.3, PLUG_C[1] - PLUG_BODY[2] / 2 - 0.3]) cube([PLUG_BODY[0] + 0.3 + 1, PLUG_BODY[1] + 0.6, PLUG_BODY[2] + 0.6]);   // オスの胴の部屋 ⚠ 線の出口は無し
module wood() color("#c9a26b") difference() { translate([WOOD_X0, 0, 0]) cube([WOOD_W, H, T]); wood_pocket(); }

UNITS = ["rsp", "oled", "knob", "btn", "spk", "reed", "mark", "bat", "tc", "wood", "plug"];
module one(n) {
    if (n == "rsp")  at_rsp()  u_rsp(dupont = false);
    if (n == "oled") at_oled() u_oled();
    if (n == "knob") at_knob() u_knob_flat(pcb_bot = -cu_btn_deep());   // 底を会話ボタンのバスタブの底に揃える
    if (n == "btn")  at_btn()  u_btn();
    if (n == "spk")  at_spk()  u_spk();
    if (n == "reed") at_reed() reed_switch();
    if (n == "mark") at_mark() mark();
    if (n == "bat")  at_bat()  u_bat();
    if (n == "tc")   at_tc()   u_tc();
    if (n == "wood") wood();
    if (n == "plug") plug();
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
    at_mark() c_mark();
    for (mx = cu_rsp_mic_x()) translate([RSP_X0 + mx, RSP_Y1 - cu_rsp_h() / 2, T]) rotate([0, 0, 90]) c_mic();   // マイクの口: 顔の上の帯の両端 ⚠ Y は板の中央と仮定
    translate([0, RSP_Y1 - xiao_usb_yz()[1], RSP_Z0 - xiao_usb_yz()[0]]) rotate([0, 90, 0]) rotate([0, 0, 90]) c_usbc();   // XIAO の USB-C（左の縁。板の x 0 端が RSP_X0 ＝ 左）
    translate([W, RSP_Y1 - cu_rsp_jack_yz()[0], RSP_Z0 + cu_rsp_jack_yz()[1]]) rotate([0, 90, 0]) c_jack();               // ジャック（右の縁）
    translate([0, PLUG_C[0], PLUG_C[1]]) rotate([0, 90, 0]) rotate([0, 0, 90]) c_usbc();   // 充電の Type-C の口（左の壁。木のオスがここへ挿さる）
}
module shell() difference() { outer(); inner(); openings(); }

module scene(sk = true, gt = true) { if (gt) guts(); if (sk) color("#c9d0d8", 0.35) shell(); }
if (part == "look")  scene();
if (part == "guts")  scene(sk = false);
if (part == "shell") { color("#c9d0d8") shell(); wood(); }
if (part == "cut")   intersection() { scene(); translate([KNOB_C[0], -100, -100]) cube([200, 300, 200]); }
if (part == "pair")  intersection() { one(A); one(B); }

echo(str("E 文庫本 外形 木 ", WOOD_W, "（左）＋ 本体 W ", W, " ＝ ", W_ALL, " × H ", H, " × T ", T, "・リード芯 Z ", REED_Z, " X ", MAG_W[0], " Y ", MAG_W[1], "・磁石の上面から リードの芯 ", REED_Z - (MARK_Z + magnet_reed_t() / 2), "（閉じる距離 5）", "・ReSpeaker の鎖 ", WALL + cu_rsp_front() + cu_rsp_t() + cu_rsp_back_pins() + WALL, "・つまみの底 ", T - cu_kflat_deep(-cu_btn_deep()), "・会話ボタンの底 ", T - cu_btn_deep()));
