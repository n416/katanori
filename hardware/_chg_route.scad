include <case_v3.scad>
// 上から: 灰 = ブリッジ / 橙 = PWR の 3 本（立ち上がりを Y 68.5 へ送った）
bridge_v3();
color("#dd6b20") intersection() { wires_v3(); translate([60, 55, 15]) cube([26, 17, 20]); }
