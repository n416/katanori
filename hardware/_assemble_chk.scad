// ============================================================
// 組めるかを実体で当てる道具（2026-08-22）。筐体の部品ではない
// ============================================================
// ユーザー「組み立てられないよな」を確かめる。上シェル側の物と下シェル側の物に分け、
// **下シェル側を真っ直ぐ Z で近づける**通り道（0〜SWEEP mm 手前まで）と上シェル側を当てる。
// 0 なら真っ直ぐ閉じられる。体積が出たら、その場所で引っ掛かる。
//
//   上シェル側: 上シェル・OLED(1)・つまみ(3)・スピーカー(4)・PowerBoost(5)・INA226(7)・タクト(10)
//   下シェル側: 下シェル・ハブ(2)・トグル(8)・尻尾(9)
//   ReSpeaker(0) はどちらに付けて閉じるかで結果が変わるので RSP_UP で切り替える
//   電池(6) は最後に左の口から入れるので含めない
//
//   openscad --backend=manifold -o x.stl -D 'part="close"' -D RSP_UP=true  hardware/_assemble_chk.scad
//   openscad --backend=manifold -o x.stl -D 'part="rsp_z"'  hardware/_assemble_chk.scad   // ReSpeaker を上シェルへ下から入れる道
//   openscad --backend=manifold -o x.stl -D 'part="rsp_x"'  hardware/_assemble_chk.scad   // そのあと USB-C の殻を口へ差す 0.9mm
//   PICK_L / PICK_U で片側を 1 つに絞れる（-1 = 全部）
// ============================================================
use <case_v2.scad>
part   = "close";
RSP_UP = true;
SWEEP  = 40;      // 下シェル側を下げる量（mm）
STEP   = 1;
PICK_L = -1;      // 下シェル側を 1 つに: -2 = 下シェルだけ, 2/8/9/0 = その部品
PICK_U = -1;      // 上シェル側を 1 つに: -2 = 上シェルだけ, 1/3/4/5/7/8/9/10/0 = その部品
RSP_DX = 0.9;     // USB-C の殻が増し壁の口へ入っている量（レセプタクルの面 85.55 − 壁の内面 84.65）

function has(l, v) = len([for (x = l) if (x == v) 1]) > 0;
UP_IDS = concat([1, 3, 4, 5, 7, 10], RSP_UP ? [0] : []);
LO_IDS = concat([2, 8, 9],           RSP_UP ? [] : [0]);

module upper_group() {
    if (PICK_U == -1 || PICK_U == -2) shell_upper();
    for (i = UP_IDS) if (PICK_U == -1 || PICK_U == i) parts_v2(i);
}
module lower_group() {
    if (PICK_L == -1 || PICK_L == -2) shell_lower();
    for (i = LO_IDS) if (PICK_L == -1 || PICK_L == i) parts_v2(i);
}
module sweep_z(n) for (t = [0 : STEP : n]) translate([0, 0, -t]) children();

if (part == "close")
    intersection() { upper_group(); sweep_z(SWEEP) lower_group(); }
// ReSpeaker を上シェルに入れる: 殻のぶん左へ寄せたまま下から上がる
else if (part == "rsp_z")
    intersection() { upper_group_no_rsp(); translate([-RSP_DX, 0, 0]) sweep_z(SWEEP) parts_v2(0); }
// 最後に右へ 0.9 滑らせて殻を口へ
else if (part == "rsp_x")
    intersection() { upper_group_no_rsp(); for (s = [0 : 0.1 : RSP_DX]) translate([-s, 0, 0]) parts_v2(0); }
else if (part == "look_upper") upper_group();
else if (part == "look_lower") lower_group();
else if (part == "rsp_only") parts_v2(0);

module upper_group_no_rsp() {
    if (PICK_U == -1 || PICK_U == -2) shell_upper();
    for (i = [1, 3, 4, 5, 7, 10]) if (PICK_U == -1 || PICK_U == i) parts_v2(i);
}

// rsp_z を左の壁（X<0）と右の増し壁（X>84）とそれ以外に分けて見る
CLIP = "";
module clip() { if (CLIP == "L") translate([-10, -10, -10]) cube([10, 100, 80]);
                else if (CLIP == "R") translate([84, -10, -10]) cube([10, 100, 80]);
                else if (CLIP == "M") translate([0, -10, -10]) cube([84, 100, 80]);
                else translate([-10, -10, -10]) cube([110, 100, 80]); }
if (part == "rsp_z_clip")
    intersection() { clip(); upper_group_no_rsp(); translate([-RSP_DX, 0, 0]) sweep_z(SWEEP) parts_v2(0); }
if (part == "lo0_clip")
    intersection() { clip(); shell_upper(); sweep_z(SWEEP) parts_v2(0); }
// 1 点だけ: ReSpeaker を DX 左・T 下へ置いて上シェルと当てる
DX = 0; T = 0;
if (part == "rsp_at") intersection() { clip(); shell_upper(); translate([-DX, 0, -T]) parts_v2(0); }

// ============================================================
// 絵: 真っ直ぐ閉じられない 2 か所の断面
//   左 = X 40 の Y-Z 断面（トグルの胴がブリッジとトンネルの上に居る）
//   右 = Y 18.4 の X-Z 断面（XIAO の USB-C の殻が右の増し壁の口の中に居る）
//   "C:\Program Files\OpenSCAD (Nightly)\openscad.exe" --backend=manifold --render --projection=o //     --autocenter --viewall --camera=0,0,0,0,0,0,260 --imgsize=1700,900 -o hardware/_assemble_chk.png //     -D 'part="pic"' hardware/_assemble_chk.scad
// ============================================================
module sec_x(x) { mirror([1, 0]) rotate(90) projection(cut = true) rotate([0, 90, 0]) translate([-x, 0, 0]) children(); }
module sec_y(y) { mirror([0, 1]) projection(cut = true) rotate([90, 0, 0]) translate([0, -y, 0]) children(); }
module slab(c) color(c) linear_extrude(1) children();
if (part == "pic") {
    translate([0, 0, 0]) {
        slab("#c9d0d8") sec_x(40) shell_upper();
        slab("#7d8794") sec_x(40) shell_lower();
        slab("#e6194b") sec_x(40) parts_v2(8);
        slab("#555")    sec_x(40) parts_v2(2);
        translate([0, 56]) linear_extrude(1) text("X 40 (Y-Z)  toggle vs bridge", size = 4);
    }
    translate([100, 0, 0]) {
        slab("#c9d0d8") sec_y(18.4) shell_upper();
        slab("#7d8794") sec_y(18.4) shell_lower();
        slab("#e6194b") sec_y(18.4) parts_v2(0);
        slab("#555")    sec_y(18.4) parts_v2(2);
        translate([0, 56]) linear_extrude(1) text("Y 18.4 (X-Z)  USB-C shell in the wall", size = 4);
    }
}
