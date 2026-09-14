// ============================================================
// 筐体 v6 — 配置（ブロック）
//   方針（ユーザー 2026-09-12）: 全リニューアル。部品をブロックとして置き直す所からやる。
//   数字と向きの正は docs/CASE-V6-PLAN.md。v5 のファイルは読まない（座標を写さない）。
//   この版はまだ**実測の直方体を置いただけ**で、皮・柱・口・線・締結は無い。当たり検査も無い。
//
//   実行:
//     "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o x.png -D "part=\"look\"" hardware/case_v6.scad
//
//   part の値:
//     look   … 中身ぜんぶ（ブロック 4 つ＋段＋電池＋操作部）。内寸の箱は輪郭だけ
//     blocks … ブロック 4 つだけ（OLED・ReSpeaker・ハブ・電源板）
//     front  … 前から見た絵（顔の窓と充電の口の位置を見る）
//     side   … 左半分の側面（前から後ろへの断面の代わり。高さの鎖を見る）
//     （語を足すときはここへ書く。既にある語の意味は変えない）
// ============================================================
part = "look";

use <../../parts/parts.scad>
$fn = 48;

// ---- 箱の中の座標 ----
//   X 0 = 左の壁の内面 ／ Y 0 = 前の壁の内面 ／ Z 0 = 床の上面
//   +X 右（XIAO の USB-C 側）・+Y 後ろ（ハッチ側）・+Z 上（天面）
IN_X = 88.0;
IN_Y = 74.0;
IN_Z = 40.0;

WALL = 2.0;
PORT_BACK = 0.8;   // 口の面を壁の外面の何 mm 裏に置くか。🔒 1.6 裏は実機で挿さらなかった（2026-09-11）

// ---- OLED HS154L03W2C01（📄 hardware/ref/oled_hs154l03w2c01/）----
//   42.40 が横・38.00 が縦。ガラス面が前。🔒 顔は左（ユーザー 2026-09-12）
OLED_L  = 42.40;
OLED_H  = 38.00;
OLED_T  =  2.65;
OLED_X  =  1.0;
OLED_Z  =  1.0;
OLED_AA = [35.05, 17.52];
OLED_AA_EDGE = 8.15;   // 📄 端子側の縁から AA まで。反対側は 12.33（FPC の折り返し）
OLED_PIN_EDGE = 2.50;  // 📄 端子の列から、その縁まで
OLED_PIN_N = 4;
// ⚠ 私が置いた前提①: 端子を**上**の縁へ（窓が高くなる側。下にすると窓は Z 9.2〜26.7）
OLED_PIN_TOP = true;
// ⚠ 私が置いた前提③: L 字の 4 ピンヘッダ。ピンは列と直交する向きに曲がるので**上下（Z）へ出る**。
//    端子が上なので下向きに出す。縁の外へ ピン 6 ＋ ハウジング 14 ＋ 逃げ 3.6 = 23.6（parts.scad の as5600(ra=true) と同じ数え方）
OLED_RA_OUT = 23.6;
OLED_RA_T   =  4.0;   // 板の裏から出る量（L 字にするとここが 17 → 4 になる）

// ---- ReSpeaker Lite（📄 docs/RESPEAKER-LITE.md 5.6 公式 CAD）----
//   立てる。マイク面が前・XIAO 面が後ろ。XIAO は箱の +X 側に来る
RSP_L = 82.024;
RSP_H = 34.007;
RSP_T =  1.85;
RSP_Z =  2.5;                                   // 半田面の逃げ
XIAO_USB_OUT = 1.53;                            // 📄 板の端からの張り出し
RSP_X = IN_X + WALL - PORT_BACK - XIAO_USB_OUT - RSP_L;   // 右端の口を壁に合わせて左端が決まる
RSP_Y = 8.2;                                    // マイク面の Y
JACK_OUT = 1.576;                               // 📄 3.5mm ジャックの筒が左端から出る量
HDR_OUT  = 13.9;                                // ✅ XIAO 面のヘッダ＋線（ユーザー 2026-08-24）

// ---- ハブ基板（hardware/parts/hub_board_parts.scad）----
HUB_L = 74.0;
HUB_W = 52.0;
HUB_T =  1.6;
HUB_X = (IN_X - HUB_L) / 2;
HUB_Y = 15.9;
HUB_Z =  2.5;
HUB_PLUG_TOP = 23.1;   // 床から、口の曲がりの頭まで（樹脂 2.5 ＋ ハウジング 14 ＋ 曲がり 3.0）

// ---- 電源板（docs/POWER.md 案③）----
//   前の壁に立てる。部品面が後ろ。充電の USB-C は右の縁で、板から 3.0 出る
PWR_L = 40.0;
PWR_H = 32.0;
PWR_T =  1.6;
PWR_PARTS_T = 6.4;
PWR_Z = 1.0;
USBC_OUT = 3.0;
PWR_X = IN_X + WALL - PORT_BACK - USBC_OUT - PWR_L;
USBC_FROM_END = 10.0;   // 📄 32 の縁の端から、口の芯まで
USBC_W = 8.94;
USBC_T = 3.16;

// ---- 段と電池 ----
TRAY_T = 2.0;
TRAY_Z = HUB_PLUG_TOP;
BAT_X = 12.0;
BAT_Y = 13.9;
BAT_Z = TRAY_Z + TRAY_T;

// ---- 天板から下がる操作部（🔒 ユーザー 2026-09-08 の席）----
ROW_Y  = 17.3;
ROW_RX = 64.7;
SPK_X  = 19.0;
KNOB_Y = 41.8;
TGL_FROM_TOP = 7.1;
TOP_T = 2.5;
// つまみの AS5600 のヘッダ。false = 直立て ／ true = L 字（ユーザー 2026-09-12 の提案）
KNOB_HDR_RA = false;
// 天板の外面から下への鎖（knob_v5 の Z_PCB_BOT と plug.scad）:
//   基板の裏 19.7 ＋ 直立てなら 樹脂 2.5 ＋ ハウジング 14 ＝ 16.5 ／ L 字なら樹脂まわり 約 4
//   🔴 22.4（バスタブ 2 の板の裏）はヘッダを含まない。2026-09-12 にここを 22.4 で描いて 11.3 浅くしていた
KNOB_PCB_BOT = 19.7;
KNOB_HDR_DEEP = KNOB_HDR_RA ? 4.0 : 2.5 + 14.0;
KNOB_DEEP = KNOB_PCB_BOT + KNOB_HDR_DEEP - TOP_T;   // 内側の天井から下への深さ
KNOB_RA_OUT = 23.6;   // L 字のとき基板の縁の外へ出る量（片側・ピン 6 ＋ ハウジング 14 ＋ 逃げ 3.6）
AS5600_PCB = 23.0;

// ============================================================
module box_outline() {
    difference() {
        cube([IN_X, IN_Y, IN_Z]);
        translate([1, 1, 1]) cube([IN_X - 2, IN_Y - 2, IN_Z - 2]);
    }
}

module oled_block() {
    color("#7f77dd") translate([OLED_X, 0, OLED_Z]) cube([OLED_L, OLED_T, OLED_H]);
    // 窓（AA）。42.40 の方向は中央・38.00 の方向は端子側の縁から OLED_AA_EDGE
    aa_x = OLED_X + (OLED_L - OLED_AA[0]) / 2;
    aa_z = OLED_PIN_TOP ? OLED_Z + OLED_H - OLED_AA_EDGE - OLED_AA[1]
                        : OLED_Z + OLED_AA_EDGE;
    color("#2c2c2a") translate([aa_x, -0.4, aa_z]) cube([OLED_AA[0], 0.4, OLED_AA[1]]);
    // 端子 4 本（φ1.0・2.54 ピッチ・列は 42.40 の方向の中央）と、L 字の包絡
    pin_z = OLED_PIN_TOP ? OLED_Z + OLED_H - OLED_PIN_EDGE : OLED_Z + OLED_PIN_EDGE;
    span  = (OLED_PIN_N - 1) * 2.54;
    pin_x = OLED_X + OLED_L / 2 - span / 2;
    for (i = [0 : OLED_PIN_N - 1])
        color("#bba") translate([pin_x + i * 2.54, OLED_T, pin_z]) rotate([-90, 0, 0]) cylinder(d = 1.0, h = OLED_RA_T);
    ra_z0 = OLED_PIN_TOP ? pin_z - OLED_RA_OUT : pin_z;
    color("#85b7eb", 0.45) translate([pin_x - 1.27, OLED_T, ra_z0]) cube([span + 2.54, OLED_RA_T, OLED_RA_OUT]);
}

module respeaker_block() {
    color("#1d9e75") translate([RSP_X, RSP_Y, RSP_Z]) cube([RSP_L, RSP_T, RSP_H]);
    // 右端の XIAO の USB-C（壁を貫く）と、左端の 3.5mm ジャックの筒
    color("#85b7eb") translate([RSP_X + RSP_L, RSP_Y + RSP_T / 2 - 1.6, RSP_Z + RSP_H / 2 - 4.47])
        cube([XIAO_USB_OUT + WALL, 3.2, 8.94]);
    color("#85b7eb") translate([RSP_X - JACK_OUT, RSP_Y + RSP_T / 2, RSP_Z + 6.502])
        rotate([0, -90, 0]) cylinder(d = 5.45, h = JACK_OUT + WALL);
    // XIAO 面のヘッダ＋線の層（📄 左から 2.932〜18.172 のパッド列。マイク面を前にすると箱の +X 側へ回る）
    hx0 = RSP_X + RSP_L - 18.172;
    color("#9fe1cb", 0.45) translate([hx0, RSP_Y + RSP_T, RSP_Z + 8.1]) cube([15.24, HDR_OUT, 20.8]);
    // 🔒 マイク 2 個（📄 公式 CAD: U4 左から 4.16〜6.81・U5 左から 75.16〜77.81・どちらも下から 15.25〜18.75）。
    //    塞いだら音が死ぬ場所。マイク面を前にすると「左から」は箱の +X 側から数える向きになる
    for (d = [[4.16, 6.81], [75.16, 77.81]])
        color("#e24b4a") translate([RSP_X + RSP_L - d[1], RSP_Y - 1.28, RSP_Z + 15.25])
            cube([d[1] - d[0], 1.28, 3.5]);
}

module hub_block() {
    color("#d85a30") translate([HUB_X, HUB_Y, HUB_Z]) cube([HUB_L, HUB_W, HUB_T]);
    // 口の層（口 8 つは全部上向き。曲がりの頭まで床から HUB_PLUG_TOP）
    color("#f0997b", 0.35) translate([HUB_X, HUB_Y, HUB_Z + HUB_T])
        cube([HUB_L, HUB_W, HUB_PLUG_TOP - HUB_Z - HUB_T]);
}

module power_block() {
    color("#993c1d") translate([PWR_X, 0, PWR_Z]) cube([PWR_L, PWR_T, PWR_H]);
    color("#f0997b", 0.35) translate([PWR_X, PWR_T, PWR_Z]) cube([PWR_L, PWR_PARTS_T, PWR_H]);
    // 充電の USB-C（右の縁・32 の縁の下の端から 10・板から USBC_OUT 出て壁を貫く）
    color("#378add") translate([PWR_X + PWR_L, PWR_T, PWR_Z + USBC_FROM_END - USBC_W / 2])
        cube([USBC_OUT + WALL, USBC_T, USBC_W]);
}

module tray_and_battery() {
    color("#b4b2a9", 0.5) translate([HUB_X + 2, BAT_Y - 1, TRAY_Z]) cube([HUB_L - 4, 54, TRAY_T]);
    color("#ef9f27") translate([BAT_X, BAT_Y, BAT_Z]) cube([lipo_size()[1], lipo_size()[0], lipo_size()[2]]);
}

module deck_parts() {
    // スピーカー（天板の裏・振動面が上）
    color("#534ab7") translate([SPK_X - 11.5, ROW_Y - 7.5, IN_Z - 5.5]) cube([23, 15, 5.5]);
    // 会話ボタン（天板・押しは縦）
    color("#534ab7") translate([ROW_RX - 6.4, ROW_Y - 2.9, IN_Z - 6.5]) cube([12.8, 5.8, 6.5]);
    // つまみの柱（天板から下へ KNOB_DEEP。AS5600 の板 23 角＋逃げ）
    color("#afa9ec", 0.6) translate([ROW_RX - 12, KNOB_Y - 12, IN_Z - KNOB_DEEP]) cube([24, 24, KNOB_DEEP]);
    // トグル MTS-102（ハッチ・軸は水平・後ろ向き。内側に mts102_deep()）
    color("#26215c") translate([ROW_RX - mts102_w() / 2, IN_Y - mts102_deep(), IN_Z - TGL_FROM_TOP - mts102_d() / 2])
        cube([mts102_w(), mts102_deep(), mts102_d()]);
    // リードスイッチ（つまみの脇・軸は水平）
    color("#26215c") translate([ROW_RX + 14, KNOB_Y - 7, IN_Z - 9]) cube([3.2, 14, 3.2]);
}

module blocks_only() {
    oled_block();
    respeaker_block();
    hub_block();
    power_block();
}

if (part == "blocks") {
    blocks_only();
    %box_outline();
} else if (part == "look" || part == "front" || part == "side") {
    blocks_only();
    tray_and_battery();
    deck_parts();
    %box_outline();
} else {
    echo(str("🔴 part の値が不明: ", part));
}

echo(str("内寸 ", IN_X, " x ", IN_Y, " x ", IN_Z, " = ",
         IN_X * IN_Y * IN_Z / 1000, "cm3"));
echo(str("ReSpeaker 左端 ", RSP_X, " / XIAO の口の面 ", RSP_X + RSP_L + XIAO_USB_OUT,
         " / ジャックの筒の先 ", RSP_X - JACK_OUT));
echo(str("電源板 X ", PWR_X, "〜", PWR_X + PWR_L, " / 充電の口の面 ", PWR_X + PWR_L + USBC_OUT));
echo(str("顔と電源板のすき間 ", PWR_X - (OLED_X + OLED_L)));
echo(str("窓 X ", OLED_X + (OLED_L - OLED_AA[0]) / 2, "〜", OLED_X + (OLED_L + OLED_AA[0]) / 2,
         " / Z ", OLED_PIN_TOP ? OLED_Z + OLED_H - OLED_AA_EDGE - OLED_AA[1] : OLED_Z + OLED_AA_EDGE,
         "〜", OLED_PIN_TOP ? OLED_Z + OLED_H - OLED_AA_EDGE : OLED_Z + OLED_AA_EDGE + OLED_AA[1]));
