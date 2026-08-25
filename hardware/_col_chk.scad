include <case_v3.scad>
part = "none";
WHICH = "L";
X0 = (WHICH == "R") ? IN_X - EAR_W : 0;
module probe() translate([X0 - 0.1, EAR_Y0 - 0.1, IN_Z - EAR_T - EAR_COL_H - 0.1]) cube([EAR_W + 0.2, EAR_Y1 - EAR_Y0 + 0.2, EAR_COL_H + 0.2]);
if (WHICH == "solo") ear_col(0);
if (WHICH == "L") intersection() { probe(); left_wall_v3(); }
if (WHICH == "R") intersection() { probe(); right_wall_v3(); }
