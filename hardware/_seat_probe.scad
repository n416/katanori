// 座のナットとネジの検算（2026-08-25）。穴ごとに: 横穴にできるか・通路の向きと長さ・天井/床の肉・掛かり・先の余裕
//   実行: openscad --backend=manifold -o _seat_probe.stl hardware/_seat_probe.scad
include <case_v4.scad>
part = "none";
module row(name, hy, t, wy, th = THETA) {
    ok = slot_ok(hy, wy, th); c = seat_nut_ceil(hy, wy, th); tip = t - seat_scr_l(hy, wy);
    echo(str(name, " hy=", hy, " Y=", wy, "  ", ok ? "横穴" : "下向き",
             ok ? str("  抜く向き=", slot_out(wy) > 0 ? "後ろ" : "前", " 長さ=", slot_len(wy),
                      "  天井の肉=", slot_ceil(wy, th), "  床の肉=", seat_d(hy, th) - slot_ceil(wy, th) - NUT_SLOT_H) : "",
             "  ナットの上面=", c, "  掛かり=", min(NUT_T - 0.2, c - tip), "  先→天板の裏=", tip + seat_d(hy, th)));
}
for (h = ina_holes()) row("INA", h[1], ina_size()[2], ina_hole_wy(h[1]), INA_THETA);
for (h = pb_mount())  row("PB ", h[1], pb_pcb_t(),    pb_hole_wy(h[1]), THETA);
