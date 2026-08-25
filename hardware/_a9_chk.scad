// A-9 の再測（2026-08-26）: OLED（フィルム込み）↔ ReSpeaker / 床
//   結果: rsp 0 / floor 0。OLED を後ろへ押すと floor に +0.3、rsp に +0.6 で当たる（逃げ 0.2 / 約 0.5）
//   実行: openscad --backend=manifold -o x.stl -D 'part="none"' -D 'Q="rsp"' hardware/_a9_chk.scad
//        Q= rsp / rsp_film / floor / floor_film / oled / film / rspb / push（D= で +Y へ押す）
//   🔴 part="none" を必ず付ける（case_v4.scad の既定の部品が一緒に出てしまう）
include <case_v4.scad>
Q = "";
module oled_all() { oled_at(); }
module film_only() { translate([OLED_X0, OLED_Y1, OLED_Z0]) rotate([90, 0, 0]) oled_film(); }
if (Q == "rsp")      intersection() { oled_all();  respeaker_at(); }
if (Q == "rsp_film") intersection() { film_only(); respeaker_at(); }
if (Q == "floor")    intersection() { oled_all();  floor_v4(); }
if (Q == "floor_film") intersection() { film_only(); floor_v4(); }
if (Q == "oled")  oled_all();
if (Q == "film")  film_only();
if (Q == "rspb")  respeaker_at();
// 隙間の実測: OLED を +Y へ d だけ動かして初めて当たる d を探す
D = 0;
if (Q == "push")  intersection() { translate([0, D, 0]) oled_all(); union() { respeaker_at(); floor_v4(); } }
if (Q == "push_rsp")   intersection() { translate([0, D, 0]) oled_all(); respeaker_at(); }
if (Q == "push_floor") intersection() { translate([0, D, 0]) oled_all(); floor_v4(); }
