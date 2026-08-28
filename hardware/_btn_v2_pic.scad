include <btn_v2.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN2_SOLO = false;
V = "asm"; EX = 0;
module top_patch() color("#dfe3e8") difference() {
    union() {
        translate([BTN4[0]-16, BTN4[1]-12, IN_Z]) cube([32, 24, TOP_T]);
        btn2_at_add();
    }
    btn2_at_cut();
}
module scene() {
    top_patch();
    translate([0,0,-EX*8]) btn2_at_piston();
    translate([0,0,-EX*18]) btn2_at_switch();
    translate([0,-EX*12,0]) color("#b0b0b0") btn2_at_screws();
}
if (V=="asm" || V=="exp") scene();
if (V=="cut") difference() { scene(); translate([-100, BTN4[1]-100, -100]) cube([200,100,200]); }
