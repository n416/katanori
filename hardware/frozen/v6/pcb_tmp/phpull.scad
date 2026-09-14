// スピーカーの PH コネクタ（上出し）のプラグを、真上へ S mm 引き抜くときの当たり。
// PORT="PHIN" か "PHOUT"、S = 引き抜く量 [mm]。0 は挿さったまま。
use <../case_v5.scad>
include <../parts/hub_board_parts.scad>
PORT = "PHIN";
S = 0;
HUB_AT = [6.0, 15.9, 2.5];   // case_v5 の HUB_AT（§2「X 6.0・前縁 Y 15.9」）
h = [for (p = HUB_HEADERS) if (p[0] == PORT) p][0];
intersection() {
    translate(HUB_AT) translate([h[3], h[4], 1.6 + S])
        cube([h[5] - h[3], h[6] - h[4], h[7]]);
    union() {
        others("hub");
        p_top(); p_floor(); p_lwall(); p_rwall(); p_front(); p_hatch();
    }
}
