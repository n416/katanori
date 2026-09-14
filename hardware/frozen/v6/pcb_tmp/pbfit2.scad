// 電源板を L × W にしたときの当たり（後ろ＝ハッチ側へ伸ばす向き）。
use <../case_v5.scad>
use <../parts/parts.scad>
NEW_L = 36.068; NEW_W = 32.0;
GROW = NEW_W - 22.86;
intersection() {
    at_pb() translate([0, -GROW, 0]) cube([NEW_L, NEW_W, 1.6]);
    union() { others("pb"); p_top(); p_floor(); p_lwall(); p_rwall(); p_front(); p_hatch(); }
}
