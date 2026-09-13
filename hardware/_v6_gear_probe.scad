include <_v6_gear.scad>
part = "probe";
// 読み取りの芯まわり φ12 の柱で ReSpeaker を切り、Z 17.0 より下に何が垂れているかを見る
intersection() { rs_solid(); translate([SENS[0], SENS[1], 0]) cylinder(d = 14, h = 17.0); }
