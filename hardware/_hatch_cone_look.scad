include <case_v4.scad>
intersection() {
    union() { hatch_print(); props_hatch(); raft_hatch(); }
    translate([4, 18.5, -0.5]) cube([14, 15, 8]);
}
