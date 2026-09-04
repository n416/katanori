include <case_v3.scad>
// ============================================================
// 🔍 v4 の置き場スタディ①: PowerBoost（2026-08-24）
//   v3 打ち切りの反省（PowerBoost を本物にしたら置く場所が無かった）を受け、
//   v4 は「一番面倒なピース＋挿す手」を最初に置く。ここはその測定ファイル。
//   障害物は**固定と決まっている物だけ**:
//     外皮（素の板）・ハブ（＋挿した線 10 本）・ReSpeaker・OLED・天板の部品群（つまみ込み）・フロント・トグル（ハッチ）
//   v3 の機構（ブリッジ・トンネル・壁の棚・柱・フック）は障害物に**入れない**（v4 で作り直す物）。
//   ⚠ ただし top_plate_raw には v3 の PB フック等が残っている。当たりが出たら場所で仕分ける。
//   実行: openscad --backend=manifold -o x.stl -D "part=\"none\"" -D "CAND=\"E\"" -D "W=\"chk\"" hardware/_v4_pb.scad
// ============================================================
CAND = "E";    // "E" 平置き・右・低い ／ "A" 平置き・左・電池の下 ／ "C" 背面に立てる
W    = "chk";  // chk / seat / hup / husb / p4 / top / bat / look / who
WHO  = "hub";

// ---- ReSpeaker の挿さる物（2026-08-24 ユーザー「ピンヘッダも精緻化」）------
// J2（スピーカーソケット）は 🔒 PH2.0 のトップ型（真上＝XIAO 面の法線へ挿す・RESPEAKER-LITE.md）。
// プラグ＋線の空間は respeaker_mating_space と同じ「面から 15」。世界座標では Y 10.035〜25.04・X 5.1〜12.1・Z 15.5〜23.5。
// XIAO の 7 本の挿し口（✅ 2026-08-24 ユーザー「ReSpeaker の上に XIAO の基板が載り、その上にピンヘッダが挿さっている」）:
//    模型は respeaker_lite.scad がピン単位で持つ（直付け XIAO → 貫通ヘッダ → 使う 7 本の DuPont）。
//    線の頭は面から 13.9 ＝ 世界の Y 23.9・曲がり込みで 27.5（✅ 2026-08-24 構成確定・CASE-V4.md 台帳）。
//    🔴 ここに一時「19.24 ＝ Y 29.3」と書いていたのは誤り②（ソケット浮きの作り話）の値の消し忘れ。
//    スタディ②の置き物は帯（X 64〜83・Y 14〜28・Z 10〜29）を空けておく。抜き挿しは xpull。
module at_rsp() translate([RSP_X + respeaker_L(), RSP_BD_Y1, RSP_Z]) rotate([0, 0, 180]) children();
module rsp_j2_space() at_rsp() { j = respeaker_spk_j2(); translate([j[0], -15, j[2]]) cube([j[1] - j[0], 15, j[3] - j[2]]); }
module xiao_hous() at_rsp() respeaker_xiao_housings(hous_h = HOUS_H);   // XIAO の線 7 個（挿した状態・曲がり込み付き）
module at_oled() translate([OLED_X0, OLED_Y1, OLED_Z0]) rotate([90, 0, 0]) children();   // oled_at() と同じ変換
module oled_hdr()  at_oled() oled_i2c_header();      // OLED の I2C ヘッダ（✅ 2026-08-24 写真・上辺の裏の直 4 ピン）
module oled_hous() at_oled() oled_i2c_housing();     // OLED の線（4 連 DuPont・挿した状態）

// ---- 固定の障害物 ----------------------------------------------------
module fix4() {
    translate([-WALL, 0, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y, FLOOR_T]);            // 床（素の板）
    translate([-WALL, 0, 0])        cube([WALL, IN_Y, IN_Z + TOP_T]);                  // 左の壁（素）
    translate([IN_X, 0, 0])         cube([WALL, IN_Y, IN_Z + TOP_T]);                  // 右の壁（素）
    translate([-WALL, IN_Y, -FLOOR_T]) cube([IN_X + 2 * WALL, HATCH_T, IN_Z + TOP_T + FLOOR_T]);   // ハッチ（素）
    toggle_on_hatch();
    hub_at(); one("hous");
    respeaker_at(); xiao_hous(); oled_hous();
    top_plate(); one("knob");
    front_plate();                                                                     // OLED 込み
    rsp_j2_space();
}

// ---- 平置きポーズ（部品面が上）---------------------------------------
// ⚠ 前提: 8 ピン列は**真っ直ぐなヘッダ**（垂直ピン 3 本・GND/EN/USB）。
//    L 型のままだと、内向きはハウジングがインダクタ L1 の上 0.3 を横に滑ることになり挿す軌跡が無い。
//    外向きは前縁から横へ 16 出て ReSpeaker に刺さる。⬜ L 型を半田付け済みなら平置き案は付け替えが要る。
A_AT = [4, 25, 28.5];    // 左・高い（電池はこの下・スピーカーの裏の下に収める）
E_AT = [44, 22, 19.5];   // 右・低い（ハブの線の頭 17.7 の上・つまみのデッキ 41.95 の下）
function flat_at() = (CAND == "A") ? A_AT : E_AT;

module pb_flat() translate(flat_at()) {
    powerboost_1000c(hdr = "none");   // 8 ピン列は下で真っ直ぐ 3 本を置く（4 ピンヘッダと SMD は模型に入っている）
    pb_jst_plug();
    for (i = [3, 4, 7]) { x = 12.83 + i * 2.54;
        color("#222")    translate([x - 1.27, 0, 1.6]) cube([2.54, 2.54, 2.5]);
        color("#c8ccd0") translate([x - 0.32, 1.27 - 0.32, -1.2]) cube([0.64, 0.64, 1.2 + 1.6 + 2.5 + 6]);
    }
}
module hous_flat() translate(flat_at()) {
    // 🔴 2026-08-24: 線の曲がり込み（HOUS_R）を頭に載せる。housing(id) には載せて自分の部品には載せていなかった
    for (i = [3, 4, 7]) { x = 12.83 + i * 2.54;
        translate([x - 1.27, 0, 1.6 + 2.5]) cube([2.54, 2.54, HOUS_H]);
        translate([x, 1.27, 1.6 + 2.5 + HOUS_H]) cylinder(d = HOUS_R, h = HOUS_R, $fn = 24); }
    translate([pb_hdr_x() - 1.27, pb_hdr_y0(), 1.6 + 2.5]) cube([2.54, 4 * 2.54, HOUS_H]);   // PWR（4 ピン）
    translate([pb_hdr_x(), pb_hdr_y0() + 2 * 2.54, 1.6 + 2.5 + HOUS_H]) cylinder(d = HOUS_R, h = HOUS_R, $fn = 24);
}

// ---- 背面に立てるポーズ（C）------------------------------------------
// 部品面はハブ側（−Y）・8 ピン列の縁が上・JST の縁が下（プラグは下向き＝⑥で先に挿す）。
// ヘッダは v3 の 🔒 のまま: GND/EN は L 型を外向き（＝上向き）・USB は真っ直ぐ 1 ピン（＝ハブ側へ水平）。
// 変換: 世界 = [CX − x, CY − z, CZ − y]（局所 x→−X, 部品面 z→−Y, 8 ピン列 y→上）
C_AT = [84.3, IN_Y - 0.5 - 1.2, 34.5];   // [右端 X, 板の裏の Y, 上縁の Z]。裏にヘッダの足 1.2 が出るのでハッチから 0.5 ＋ 1.2。
                                         // Z 36 だと 4 ピンハウジングの頭（上縁 − 6.6）が v3 の電池の抜き道の膜（Z 29.0）に 2mm³ 入る → 35.0。
                                         // 🔴 X 51.5 だと USB の水平ハウジングの先（右端 − 31.9）が電池の尻（X 〜52・Z 32.5〜35）に 13mm³ 入る
                                         //    → 右端 84.3（micro-USB の張り出し 0.5 で壁まで 1.2）。水平 2 本の先は X 52.4 より右になる
module pose_c() translate(C_AT) rotate([0, 0, 180]) rotate([-90, 0, 0]) children();
module pb_c() pose_c() { powerboost_1000c(hdr = "front", ra_dir = -1); pb_jst_plug(); }
module hous_c() pose_c() {
    // L の先（上向き）に挿すハウジング。[3, 4] は parts.scad の PB_RA_PINS（use<> は変数を出さないのでリテラル）
    // 🔴 2026-08-24: 頭に線の曲がり込み（HOUS_R・局所 −y ＝ 世界の上）を載せる
    for (i = [3, 4]) { x = 12.83 + i * 2.54;
        translate([x - 1.27, -HOUS_H, 1.6 + 2.5 - 1.27]) cube([2.54, HOUS_H, 2.54]);
        translate([x - HOUS_R / 2, -HOUS_H - HOUS_R, 1.6 + 2.5 - HOUS_R / 2]) cube([HOUS_R, HOUS_R, HOUS_R]); }
    translate([12.83 + 7 * 2.54 - 1.27, 0, 1.6 + 2.5]) cube([2.54, 2.54, HOUS_H]);                            // USB（ハブ側へ水平）
    translate([pb_hdr_x() - 1.27, pb_hdr_y0(), 1.6 + 2.5]) cube([2.54, 4 * 2.54, HOUS_H]);                             // PWR（ハブ側へ水平）
}
module hous_c_horiz() pose_c() {   // 水平に抜き挿しする 2 つだけ（USB・PWR）
    translate([12.83 + 7 * 2.54 - 1.27, 0, 1.6 + 2.5]) cube([2.54, 2.54, HOUS_H]);
    translate([pb_hdr_x() - 1.27, pb_hdr_y0(), 1.6 + 2.5]) cube([2.54, 4 * 2.54, HOUS_H]);
}

module unit()  { if (CAND == "C") pb_c(); else pb_flat(); }
module hous()  { if (CAND == "C") hous_c(); else hous_flat(); }
module both()  { unit(); hous(); }

// ---- 電池（左から抜く 🔒）との取り合い --------------------------------
// E: 電池は v3 の位置のまま（Z 29.3・PB の上の空間）
// A: 電池は PB の下（Z 18.4・ハブの線の頭 17.7 の上）
BAT_E = [LIPO_AT[0], LIPO_AT[1], LIPO_AT[2]];
BAT_A = [2, 25.4, 18.4];   // 🔴 v3 の Y 22.9 だと前面が J2 のプラグ＋線の空間（Y 〜25.04）に入る。抜き道ごと後ろへ 2.5
module bat4() { p = (CAND == "A") ? BAT_A : BAT_E; translate(p) { lipo_1000mah(); lipo_swap_path(); } }

module sweep_up(n) for (t = [0 : STEP : n]) translate([0, 0, t]) children();

// PB を置く時点で既に在る物（天面・つまみ・フロント・OLED・ハッチ・トグルは後から載るので入れない）
module fix_mid() {
    translate([-WALL, 0, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y, FLOOR_T]);
    translate([-WALL, 0, 0])        cube([WALL, IN_Y, IN_Z + TOP_T]);
    translate([IN_X, 0, 0])         cube([WALL, IN_Y, IN_Z + TOP_T]);
    hub_at(); one("hous");
    respeaker_at(); xiao_hous();
    rsp_j2_space();
}

// ---- 検査 -------------------------------------------------------------
if (W == "chk")  intersection() { both(); fix4(); }                                    // 座った状態 ↔ 完成形の全部
if (W == "seat") intersection() { both(); sweep_z(SWEEP) fix_mid(); }                  // 線を全部挿した単位を上から降ろす
if (W == "hup")  intersection() { sweep_up(30) hous(); fix_mid(); }                    // ハウジングを後から上へ抜く/挿す（天面はまだ無い）
if (W == "husb") intersection() { sweep_ny(11) hous_c_horiz(); fix4(); }               // C: 水平の 2 つを −Y へ抜く（完成後でも）。11 ＝ ハウジング 10 ＋ 1。
                                                                                        //    30 まで真っ直ぐ引くと USB の 1 本がつまみの島の角（X 54.2〜55・Y 〜45.3・Z 32.5〜35）に 36mm³。抜けた後は線が曲がる
if (W == "top")  intersection() { union() { top_plate(); one("knob"); } sweep_z(SWEEP) both(); }   // ⑫ 天面を降ろす
if (W == "bat")  intersection() {                                                     // 電池（座＋左の壁の外 5 まで抜く道）↔ PB
    union() { p = (CAND == "A") ? BAT_A : BAT_E;
              translate(p) lipo_1000mah();
              translate(p - [LIPO_L + WALL + 5, 0, 0]) lipo_swap_path(travel = LIPO_L + WALL + 5, clear = 0.3); }
    both(); }
if (W == "who")  intersection() { both(); one(WHO); }
if (W == "seatw") intersection() { both(); sweep_z(SWEEP) one(WHO); }                  // 降ろし掃引の相手を 1 つに絞る
if (W == "look") { show_only(["floor", "hub", "rsp", "oled", "hous"]); xiao_hous(); oled_hous(); if (CAND == "C") toggle_on_hatch(); color("#f6ad55") unit(); color("#63b3ed", 0.85) hous();
    p = (CAND == "A") ? BAT_A : BAT_E; color("#9ae6b4", 0.55) translate(p) lipo_1000mah(); }
echo(CAND = CAND, FLAT = flat_at(), C_AT = C_AT);
if (W == "fixm") fix_mid();
if (W == "wallsw") intersection() { both(); sweep_z(SWEEP) { translate([-WALL, 0, 0]) cube([WALL, IN_Y, IN_Z + TOP_T]); translate([IN_X, 0, 0]) cube([WALL, IN_Y, IN_Z + TOP_T]); } }
if (W == "batf") intersection() {                                                     // 電池（座＋抜き道）↔ 固定の障害物
    union() { p = (CAND == "A") ? BAT_A : BAT_E;
              translate(p) lipo_1000mah();
              translate(p - [LIPO_L + WALL + 5, 0, 0]) lipo_swap_path(travel = LIPO_L + WALL + 5, clear = 0.3); }
    fix4(); }
if (W == "hx") hous();
// ---- XIAO の 7 本の挿す軌跡 ------
// 抜き挿しの道: 線の DuPont（ピンの余り 6 に挿さっている）を +Y へ 12（抜け切り＋余裕）掃く
module fix4_norsp() {   // fix4 から ReSpeaker（掃く物自身）を除いた物
    translate([-WALL, 0, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y, FLOOR_T]);
    translate([-WALL, 0, 0])        cube([WALL, IN_Y, IN_Z + TOP_T]);
    translate([IN_X, 0, 0])         cube([WALL, IN_Y, IN_Z + TOP_T]);
    translate([-WALL, IN_Y, -FLOOR_T]) cube([IN_X + 2 * WALL, HATCH_T, IN_Z + TOP_T + FLOOR_T]);
    toggle_on_hatch();
    hub_at(); one("hous");
    top_plate(); one("knob");
    front_plate();
    rsp_j2_space();
}
if (W == "xpull")   intersection() { sweep_y(12) xiao_hous(); union() { both(); fix4_norsp(); } }
if (W == "xpull40") intersection() { sweep_y(40) xiao_hous(); union() { both(); fix4_norsp(); } }

if (W == "xh") intersection() { xiao_hous(); fix4_norsp(); }   // XIAO の線 ↔ 他の固定物（固定どうしの検算）
module fix4_nooled() {   // OLED 以外の固定物（oh/opull 用。front_plate は OLED＋ヘッダ込みになったので入れない）
    translate([-WALL, 0, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y, FLOOR_T]);
    translate([-WALL, 0, 0])        cube([WALL, IN_Y, IN_Z + TOP_T]);
    translate([IN_X, 0, 0])         cube([WALL, IN_Y, IN_Z + TOP_T]);
    translate([-WALL, IN_Y, -FLOOR_T]) cube([IN_X + 2 * WALL, HATCH_T, IN_Z + TOP_T + FLOOR_T]);
    toggle_on_hatch();
    hub_at(); one("hous");
    respeaker_at(); xiao_hous();
    top_plate(); one("knob");
    rsp_j2_space();
}
if (W == "oh") intersection() { union() { oled_hdr(); oled_hous(); } fix4_nooled(); }   // OLED のヘッダ＋線 ↔ OLED 以外の固定物
if (W == "opull") intersection() { sweep_y(12) oled_hous(); fix4_nooled(); }            // OLED の線を +Y へ抜く
if (W == "xhx") xiao_hous();
