// m2_align_tray.scad — M2 のねじ整列皿（2026-09-07 ユーザー「こんなの作れます？2mm 用の」）。
//   平行なスリットの板（トレイ）。2026-09-07 ユーザー「トレイにしてほしい。下の箱はいらない」で箱を外した。板の上に低い縁だけ。振るとねじが先からスリットに落ち、頭（φ3.8）がスリットの縁に掛かって並ぶ。
//   市販品（日東工器 ねじ整列皿 静電 2.0〜2.6mm・トラスコ 392-4233・94×142・穴 273・ピッチ 6）と同じ原理。
//   2026-09-08 ユーザー「スリットの1辺を外までやって、トレイの1辺を上から落とす形にしておいたら列で取り出せたりするかも」:
//     スリットは片端まで抜ける。その縁は別部品の戸（gate）で、板の溝と両端の座の縦溝に上から落とす。戸を抜いて傾ければ列のまま端から出る。
//   2026-09-08 ユーザー「スリットの方向を縦にしてみましょうか。蓋も出口も長辺にしてください」:
//     スリットは短辺（47.5）に沿って走り、出口と戸は長辺（72）の +Y 側。4 隅の座の間（X 52）に 7 本。
//   2026-09-08 ユーザー「スリットの形がクソ適当になってる」「トレイが厚くなっても問題ありません」:
//     ① 出口の外に 1.0 の唇を残していたので、歯の先が 1.6 × 1.0 の小さな爪に切り刻まれていた。唇は廃止（戸が内側へ移ったので要らない）。歯の先は座と面一の 47.5。
//     ② 板 2.0 では歯（両側がスリットの帯）が断面 5.6mm² の片持ちだった。板 3.5・ピッチ 7 にして 12.0mm² に。
//     ③ 下の逃げは 45° をやめて垂直から 30°。深さ 2.3 でも口が 5.06 に収まり、傾けて抜ける角（下の CHAMF_B の項）は 33° → 30° とほぼ同じ。
//
// 数字（📄 JIS M2 なべ: 軸 2.0・頭 φ3.8 × 1.4。手元の実測は無い）:
//   スリット幅 2.4（軸 2.0 + 0.4。頭 3.8 は落ちない）。縁は 45° の面取りで上の口を 4.4 に広げ、先が口の近くに来れば滑り込む。下面にも面取り（抜くときに傾けられるように）。
//   板厚 3.5。上に高さ RIM_H の縁（振るときに山が板から落ちない）。板の下は何も無い（吊るされた軸が下に出るので、4 隅のナットにスペーサーを立てる）。ピッチ 7。
//   刷り方: そのまま（板の下面を下）。天井はナットのポケットだけ（張り出し 3.0）。戸は厚みの向きを立てて刷る（断面が一定なので天井も島も無い）。
//
// 作図は「スリットが局所 X に走り +X へ抜ける」形で書き、最後に 90° 回して外形 72 × 47.5・出口 +Y にしている。
// part = "tray"（使う向き。板の下面が Z=0。刷るのもこの向き） | "gate"（戸。広い面を下） | "asm"（戸を差した姿） | "look"（ねじを吊るした絵） | "sec"（スリットの断面）

part = "tray";

SLIT_W  = 2.4;     // スリットの幅
CHAMF   = 1.0;     // 面取りの深さ（45°）。上の口は SLIT_W + 2*CHAMF = 4.4
FLARE_A = 30;      // 下の逃げの角（垂直から）。板を厚くしてもピッチ 7 に収まるように 45° から寝かせた
WALL_V  = 0.2;     // スリットの垂直な壁の高さ。2026-09-08 ユーザー「手で取ろうとしたら斜めになって引っかかる」:
                   //   壁が 1.0 あると軸 2.0 が幅 2.4 の中で傾けるのは 17° まで（2/cos θ + 1.0 sin θ ≤ 2.4）。壁 0.2 なら 33°、その先は逃げの面に沿う（30°）
PITCH   = 7.0;     // スリットのピッチ
N_SLIT  = 7;       // スリットの本数。座の間 52 に、口 4.4 で (7−1)×7 + 4.4 = 46.4（両側 2.8 余る）
OUT_L   = 72;      // 外形（秋月 C タイプのユニバーサル基板 72 × 47.5。2026-09-07 ユーザー「サイズはユニバーサル基板くらい」「もっと小さいやつ」）
OUT_W   = 47.5;
SL      = OUT_W;   // 局所 X（スリットの走る向き）の長さ 47.5
SW      = OUT_L;   // 局所 Y（スリットの並ぶ向き）の長さ 72
PLATE_T = 3.5;     // 板の厚み（2.0 → 3.5。歯の断面 5.6 → 12.0mm²）
HOLE_D  = 3.4;     // 4 隅の M3 の通し穴（M3_CLEAR 3.4。ユーザー「スペーサーで立たせる」）
HOLE_IN = 4.5;     // 穴の中心の、縁からの距離（閉じた端は両方向、開く端は並ぶ向きだけ）
NUT_AF  = 5.5;     // M3 ナットの二面幅（📄 規格 5.5・厚 2.4。v5 の床と同じ数）。2026-09-08 ユーザー「ナットポケットにしておこう。吊り下げでも持ち上げでもできるし」
NUT_FIT = 0.3;     // 六角ポケットの見込み（✅ 呼び +0.3 の実績値）→ 二面幅 5.8。二面幅をスリットの向きに向ける
NUT_T   = 2.4 + 0.2;   // ナットの厚み側の見込み（ポケットの高さ）
NUT_Z0  = 1.5;     // ポケットの床の Z（座の中。上は塞ぐ）。2026-09-08 ユーザー「六角もポケットにしてください。側面から入れる形で」
PAD_X   = 10.0;    // 閉じた端の座の長さ（スリットの向き）
PAD_XO  = 13.0;    // 開く端の座の長さ（スリットの向き）。戸の溝 2.3 とナットの六角を両方入れる
PAD_Y   = 10.0;    // 座の幅（並ぶ向き）
HOLE_XO = SL - 7.5;    // 開く端の穴の中心（40）。六角の面 37.1〜42.9: 座の面 34.5 まで 2.6・戸の溝 44.2 まで 1.3
WALL    = 2.0;     // 縁の厚み
RIM_H   = 3.0;     // 板の上に立つ縁の高さ
// 戸（gate）。2026-09-08 ユーザー「①画像の位置に移動＋幅をすこし広く ②スリットに入る櫛を持たせて（ネジを押し出す器具に）
//   ③ネジ留め時に一緒に挟み込めるように耳を付けて」「トレイ側もレールに呼びをつけて」
GATE_T  = 5.0;     // 戸の厚み（2.0 → 5.0。ユーザーの赤枠は約 4.9）
GATE_FIT= 0.5;     // 戸とレールの呼び（0.3 → 0.5。ユーザー「出し入れしやすいように」）
GATE_LEAD = 0.6;   // レールの口の面取り（落とし込みの誘い）
GATE_XC = HOLE_XO;                             // 戸の中心 = 4 隅のねじの線（40）。耳がねじで挟まれる
GATE_X0 = GATE_XC - (GATE_T + GATE_FIT) / 2;   // レール 37.25〜42.75
GATE_IN = 1.0;     // レールの深さ（座の内側の面に彫る）。2026-09-08 ユーザー「止め板の下のスリットの形状が変わっちゃってるから、ネジそこで止まっちゃう」:
                   //   帯を横切る溝は歯の頭を 1.3 削り、頭（Z 3.2 で受かる）が落ちて向こう側の 1.3 の壁に当たっていた。レールは両端の座だけにして帯には触らない
GATE_Z0 = PLATE_T;                             // 3.5 戸の下端（＝板の上面。歯の頭に載る）
EAR_T   = 2.0;     // 耳の厚み。座の上面 H から EAR_T
GATE_TOP= PLATE_T + RIM_H + EAR_T;             // 戸の上端 8.5（耳と面一。縁より 2.0 出る）
EAR_HD  = 3.8;     // 耳の穴（トレイの 3.4 より緩い。2 本のねじに落とすため）
EAR_W   = 9.0;     // 耳の幅（厚みの向き）。刃の 5.0 では M3 の頭 φ5.5 が載らず穴の残り肉も 0.6 だった。刃の外面から出口側へ広げる（刷る向きの底は刃と同じ面のまま）
EAR_END = 0.5;     // 耳の先を板の縁から引く量
PRONG_W = SLIT_W - 0.4;    // 2.0 櫛の歯の幅（スリット 2.4 に片側 0.2）
PRONG_Z = 0.6;     // 歯の先の Z（板の下面から浮かす）
GATE_Y0 = PAD_Y - GATE_IN + GATE_FIT / 2;      // 戸の刃の端（座に 1.0 食い込む。9.25）
GATE_L  = SW - 2 * GATE_Y0;                    // 刃の長さ 53.5
SLIT_X0 = WALL;                 // スリットの始まり = 閉じた端の縁の内側。2026-09-08 ユーザー「スリットだけど、トレイの端まで繋いでおいて欲しい」
                                //   （帯 12.47〜59.53 は 4 隅の座 0〜10 / 62〜72 に掛からないので、座を避ける必要は無い）
IW = SW - 2 * WALL;             // 68
SLIT_Y0 = WALL + (IW - N_SLIT * PITCH) / 2;   // スリットの帯を中央に（12）
H = PLATE_T + RIM_H;            // 6.5（板 + 縁）
FLARE_D = PLATE_T - CHAMF - WALL_V;           // 下の逃げの深さ 2.3
FLARE_W = SLIT_W + 2 * FLARE_D * tan(FLARE_A);   // 下の口 5.06
$fn = 32;
NUT_R = (NUT_AF + NUT_FIT) / cos(30) / 2;     // 六角の角までの半径 3.35
echo(str("align_tray: ", OUT_L, " x ", OUT_W, " x ", H, "  slits ", N_SLIT, " x ", SL - SLIT_X0, " (open +Y)",
         "  nut pocket AF ", NUT_AF + NUT_FIT, " x ", NUT_T, "  wall: edge ", HOLE_IN - NUT_R, " pad face ", PAD_Y - HOLE_IN - NUT_R,
         " open-end pad face ", HOLE_XO - (NUT_AF + NUT_FIT) / 2 - (SL - PAD_XO),
         " root wall ", WALL, "  slit1 mouth ", SLIT_Y0 + PITCH / 2 - SLIT_W / 2 - CHAMF, " / flare ", SLIT_Y0 + PITCH / 2 - FLARE_W / 2, " vs pad ", PAD_Y, "  gate ", GATE_L,
         "  tooth top/waist/bottom ", PITCH - SLIT_W - 2 * CHAMF, "/", PITCH - SLIT_W, "/", PITCH - FLARE_W,
         "  nut Z ", NUT_Z0, "..", NUT_Z0 + NUT_T, " ceiling ", H - NUT_Z0 - NUT_T,
         "  gate T ", GATE_T, " rail ", GATE_T + GATE_FIT, " at x ", GATE_X0, "..", GATE_X0 + GATE_T + GATE_FIT,
         " blade Z ", GATE_Z0, "..", GATE_TOP, " prong ", PRONG_W, " x ", GATE_Z0 - PRONG_Z, " ear ", H, "..", GATE_TOP, " x ", EAR_W, " hole wall ", GATE_XC - EAR_HD / 2 - (GATE_XC - GATE_T / 2), "/", (GATE_XC - GATE_T / 2) + EAR_W - (GATE_XC + EAR_HD / 2)));

module slit(x0, x1) {                       // 断面: 上の口 4.4（45°）→ 垂直 0.2 → 下の逃げ（垂直から 30°）→ 下の口 5.06
    // convexity: F5（OpenCSG）のプレビューは奥行きの層数がこれで決まる。既定の 1 だと抜きが重なる所が縞になる（形は無事）
    translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0, convexity = 10)
        polygon([[-FLARE_W / 2, -0.01], [FLARE_W / 2, -0.01],
                 [ SLIT_W / 2, FLARE_D], [ SLIT_W / 2, FLARE_D + WALL_V], [ SLIT_W / 2 + CHAMF, PLATE_T + 0.01],
                 [-SLIT_W / 2 - CHAMF, PLATE_T + 0.01], [-SLIT_W / 2, FLARE_D + WALL_V], [-SLIT_W / 2, FLARE_D]]);
}

module tray_local() {                       // スリットは +X へ抜ける
    difference() {
        cube([SL, SW, H]);
        difference() {
            translate([WALL, WALL, PLATE_T]) cube([SL, IW, RIM_H + 1]);                  // 縁の内側。+X は縁を残さない（戸が縁になる）
            for (y = [0, SW - PAD_Y]) {                                                 // 角の座は残す
                translate([0, y, 0]) cube([PAD_X, PAD_Y, H + 2]);
                translate([SL - PAD_XO, y, 0]) cube([PAD_XO, PAD_Y, H + 2]);
            }
        }
        for (i = [0 : N_SLIT - 1]) translate([0, SLIT_Y0 + PITCH / 2 + i * PITCH, 0]) slit(SLIT_X0, SL + 1);   // 全部 +X へ抜ける
        for (y = [PAD_Y - GATE_IN, SW - PAD_Y]) translate([GATE_X0, y, PLATE_T])                          // 戸のレール（両端の座の内側の面に 1.0。帯は削らない）
            cube([GATE_T + GATE_FIT, GATE_IN, RIM_H + 1]);
        for (sgn = [-1, 1], y = [PAD_Y - GATE_IN, SW - PAD_Y])                                             // レールの口の誘い（45°・上端から 0.6）
            translate([GATE_XC + sgn * (GATE_T + GATE_FIT) / 2, y - 0.01, H]) rotate([-90, 0, 0]) linear_extrude(GATE_IN + 0.02)
                polygon([[0, 0], [sgn * GATE_LEAD, 0], [0, GATE_LEAD]]);
        for (p = [[HOLE_IN, HOLE_IN], [HOLE_IN, SW - HOLE_IN], [HOLE_XO, HOLE_IN], [HOLE_XO, SW - HOLE_IN]]) translate([p[0], p[1], 0]) {
            translate([0, 0, -1]) cylinder(d = HOLE_D, h = H + 2);
            translate([0, 0, NUT_Z0]) rotate([0, 0, 30]) cylinder(r = NUT_R, h = NUT_T, $fn = 6);   // M3 ナットの六角ポケット（座の中。上は塞がる）
            sg = (p[1] < SW / 2) ? -1 : 1;                                                          // 側面（並ぶ向きの外）へ抜ける差し込み口
            translate([-(NUT_AF + NUT_FIT) / 2, sg > 0 ? 0 : -(PAD_Y + 1), NUT_Z0]) cube([NUT_AF + NUT_FIT, PAD_Y + 1, NUT_T]);
        }
    }
}
module to_world() translate([SW, 0, 0]) rotate([0, 0, 90]) children();   // 局所 X → 世界 Y。外形 X 0〜72・Y 0〜47.5、出口は +Y
module tray() to_world() render(convexity = 10) tray_local();   // F5 でも実体を出す（縞が出ない）
// 戸は局所 X（厚み 5.0）に一定の断面。刃 + 櫛の歯 + 両端の耳。据えた位置で書く
module gate() {
    x0 = GATE_XC - GATE_T / 2;
    translate([x0, GATE_Y0, GATE_Z0]) cube([GATE_T, GATE_L, GATE_TOP - GATE_Z0]);                    // 刃
    for (i = [0 : N_SLIT - 1])                                                                       // スリットに入る櫛の歯
        translate([x0, SLIT_Y0 + PITCH / 2 + i * PITCH - PRONG_W / 2, PRONG_Z]) cube([GATE_T, PRONG_W, GATE_Z0 - PRONG_Z + 0.01]);
    difference() {                                                                                   // 耳（座の上に載り、M3 で一緒に挟まれる）
        for (sgn = [0, 1])
            translate([x0, sgn ? SW - PAD_Y - GATE_FIT / 2 : EAR_END, H]) cube([EAR_W, PAD_Y + GATE_FIT / 2 - EAR_END, EAR_T]);
        for (y = [HOLE_IN, SW - HOLE_IN]) translate([GATE_XC, y, H - 1]) cylinder(d = EAR_HD, h = EAR_T + 2);
    }
}
module gate_in_place() to_world() gate();

module screw(len) color("#c8a030") { cylinder(d = 2.0, h = len); translate([0, 0, len]) cylinder(d = 3.8, h = 1.4); }

if (part == "tray") tray();
// 刷り方: 厚みの向き（局所 X）を Z に立てる。断面が一定なので天井も島も出ない
if (part == "gate") translate([GATE_TOP, -EAR_END, -(GATE_XC - GATE_T / 2)]) rotate([0, -90, 0]) gate();
if (part == "asm") { color("#b8c4d0") tray(); color("#d0a040") gate_in_place(); }
if (part == "sec") intersection() { tray(); translate([-1, OUT_W / 2 - 0.5, -1]) cube([OUT_L + 2, 1, H + 2]); }
if (part == "look") {
    color("#b8c4d0") tray(); color("#d0a040") gate_in_place();
    for (i = [0 : N_SLIT - 1], k = [0 : 3])
        if ((i * 7 + k * 3) % 5 != 0)
            to_world() translate([SLIT_X0 + 4 + k * 8 + i * 1.0, SLIT_Y0 + PITCH / 2 + i * PITCH, PLATE_T - [4, 6, 8, 10, 12][(i + k) % 5]]) screw([4, 6, 8, 10, 12][(i + k) % 5]);
}
