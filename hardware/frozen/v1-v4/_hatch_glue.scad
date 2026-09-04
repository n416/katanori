include <case_v4.scad>
// ハッチと床の板の接着面（合わせ面 Y 71.0 で両方に肉がある所）。
//   openscad --backend=manifold -o glue.stl -D 'part="none"' hardware/_hatch_glue.scad → 体積 ÷ 0.1 = 面積 mm²
//   --preview で PNG にすると接着面だけが濃い色で出る
GLUE_T = 0.1;
module glue_face() intersection() {
    translate([0, -GLUE_T, 0]) intersection() { hatch_v4(false); translate([-100, sw4_yg(), -100]) cube([300, GLUE_T, 300]); }   // ハッチの Y 71 の面（縁の底）
    intersection() { battery_floor4(); translate([-100, sw4_yg() - GLUE_T, -100]) cube([300, GLUE_T, 300]); }                    // 床の板の上面
}
if (part == "none") color("red") glue_face();
// 接着面（赤）をハッチの輪郭（薄灰・奥 20mm に引いた）の上に描く。外（背面）から見た向き
//   openscad --backend=manifold --preview -o x.png --camera=40,71,25,90,0,180,190 --projection=o -D 'part="glue_map"' hardware/_hatch_glue.scad
if (part == "glue_map") { color("red") glue_face(); color("#ececec") translate([0, -20, 0]) hatch_v4(false); }
