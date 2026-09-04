// ============================================================
// 充電口をどこに開けられるか —— 壁ごとの「置ける所」の地図
// ============================================================
// 2026-08-22。市販の固い変換アダプタが向きも大きさも合わないと分かったので
// （docs/CASE-V2.md §⬜ 充電口のアダプタ探し）、口を右の壁から動かす前提で
// 「Type-C のメスの胴が入る壁の場所」を実体で出す道具。
// ✅ この地図を見てユーザーが背面を選び、2026-08-22 夜に口を移した（case_v2.scad §4.3f）。
//
//   刷る絵:
//   "C:\Program Files\OpenSCAD (Nightly)\openscad.exe" --backend=manifold --render //     --projection=o --autocenter --viewall --camera=0,0,0,0,0,0,260 --imgsize=1700,1250 //     -o hardware/_port_area.png hardware/_port_area.scad
//
// やっていること: 壁の内面から DEP mm の間に 3mm おきの断面を取り、どの断面でも
// 空いている所だけを残し、受け口の外形の半分（PORT/2）だけ縮める。残った塗りが
// **受け口の中心を置ける範囲**。輪郭はその壁のすぐ内側にある物。
// ⚠ 出るのは「壁ぎわに胴が入るか」だけで、**線がそこまで通るかは別**（下の §経路）。
// ============================================================
use <case_v2.scad>
IN   = [86, 72, 48.1];
PORT = 12;    // 受け口の外形（12mm 角）。出るのは「中心を置ける範囲」
DEP  = 10;    // 壁の内側に要る奥行
module obstacles() union() { shell_lower(); shell_upper(); parts_v2(); wires_v2(); back_rail(); }
module inbox() cube(IN);
module sec_p(rot,z) projection(cut=true) translate([0,0,-z]) rotate(rot) obstacles();
module ibx_p(rot,z) projection(cut=true) translate([0,0,-z]) rotate(rot) inbox();
module free_p(rot,zc,d) difference(){ ibx_p(rot,zc-d); sec_p(rot,zc-d); }
module ok_p(rot,zc,dep)
    offset(delta=-PORT/2)
    intersection_for(d = [for (i=[0:1:floor((dep-1.5)/3)]) 1.5+i*3]) free_p(rot,zc,d);

// uvmin = 回す前の左下, a = 外から見た向きに直す回転, org = 置き場所, lab = 文字の位置
module panel(rot, zc, uvmin, a, org, lab, cap) {
    translate(org) rotate(a) translate([-uvmin[0], -uvmin[1]]) {
        difference(){ offset(delta=1.2) ibx_p(rot,zc-1.5); ibx_p(rot,zc-1.5); }
        intersection(){
            ibx_p(rot,zc-1.5);
            difference(){ offset(delta=0.5) sec_p(rot,zc-1.5); sec_p(rot,zc-1.5); }
        }
        ok_p(rot,zc,DEP);
    }
    translate(lab) text(cap, size=4.0, halign="left");
}
linear_extrude(1) {
    panel([0,0,0],   IN[2], [0,0],      0,   [  0,120],      [  0,113], "TOP (+Z)    right = X+   up = Y+     [86 x 72]");
    panel([90,0,0],  IN[1], [0,-48.1],  180, [200,168.1],    [114,113], "BACK (+Y)   right = X-   up = Z+     [86 x 48.1]");
    panel([0,90,0],  0,     [0,0],     -90,  [  0, 93.1],    [  0, 38], "LEFT (-X)   right = Y-   up = Z+     [72 x 48.1]");
    panel([0,-90,0], IN[0], [-48.1,0],  90,  [186, 45],      [114, 38], "RIGHT (+X)  right = Y+   up = Z+     [72 x 48.1]");
    translate([0, 210]) text("solid = where the CENTER of a 12mm port can sit (needs 10mm clear depth behind the wall)", size=5);
    translate([0, 201]) text("outline = what already sits just inside that wall.   FRONT (-Y) and BOTTOM (-Z): nothing fits.", size=4.2);
}
