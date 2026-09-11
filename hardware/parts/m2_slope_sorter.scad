// m2_slope_sorter.scad — M2 のねじを長さで仕分ける皿（2026-09-07 ユーザー案）。
//
// ユーザーの案（2026-09-07 の会話をそのまま）:
//   ・スリットを入れた板の上に、漏斗でねじを落とす → ねじは先を下にしてスリットの中の床に立つ
//   ・スリットの端に送る板を置き、スリットに沿って押して滑らせる
//   ・床がだんだん浅くなるスロープ → 長いねじから先に頭が板の上へ出る → 風で倒す（倒れる場所が長さで決まる）
//   ・選別の区間だけスリットを 12° 傾ける。ねじは +Y の壁に寄りかかり、重心が壁の上端を越える床で倒れる。風は要らない
//
// この CAD で決めた数字（ユーザーが言っていないもの。全部この上の変数で動く）:
//   スリット幅 4.6（頭 3.8 + 0.8）。入れ口の床の深さ 14（一番長い 12 + 頭 1.4 + 余り 0.6 で、全部が板の下に隠れる）。
//   スロープは 60mm で 14 → 2（勾配 1:5。長さが 2 違うと頭の出る位置が 10 ずれる）。
//   送る板は櫛。歯がスリットに入って床に乗り、押すとスロープを登る（歯の底はスロープと同じ角度に削いである）。
//   漏斗は皿に載せたまま、スリットに沿って左右に揺する別部品（2026-09-07 ユーザー「この形状だから左右に振る」）。
//   両端の足がスリットに入って案内になり、口の縁が板の上面に載って滑る。押すときは外す（櫛の柄が当たるため）。
//
//   スロープの床（くさび）は別部品（2026-09-07 ユーザー「スロープ部分はスリットの中に X 方向から入れる」）。
//   皿のスロープ側の端の壁にスリット幅の切り欠きがあり、そこからくさびをスリットの中へ X 方向に差し込む。
//   くさびは皿のポケット（平らなレールの床より 1.5 低い）を滑って X_R0 の段に当たって止まる。始まりの厚み 1.5 で平らなレールと段差なく続く。
//   外の端につまみの板があり、端の壁の外面に当たる。抜け止めは無い（つまみを引けば抜ける）。
//
// part = "base" | "insert" | "funnel" | "pusher" | "asm" | "explode"（分解図: 漏斗と櫛は上へ、くさびは端から X へ） | "secx" | "secy"（床 12 の所の Y-Z 断面）

part = "explode";

// ---- ねじ（📄 JIS B1111 M2 なべ）----
HEAD_D = 3.8; HEAD_H = 1.4; SHANK = 2.0;
LENS = [12, 10, 8, 6, 4];

// ---- 皿 ----
LANES  = 1;            // 2026-09-07 ユーザー「スリットは 1 本でいい」（隣の列に倒れ込むため）
SLIT_W = 4.6;          // 頭 3.8 + 0.8
RIB_W  = 2.0;
WALL   = 5.0;          // 傾けたスリットが 1.6 ずつはみ出すので 3.0 → 5.0
BOT_T  = 3.0;          // ポケットの底の下の肉 1.5 が要るので 3.0
FUN_L  = 15;           // 漏斗の下（床が平ら・深さ D_DEEP）。2026-09-07 ユーザー「ロートは小さくていい」で 30 → 15
FLAT_L = 41;           // 漏斗とスロープのあいだの、何も無い平らなレール（2026-09-07 ユーザー「ロートとスロープの間に何もない空間が要る」）。頭 3.8 で 10 本。全長 141 で LCD 143.4 に収める
LOAD_L = FUN_L + FLAT_L;   // 平らな床の全長 66。全長 140 で Mars 3 の LCD 143.4 に収める
// スロープは階段（2026-09-07 ユーザー「ねじ高さ 2mm ごとにフロアが欲しい」）。
// 床の深さ ＝ 床からの壁の高さ。倒れるかは重心（先から ×12 8.0・×10 6.9・×8 5.8・×6 4.7・×4 3.5）が壁より上かで決まるので、
// 隣り合う長さの重心の中間に置く（2026-09-07 の静力学の計算。余裕 ±0.55）。ユーザー了承「お願いします」
STEP_D  = [7.45, 6.37, 5.26, 4.10, 1.75];   // 床の深さ（板の上面から）。担当 12・10・8・6・4
FLOOR_L = 8;                   // 床の長さ
RISE_L  = 4;                   // 床から次の床への登りの長さ（2 上がる）
RISE0_L = 13;                  // 平らなレール（14）から最初の床（7.45）への登り（6.55 上がる・27°）
FLOOR_TILT = 0;                // 床だけの Y の傾き。スリットごと傾けるので 0
SLIT_TILT  = 12;               // 選別の区間（X_R0 から先）だけ、スリットを床・壁ごと Y に傾ける（2026-09-07 ユーザー「スリットを傾けて置いたらいい」「選別範囲に入ったら」）。
                               // 受けの側（+Y）が低い。5° では ×8 以下が先の平ら φ1.2 の上に立ったままになる計算。12° で全部が壁へ寄りかかる。
                               // 回す軸はスリットの −Y の面・高さの真ん中。上の口は +Y へ 1.6 ずれ、ポケットの底は −Y へ 1.6 ずれる
TRANS_L    = 20;               // レールの最後で、スリットが 0° → SLIT_TILT へ連続にねじれる区間（2026-09-07 ユーザー「なめらかに移行しないと入らない」）
TRANS_N    = 16;               // ねじれの区間を刻む数（hull で繋ぐ）
RAMP_L = RISE0_L + FLOOR_L + (len(STEP_D) - 1) * (RISE_L + FLOOR_L);   // 58
END_L  = 6;            // スロープの先の平ら（深さ D_SHALLOW）。くさびの一部
POCKET_DZ = 1.5;       // くさびが載るポケットは平らなレールの床より 1.5 低い（くさびの始まりの厚み）
INS_GAP = 0.15;        // くさびとスリットの片側・端の隙間
GRIP_T = 2.0; GRIP_H = 8; GRIP_W = SLIT_W + 6;   // つまみの板（端の壁の外）
D_DEEP = 14.0;         // 入れ口の床の深さ（板の上面から）
D_SHALLOW = STEP_D[len(STEP_D) - 1];   // 最後の床の深さ（5）。先の平らもこの深さ

IW  = LANES * SLIT_W + (LANES - 1) * RIB_W;   // 31
W   = IW + 2 * WALL;                           // 35
L   = 2 * WALL + LOAD_L + RAMP_L + END_L;      // 102
Z_T = BOT_T + D_DEEP;                          // 15.5 板の上面
X_R0 = WALL + LOAD_L;                          // スロープの始まり
X_R1 = X_R0 + RAMP_L;                          // スロープの終わり
SLOPE = atan((D_DEEP - STEP_D[0]) / RISE0_L);   // 一番急な登りの角度 27°（櫛の歯の底を削ぐ角度）
function lane_y(j) = WALL + SLIT_W / 2 + j * (SLIT_W + RIB_W);
// 階段の断面（X → 深さ）。頂点の列 [x, depth]
function step_pts() = concat([[X_R0, D_DEEP]],
    [for (i = [0 : len(STEP_D) - 1]) each
        [[X_R0 + (i == 0 ? RISE0_L : RISE0_L + FLOOR_L + (i - 1) * (RISE_L + FLOOR_L) + RISE_L), STEP_D[i]],
         [X_R0 + RISE0_L + FLOOR_L + i * (RISE_L + FLOOR_L), STEP_D[i]]]]);
function floor_d_at(pts, x, i = 0) = i >= len(pts) - 1 ? pts[len(pts) - 1][1]
    : x <= pts[i][0] ? pts[i][1]
    : x <= pts[i + 1][0] ? pts[i][1] + (pts[i + 1][1] - pts[i][1]) * (x - pts[i][0]) / (pts[i + 1][0] - pts[i][0])
    : floor_d_at(pts, x, i + 1);
function floor_d(x) = x < X_R0 ? D_DEEP : x > X_R1 ? D_SHALLOW : floor_d_at(step_pts(), x);
function floor_x(i) = X_R0 + RISE0_L + FLOOR_L / 2 + i * (RISE_L + FLOOR_L);   // i 番目の床の中央

// ---- 倒れたねじを受ける斜面（+Y 側）----
//   板の上面から下り、下端に縁は無い。ねじは斜面を滑って先から落ちる（2026-09-07 ユーザー「下に箱を置くから普通に落としていい」）
//   床ごとの仕切りで、落ちる位置が長さで分かれたまま先まで行く
CATCH_W   = 25;        // 斜面の幅（Y）
CATCH_ANG = 20;        // 斜面の角度
CATCH_X0  = WALL + FUN_L;        // 斜面の始まり（漏斗の先から）
DIV_T     = 1.2;       // 仕切りの厚み。登りの真ん中に立てる。0 で無し
function div_x(i) = i == 0 ? X_R0 + RISE0_L - 2 : X_R0 + RISE0_L + FLOOR_L + (i - 1) * (RISE_L + FLOOR_L) + RISE_L / 2;   // 床 i の手前の仕切り

// ---- 櫛（送る板）----
TOOTH_W = 2.5;         // 歯の幅。傾いたスリット（横幅 4.7・1mm 上がるごとに 0.21 ずれる）に高さ 9.5 の縦の歯が入る幅
TOOTH_T = 2.0;         // 歯の厚み（X）
PUSH_H  = 12;          // 板の上に出る柄の高さ
PUSH_REACH = 9.5;      // 歯が板の上面から届く深さ。レールで ×4 の頭の上面は 8.6 なので 0.9 かかる。傾いた区間で歯が壁に当たらない上限

// ---- 漏斗 ----
FUN_H = 18;            // 漏斗の高さ（口の上から）
FUN_TOP = [32, 24];    // 上の口
FUN_T = 1.5;
SPOUT_H = 4;           // 位置決めの足がスリットに入る深さ

$fn = 48;
echo(str("slope_sorter: base ", L, " x ", W, " (+catch ", CATCH_W, ") x ", Z_T, "  steps ", step_pts()));

// スリット 1 本ぶんの空間（床は平ら → スロープ → 平ら）
PZ = Z_T - D_DEEP - POCKET_DZ;              // ポケットの底
TILT_PZ = (PZ + Z_T) / 2;                    // 傾ける軸の高さ（スリットの高さの真ん中）
module tilt_frame(j, ang = SLIT_TILT) translate([0, lane_y(j) - SLIT_W / 2, TILT_PZ]) rotate([-ang, 0, 0]) translate([0, -(lane_y(j) - SLIT_W / 2), -TILT_PZ]) children();
module twist_slice(j, x, ang) tilt_frame(j, ang) translate([x, lane_y(j) - SLIT_W / 2, Z_T - D_DEEP]) cube([0.01, SLIT_W, D_DEEP + 12]);
module slit_void(j) {
    yc = lane_y(j);
    // 平らなレール（漏斗の下＋空き）: 床 D_DEEP。最後の TRANS_L はねじれの区間
    xt = X_R0 - TRANS_L;
    translate([0, yc - SLIT_W / 2, 0]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(SLIT_W)
        polygon([[WALL, Z_T - D_DEEP], [xt + 0.01, Z_T - D_DEEP], [xt + 0.01, Z_T + 1], [WALL, Z_T + 1]]);
    // ねじれの区間: 断面（幅 SLIT_W・床 D_DEEP）を軸まわりに少しずつ回した薄い板を hull で繋ぐ
    for (k = [0 : TRANS_N - 1]) hull() {
        twist_slice(j, xt + k * TRANS_L / TRANS_N, SLIT_TILT * k / TRANS_N);
        twist_slice(j, xt + (k + 1) * TRANS_L / TRANS_N, SLIT_TILT * (k + 1) / TRANS_N);
    }
    // 選別の区間: ポケット（床 PZ）を床・壁ごと SLIT_TILT 傾ける。端の壁を抜けて外へ開く（くさびの差し込み口）
    tilt_frame(j) translate([0, yc - SLIT_W / 2, 0]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(SLIT_W)
        polygon([[X_R0, PZ], [L + 1, PZ], [L + 1, Z_T + 12], [X_R0, Z_T + 12]]);
}

W_ALL = W + CATCH_W;
CATCH_DROP = CATCH_W * tan(CATCH_ANG);
module base() {
    difference() {
        cube([L, W, Z_T]);
        for (j = [0 : LANES - 1]) slit_void(j);
    }
    // 受けの斜面: 板の上面から +Y へ下る。断面（Y-Z）を X に伸ばす。縁は無し
    translate([CATCH_X0, 0, 0]) rotate([90, 0, 90]) linear_extrude(L - CATCH_X0)
        polygon([[W - 0.01, 0], [W - 0.01, Z_T], [W + CATCH_W, Z_T - CATCH_DROP], [W + CATCH_W, 0]]);
    // 仕切り: 床ごとの区画。上面は板の上面と同じ高さ
    if (DIV_T > 0) for (i = [0 : len(STEP_D) - 1])
        translate([div_x(i) - DIV_T / 2, W - 0.01, 0]) cube([DIV_T, CATCH_W + 0.01, Z_T]);
}

// くさび: 原点 = 皿側の端・スリットの −Y の面・ポケットの底
IL = L - X_R0 - INS_GAP;   // 皿の中 (L - WALL - X_R0) + 端の壁 WALL、隙間ぶん短く
module insert() {
    // 断面を Y に伸ばし、Z を Y でずらす（せん断）と、床と登りが +Y へ向かって FLOOR_TILT だけ下がる。立った面はそのまま。底は平らに切り直す
    difference() {
        multmatrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, -tan(FLOOR_TILT), 1, 0], [0, 0, 0, 1]])
            translate([0, INS_GAP, 0]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(SLIT_W - 2 * INS_GAP)
                polygon(concat([[0, -1], [IL, -1], [IL, POCKET_DZ + D_DEEP - D_SHALLOW]],
                               [for (i = [len(step_pts()) - 1 : -1 : 0]) [step_pts()[i][0] - X_R0, POCKET_DZ + D_DEEP - step_pts()[i][1]]]));
        translate([-1, -1, -5]) cube([IL + GRIP_T + 2, SLIT_W + 2, 5]);
    }
    // つまみ: 端の壁の外面に当たる板
    translate([IL, SLIT_W / 2 - GRIP_W / 2, 0]) cube([GRIP_T, GRIP_W, POCKET_DZ + D_DEEP - D_SHALLOW + GRIP_H]);
}
module insert_in_place(pull = 0) tilt_frame(0) translate([X_R0 + INS_GAP + pull, lane_y(0) - SLIT_W / 2, PZ]) insert();

module pusher() {
    // 柄: 板の上面より上に横一文字。歯: 各スリットに下りて床の手前 PUSH_GAP まで
    translate([0, 0, Z_T]) cube([TOOTH_T, W, PUSH_H]);
    for (j = [0 : LANES - 1])
        translate([0, lane_y(j) - TOOTH_W / 2, Z_T - PUSH_REACH])
            difference() {
                cube([TOOTH_T, TOOTH_W, PUSH_REACH + 0.01]);
                // 歯の底をスロープの角度に削ぐ（前へ進むほど床が上がる）
                translate([0, -1, 0]) rotate([0, -SLOPE, 0]) translate([0, 0, -10]) cube([TOOTH_T * 2, TOOTH_W + 2, 10]);
            }
}

module funnel() {
    // 皿に載せたまま、スリットに沿って左右に揺する漏斗（2026-09-07 ユーザー「ロートも振れない」「小さくていい」「この形状だから左右に振る」）。
    // 底の口はスリットと同じ幅で、板の上面に載って滑る。両端の足（幅 4.2）がスリット（4.6）に入って案内になる
    mouth = [FUN_L, SLIT_W];
    translate([WALL + FUN_L / 2, lane_y(0), Z_T]) {
        difference() {
            frustum([mouth[0] + 2 * FUN_T, mouth[1] + 2 * FUN_T], FUN_TOP, FUN_H);
            translate([0, 0, -0.01]) frustum(mouth, [FUN_TOP[0] - 2 * FUN_T, FUN_TOP[1] - 2 * FUN_T], FUN_H + 0.02);
        }
        for (sx = [-1, 1]) translate([sx * (mouth[0] / 2 - 1.0) - 1.0, -(SLIT_W - 0.4) / 2, -SPOUT_H]) cube([2.0, SLIT_W - 0.4, SPOUT_H + 0.01]);
    }
}
module frustum(b, t, h) hull() {
    translate([-b[0] / 2, -b[1] / 2, 0]) cube([b[0], b[1], 0.01]);
    translate([-t[0] / 2, -t[1] / 2, h - 0.01]) cube([t[0], t[1], 0.01]);
}

// 絵のねじ（先を床に付けて立つ）。原点 = 先
module screw(len) color("#c8a030") { cylinder(d = SHANK, h = len); translate([0, 0, len]) cylinder(d = HEAD_D, h = HEAD_H); }

// ex = 分解の度合い（0 = 組んだ姿・1 = 分解図）。漏斗は上へ、櫛は上へ、くさびは端から X へ
module scene(with_funnel = true, pusher_x = X_R0 - 12, pull = 0, ex = 0) {
    color("#b8c4d0") base();
    color("#9fb8a0") insert_in_place(pull + ex * 45);
    if (with_funnel) color("#d0d8e0", ex > 0 ? 0.9 : 0.25) translate([0, 0, ex * 25]) funnel();
    color("#e0a0a0") translate([pusher_x, 0, D_DEEP - floor_d(pusher_x) + ex * 22]) pusher();
    // 各長さのねじを「頭が板の上面に出る所」に立てる（床の深さ = 長さ + 頭）
    for (i = [0 : len(LENS) - 1], j = [0 : LANES - 1]) {
        x = floor_x(i);
        tilt_frame(j) translate([x, lane_y(j) + SLIT_W / 2 - 1.0, Z_T - floor_d(x)]) screw(LENS[i]);   // +Y の壁に寄りかかった位置
    }
    // 受けのスロープの縁に、倒れて滑り落ちたねじ（長さ順のまま）
    // 斜面を滑っているねじ: 先は上、頭は下。軸は斜面と平行で、頭の半径 1.9 だけ浮かせる
    for (i = [0 : len(LENS) - 1])
        translate([floor_x(i), W + 6, Z_T - 6 * tan(CATCH_ANG) + HEAD_D / 2]) rotate([-CATCH_ANG, 0, 0]) rotate([-90, 0, 0]) screw(LENS[i]);
    // 入れ口に何本か
    for (k = [0 : 3]) translate([WALL + 12 + k * 4.5, lane_y(0), Z_T - D_DEEP]) screw(LENS[(k + 1) % 5]);
}

if (part == "base")   base();
if (part == "insert") insert();
if (part == "funnel") funnel();
if (part == "explode") scene(ex = 1);
if (part == "sim_static") { base(); insert_in_place(); }   // 物理エンジン用: 皿とくさびを 1 つに
if (part == "secy")   intersection() { scene(with_funnel = false, pusher_x = L + 10); translate([-1, -1, -1]) cube([floor_x(0) + 1, W_ALL + 2, 60]); }
if (part == "pusher") pusher();
if (part == "asm")    scene();
if (part == "secx")   intersection() { scene(with_funnel = false); translate([-5, lane_y(0) - 50, -1]) cube([L + 10, 50, 60]); }
