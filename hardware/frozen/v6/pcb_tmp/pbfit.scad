// 新しい電源板（36 × 28 × 1.6）を、いまの PowerBoost の枠に置いて当たりを見る。
// 伸ばす向きを DY で選ぶ: 0 = 後ろ（局所 +y）だけ・1 = 前（局所 −y）だけ・2 = 半分ずつ
// 使い方: openscad --backend=manifold -D 'DY=0' -o out.stl hardware/frozen/v6/pcb_tmp/pbfit.scad
use <../case_v5.scad>
use <../parts/parts.scad>
DY = 0;
NEW_W = 28.0;
GROW = NEW_W - 22.86;           // 22.86 = PB_W（parts.scad）
OFF = (DY == 0) ? 0 : (DY == 1) ? -GROW : -GROW / 2;
intersection() {
    at_pb() translate([0, OFF, 0]) cube([36.068, NEW_W, 1.6]);
    union() {
        others("pb");
        p_top(); p_floor(); p_lwall(); p_rwall(); p_front(); p_hatch();
    }
}
