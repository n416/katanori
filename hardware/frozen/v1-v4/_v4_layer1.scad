// 天板の刷る向きの「1 層目の断面」を絵にするだけの使い捨て（CHITUBOX の底面ビューと同じ見え方）。
//   使い方: openscad --camera=63.204,-41.8,0,0,0,0,76 -o png -D 'Z=0.02' _v4_layer1.scad
use <case_v4.scad>
Z = 0.02;   // 切る高さ
linear_extrude(1) projection(cut = true)
    translate([0, 0, -Z]) { top_print(); props_top(); raft_top(); }
