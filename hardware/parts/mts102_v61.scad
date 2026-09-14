// ============================================================
// トグルスイッチ MTS-102（SPDT・ON-ON・3 端子）— v6.1 用に図面から起こしたもの
//   🔴 parts/parts.scad の mts102() は v5 と共用なので触らない。v6.1 の直しはこのファイルだけ。
//      向こうは 胴 13×8×12・端子 6・ブッシング 5・レバー 9 で、⚠ 写真読みの数が 4 つ入っていた。
//
//   📄 出どころ: MTS / SMTS Series カタログ（MTS Series の寸法図）
//      https://www.electronicoscaldas.com/datasheet/MTS-SMTS-Series.pdf  4 ページ目・SPDT 3P の図
//   📄 図の数字:
//      胴        13.2（端子が並ぶ向き）× 7.9（奥行）× 9.5（高さ）
//      端子      3 本・ピッチ 4.7・板厚 0.8・胴の下端から 4・幅 2.0
//      ブッシング M6×0.75（1/4"-40NS の品もある）・胴の上面から 8.8（図はナットと座金が付いた状態）
//      レバー    φ3・ブッシングの上面から 11。**真っ直ぐな棒で先が丸い**（先細りではない）
//      倒れ      全 24 度（真ん中から ±12 度）。**レバーは端子が並ぶ面の中で倒れる**
//      パネルの穴 φ6 ＋ 回り止め φ2.4（芯間 6.4）
//
//   原点は **胴の上面の中心**（= ブッシングの根元 / パネルの内面）。+Z がパネルの外。
//   🔒 レバーは ON-ON なので実物は必ずどちらかに倒れている。ang = 0 で描くと当たりも見た目も嘘になる。
//      既定は +12 度＝**局所 −X 側（v6.1 では箱の上）へ倒した姿**。
//      ⚠ どちらへ倒すとどの端子が繋がるかは図に描かれていない。v6.1 は
//      🔒 ユーザー 2026-09-14「上と真ん中だよ。じゃないと上にしたときに ON にならないでしょ」で配線している。
// ============================================================
M61_W = 13.2; M61_D = 7.9; M61_H = 9.5;          // 📄 胴
M61_PIN_P = 4.7; M61_PIN_L = 4.0; M61_PIN_T = 0.8; M61_PIN_W = 2.0;   // 📄 端子
M61_BUSH_D = 6.0; M61_BUSH_H = 8.8;              // 📄 M6×0.75・胴の上面から
M61_LEVER_D = 3.0; M61_LEVER_L = 11.0;           // 📄 レバー
M61_ANG = 12;                                    // 📄 全 24 度の半分
M61_KEY_D = 2.4; M61_KEY_P = 6.4;                // 📄 パネルの回り止めの穴
M61_RELIEF_D = 5.0; M61_RELIEF_H = 2.2;          // ⚠ ブッシングの口のレバーの逃げ（図面に無い・24 度振るのに要る分をこちらで決めた）

function mts_w61()     = M61_W;
function mts_d61()     = M61_D;
function mts_body_h61() = M61_H;
function mts_pin_h61() = M61_PIN_L;
function mts_pin_p61() = M61_PIN_P;
function mts_deep61()  = M61_H + M61_PIN_L;      // パネルの内面から端子の先まで 13.5
function mts_bush_h61() = M61_BUSH_H;
function mts_lever61() = M61_LEVER_L;
function mts_out61()   = M61_BUSH_H + M61_LEVER_L;   // パネルの内面から外へ出る全長 19.8
function mts_ang61()   = M61_ANG;

// ang: レバーの倒れ（度）。+ が局所 −X 側（箱の上）
module mts102_61(ang = M61_ANG) {
    color("#2f6fd0") translate([-M61_W / 2, -M61_D / 2, -M61_H]) cube([M61_W, M61_D, M61_H]);   // 胴
    color("#c9a227") for (i = [-1, 0, 1])                                                       // 端子 3 本
        translate([i * M61_PIN_P - M61_PIN_W / 2, -M61_PIN_T / 2, -M61_H - M61_PIN_L])
            cube([M61_PIN_W, M61_PIN_T, M61_PIN_L]);
    color("#ccc") difference() {                                                                // ブッシング（ナット・座金込みの図の 8.8）
        cylinder(d = M61_BUSH_D, h = M61_BUSH_H, $fn = 32);
        // ⚠ レバーの逃げ。**図面に描かれていない**。24 度振れる以上そこは空いているはずなので、こちらで円錐にした
        translate([0, 0, M61_BUSH_H - M61_RELIEF_H])
            cylinder(d1 = M61_LEVER_D + 0.2, d2 = M61_RELIEF_D, h = M61_RELIEF_H + 0.01, $fn = 32);
    }
    color("#888") rotate([0, -ang, 0]) translate([0, 0, M61_BUSH_H])                            // レバー（端子の並ぶ面の中で倒れる）
        union() {   // 📄 先が丸い**真っ直ぐな φ3 の棒**。先細りではない（全長 11 は丸い先まで）
            cylinder(d = M61_LEVER_D, h = M61_LEVER_L - M61_LEVER_D / 2, $fn = 24);
            translate([0, 0, M61_LEVER_L - M61_LEVER_D / 2]) sphere(d = M61_LEVER_D, $fn = 24);
        }
}
// パネルの穴。key = true で回り止めの φ2.4 も開ける（📄 芯間 6.4）
module mts102_hole61(t = 10, key = false) {
    cylinder(d = M61_BUSH_D + 0.4, h = t, $fn = 32);
    if (key) translate([0, M61_KEY_P, 0]) cylinder(d = M61_KEY_D + 0.3, h = t, $fn = 24);
}
