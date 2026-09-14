include <../_v6_gear.scad>
SGUP = 0.0;
// ① 持ち上げた歯車が殻（前の壁）に当たるか
if (part == "up_shell") intersection() { translate([0,0,SGUP]) sgear(); shell_mech(); }
// ② 持ち上げた後も柱に掛かっているか（穴の空間 × 柱。体積 ÷ 柱の断面 ＝ 掛かり）
module sg_bore(dz) translate([SENS[0], SENS[1], SGBOT + dz]) rotate([0,0,ROT_S])
    intersection() {
        cylinder(d = ROT_WST - SG_PRESS, h = ROT_PEGT - SGBOT);
        translate([-ROT_WST, -(ROT_WST - 0.8 - SG_PRESS)/2, 0])
            cube([2*ROT_WST, ROT_WST - 0.8 - SG_PRESS, ROT_PEGT - SGBOT]);
    }
module sg_peg() translate([SENS[0], SENS[1], 0]) rotate([0,0,ROT_S]) intersection() {
    translate([0,0,ROT_SHLD]) cylinder(d = ROT_WST, h = ROT_PEGT - ROT_SHLD);
    translate([-ROT_WST, -(ROT_WST-0.8)/2, ROT_SHLD-1]) cube([2*ROT_WST, ROT_WST-0.8, 3]);
}
if (part == "up_grip") intersection() { sg_bore(SGUP); sg_peg(); }
