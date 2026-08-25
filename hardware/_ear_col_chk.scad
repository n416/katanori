// 耳の下に壁の柱が置けるか（案A の下調べ）: 候補の柱 ↔ 中身・線・他の外皮
include <case_v3.scad>
part = "none";
SIDE = "L"; H = 12;
x0 = (SIDE == "L") ? 0 : IN_X - EAR_W;
module cand() translate([x0, EAR_Y0, IN_Z - EAR_T - H]) cube([EAR_W, EAR_Y1 - EAR_Y0, H]);
module others() { manaita(PLUGGED_9); bridge_v3(); pb_v3(); translate(LIPO_AT) lipo_1000mah();
    translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module();
    top_plate(); front_plate(); hatch_raw(); oled_brackets(); wires_v3(); }
intersection() { cand(); others(); }
