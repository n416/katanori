include <case_v3.scad>
C = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2]);
module obst() union() { manaita(); side_struct(); top_plate(); front_plate(); hatch(); }
// 口の面から手前へ dy 出る胴。ox = 軸から X 方向へずらす量（+ が壁側）
module body() translate([C[0] - px/2 + ox, C[1] - dy, C[2] - pz/2]) cube([px, dy, pz]);
intersection() { body(); obst(); }
