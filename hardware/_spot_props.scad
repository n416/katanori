// 🔴 自動生成。手で直さない。作り直しは `python hardware/_spot_props.py`
//    検算が出した 1 か所にだけ足す支柱。支柱の形（one_prop_free / _strut / _branch）は
//    _v4_post_props.scad が持っているので、使う側でそちらも include すること。
// bridge: 接触点の候補 9 / 置けた 4
module spot_props_bridge() { one_prop_strut(0.987, 44.100, 1.876, 1.340, 44.454, 2.376, 1.989, 45.299, 3.432, 134.75, 0.7934, -0.6087, 0.0000, 1.500); one_prop_strut(0.255, 49.843, 1.959, 0.755, 49.843, 2.459, 1.816, 49.843, 3.519, 135.00, -0.0000, -1.0000, 0.0000, 1.500); one_prop_strut(6.917, 43.762, 1.909, 6.726, 44.224, 2.409, 6.318, 45.208, 3.465, 134.75, 0.9239, 0.3827, -0.0000, 1.500); one_prop_strut(7.717, 49.186, 1.871, 7.526, 49.648, 2.371, 6.475, 49.857, 3.421, 134.44, 0.1949, 0.9808, -0.0000, 1.500); }
module spot_raft_bridge() hull() {
        linear_extrude(0.050) hull() { translate([0.99, 44.10]) circle(d = 5.00, $fn = 32); translate([0.26, 49.84]) circle(d = 5.00, $fn = 32); translate([6.92, 43.76]) circle(d = 5.00, $fn = 32); translate([7.72, 49.19]) circle(d = 5.00, $fn = 32); }
        translate([0, 0, 0.550]) linear_extrude(0.050) hull() { translate([0.99, 44.10]) circle(d = 6.20, $fn = 32); translate([0.26, 49.84]) circle(d = 6.20, $fn = 32); translate([6.92, 43.76]) circle(d = 6.20, $fn = 32); translate([7.72, 49.19]) circle(d = 6.20, $fn = 32); }
    }
