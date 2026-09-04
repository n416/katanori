// 前の床ボス（左右）と ReSpeaker の部品の関係を見る絵（2026-08-25）
//   壁が上から降りるので、ボスの XY の影に居る物は全部避ける必要がある → ボスは L 形になった
include <case_v4.scad>
part = "none";
S = "r";
module clip(x0, x1) translate([x0, -1, -0.5]) cube([x1 - x0, 11, 13.5]);
intersection() {
    union() {
        rwall_v4(); lwall_v4();
        color("#68d391") respeaker_at();
    }
    if (S == "r") clip(76.5, 88); else clip(-2, 9.5);
}
