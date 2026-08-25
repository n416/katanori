// ============================================================
// 底を前下ヒンジで開く分割の、組み立てシミュレーション（2026-08-23・見るための道具）
// ============================================================
// ユーザーの絵（2026-08-23）: 背板を床から切り離して Upper へ渡す（赤の帯は高さ 0 ＝
// 背板は丸ごと Upper）。残った**床の皿**が、OLED 側の下（前下）を軸に Z 方向へ開く。
//
//   本体（Upper）= 天板＋左右の壁＋正面の枠＋ブリッジ＋**背板（レール・トグルごと）**
//   皿（Tray）  = 床だけ（ハブの柱・ReSpeaker の溝・OLED の棚・PowerBoost の床の柱）
//   ヒンジの軸  = 正面の外の下の角（Y = HINGE_Y / Z = HINGE_Z）を通る X 軸
//
//   openscad --backend=manifold --summary geometry -o x.stl -D 'part="swing"' hardware/_hinge_chk.scad
//   part="swing"  … 皿を 0〜ANG 度まで振った通り道 ⇔ 本体。0 なら開閉できる
//   part="closed" … 閉じた状態だけの当たり（＝いまの chk と同じ意味）
//   PICK_L / PICK_U で片側を 1 つに絞る（-2 = 殻だけ、番号 = PARTS_V2 の番号）
// ============================================================
use <case_v2.scad>

part   = "swing";
RSP_UP = true;    // ReSpeaker を本体側に付けるか（false なら皿に載ったまま振れる）
ANG    = 90;      // 開く角度
STEP   = 2;
PICK_L = -1;
PICK_U = -1;
RAIL   = true;    // 背板のレールを残すか（false = 捨てた場合）
FLAT   = false;   // 皿を本当に「床だけ」にするか（前まわりの立ち上がりを本体へ渡す）

IN_X = 86; IN_Y = 72; IN_Z = 48.1; BOSS = 7.0; WALL = 2.0; BEZ_T = 2.0;
HINGE_Y = -BEZ_T;   // 正面の外の面
HINGE_Z = -WALL;    // 床の外の面

// ---- 背板の側（背板そのもの・レール・奥のボス）----
module back_region() {
    translate([-10, IN_Y, -10]) cube([110, 10, 80]);
    translate([-10, 64.5, 10]) cube([110, 20, 60]);
}
// 前まわりの立ち上がり（窓の下枠・OLED の棚・ReSpeaker の土手と振れ止め）。床より上だけ
module front_region() {
    translate([-10, -BEZ_T, 0]) cube([110, BEZ_T + 11.5, 60]);
}
// レールだけの領域（捨てる場合にここを引く）。背板の内面より手前・床より上
module rail_region() { translate([-10, 60.0, 2.0]) cube([110, IN_Y - 60.0 + 0.01, 60]); }

NEW_BOSSES = [[[0,           IN_Y - BOSS, 0], -1],
              [[IN_X - BOSS, IN_Y - BOSS, 0], +1]];

module body() {
    difference() {
        union() {
            shell_upper();
            intersection() { shell_lower(); back_region(); }
        }
        for (b = NEW_BOSSES) screw_hole(b[0], b[1]);
        if (!RAIL) rail_region();
    }
    if (FLAT) intersection() { shell_lower(); front_region(); }
}
module tray() {
    difference() { shell_lower(); back_region(); if (FLAT) front_region(); }
    for (b = NEW_BOSSES) screw_boss(b[0], b[1]);
}

UP_IDS = concat([1, 3, 4, 5, 7, 8, 9, 10], RSP_UP ? [0] : []);
LO_IDS = concat([2],                       RSP_UP ? [] : [0]);

module body_group() {
    if (PICK_U == -1 || PICK_U == -2) body();
    for (i = UP_IDS) if (PICK_U == -1 || PICK_U == i) parts_v2(i);
}
module tray_group() {
    if (PICK_L == -1 || PICK_L == -2) tray();
    for (i = LO_IDS) if (PICK_L == -1 || PICK_L == i) parts_v2(i);
}
// 前下の軸まわりに t 度だけ下へ開く
module at_angle(t) translate([0, HINGE_Y, HINGE_Z]) rotate([-t, 0, 0])
    translate([0, -HINGE_Y, -HINGE_Z]) children();
module swing(n) for (t = [0 : STEP : n]) at_angle(t) children();

CY0 = -100; CY1 = 100;   // 見たい Y の帯だけに切る
module cbox() translate([-20, CY0, -20]) cube([130, CY1 - CY0, 100]);
if (part == "swing_c") intersection() { cbox(); body_group(); swing(ANG) tray_group(); }
else if (part == "swing")  intersection() { body_group(); swing(ANG) tray_group(); }
else if (part == "closed") intersection() { body_group(); tray_group(); }
else if (part == "body")   body_group();
else if (part == "tray")   tray_group();
else if (part == "open") {           // 絵: ANG 度だけ開いた姿
    color("#b6c0cc") body();
    color("#6c7a89") for (i = UP_IDS) parts_v2(i);
    at_angle(ANG) { color("#9aa5b1") tray(); color("#3cb44b") for (i = LO_IDS) parts_v2(i); }
}
