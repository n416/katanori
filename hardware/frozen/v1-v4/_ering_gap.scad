use <knob_v5.scad>
WHAT = "sweep";
if (WHAT == "sweep") ering_sweep(1);
if (WHAT == "obst")  ering_obstacles();
if (WHAT == "posts") for (x = [-1, 1], y = [-1, 1]) post_solid(x, y);   // 柱だけ
if (WHAT == "nuts")  stop_nuts();                                       // 島を留めるナットだけ
