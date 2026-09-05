// ============================================================
// 組み立ての動きの検査 v5（2026-09-05）。筐体の部品ではない・マニュアル（docs/manual/assembly_v5.html）の手順が
// 「その動きで本当に入るか」を、動く物を道に沿って T だけずらした姿と、その手順の時点で箱に在る物との重なり（体積）で見る。
//   実行: openscad --backend=manifold -D 'SW="st6"' -D 'T=5' -o x.stl hardware/_asm_chk_v5.scad → tools/stl_vol.py で体積（0 が正）
//   SW と道（T の意味）:
//     st2   ReSpeaker を上から座へ        T = 上へ [mm]       相手: 床・ハブ基板
//     st4l  左の壁を左から               T = 左へ [mm]       相手: 床・ハブ（口込み）・ReSpeaker（XIAO の口込み）
//     st4r  右の壁を右から               T = 右へ [mm]       同上
//     st5   Type-C 基板を後ろから         T = 後ろへ [mm]     相手: 〜手順 4
//     st6   ブリッジ（前板込み）を上から   T = 上へ [mm]       相手: 〜手順 5
//     st7a  帯 3 本を右 2 の位置で上から   T = 上へ [mm]       相手: 〜手順 6
//     st7b  帯 3 本を右から左へ 2         T = 右へ [mm]（0〜2） 同上
//     st8   電池を後ろから               T = 後ろへ [mm]     相手: 〜手順 7
//     st9   電流計を上から               T = 上へ [mm]       相手: 〜手順 8
//     st11  OLED を上から                T = 上へ [mm]       相手: 〜手順 9（天板の小組は箱に無い）
//     st12t 天板の小組を上から           T = 上へ [mm]       相手: 〜手順 9 ＋ OLED
//     st12f フロントを前から             T = 前へ [mm]       相手: 〜手順 9 ＋ OLED ＋ 天板の小組
//     st13r ハッチ一式を爪の先を軸に倒す  T = 傾き [deg]（上が後ろへ）相手: 全部
//     st13y ハッチ一式を真後ろへ         T = 後ろへ [mm]     相手: 全部（垂直のまま後ろから前へ押す動き）
//   WIRES=true で線（最終の形）も相手に足す
// ============================================================
include <case_v5.scad>
part = "none";
SW = ""; T = 0; WIRES = false; LOOK = "";

module c_floor()  p_floor();
module c_hub()    { at_hub() hub_board(ra = false); hub_plugs(); }
module c_rsp()    one("rsp");
module c_lwall()  { p_lwall(); panel_ribs("lwall"); }
module c_rwall()  { p_rwall(); panel_ribs("rwall"); }
module c_tc()     one("tc");
module c_brg()    { brg_front(); bridge(); panel_ribs("bridge"); }
module c_straps() straps();
module c_bat()    one("bat");
module c_ina()    one("ina");
module c_oled()   one("oled");
module c_topgrp() { p_top(); one("pb"); one("knob"); one("btn"); one("spk"); }
module c_front()  { p_front(); panel_ribs("front"); }
module c_hatch()  { p_hatch(); panel_ribs("hatch"); one("tgl"); one("hatchplate"); one("shutter"); one("lock"); }

// その手順の時点で箱に在る物（動く物は含めない）
module have(n) {
    if (n >= 1)  c_floor();
    if (n >= 1)  { at_hub() hub_board(ra = false); }
    if (n >= 3)  hub_plugs();
    if (n >= 2)  c_rsp();
    if (n >= 4 && n != 5.5 && n != 5.7)  { c_lwall(); c_rwall(); }   // 5.5 = 壁の前にブリッジ・5.7 = 壁の前に Type-C とブリッジ（新しい順）
    if ((n >= 5 && n != 5.5) || n == 3.5)  c_tc();
    if (n >= 5.5) c_brg();
    if (n >= 7)  c_straps();
    if (n >= 8)  c_bat();
    if (n >= 9)  c_ina();
    if (n >= 11) c_oled();
    if (n >= 12) c_topgrp();
    if (n >= 12.5) c_front();
    if (WIRES) wires();
}

// ハッチの回転の軸: 唇の先（X 方向の線・Y = バーの前面 + 隙間・Z = 唇の上面）
HP = [CLAW_BAR_Y0 + CLAW_CL, 0.3 + CLAW_CL + CLAW_LIP_T];
module tilt(a) translate([0, HP[0], HP[1]]) rotate([-a, 0, 0]) translate([0, -HP[0], -HP[1]]) children();   // 上が後ろ（+Y）へ倒れる

module mover() {
    if (SW == "st2")   translate([0, 0, T]) c_rsp();
    if (SW == "st4l")  translate([-T, 0, 0]) c_lwall();
    if (SW == "st4r")  translate([T, 0, 0]) c_rwall();
    if (SW == "st5")   translate([0, T, 0]) c_tc();
    if (SW == "st6")   translate([0, 0, T]) c_brg();
    if (SW == "st7a")  translate([2, 0, T]) c_straps();
    if (SW == "st7b")  translate([T, 0, 0]) c_straps();
    if (SW == "st8")   translate([0, T, 0]) c_bat();
    if (SW == "st9")   translate([0, 0, T]) c_ina();
    if (SW == "st11")  translate([0, 0, T]) c_oled();
    if (SW == "st12t") translate([0, 0, T]) c_topgrp();
    if (SW == "st12f") translate([0, -T, 0]) c_front();
    if (SW == "st13r") tilt(T) c_hatch();
    if (SW == "st13y") translate([0, T, 0]) c_hatch();
    if (SW == "st5t")  translate([0, 0, T]) c_tc();          // Type-C 基板を壁より先に上から（相手: 床・ハブ・ReSpeaker）
    if (SW == "st4lt") translate([-T, 0, 0]) c_lwall();      // その後で左の壁を横から（相手: 〜手順 3 ＋ Type-C）
    if (SW == "st4lc") translate([-T, 0, 0]) c_lwall();      // 新しい順: Type-C とブリッジを置いてから左の壁を横から
    if (SW == "st4rc") translate([T, 0, 0]) c_rwall();
    if (SW == "st4lb") translate([-T, 0, 0]) c_lwall();   // 壁を横から（ブリッジと前板が先に置いてある順）
    if (SW == "st4rb") translate([T, 0, 0]) c_rwall();
    if (SW == "probeL") translate([7.0, 8.2, 43.0]) cube([6.0, IN_Y - 8.2, 6.5]);     // OLED の左の L の後ろの六角へ、ハッチの口から真っ直ぐ届く道（X 7〜13・Z 43〜49.5）に何が居るか
    if (SW == "probeR") translate([73.1, 8.2, 43.0]) cube([6.0, IN_Y - 8.2, 6.5]);
    if (SW == "st13r2") tilt2(T) translate([0, HB, 0]) c_hatch();                                          // 2 後ろに置いたまま倒す（唇はまだバーの後ろ）
    if (SW == "st13u")  translate([0, T * sin(HA), T * cos(HA)]) tilt2(HA) translate([0, HB, 0]) c_hatch();   // HA 度傾けたまま自分の面に沿って上へ（爪をポケットへ下ろす道の逆）
}
HB = 2.0; HA = 12;   // ハッチを後ろに置く量・爪を下ろすときの傾き
module tilt2(a) translate([0, HP[0] + HB, HP[1]]) rotate([-a, 0, 0]) translate([0, -HP[0] - HB, -HP[1]]) children();
function stage(s) = s == "st2" ? 1 : s == "st5t" ? 3 : s == "st4lc" ? 5.7 : s == "st4rc" ? 5.7 : s == "st4lt" ? 3.5 : s == "st4lb" ? 5.5 : s == "st4rb" ? 5.5 : s == "probeL" ? 12 : s == "probeR" ? 12 : s == "st4l" ? 3 : s == "st4r" ? 3 : s == "st5" ? 4 : s == "st6" ? 5 : s == "st7a" ? 6 : s == "st7b" ? 6
                  : s == "st8" ? 7 : s == "st9" ? 8 : s == "st11" ? 9 : s == "st12t" ? 11 : s == "st12f" ? 12 : 12.5;

if (SW != "" && SW != "look" && LOOK == "") intersection() { mover(); have(stage(SW)); }
if (SW == "look") { mover(); color("#888", 0.4) have(stage(SW)); }
if (LOOK != "") { color("red") intersection() { _mv(LOOK); have(stage(LOOK)); } color("#e0a040", 0.6) _mv(LOOK); color("#9aa", 0.35) _bg(LOOK); }   // 絵: 動く物＝橙・相手＝灰・重なり＝赤
// 断面の絵: SEC="st5"/"st6"・SX = 切る X。2D の横 = 世界 Y・縦 = 世界 Z（--preview で色が付く）
SEC = ""; SX = 4.4;
module _cut(x) projection(cut = true) rotate([0, 0, -90]) rotate([0, -90, 0]) translate([-x, 0, 0]) children();   // 世界 (x,y,z) → (y, z, x−SX): X=SX の面で切って 2D (Y, Z) を出す
if (SEC != "") { color("#9aa") _cut(SX) _bg(SEC); color("#e0a040") _cut(SX) _mv(SEC); color("red") _cut(SX) intersection() { _mv(SEC); have(stage(SEC)); } }
module _bg(k) { if (k == "st5") { p_floor(); p_lwall(); } if (k == "st6") c_lwall(); }
module _mv(k) { if (k == "st5") translate([0, T, 0]) c_tc(); if (k == "st6") translate([0, 0, T]) c_brg(); }
