// 留め帯と支柱を一体にした場合の印刷性の研究（2026-09-02・数字を出すだけ。設計は変えない）
//   帯 1 本（strap_one）と、その帯の Y 範囲に post_xy(i) が入る支柱（post_one）を union した形を、
//   姿勢（pose）を変えてプレート z=0 に置く。_stl_preflight.py / _tilt_sweep.py に掛ける用。
//   使い方:
//     openscad --backend=manifold --export-format=binstl -D band=1 -D pose="\"flip\"" -D variant="\"post\"" -o out.stl hardware/_onepiece_study.scad
//   variant = "post"    … いまの支柱（E リングのピン）を帯に生やした形
//           = "oldseat" … 旧の一体型の座（seats_v4 ＋ slot_outer_walls − seat_screws・M2 ＋ 横差しナット）
//   pose    = assembled（組んだ姿勢・足が下）/ flip（天面が下・いまの帯の向き。支柱は下へ突き出る）
//           / side_py（+Y の面が下）/ side_my（−Y の面が下）… X 軸回り ∓90°
//           / end_px（+X の端＝右の足の外側が下）/ end_mx（−X の端が下）… Y 軸回り ±90°
//   zfix    = 底を z=0 に合わせる追加の送り。post は解析値で 0 に来る。oldseat の座の天面は板の傾きで
//             決まるので解析では出さず、書き出した STL の底を実測して -D zfix で渡す（研究の driver は scratchpad）
include <case_v4.scad>
part = "none";

band = 1;
pose = "assembled";
variant = "post";
zfix = 0;
showplate = false;   // 絵の用: プレート（z=0 の薄い板）を敷く

s  = STRAP_BANDS[band];
bp = [for (i = [0 : 5]) if (post_xy(i)[1] >= s[0] - 0.01 && post_xy(i)[1] <= s[0] + s[1] + 0.01) i];   // この帯に座る支柱

// 🔒 2026-09-03 一体化が採用された（ユーザー）。strap_one(s) がそのまま支柱ごとの 1 部品なので、
//    穴を埋め戻す細工（旧 strap_fill）は要らなくなった。この研究ファイルの役目は §31 で終わり。
module onepiece_post(s)  strap_one(s);
module onepiece_oldseat(s) intersection() {
    difference() {
        union() { strap_one(s); seats_v4(); slot_outer_walls(); }
        seat_screws();
    }
    translate([-100, strap_ya(s) - 0.05, -100]) cube([400, strap_yb(s) - strap_ya(s) + 0.1, 400]);
}
module piece() { if (variant == "oldseat") onepiece_oldseat(s); else onepiece_post(s); }

// 外形（解析値）。X は帯の足の外面、Y はツバ込みの端と支柱の胴、Z は皿の上〜ピンの先
xmin = min(concat([BAT_X0 - 2.5], [for (i = bp) post_xy(i)[0] - SPACER_R]));
xmax = max(concat([BAT_X0 + lipo_size()[1] + 0.5 + STRAP_T], [for (i = bp) post_xy(i)[0] + SPACER_R]));
ymin = min(concat([strap_ya(s)], [for (i = bp) post_xy(i)[1] - SPACER_R]));
ymax = max(concat([strap_yb(s)], [for (i = bp) post_xy(i)[1] + SPACER_R]));
zmin = BAT_Z;
zmax = max(concat([plate_top()], [for (i = bp) post_top_z(i)]));

// tilt … 提案の刷る向きの絵の用: 組んだ姿勢（足が下）のまま長軸（X）回りに tilt_deg 傾け、
//        プレートから tilt_lift 浮かせる（支え・ラフトは _v4_post_props.py の仕事なので描かない）
tilt_deg = 30; tilt_lift = 5.0;
module posed() translate([0, 0, zfix]) {
    if (pose == "tilt")      translate([0, 0, tilt_lift]) rotate([tilt_deg, 0, 0]) translate([0, -(ymin + ymax) / 2, -zmin]) children();
    if (pose == "assembled") translate([0, 0, -zmin]) children();
    if (pose == "flip")      translate([0, 0,  zmax]) rotate([180, 0, 0]) children();
    if (pose == "side_py")   translate([0, 0,  ymax]) rotate([-90, 0, 0]) children();   // z' = -y
    if (pose == "side_my")   translate([0, 0, -ymin]) rotate([ 90, 0, 0]) children();   // z' =  y
    if (pose == "end_px")    translate([0, 0,  xmax]) rotate([0,  90, 0]) children();   // z' = -x
    if (pose == "end_mx")    translate([0, 0, -xmin]) rotate([0, -90, 0]) children();   // z' =  x
}
echo(band = band, pose = pose, variant = variant, posts = bp, box = [[xmin, ymin, zmin], [xmax, ymax, zmax]]);
posed() piece();
if (showplate) color("#bbbbbb", 0.5) translate([-100, -100, -0.3]) cube([300, 300, 0.3]);
