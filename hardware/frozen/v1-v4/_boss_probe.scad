// 床の前ボス（左右）の真上の柱に、ReSpeaker の部品がどれだけ入っているかを洗う道具（2026-08-25）
//   ボスは壁と一緒に上から降りるので、柱（ボスの XY の影を上まで伸ばした角柱）に居る部品は
//   静止で当たっていなくても軌跡で当たる。ここに出た bbox がそのまま「欠くべき帯」。
//   実行: openscad --backend=manifold -D 'P="r"' -o _boss_probe_r.stl hardware/_boss_probe.scad
include <case_v4.scad>
part = "none";
P = "";
module col(x0, y0) translate([x0, y0, -0.01]) cube([BOSS, BOSS_B_DY_F, 40]);
if (P == "l") intersection() { col(0.7, 2); respeaker_at(); }
if (P == "r") intersection() { col(78.3, 2); respeaker_at(); }
if (P == "r_hi") intersection() { col(78.3, 2); respeaker_at(); translate([0, 0, 12]) cube([200, 200, 200]); }
if (P == "r_lo") intersection() { col(78.3, 2); respeaker_at(); translate([-1, -1, -1]) cube([200, 200, 13]); }
