// 薄いと出た所だけ切り出して、細かい格子で測り直す（2026-08-25）
include <case_v4.scad>
part = "none";
R = "mouth";
if (R == "mouth") intersection() { straps_v4(); translate([20, 14, 30]) cube([11, 9, 6]); }   // 電流計の前穴の溝の口（帯 A の後ろの面）
if (R == "seat")  intersection() { straps_v4(); translate([20, 33, 30]) cube([11, 6, 7]); }   // 座と座の谷（Y 36.55/37.05）
