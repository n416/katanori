// 組み立てマニュアル v6.1 / v6.1n の「部品の呼び名」の挿絵。筐体の部品ではない・絵だけの道具
//   openscad --backend=manifold --render=full --autocenter --viewall -D 'MAT="nylon"' -D 'G="boss"' -o x.png hardware/tools/manual_v61/_asm_gloss_v61.scad
//   🔴 case_v6_1.scad は読むだけ
include <../../case_v6_1.scad>
part = "none";
G = "";
HLC = "#e07a5f"; GH = "#c9d0d8";
// 共通
if (G == "riser")  { color("#2b6b3f", 0.35) one("hub"); color(HLC) { riser61(); oriser61(); } }                     // ライザー 2 枚（PCB の J1・J2 に立つ）
if (G == "press")  { color(GH, 0.3) p_top(); color(HLC) { rsp_press(); oled_brackets(); } }                          // 羊羹とマッチ棒・OLED の L（天板の裏）
if (G == "seat")   { color(GH, 0.3) p_floor(); color(HLC) { rsp_seat(); oled_rib(); if (nylon()) { oled_guides(); rsp_stop(); } } }   // 座と OLED のリブ（ナイロンはガイドと止めも）
// ナイロン
if (G == "shell")  color(HLC) shell();                                                                              // 底パーツ
if (G == "lid")    color(HLC) lid();                                                                                // 蓋（天板＋左の板＋足）
if (G == "boss")   { color(GH, 0.3) shell(); color(HLC) { rear_post(); flap_seat(); } }   // ⭐ 2026-09-16 夕: corner_boss / lid_foot を廃止し、床から立つ柱（rear_post）とフラップが持つ座（flap_seat）に入れ替えた                            // 隅の台と蓋の足
if (G == "rail")   { color(GH, 0.3) shell(); color(HLC) flap_rails(); }                                             // レール（左の板の縁を受ける）
if (G == "nposts") { color(GH, 0.3) shell(); color(HLC) { hub_posts(); fasten_lwall(); fasten_rwall(); } }          // 柱（PCB の柱と上の柱）
// レジン
if (G == "rposts") { color(GH, 0.3) { p_lwall(); p_rwall(); } color(HLC) { fasten_lwall(); fasten_rwall(); } }       // 柱（壁の内面の下の柱・上の柱）
if (G == "ears")   { color(GH, 0.3) { p_front(); p_hatch(); } color(HLC) { front_ears(); front_ears_low(); hatch_ears_top(); hatch_feet(); } }   // 耳と足
if (G == "hposts") { color(GH, 0.3) p_floor(); color(HLC) hub_posts(); }                                            // PCB の柱（床）
