include <case_v3.scad>
// ============================================================
// 🔍 v4 スタディ②: 魚の開き（_v4_sakana.scad）を立体に畳む（2026-08-24）
//   魚の開きは「口の役割」の正（実配線・入れ替え済み）。立体の座標の正は
//   v3 の値（固定部品）＋ スタディ①の C 案（PowerBoost 背面立て・_v4_pb.scad）。
//   ここで新しく置く物は INA226（v3 の位置が C でも空いているかの検査）と
//   Type-C 基板（🔒 左の壁・後ろ下 CHG_C_LW）。電池・トグルは v3 の位置のまま。
//   C_AT は _v4_pb.scad と同値。変えるときは両方を変える。
//   実行: openscad --backend=manifold -o x.stl -D "W=\"ina\"" hardware/_v4_asm.scad
//        絵は -o x.png（look / lookbox / looktop）
// ============================================================
part = "none";   // case_v3 の top-level の形は出さない
W = "look";      // look / lookbox / ina / tcb / bat
INA_RA = true;   // INA226 のヘッダの 2 モデル（true = L 字横出し / false = 直立て）。-D で切替

// ---- ReSpeaker / OLED の挿さる物（_v4_pb.scad と同じ）--------------------
module at_rsp() translate([RSP_X + respeaker_L(), RSP_BD_Y1, RSP_Z]) rotate([0, 0, 180]) children();
module rsp_j2_space() at_rsp() { j = respeaker_spk_j2(); translate([j[0], -15, j[2]]) cube([j[1] - j[0], 15, j[3] - j[2]]); }
module xiao_hous() at_rsp() respeaker_xiao_housings();
module at_oled() translate([OLED_X0, OLED_Y1, OLED_Z0]) rotate([90, 0, 0]) children();
module oled_hous() at_oled() oled_i2c_housing();

// ---- PowerBoost C 案（スタディ①の生き残り・_v4_pb.scad の C と同値）------
C_AT = [84.3, IN_Y - 0.5 - 1.2, 33.0];   // ⚠ 上縁 Z はやり直しの走査（W="pbz"/"pbzh"）で窓 [32, 34.5] の中央 33 へ（2026-08-24。スタディ①の 34.5 は「上から下げて最初の 0」で窓の上端だった）
module pose_c() translate(C_AT) rotate([0, 0, 180]) rotate([-90, 0, 0]) children();
module pb_c() pose_c() { powerboost_1000c(hdr = "front", ra_dir = -1); pb_jst_plug(); }
module hous_c() pose_c() {
    for (i = [3, 4]) { x = 12.83 + i * 2.54;
        translate([x - 1.27, -HOUS_H, 1.6 + 2.5 - 1.27]) cube([2.54, HOUS_H, 2.54]);
        translate([x - HOUS_R / 2, -HOUS_H - HOUS_R, 1.6 + 2.5 - HOUS_R / 2]) cube([HOUS_R, HOUS_R, HOUS_R]); }
    translate([12.83 + 7 * 2.54 - 1.27, 0, 1.6 + 2.5]) cube([2.54, 2.54, HOUS_H]);          // USB（ハブ側へ水平）
    translate([pb_hdr_x() - 1.27, pb_hdr_y0(), 1.6 + 2.5]) cube([2.54, 4 * 2.54, HOUS_H]);  // PWR（ハブ側へ水平）
}

// ---- 新しく当てる 2 つ ---------------------------------------------------
// INA226: v3 の位置（部品面を下へ吊る姿勢）のまま。板の面は Z 21.6〜23.2 で固定し、
//         ヘッダの 2 モデル（L 字横出し / 直立て）を差し替えて当てる（🔒 2026-08-24 ユーザー「2 モデル作って置く」）
module ina_v4() translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module(ra = INA_RA);
// Type-C 基板（秋月 115426）: 🔒 左の壁・後ろ下（CHG_C_LW）。板＋L ピン＋挿した線
module tcb_unit() { tcb_at(); tcb_ra(); tcb_hous(); }

// ---- 障害物（スタディ①の fix4 と同じ固定物）------------------------------
module skin() {
    translate([-WALL, 0, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y, FLOOR_T]);                       // 床（素の板）
    translate([-WALL, 0, 0])        cube([WALL, IN_Y, IN_Z + TOP_T]);                             // 左の壁（素）
    translate([IN_X, 0, 0])         cube([WALL, IN_Y, IN_Z + TOP_T]);                             // 右の壁（素）
    translate([-WALL, IN_Y, -FLOOR_T]) cube([IN_X + 2 * WALL, HATCH_T, IN_Z + TOP_T + FLOOR_T]);  // ハッチ（素）
}
module fix_v4() {
    skin(); toggle_on_hatch();
    hub_at(); one("hous");
    respeaker_at(); xiao_hous(); oled_hous();
    top_plate(); one("knob");
    front_plate();                                                                                // OLED＋ヘッダ込み
    rsp_j2_space();
}
// 相手 = 自分以外の全部（固定物 ＋ C の PowerBoost ＋ 電池 ＋ もう片方の新入り）
module others(k) {
    difference() { fix_v4(); tcb_slot_cut(); left_wall_port_cut(); }   // 左の壁の溝（板の縁が 0.9 入る）と口の開口。v3 の左の壁と同じ扱い
    pb_c(); hous_c();
    translate(LIPO_AT) lipo_1000mah();
    if (k != "ina") ina_at_x();   // ⚠ INX の仮決め位置（v3 の位置の検査だけ ina_v4 を直接使う）
    if (k != "tcb") tcb_unit();
}

// ---- 検査 ----------------------------------------------------------------
if (W == "ina") intersection() { ina_v4(); others("ina"); }
if (W == "tcb") intersection() { tcb_unit(); others("tcb"); }
if (W == "bat") intersection() {   // 電池の座＋左へ抜く道 ↔ 新入り 2 つ（他はスタディ①で検査済み）
    union() { translate(LIPO_AT) lipo_1000mah();
              translate(LIPO_AT - [LIPO_L + WALL + 5, 0, 0]) lipo_swap_path(travel = LIPO_L + WALL + 5, clear = 0.3); }
    union() { ina_at_x(); tcb_unit(); }
}

// ---- 絵（畳んだ姿）--------------------------------------------------------
module fold_parts() {
    hub_at(); one("hous");
    respeaker_at(); xiao_hous();
    oled_at(); oled_hous();
    color("#f6ad55") pb_c(); color("#63b3ed", 0.85) hous_c();
    color("#9ae6b4", 0.8) translate(LIPO_AT) lipo_1000mah();
    ina_at_x();
    tcb_unit();
    as_conn();   // AS5600 のコネクタ（④⑤ スタディ・R/RA の既定 = 直立て R0）
    toggle_on_hatch();
    one("knob");
    translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495();
    translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch();
}
// ---- §4 ①〜③ まな板の再検査（v3→v4 差分④: ハブの口の柱・座を直した頭 20.2 で当て直す）----
// 🔴 探針に親基板を入れない: housing() は樹脂ごと描くので、ハブ自身のヘッダ（挿さる相手）と自己重複する。
//    ハブの線 ↔ ハブ、XIAO の線 ↔ ReSpeaker は「挿さっている」が正で、検査するのは他人との当たりだけ
module sweep_up2(n) for (t = [0 : STEP : n]) translate([0, 0, t]) children();
if (W == "mana")   intersection() { union() { one("hous"); xiao_hous(); } floor_v3(); }           // 挿し終わった線 ↔ 床の形（柱・土手・リブ）
if (W == "mana2")  intersection() { one("hous"); respeaker_at(); }                                // ハブの線 ↔ ReSpeaker（積み重ね込み）
if (W == "manain") intersection() { sweep_up2(30) one("hous"); union() { floor_v3(); respeaker_at(); } }   // 線を上から挿す軌跡（上は開いている時点）
// ---- 天面の前リブ（差分②）の帯出し: リブを全幅に伸ばした探針を相手ごとに当て、空いている X を読む ----
//   形は v3 の前リブそのもの（Y RSP_BD_Y0−0.5 から 2.85・Z RSP_TOP−0.3 から天井）を X 2〜84 に伸ばした物
module rib_probe() translate([2, RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([82, respeaker_T() + 1.0, IN_Z - RSP_TOP + RSP_PRESS + 0.01]);
if (W == "ribf") intersection() { rib_probe(); front_plate(); }                                   // ↔ フロント＋OLED（ヘッダ込み）
if (W == "ribh") intersection() { rib_probe(); oled_hous(); }                                     // ↔ OLED の線
if (W == "ribs") intersection() { rib_probe(); translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495(); }   // ↔ スピーカー
if (W == "ribk") intersection() { rib_probe(); union() { one("knob"); translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch(); } }   // ↔ つまみの島・タクト
if (W == "ribr") intersection() { rib_probe(); respeaker_at(); }                                  // ↔ ReSpeaker 自身（押さえ 0.3 の分だけ出るのが正）
// 帯の絵: 塞がり（OLED の線 X 37.9〜48.1・フロントの耳 〜6.25 / 79.75〜）を赤、空きを緑
module rib_band(x0, x1) translate([x0, RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([x1 - x0, respeaker_T() + 1.0, IN_Z - RSP_TOP + RSP_PRESS]);
if (W == "riblook") {
    front_plate(); oled_hous(); respeaker_at();
    translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495();
    one("knob");
    color("#6ee7b7") { rib_band(6.25, 37.9); rib_band(48.1, 79.75); }     // 空き（リブ幅 6 が入る帯・明るいミント）
    color("#c53030", 0.92) { rib_band(2, 6.25); rib_band(37.9, 48.1); rib_band(79.75, 84); }   // 塞がり
    color("#dd6b20") translate([RIB1_X, RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([RIB1_W, respeaker_T() + 1.0, IN_Z - RSP_TOP + RSP_PRESS + 2]);   // v3 の前リブ（当たっていた位置）
}
// ---- ④⑤ AS5600 の取付回転 × ヘッダの形（4 × 2 ＝ 8 通り）--------------------
//   基板は knob_v5 の位置（KNOB_AT・裏面 Z = Z_TOP − knob_deep()）。探針はコネクタだけ
//   （as5600_headers()。2026-08-28 まで as5600(true) − as5600(false) と書いていた）。相手は箱の全部（つまみの島・柱・天板・線・電源系）
R  = 0;      // 取付回転 0 / 90 / 180 / 270
RA = false;  // ヘッダの形（false = 直立て / true = L 字横出し）
// 🔒 2026-08-28 _v4_core.scad と同じ直し（「基板＋コネクタ − 基板」はプレビューで基板が残る）
module as_conn() translate(KNOB_AT) translate([0, 0, -knob_deep()]) rotate([0, 0, R])
    as5600_headers(RA);
if (W == "asc") intersection() { as_conn(); union() { others("none"); } }
if (W == "ascx") as_conn();   // 探針の単体出し（空検査の検算用）
ASCW = "ina";                 // asc の who 検査: ina / lipo / xh / knob / top / hub
if (W == "ascw") intersection() { as_conn();
    union() { if (ASCW == "ina") ina_v4(); if (ASCW == "lipo") translate(LIPO_AT) lipo_1000mah();
              if (ASCW == "xh") xiao_hous(); if (ASCW == "knob") one("knob");
              if (ASCW == "top") top_plate(); if (ASCW == "hub") one("hous"); } }
// ---- INA226 の置き場の走査（AS5600 のコネクタと v3 の位置が両立しないため）------
//   姿勢は v3 のまま（部品面を下に吊る・L 字は −X へ）で、X だけ動かして当てる。Y・Z は v3 の値。
//   相手 = 自分以外の全部 ＋ AS5600 のコネクタ（直立て・R は AS_R で指定）
INX = 24;   // INA の左端 X。⚠ 仮決め 2026-08-24: AS5600 のコネクタ（直立て）との連立で v3 の 48 が落ち、
            //   走査で空きは 22〜28（0）・その中央。v3 の値は 48（W="ina" は歴史的にその検査）
module ina_at_x() translate([INX - INA_AT[0], 0, 0]) ina_v4();
if (W == "inam") intersection() { ina_at_x(); union() { others("ina"); as_conn(); } }
// ---- スタディ①やり直し用: 本当に固定の物のグループ別エクスポート（bbox を Python で読む）----
EK = "rsp";   // rsp / oled / knobf / spk / btn / tcbf
if (W == "exp") {
    if (EK == "rsp")   { respeaker_at(); xiao_hous(); rsp_j2_space(); }
    if (EK == "oled")  { front_plate(); oled_hous(); }
    if (EK == "knobf") { one("knob"); as_conn(); }
    if (EK == "spk")   translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495();
    if (EK == "btn")   { translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch(); }
    if (EK == "tcbf")  tcb_unit();
}
// ---- スタディ①やり直し: PB（C 姿勢）の Z 窓を「本当に固定の物」だけで測る ----
//   従属変数（ハブ・電池・トグル・INA）は入れない。ハブだけは別枠で当てる（床の平置きは動かせないため）
PBZ = 33.0;   // 走査用の上縁 Z（既定は C_AT と同値。C_AT からの差で動かす）
module fixed_true() {
    skin(); translate([-WALL, 0, IN_Z]) cube([IN_X + 2 * WALL, IN_Y, TOP_T]);   // 素の外皮＋天井
    respeaker_at(); xiao_hous(); rsp_j2_space();
    front_plate(); oled_hous();
    one("knob"); as_conn();
    translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495();
    translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch();
    tcb_unit();   // 🔒 充電口
}
module pb_at_z() translate([0, 0, PBZ - C_AT[2]]) { pb_c(); hous_c(); }
if (W == "pbz")  intersection() { pb_at_z(); fixed_true(); }                    // ↔ 固定の物
if (W == "pbzh") intersection() { pb_at_z(); union() { hub_at(); one("hous"); } }   // ↔ ハブ（床の平置き・v3 の XY）
if (W == "inax") ina_v4();      // 探針の単体出し（空検査の検算用）
if (W == "tcbx") tcb_unit();
if (W == "look")    fold_parts();
if (W == "lookbox") { fold_parts(); color("#8899aa", 0.18) skin();
    color("#8899aa", 0.18) translate([-WALL, 0, IN_Z]) cube([IN_X + 2 * WALL, IN_Y, TOP_T]); }   // 素の天井（L の頭との隙間 0.35 の相手）
echo(C_AT = C_AT, INA_AT = INA_AT, INA_RA = INA_RA);
