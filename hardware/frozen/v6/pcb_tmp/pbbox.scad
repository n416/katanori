use <../case_v5.scad>
DY = 0; NEW_W = 28.0;
GROW = NEW_W - 22.86;
OFF = (DY == 0) ? 0 : (DY == 1) ? -GROW : -GROW / 2;
at_pb() translate([0, OFF, 0]) cube([36.068, NEW_W, 1.6]);
