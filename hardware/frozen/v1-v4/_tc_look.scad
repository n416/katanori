// 充電（Type-C）基板の受けを見るための絵（2026-08-25）。形の定義は case_v4.scad / _v4_core.scad の側にある
//   実行: openscad --backend=manifold --render=full -o _tc_iso.png -D 'part="none"' -D 'Q="iso"'
//           --camera=4,63,9,64,0,205,88 --imgsize=1100,820 --projection=o _tc_look.scad   （Q="seat" で受けだけ）
include <case_v4.scad>
module band() intersection() { brg_v4(); translate([-1, 50, 20]) cube([12, 14, 4]); }   // 帯の裏の押さえだけ見せる
module cutbox() translate([-2, 44, -3]) cube([14, 32, 28]);
if (Q == "seat")  intersection() { floor_v4(); cutbox(); }                                                // 受けだけ（基板も壁も無し）
if (Q == "iso")   intersection() { union() { floor_v4(); tcb_v4(); band(); } cutbox(); }                    // 基板を座らせた姿（壁は外して中を見せる）
