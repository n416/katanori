// m2_lean_sieve.scad — M2 のねじを長さで分ける「寄りかかりのふるい」＋ ねじを装填する帯（2026-09-10）。
//   出発点はユーザーの言葉（2026-09-10）: 「振れば小さいのは下に落ちるでしょ？特定の長さが残るふるいを作れればそれで解決」
//   「なんで転がさないとふるいにかけられないのか。傾くから。なら整列させればいい」「摩擦を減らせばいいのなら微振動かければいい」。
//   ふるいの形は私（AI）が引いた。整列した列（頭が上）から 2mm 刻みで抜き出すのに、頭を浮かせて上で分ける形は頭 1.4 対 刻み 2.0 で窓が 0.6 しか無く閉じた。
//   開いたのは「寝かせて 2 点で支える」形: 頭を片側の縁に、軸を向かいの低い庇（lip）に寄りかからせ、庇までの距離 w を樋に沿って
//   1:7 で広げる。自分の長さで庇に届かなくなった所で、そのねじだけが落ちる。ふるいの目が「穴の径」ではなく「庇までの距離」になった物。
//
//   帯（belt）: 2026-09-10 ユーザー「銃の弾をベルトで巻くやつのイメージで、このふるいの上でネジをスライドさせるためのベルト」「間隔 6・厚み 1.0で一旦やってみよ。3つくらいでいいよ装填数」
//   「ネジは帯に圧入されていて、スリットにいれると外れるが、垂直に（立ったまま水平に）押されていくみたいな感じにしないと」:
//     帯は 2 層。下 0.5 は軸を受ける U の切り欠き（幅 2.4・奥 1.5。口の角に丸い当たりを付けて口を 1.9 に絞る＝圧入）、上 0.5 は頭を囲む半円の受け（r 2.0）。
//     頭は下の層の肩に乗り、口の絞りで軸が抜けない。手に持ったまま 3 本入る。
//     樋の入り口 15 に「外す坂」（帯の下を走る固定の肋。軸を庇側へ押して口の絞りを越えさせる）。外れた頭は帯の縁と向かいの縁に乗って垂直に吊られ、
//     上の層の受けの後ろの壁が頭を押して進む。その先で向かいの縁が庇に下がり、寄りかかって落ちる。
//     私が足した物: ①外す坂 ②縁側の壁 4.0 と深さ 2.5 の溝（帯の外側 2.5 が溝、内側 1.5 が樋の上）。縁（帯の床）は無し（軸が帯の下に出るので）
//     ③帯の長さ 130（受け 18 + 尻尾 112。尻尾を押して送る。受け 3 つ目が ×15 の線を越えるまで押せる） ④出口の壁に帯の通り穴 ⑤入り口の上の橋（左右の壁を繋ぐ）
//     圧入の当たり 0.1（口 1.9 に軸 2.0）は樹脂の弾性を見ていない私の仮の数字。
//
// 数字（📄 JIS B1111 M2 なべ: 軸 φ2.0・頭 φ3.8 × 1.4。手元の実測は無い）:
//   落ちる w（庇の深さ 3.0）: 支えは「頭の下面が帯の縁（受けの口の角 X ±1.2）に乗り、先端が庇の上面に乗る」の 2 点。
//     頭の接点は軸から 1.47（= √(1.9² − 1.2²)）なので、接点から先端までは常に √(1.47² + L²)。先端が深さ 3.0 の庇に着く横位置は √(L² + 1.47² − 3²):
//     ×4 3.03 / ×6 5.41 / ×8 7.56 / ×10 9.65 / ×12 11.71 / ×15 14.78   — 長さ 2mm 差で w が 2.1〜2.4 ずれる
//   庇の深さ 3.0 は ×4 が入り口（w 2.5）で支えられるための数字。
//   庇の幅 2.0: 庇の上の壁の面を w + 2.0 に置き、寄りかかった頭（×4 が最も立つ）が壁に当たらないように。
//   樋の全長 = 外す坂 15 + 受け渡し 10 + ふるい 91（w 2.5 → 15.5 ÷ 1/7）= 116。帯 130。Mars 3 の LCD 143.4 に入る。
//   縁側の壁の上面に、落ちる X ごとに溝 1 本（幅 0.5・深さ 0.4。2026-09-10 ユーザー「線だけ書いておいて」）。
//   微振動と樋の傾きはこの部品に無い。刷り方は未決。桶は無し（2026-09-10 ユーザー「ひとまずは桶なしで良い」）。
//
// part = "trough"（樋。使う向き） | "belt"（帯。上を上） | "belt_loaded"（帯に ×6 を 3 本装填した絵）
//      | "asm"（帯を差した姿。1 本目は帯に持たれたまま、3 本目は外れて向かいの縁に乗る） | "sec"（SEC_X の Y-Z 断面。帯は SEC_X が 3 本目の受けの中心に来る位置）
//      | "look"（×6 を w=4.0 に寄りかからせた絵）

part = "trough";
SEC_X = 0;         // "sec" の断面の位置（X）。0 = 帯に持たれている / 15 = 外れた / 35.5 = w 4.0 で寄りかかる（×6）

// ---- ねじ（📄）----
HEAD_D = 3.8; HEAD_H = 1.4; SHANK = 2.0;

// ---- 帯 ----
BELT_T   = 1.0;    // 帯の厚み（ユーザー 2026-09-10）
LOW_T    = 0.5;    // 下の層（軸の U・頭が乗る肩）
PITCH    = 6.0;    // 受けの間隔（ユーザー 2026-09-10）
N_POCKET = 3;      // 装填数（ユーザー 2026-09-10）
NOTCH_W  = 2.4;    // 軸の U の幅
NOTCH_D  = 1.5;    // 軸の U の奥（縁から）。軸の中心は縁から 0.3 内側
MOUTH_W  = 1.9;    // U の口（圧入。軸 2.0 に当たり 0.1）
BUMP_R   = (NOTCH_W - MOUTH_W) / 2;   // 0.25 口の当たり（丸）
POCKET_R = 2.0;    // 頭の受け（上の層の半円。頭 3.8 に 0.2）
SHANK_Y  = -(NOTCH_D - NOTCH_W / 2);  // -0.3 装填時の軸の中心（帯の縁を Y 0）
SLOT_D   = 2.5;    // 溝の深さ（壁の面から外へ）
BELT_IN  = 1.5;    // 帯の、壁の面から内側に出る幅
BELT_W   = SLOT_D + BELT_IN;          // 4.0
BELT_L   = 130;    // 帯の全長（受け 18 + 尻尾）
BELT_FIT = 0.15;   // 溝との見込み（厚み・幅）

// ---- 樋 ----
W0      = 2.5;     // 入り口の縁〜庇の距離
W1      = 15.5;    // 出口の縁〜庇の距離（×15 が 14.78 で落ちる）
TAPER   = 7;       // 広がり 1:7
LIP_DROP= 3.0;     // 庇の深さ（頭の座面 → 庇の上面）
LIP_W   = 2.0;     // 庇の幅（庇の縁 → 壁の面）
SLIT_W  = 2.4;     // 吊りの区間の、帯の縁から向かいの縁までの幅
LEAD_R  = 15;      // 外す坂の区間（向かいの縁は座面の高さ）
LEAD_T  = 10;      // 受け渡しの区間（向かいの縁が LIP_DROP 下がって庇になる）
SIEVE_L = (W1 - W0) * TAPER;     // 91
L_TOT   = LEAD_R + LEAD_T + SIEVE_L;  // 116
PLATE_T = 0.8;     // 庇の厚み
WALL    = 1.5;
WALL_N  = SLOT_D + 1.5;               // 4.0 縁側の壁
GUIDE_H = 4.0;
SLOT_Z  = LIP_DROP + PLATE_T + 1.5 - LOW_T;   // 4.8 溝の床（帯の下面）
SEAT_Z  = SLOT_Z + LOW_T;             // 5.3 頭の座面（帯の下の層の上面 ＝ 向かいの縁の上面）
LIP_Z   = SEAT_Z - LIP_DROP;          // 2.3 庇の上面
TOP_Z   = SLOT_Z + BELT_T + GUIDE_H;  // 9.8
Y_WALL  = -BELT_IN;                   // -1.5 縁側の壁の面（帯の縁が Y 0）
Y_NEAR  = Y_WALL - WALL_N;            // -5.5 外形（縁側）
Y_OUT   = W1 + LIP_W + WALL;          // 19.0 外形（庇側）
RAMP_Z0 = SLOT_Z - 1.4; RAMP_H = 1.2; // 外す坂の Z（帯の下 0.2 から 1.2）
RAMP_Y1 = 0.05;                       // 坂の終わりの面（軸の手前側の面がここまで来る → 軸の中心 1.05・口の当たりを越える）
MARK_W  = 0.5; MARK_D = 0.4;          // 落ちる位置の線

R_C     = sqrt((HEAD_D / 2) * (HEAD_D / 2) - (NOTCH_W / 2) * (NOTCH_W / 2));   // 1.47 頭の接点の、軸からの距離
DROP_W  = [for (L = [4, 6, 8, 10, 12, 15]) sqrt(L * L + R_C * R_C - LIP_DROP * LIP_DROP)];
function xw(w) = LEAD_R + LEAD_T + (w - W0) * TAPER;
function edge_y(x) = x <= LEAD_R ? SLIT_W
                   : x <= LEAD_R + LEAD_T ? SLIT_W + (W0 - SLIT_W) * (x - LEAD_R) / LEAD_T
                   : W0 + (x - LEAD_R - LEAD_T) / TAPER;
function face_y(x) = edge_y(x) + LIP_W;

echo(str("lean sieve  L_TOT ", L_TOT, "  drop w ", DROP_W, "  drop X ", [for (w = DROP_W) xw(w)],
         "  seat Z ", SEAT_Z, " lip Z ", LIP_Z, "  Y ", Y_NEAR, "..", Y_OUT, "  belt ", BELT_L, " x ", BELT_W, " x ", BELT_T));

module trough() {
    difference() {
        union() {
            translate([0, Y_NEAR, 0]) cube([L_TOT, WALL_N, TOP_Z]);                                   // 縁側の壁
            translate([L_TOT - WALL, Y_NEAR, 0]) cube([WALL, Y_OUT - Y_NEAR, TOP_Z]);                 // 出口の壁
        }
        for (w = DROP_W) translate([xw(w) - MARK_W / 2, Y_NEAR - 0.01, TOP_Z - MARK_D]) cube([MARK_W, WALL_N + 0.02, MARK_D + 0.01]);
        translate([-1, Y_WALL - SLOT_D - BELT_FIT, SLOT_Z]) cube([L_TOT + 2, SLOT_D + BELT_FIT + 1, BELT_T + BELT_FIT]);   // 帯の溝（全長・出口の壁も抜く）
    }
    // 外す坂: 帯の下の肋。面が Y_WALL から RAMP_Y1 へ
    translate([0, 0, RAMP_Z0]) linear_extrude(RAMP_H)
        polygon([[0, Y_WALL - 0.01], [0, Y_WALL], [LEAD_R, RAMP_Y1], [LEAD_R + 3, RAMP_Y1], [LEAD_R + 3, Y_WALL - 0.01]]);
    // 庇側の壁（面は face_y。外は Y_OUT まで詰める）
    linear_extrude(TOP_Z) polygon([[0, face_y(0)], [LEAD_R, face_y(LEAD_R)], [LEAD_R + LEAD_T, face_y(LEAD_R + LEAD_T)],
                                   [L_TOT, face_y(L_TOT)], [L_TOT, Y_OUT], [0, Y_OUT]]);
    // 向かいの縁: 外す坂の区間（座面の高さ）
    translate([0, SLIT_W, SEAT_Z - PLATE_T]) cube([LEAD_R, LIP_W + 0.01, PLATE_T]);
    // 受け渡し（座面から LIP_DROP 下がる。凸なので hull）
    hull() {
        translate([LEAD_R - 0.01, SLIT_W, SEAT_Z - PLATE_T]) cube([0.01, LIP_W + 0.01, PLATE_T]);
        translate([LEAD_R + LEAD_T, W0, LIP_Z - PLATE_T]) cube([0.01, LIP_W + 0.01, PLATE_T]);
    }
    // 庇（低い・広がる）
    translate([0, 0, LIP_Z - PLATE_T]) linear_extrude(PLATE_T)
        polygon([[LEAD_R + LEAD_T, W0], [L_TOT, W1], [L_TOT, W1 + LIP_W + 0.01], [LEAD_R + LEAD_T, W0 + LIP_W + 0.01]]);
    // 入り口の上の橋
    translate([0, Y_NEAR, TOP_Z - WALL]) cube([WALL, Y_OUT - Y_NEAR, WALL]);
}

// 帯。先端が X=0、縁が Y=0、下面 Z=0。受けの中心 X = 3, 9, 15。尻尾は -X
module belt() {
    difference() {
        translate([-(BELT_L - N_POCKET * PITCH), -BELT_W, 0]) cube([BELT_L, BELT_W, BELT_T]);
        for (i = [0 : N_POCKET - 1]) {
            xc = PITCH / 2 + i * PITCH;
            translate([xc, SHANK_Y, -1]) cylinder(d = NOTCH_W, h = LOW_T + 2, $fn = 32);                        // 下の層: 軸の U
            translate([xc - NOTCH_W / 2, SHANK_Y, -1]) cube([NOTCH_W, 1, LOW_T + 2]);
            translate([xc, SHANK_Y, LOW_T]) cylinder(r = POCKET_R, h = BELT_T, $fn = 48);                        // 上の層: 頭の受け
            translate([xc - POCKET_R, SHANK_Y, LOW_T]) cube([2 * POCKET_R, 1, BELT_T]);
        }
    }
    for (i = [0 : N_POCKET - 1], s = [-1, 1])                                                                    // 口の当たり（下の層の口の角）
        translate([PITCH / 2 + i * PITCH + s * NOTCH_W / 2, -BUMP_R, 0]) cylinder(r = BUMP_R, h = LOW_T, $fn = 16);
}
module belt_at(x0) translate([x0, 0, SLOT_Z]) belt();

module screw(L) {                       // 頭が上。頭の下面が Z=0、軸は -Z
    cylinder(d = HEAD_D, h = HEAD_H, $fn = 32);
    translate([0, 0, -L]) cylinder(d = SHANK, h = L, $fn = 24);
}
module lean6() {                        // ×6 を w=4.0 に。頭の接点（軸から 1.47）が帯の縁 (Y 0, Z SEAT_Z) に乗り、先端が庇の上面に着く。傾き θ: 1.47 cos θ − 6 sin θ = −3.0
    th = 42.8;
    translate([xw(4.0), R_C * sin(th), SEAT_Z + R_C * cos(th)]) rotate([90 - th, 0, 0]) screw(6);
}

if (part == "trough") trough();
if (part == "belt")   belt();
if (part == "belt_loaded") { color("#e0a040") belt(); color("#d05030") for (i = [0 : N_POCKET - 1]) translate([PITCH / 2 + i * PITCH, SHANK_Y, LOW_T]) screw(6); }
if (part == "asm") {                    // 帯の先端が X 15。受けの中心は X 3, 9, 15
    color("#b8c4d0") trough();
    color("#e0a040") belt_at(-3);
    color("#d05030") translate([-3 + PITCH / 2, SHANK_Y, SEAT_Z]) screw(6);                             // 1 本目（X 0）: 帯に持たれたまま（坂の手前）
    color("#d05030") translate([-3 + PITCH / 2 + 2 * PITCH, RAMP_Y1 + SHANK / 2, SEAT_Z]) screw(6);    // 3 本目（X 12）: 坂で外れた
}
if (part == "sec") projection(cut = true) rotate([-90, 0, 0]) rotate([0, 0, -90]) translate([-SEC_X, 0, 0])
    union() {
        trough();
        belt_at(SEC_X - PITCH / 2 - 2 * PITCH);                                                        // 3 本目の受けの中心が SEC_X
        if (SEC_X <= 0.01) translate([SEC_X, SHANK_Y, SEAT_Z]) screw(6);
        else if (SEC_X <= LEAD_R + 0.01) translate([SEC_X, RAMP_Y1 + SHANK / 2, SEAT_Z]) screw(6);
        else if (abs(SEC_X - xw(4.0)) < 0.1) lean6();
    }
if (part == "look") { color("#b8c4d0") trough(); color("#e0a040") belt_at(xw(4.0) - PITCH / 2 - 2 * PITCH); color("#d05030") lean6(); }
