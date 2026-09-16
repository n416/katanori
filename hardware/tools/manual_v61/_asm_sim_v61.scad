// ============================================================
// 組み立てシミュレーション v6.1 / v6.1n（2026-09-16）。筐体の部品ではない・マニュアルの挿絵だけの道具
//   材料は case と同じ -D MAT="resin" | "nylon"。ST で「その手順を終えたときに在る物」を出す。
//   番号は docs/manual/assembly_v61.html（レジン）・assembly_v61n.html（ナイロン）と同じ。
//   実行: openscad --backend=manifold --render=full -D 'MAT="nylon"' -D 'ST="n3"' -o x.png hardware/tools/manual_v61/_asm_sim_v61.scad
//   🔴 case_v6_1.scad は読むだけ（include）。ここで形を変えない
// ============================================================
include <../../case_v6_1.scad>
part = "none";   // case の描画スイッチを止める（include の後の代入が勝つ）
ST = "";
HL = "#e07a5f";   // その手順で入れる物の色
C_GHOST = "#9aa5b1";

module hub_all()  one("hub");
module rsp_unit() { one("rsp"); one("riser"); }
module oled_unit() { one("oled"); one("oriser"); }
module top_units() { at_knob() for (g = KNOB61_GROUPS) knob_group(g); knob61_shaft(); one("btn"); one("spk"); one("spktub"); }
// 磁石と AS5600 は knob61() の中で PCB 側に描かれる。天板の小組の絵では knob61_shaft（伸ばした軸）まで出す

// ---- レジン（板 6 枚）----
//  r1 床に電池 / r2 PCB（柱 4 本）/ r3 ReSpeaker をライザーごと / r4 OLED のライザーを J2 へ / r5 左右の壁 / r6 天板の小組（絵は別）
//  r7 天板を載せる / r8 OLED を嵌めたフロントを前から / r9 ハッチを後ろから
module r_upto(n, hl) {
    color(n == 1 ? C_CASE : C_CASE) p_floor();
    if (n >= 1) color(hl == 1 ? HL : "#6b7c8f") one("bat");
    if (n >= 2) color(hl == 2 ? HL : "#2b6b3f") hub_all();
    if (n >= 3) color(hl == 3 ? HL : "#3d5a73") rsp_unit();
    if (n >= 4) color(hl == 4 ? HL : "#2b6b3f") one("oriser");
    if (n >= 5) { color(hl == 5 ? HL : C_CASE) { p_lwall(); panel_ribs("lwall", hl == 5 ? HL : C_CASE); } color(hl == 5 ? HL : C_CASE) { p_rwall(); panel_ribs("rwall", hl == 5 ? HL : C_CASE); } }
    if (n >= 7) { color(hl == 7 ? HL : C_CASE, hl == 7 ? 1 : 0.5) p_top(); color(hl == 7 ? HL : "#8a8f95") top_units(); }
    if (n >= 8) { color(hl == 8 ? HL : C_CASE) { p_front(); panel_ribs("front", hl == 8 ? HL : C_CASE); } color(hl == 8 ? "#222" : "#222") one("oled"); }
    if (n >= 9) { color(hl == 9 ? HL : C_CASE) { p_hatch(); panel_ribs("hatch", hl == 9 ? HL : C_CASE); } color("#555") one("tgl"); }
    if (n >= 6 && n < 7) { }   // 6 は天板の小組（箱の絵は 5 と同じ）
}

// ---- ナイロン（底パーツ＋蓋）----
//  n2 底パーツ（ナットを入れる）/ n3 PCB / n4 トグル / n5 ReSpeaker をライザーごと / n6 OLED をライザーごと / n7 電池を左から / n8 蓋を真上から
module n_upto(n, hl) {
    color(C_CASE) shell();
    if (n >= 3) color(hl == 3 ? HL : "#2b6b3f") hub_all();
    if (n >= 4) color(hl == 4 ? HL : "#555") one("tgl");
    if (n >= 5) color(hl == 5 ? HL : "#3d5a73") rsp_unit();
    if (n >= 6) color(hl == 6 ? HL : "#2b6b3f") oled_unit();
    if (n >= 7) color(hl == 7 ? HL : "#6b7c8f") one("bat");
    if (n >= 8) { color(hl == 8 ? HL : C_CASE, hl == 8 ? 1 : 0.5) lid(); color("#8a8f95") top_units(); }
}

function isd(c) = ord(c) >= 48 && ord(c) <= 57;
function stn(s, p) = (len(s) == 2 && s[0] == p && isd(s[1])) ? ord(s[1]) - 48 : -1;   // "r1"〜"r9"・"n2"〜"n8" だけ（"rtop" などは手順ではない）
if (stn(ST, "r") > 0 && ST != "r6") r_upto(stn(ST, "r"), stn(ST, "r"));
if (stn(ST, "n") > 0) n_upto(stn(ST, "n"), stn(ST, "n"));
// 蓋・天板の小組（裏返して見る絵はカメラで回す）
if (ST == "r6" || ST == "rtop") { color(C_CASE) p_top(); top_units(); color(HL) oled_brackets(); }
if (ST == "ntop") { color(C_CASE) lid(); top_units(); }
// 小組: ReSpeaker にライザーを挿した物・OLED にライザーを挿した物（机の上）
if (ST == "rspsub")  { color("#3d5a73") one("rsp"); color(HL) one("riser"); }
if (ST == "oledsub") { color("#222") one("oled"); color(HL) one("oriser"); }
// レジン: OLED をフロントに嵌めた物
if (ST == "frontsub") { color(C_CASE) { p_front(); panel_ribs("front", C_CASE); } color(HL) one("oled"); }
// ナイロン: 電池を左の窓から入れる途中（左へ 45 出した姿）
if (ST == "nbat_in") { n_upto(6, 0); color(HL) translate([-45, 0, 0.5]) one("bat"); }
// ナイロン: 蓋を降ろす途中（8 上・左の板は 1.5 外へたわんだ姿）
if (ST == "nlid_in") { n_upto(7, 0); translate([0, 0, 8]) { color(HL, 0.9) lid_flexed(); color("#8a8f95") top_units(); } }
// 線（最終の形）
if (ST == "wires") { innards(); color("#e0b060") wires(); }
