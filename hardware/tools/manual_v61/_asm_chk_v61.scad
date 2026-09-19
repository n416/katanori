// ============================================================
// 組み立ての動きの検査 v6.1 / v6.1n（2026-09-16）。筐体の部品ではない・マニュアルの手順が
// 「その動きで本当に入るか」を、動く物を道に沿って T だけずらした姿と、その手順の時点で箱に在る物との重なり（体積）で見る。
//   実行: python hardware/tools/manual_v61/_asm_chk_v61.py [SW ...]
//   材料は -D MAT="resin" | "nylon"（SW の頭の r / n と合わせる。py が渡す）
//   🔴 case_v6_1.scad は読むだけ。case の path_*（stl_v61n.py --check）はナイロンの道。ここはマニュアルに書く動きを 1 つずつ当てる
// ============================================================
include <../../case_v6_1.scad>
part = "none";
SW = ""; T = 0;

module rsp_unit()  { one("rsp"); one("riser"); }
module oled_unit() { one("oled"); one("oriser"); }
module top_units() { at_knob() for (g = KNOB61_GROUPS) knob_group(g); knob61_shaft(); one("btn"); one("spk"); one("spktub"); }

// ---- レジン: その手順の時点で箱に在る物 ----
//  1 床＋電池 / 2 PCB / 3 ReSpeaker＋ライザー / 4 OLED のライザー / 5 左の壁 / 5.5 右の壁 / 7 天板の小組 / 8 フロント＋OLED
module r_have(n) {
    p_floor(); one("bat");
    if (n >= 2) one("hub");
    if (n >= 3) rsp_unit();
    if (n >= 4) one("oriser");
    if (n >= 5) { p_lwall(); panel_ribs("lwall"); }
    if (n >= 5.5) { p_rwall(); panel_ribs("rwall"); }
    if (n >= 7) { p_top(); top_units(); }
    if (n >= 8) { p_front(); panel_ribs("front"); one("oled"); }
}
// ---- ナイロン ----
//  2 底パーツ / 3 PCB / 4 ReSpeaker＋ライザー / 5 OLED＋ライザー / 6 電池（⭐ 2026-09-19 トグルを外して繰り上げた）
module n_have(n) {
    shell();
    if (n >= 3) one("hub");
    if (n >= 4) rsp_unit();
    if (n >= 5) oled_unit();
    if (n >= 6) one("bat");
}
PCB_DY = 5.5;   // ナイロンの PCB を前へ寄せて降ろす量（2026-09-17 より前の動き。今の道は case の PATH_HUB・tools/sweep_chk.py）
module mover() {
    // レジン
    if (SW == "r_hub")    translate([0, 0, T]) one("hub");                                  // 真上から柱へ          T = 上へ
    if (SW == "r_rsp")    translate([0, 0, T]) rsp_unit();                                  // ReSpeaker をライザーごと真上から
    if (SW == "r_oriser") translate([0, 0, T]) one("oriser");                               // OLED のライザーだけ真上から J2 へ
    if (SW == "r_lwall")  translate([-T, 0, 0]) { p_lwall(); panel_ribs("lwall"); }         // 左の壁を左から        T = 左へ
    if (SW == "r_rwall")  translate([T, 0, 0]) { p_rwall(); panel_ribs("rwall"); }          // 右の壁を右から
    if (SW == "r_top")    translate([0, 0, T]) { p_top(); top_units(); }                    // 天板の小組を真上から
    if (SW == "r_front")  translate([0, -T, 0]) { p_front(); panel_ribs("front"); one("oled"); }   // OLED を嵌めたフロントを前から  T = 前へ
    if (SW == "r_hatch")  translate([0, T, 0]) { p_hatch(); panel_ribs("hatch"); }    // ハッチを後ろから   T = 後ろへ
    if (SW == "r_top_after_front") translate([0, 0, T]) { p_top(); top_units(); }           // （比べる用）フロントの後に天板
    // ナイロン
    if (SW == "n_hub_case") { translate([-PCB_SLIDE, 0, T]) one("hub"); }                   // case の path_hub と同じ（0.8 左で真上から）
    if (SW == "n_hub_dn")   translate([-PCB_SLIDE, -PCB_DY, T]) one("hub");                 // 0.8 左・5.5 前で真上から柱の頭まで   T = 上へ
    if (SW == "n_hub_back") translate([-PCB_SLIDE, -T, 0]) one("hub");                      // 柱の頭の上で後ろへ 5.5 戻す          T = 前へ（5.5 → 0）
    if (SW == "n_hub_right") translate([-T, 0, 0]) one("hub");                              // 右へ 0.8 押して口を穴へ              T = 左へ（0.8 → 0）
    if (SW == "n_rsp")      translate([0, 0, T]) rsp_unit();
    if (SW == "n_oled")     translate([0, 0, T]) oled_unit();
    if (SW == "n_bat")      translate([-T, 0, 0.5]) one("bat");                             // 左の窓から（0.5 浮かせて）          T = 左へ
    if (SW == "n_lid")      translate([0, 0, T]) { lid_flexed(); top_units(); }             // 蓋を真上から（左の板は 1.5 外へたわんだ姿）
    if (SW == "n_lid_seat") translate([0, 0, T]) { lid(); top_units(); }                    // 最後の 0.3（板が戻った姿）
}
function stage(s) = s == "r_hub" ? 1 : s == "r_rsp" ? 2 : s == "r_oriser" ? 3 : s == "r_lwall" ? 4 : s == "r_rwall" ? 5
                  : s == "r_top" ? 5.5 : s == "r_front" ? 7 : s == "r_hatch" ? 8 : s == "r_top_after_front" ? 5.5
                  : s == "n_hub_case" ? 2 : s == "n_hub_dn" ? 2 : s == "n_hub_back" ? 2 : s == "n_hub_right" ? 2
                  : s == "n_rsp" ? 3 : s == "n_oled" ? 4 : s == "n_bat" ? 5 : 6;
module have() { if (SW[0] == "r") r_have(stage(SW)); else n_have(stage(SW)); }
module have_extra() { if (SW == "r_top_after_front") { p_front(); panel_ribs("front"); one("oled"); } }

if (SW != "") intersection() { mover(); union() { have(); have_extra(); } }
