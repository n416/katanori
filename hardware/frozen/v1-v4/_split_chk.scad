// ============================================================
// 分割の変更案を実体で当てる道具（2026-08-22・提案 → 同日夜に case_v2.scad へ入れた）
// ============================================================
// 🔴 **案A は 2026-08-22 21:22 に戻した**（ユーザー却下: ハブが蓋になって配線できない）。この道具は記録として残す。
// ユーザー「筐体の分割方法を変えて収まるようにできないか」。
// case_v2.scad は触らず、ここで**背板を上シェルへ移した形**を作って
// _assemble_chk.scad と同じ通り道検査を掛ける。
//
//   案A: 背板（＋レール＋充電の口＋トグル）を上シェルへ。下シェルは床の皿だけになる。
//        奥の合わせボス2本は床の奥の角へ下ろす（前の2本と同じ形・横からねじ）。
//   ⚠ XIAO の USB-C の殻（増し壁の口に 0.9 入っている）は分割では直らない。
//      殻を口へ入れる動きは X なので、どの分割でも ReSpeaker は X へ 0.9 動く必要がある。
//      ここでは**左の壁に J2 の逃げ（深さ RELIEF）を掘った場合**も一緒に当てる（RELIEF=0 で無し）。
//
//   openscad --backend=manifold -o x.stl -D 'part="close"' -D RSP_UP=false hardware/_split_chk.scad
//   openscad --backend=manifold -o x.stl -D 'part="rsp_z"'  hardware/_split_chk.scad   // ReSpeaker を上シェルへ（J2 の逃げ付き）
//   openscad --backend=manifold -o x.stl -D 'part="boss"'   hardware/_split_chk.scad   // 新しい奥のボス ⇔ 部品・線・上シェル
// ============================================================
use <case_v2.scad>
part   = "close";
RSP_UP = false;
SWEEP  = 40;  STEP = 1;
PICK_L = -1;  PICK_U = -1;
RSP_DX = 0.9;      // 殻が口に入っている量
RELIEF = 0.0;      // 左の壁に掘る J2 の逃げ（X 方向の深さ）。J2 は壁から 0.42 なので 0.9 − 0.42 = 0.48 以上
IN_X = 86; IN_Y = 72; IN_Z = 48.1; BOSS = 7.0;

// ---- 背板の側に付ける領域（背板そのもの・レール・奥のボス）----
module back_region() {
    translate([-10, IN_Y, -10]) cube([110, 10, 80]);        // 背板（床の奥 2mm の帯ごと）
    translate([-10, 64.5, 10]) cube([110, 20, 60]);         // レール（Y 64.5〜）と奥のボス（Z 39.1〜）
}
// 新しい奥のボス（床の奥の角・前の2本と同じ）
NEW_BOSSES = [[[0,           IN_Y - BOSS, 0], -1],
              [[IN_X - BOSS, IN_Y - BOSS, 0], +1]];
// J2 の逃げ: 左の壁の内面を RELIEF だけ掘る。J2 の場所（X 0.42〜2 / Y 10〜15 / Z 2.5〜13.3）の周り
module j2_relief() { if (RELIEF > 0)
    translate([-RELIEF, 9.0, -1.0]) cube([RELIEF + 0.01, 7.0, 15.5]); }   // 壁の下端（Z 0）から J2 の頭 13.3 の上まで

module upper2() {
    difference() {
        union() {
            shell_upper();
            intersection() { shell_lower(); back_region(); }
        }
        for (b = NEW_BOSSES) screw_hole(b[0], b[1]);
        j2_relief();
        wave_trim();
    }
}
// ブリッジ前面の波の出っ張り（Y 19.02〜20.03 / Z 23.5〜24.5 / X 64〜79.2）を TRIM だけ削る。0 で無し
TRIM = 0.0;
module wave_trim() { if (TRIM > 0) translate([0, 18.5, 22.0]) cube([79.2, 20.03 - 18.5 + TRIM - 1.01, 3.0]); }   // 全長。前面 Y 20.02 より手前に出た分だけ落ちる
if (part == "trim_removed") intersection() { wave_trim(); upper2_notrim(); }
module upper2_notrim() { difference() { union() { shell_upper(); intersection() { shell_lower(); back_region(); } } } }
if (part == "hole_vs_shutter") intersection() { for (b = NEW_BOSSES) screw_hole(b[0], b[1]); union() { battery_shutter(0); battery_lock(); } }
if (part == "shutter_only") { battery_shutter(0); battery_lock(); }
if (part == "rsp_at") intersection() { clip(); upper_group_no_rsp(); translate([-DX, 0, -T]) parts_v2(0); }
DX = 0; T = 0;
// 当たりを X で 3 つに分けて見る: L = 左の壁 (X<0) / M = 中 / R = 右の増し壁 (X>84)
CLIP = "";
module clip() { if (CLIP == "L") translate([-10, -10, -10]) cube([10, 100, 80]);
                else if (CLIP == "R") translate([84, -10, -10]) cube([10, 100, 80]);
                else if (CLIP == "M") translate([0, -10, -10]) cube([84, 100, 80]);
                else translate([-10, -10, -10]) cube([110, 100, 80]); }
module lower2() {
    difference() { shell_lower(); back_region(); }
    for (b = NEW_BOSSES) screw_boss(b[0], b[1]);
}
function has(l, v) = len([for (x = l) if (x == v) 1]) > 0;
UP_IDS = concat([1, 3, 4, 5, 7, 8, 9, 10], RSP_UP ? [0] : []);   // トグル(8)・尻尾(9)も上へ
LO_IDS = concat([2],                        RSP_UP ? [] : [0]);
module upper_group() {
    if (PICK_U == -1 || PICK_U == -2) upper2();
    for (i = UP_IDS) if (PICK_U == -1 || PICK_U == i) parts_v2(i);
}
module lower_group() {
    if (PICK_L == -1 || PICK_L == -2) lower2();
    for (i = LO_IDS) if (PICK_L == -1 || PICK_L == i) parts_v2(i);
}
module sweep_z(n) for (t = [0 : STEP : n]) translate([0, 0, -t]) children();
module upper_group_no_rsp() { upper2(); for (i = [1, 3, 4, 5, 7, 8, 9, 10]) parts_v2(i); }

if (part == "close")  intersection() { upper_group(); sweep_z(SWEEP) lower_group(); }
else if (part == "rsp_z") intersection() { clip(); upper_group_no_rsp(); translate([-RSP_DX, 0, 0]) sweep_z(SWEEP) parts_v2(0); }
else if (part == "rsp_x") intersection() { clip(); upper_group_no_rsp(); for (s = [0 : 0.1 : RSP_DX]) translate([-s, 0, 0]) parts_v2(0); }
else if (part == "boss")  intersection() { for (b = NEW_BOSSES) screw_boss(b[0], b[1]); union() { parts_v2(); wires_v2(); shell_upper(); } }
else if (part == "upper2") upper2();
else if (part == "lower2") lower2();
else if (part == "explode") {
    color("#9aa5b1") lower2();
    color("#6c7a89") for (i = LO_IDS) parts_v2(i);
    translate([0, 0, 55]) { color("#b6c0cc") upper2(); color("#6c7a89") for (i = UP_IDS) parts_v2(i); }
}
