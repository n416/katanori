// ============================================================
// v6 平置き案（ユーザー 2026-09-12「ReSpeaker を平置きして、その上に OLED、OLED の隣につまみ」）
//   置いて見るための当て板。皮・柱・締結・線は無い。当たり検査も回していない。
//   ⚠ 中継基板は「適当な板」（ユーザー指示）。口の層だけ塊で置いてある。
//   ⚠ つまみを OLED の X の隣に置くと、柱が下の ReSpeaker を貫く。**私が Y の隣へ動かした。**
//
//   実行: "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o x.png -D "part=\"look\"" hardware/frozen/v6/_v6_flat.scad
//   part の値: look（中身）／ top（上から）／ blocks（板と OLED と ReSpeaker だけ）／ face（外から見た顔。皮は不透明）
// ============================================================
part = "look";

include <../../parts/fit.scad>
use <../../parts/parts.scad>
use <../../parts/respeaker_lite.scad>
use <../../parts/knob_v5.scad>
use <../../parts/btn_v3.scad>
use <../../parts/spk_v5.scad>
$fn = 48;

IN_X = 88.0;
IN_Y = 74.0;
IN_Z = 32.0;
TOP_T = 2.5;
FRONT_T = 2.8;   // 前の壁の厚み。正面付けの部品は原点を外面（y = -FRONT_T）に置く
WALL = 2.0; FLOOR_T = 2.0; BACK_T = 2.8;
BEVEL = 1.2;     // 開口の面取り（docs の見た目の規則）

// ---- ReSpeaker 平置き・マイク面が上 ----
//   rotate([90,0,0]) で マイク面（模型の +Y。face_box の f = −1）が +Z を向く。「左から」は +X のまま。
//   ⇒ XIAO の USB-C が左の壁・3.5mm ジャックが右の壁
RSP_X = 3.0;
RSP_Y = 22.0;   // 正面付けのつまみが箱の中へ 20.9 入るので、その後ろから置く
RSP_TOP = 24.0;    // マイク面（板の上面）の Z。XIAO 面のピンは下へ 10、線を挿すと 13.9
MIC_D = [[4.16, 6.81], [75.16, 77.81]];   // 📄 公式 CAD「左から」

// ---- OLED（ReSpeaker の上・画面が上）----
OLED_L = 42.40; OLED_W = 38.00; OLED_T = 2.65;
OLED_AA = [35.05, 17.52];
OLED_AA_EDGE = 8.15;
OLED_STAND = 4.0;                  // ⚠ L 字ヘッダの逃げ（私が置いた）
OLED_X = (IN_X - OLED_L) / 2;
OLED_Y = RSP_Y + 34.007 / 2 - OLED_W / 2;
OLED_Z = RSP_TOP + OLED_STAND;

// ---- つまみ（L 字ヘッダ・ユーザー 2026-09-12）----
// 🔒 2026-09-12 ユーザー「つまみと会話ボタンを正面に」: 前の壁の面に付ける（軸は水平・+Y へ）
KNOB_X = 64.7;
KNOB_Z = 16.0;
KNOB_RA_OUT = 23.6;   // L 字が基板の縁の外へ出る量（片側）
AS5600_PCB = 23.0;
KNOB_PCB_BOT = 19.7;

// ---- その他 ----
SPK_X = 15.0;  SPK_Y = 10.0;
BTN_X = 24.0;  BTN_Z = 16.0;
TGL_X = 64.7;
HUB_X = 7.0;   HUB_Y = 11.0;  HUB_Z = 2.5;
HUB_PLUG_TOP = 23.1;
BAT_X = 12.0;  BAT_Y = 15.0;  BAT_Z = 15.0;
PWR_X = 3.0;   PWR_Y = 2.0;   PWR_Z = 10.0;   // ⚠ 仮置き

module box_outline() difference() {
    cube([IN_X, IN_Y, IN_Z]);
    translate([1, 1, 1]) cube([IN_X - 2, IN_Y - 2, IN_Z - 2]);
}

// 中継基板 ── ⚠ 適当な板（ユーザー指示）。口の層だけ塊で置く
module hub_slab() {
    color("#d85a30") translate([HUB_X, HUB_Y, HUB_Z]) cube([74, 52, 1.6]);
    color("#f0997b", 0.3) translate([HUB_X, HUB_Y, HUB_Z + 1.6])
        cube([74, 52, HUB_PLUG_TOP - HUB_Z - 1.6]);
}

module respeaker_flat() {
    translate([RSP_X, RSP_Y + 34.007, RSP_TOP - 1.85]) rotate([90, 0, 0]) respeaker_lite();
    // 🔒 マイク 2 個（塞いだら音が死ぬ）。天板に穴が要る場所
    for (d = MIC_D)
        color("#e24b4a") translate([RSP_X + d[0], RSP_Y + 15.25, RSP_TOP])
            cube([d[1] - d[0], 3.5, 1.28]);
}

module oled_flat() {
    color("#7f77dd") translate([OLED_X, OLED_Y, OLED_Z]) cube([OLED_L, OLED_W, OLED_T]);
    aa_x = OLED_X + (OLED_L - OLED_AA[0]) / 2;
    aa_y = OLED_Y + OLED_W - OLED_AA_EDGE - OLED_AA[1];
    color("#2c2c2a") translate([aa_x, aa_y, OLED_Z + OLED_T]) cube([OLED_AA[0], OLED_AA[1], 0.4]);
}

module knob_all() {
    translate([KNOB_X, -FRONT_T, KNOB_Z]) rotate([90, 0, 0]) assembly(show_deck = false);
    // L 字ヘッダが基板の縁の外へ出る量（両側の列。⚠ parts.scad の as5600(ra=true) の数え方）
    for (s = [-1, 1])
        color("#85b7eb", 0.45)
            translate([KNOB_X + s * AS5600_PCB / 2 - (s < 0 ? KNOB_RA_OUT : 0),
                       -FRONT_T + KNOB_PCB_BOT, KNOB_Z - 5])
                cube([KNOB_RA_OUT, 4, 10]);
}

module deck_rest() {
    translate([SPK_X, SPK_Y, IN_Z + TOP_T]) rotate([0, 0, 180]) spk_body();
    translate([BTN_X, -FRONT_T, BTN_Z]) rotate([90, 0, 0]) { btn3_piston(); btn3_tub(); btn3_switch(); }
    translate([TGL_X, IN_Y, 10.0]) rotate([-90, 0, 0]) mts102(ang = 12);
    color("#26215c") translate([KNOB_X + 16, 2, KNOB_Z - 1.6]) cube([3.2, 14, 3.2]);   // リード（つまみの脇・正面付けに追従）
}

module bat_and_power() {
    color("#ef9f27") translate([BAT_X, BAT_Y, BAT_Z]) cube([35, 50, 6]);
    color("#993c1d") translate([PWR_X, PWR_Y, PWR_Z]) cube([40, 32, 1.6]);
    color("#f0997b", 0.35) translate([PWR_X, PWR_Y, PWR_Z + 1.6]) cube([40, 32, 6.4]);
}

if (part == "blocks") {
    hub_slab(); respeaker_flat(); oled_flat(); %box_outline();
} else {
    hub_slab(); respeaker_flat(); oled_flat(); knob_all(); deck_rest(); bat_and_power();
    %box_outline();
}

echo(str("内寸 ", IN_X, " x ", IN_Y, " x ", IN_Z, " = ", IN_X * IN_Y * IN_Z / 1000, "cm3"));
echo(str("つまみの深さ（L 字・天板の外面から）", KNOB_PCB_BOT + 4.0,
         " / 直立てなら ", KNOB_PCB_BOT + 2.5 + 14.0));
echo(str("マイクの穴 X ", RSP_X + MIC_D[0][0], "〜", RSP_X + MIC_D[0][1],
         " と ", RSP_X + MIC_D[1][0], "〜", RSP_X + MIC_D[1][1],
         " / Y ", RSP_Y + 15.25, "〜", RSP_Y + 18.75));
echo(str("OLED X ", OLED_X, "〜", OLED_X + OLED_L, " / Y ", OLED_Y, "〜", OLED_Y + OLED_W));

// ============================================================
// 顔 ── 外から見える面だけ。⚠ 形を見るための皮で、柱・締結・グリルの目は無い
// ============================================================
module win_top() {
    ax = OLED_X + (OLED_L - OLED_AA[0]) / 2;
    ay = OLED_Y + OLED_W - OLED_AA_EDGE - OLED_AA[1];
    translate([ax - BEVEL, ay - BEVEL, IN_Z - 1])
        cube([OLED_AA[0] + 2 * BEVEL, OLED_AA[1] + 2 * BEVEL, TOP_T + 2]);
}
module win_mics() for (d = MIC_D)
    translate([RSP_X + d[0] - 1, RSP_Y + 15.25 - 1, IN_Z - 1])
        cube([d[1] - d[0] + 2, 5.5, TOP_T + 2]);
module win_spk() translate([SPK_X, SPK_Y, IN_Z - 1])
    hull() for (sx = [-1, 1]) translate([sx * 4, 0, 0]) cylinder(d = 15, h = TOP_T + 2);
module win_front(x, z, d) translate([x, -FRONT_T - 1, z]) rotate([-90, 0, 0]) cylinder(d = d, h = FRONT_T + 2);

module skin() color("#ded9cf") difference() {
    translate([-WALL, -FRONT_T, -FLOOR_T])
        cube([IN_X + 2 * WALL, IN_Y + FRONT_T + BACK_T, IN_Z + FLOOR_T + TOP_T]);
    cube([IN_X, IN_Y, IN_Z]);
    win_top(); win_mics(); win_spk();
    win_front(KNOB_X, KNOB_Z, 29.0);
    win_front(BTN_X, BTN_Z, 13.0);
    translate([IN_X - 1, 20, 8]) cube([WALL + 2, 9, 3.5]);   // ⚠ 口は 1 つだけ仮に開けた
}
module screen_glass() {
    ax = OLED_X + (OLED_L - OLED_AA[0]) / 2;
    ay = OLED_Y + OLED_W - OLED_AA_EDGE - OLED_AA[1];
    color("#16181c") translate([ax, ay, IN_Z + TOP_T - 0.6]) cube([OLED_AA[0], OLED_AA[1], 0.6]);
}
if (part == "face") {
    skin(); screen_glass();
    translate([KNOB_X, -FRONT_T, KNOB_Z]) rotate([90, 0, 0]) assembly(show_deck = false);
    translate([BTN_X, -FRONT_T, BTN_Z]) rotate([90, 0, 0]) { btn3_piston(); btn3_tub(); }
}
