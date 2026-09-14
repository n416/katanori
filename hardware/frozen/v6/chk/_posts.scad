include <../_v6_portrait.scad>
part = "postecho";
for (i = [0 : len(POSTS) - 1])
    echo(str("POST ", i, " ", POSTS[i][0], " ", POSTS[i][1], " ", POSTS[i][2], " ",
             POSTS[i][3], " ", POSTS[i][4]));
echo(str("CB ", CB_D, " ", CB_H));
// 皿ぐりどうし・通し穴どうしが実体で重なっていないか
A = 0; B = 1;
module cb(i) translate([POSTS[i][0], POSTS[i][1], -0.01]) cylinder(d = CB_D, h = CB_H + 0.01, $fn=96);
module ho(i) translate([POSTS[i][0], POSTS[i][1], -1]) cylinder(d = POSTS[i][4], h = POSTS[i][2] + 2, $fn=96);
module so(i) translate([POSTS[i][0], POSTS[i][1], WALL]) cylinder(d = POSTS[i][3], h = POSTS[i][2] - WALL, $fn=96);
if (part == "cb_pair")   intersection() { cb(A); cb(B); }
if (part == "hole_pair") intersection() { ho(A); ho(B); }
if (part == "sol_pair")  intersection() { so(A); so(B); }
