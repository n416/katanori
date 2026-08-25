include <_v4_core.scad>
// 結束バンド式の帯（ロの字断面・厚み2・幅 W6）。y0 = 帯の手前端
module strap(y0, w = 6, t = 2) {
    difference() {
        translate([BAT_X0 - 0.5 - t, y0, BAT_Z - BRG_T - t]) cube([lipo_size()[1] + 1 + 2 * t, w, BRG_T + lipo_size()[2] + 2 * t + 1]);
        translate([BAT_X0 - 0.5, y0 - 1, BAT_Z - BRG_T]) cube([lipo_size()[1] + 1, w + 2, BRG_T + lipo_size()[2]]);
    }
}
if (P == 20) intersection() { strap(SY); union() { core(); tgl_v4(); tcb_v4(); brg_v4(); bat_v4(); } }
