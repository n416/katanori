// 圧入ゲージ ── リードスイッチ本体とリード用磁石の嵌合を決める（2026-08-16）
//
//   openscad -o hardware/fit_gauge.stl hardware/fit_gauge.scad
//
// 🔒 作法は [magnet-fit-gauge](gen_magnet_gauge.py) と
//    [peg_bore_gauge.scad](peg_bore_gauge.scad) に合わせてある。
//    ・板は作らない。輪と枠を**桟（2.0×1.5・ニッパーで切る）**で1枚につなぐ
//    ・番号は文字ではなく**点の数**。1点＝いちばん小さい
//    ・外形も内寸と一緒に育てる。切り離しても大小で順番が復元できる
//    ・穴は**全部貫通**。⚠ 袋穴にすると、圧入した磁石が二度と出てこない
//    ・バラバラの小部品にしない（1回目でピンを1本紛失した実績）
//
// 何を決めるか:
//   [knob_v4.scad](knob_v4.scad) は次の2つを圧入で設計しているが、机上の数字のまま。
//     ・リードスイッチ本体 3.2角 → 溝 3.25   （REED_W）
//     ・リード用磁石 φ6×2      → ポケット 6.1（MAG2_D）
//   AS5600用の磁石は 2026-08-02 にこのやり方で 4.10 を確定させた（docs/PRINT.md）。
//
// 使い方（どちらも細い→太いの順。点の数が番号）:
//   1. 角穴にリード本体の端を、丸穴に磁石を、小さい方から順に押し込む
//   2. 「入らない → 硬いが入る → 落ちない → 落ちる」の境目を見る
//   3. **落ちない中でいちばんきつい穴の点の数**を記録する
//      角穴 点1=3.20 / 点2=3.25 / 点3=3.30 / 点4=3.35
//      丸穴 点1=6.05 / 点2=6.10 / 点3=6.15 / 点4=6.20
//   4. 出た値を REED_W / MAG2_D に書き戻す
//
// ⚠ ゲージの噛み代は角穴 3.6mm・丸穴 2.6mm。本番の溝は 14.3mm 噛むので、ゲージより
//    効く。「ちょうど」に感じたら一段ゆるい方を採ること。
// ⚠ 印刷設定は本番と同じ（レジン①・0.05mm・2.5s・初期層5層/35s）。直置き・サポート不要。

$fn = 64;

REED_SET = [3.20, 3.25, 3.30, 3.35];   // 本体 3.2角
REED_H   = 3.6;
REED_P   = 10.0;

MAG_SET  = [6.05, 6.10, 6.15, 6.20];   // 磁石 φ6 × 厚2
MAG_H    = 2.6;
MAG_P    = 13.0;

// ---- リード用磁石を「立てて」入れる溝の幅（厚み方向）----
// ✅ 磁石の厚みは 2.02mm（2026-08-16・board_gauge_v2 の櫛で実測）。
//    knob_v4 は円板を立てて埋めるので、掴むのは**厚み方向の2面だけ**。
//    ここが緩いと磁石が落ち、きついと 1.05mm の外壁を割る。つまみを刷る前に決める。
// ⚠ 設計値で並べてある。刷ると約0.1 縮む（1.92 / 1.97 / 2.02 / 2.07 になる）
EDGE_SET = [2.02, 2.07, 2.12, 2.17];
EDGE_LEN = 6.3;    // 磁石の直径ぶん。立てたまま押し込む
EDGE_H   = 4.0;    // 板の厚み＝噛み代
EDGE_P   = 11.0;

WALL0    = 1.6;    // いちばん小さいものの肉厚。⚠ 太らせすぎると隣とくっつく
WALL_UP  = 0.35;    // 1つ進むごとに外形を太らせる量（順番の復元用）

SPRUE_W  = 2.0;    // 桟。peg_bore_gauge と同じ
SPRUE_H  = 1.5;
REED_SPRUE_Y = 2.0;   // 角穴の半分 1.68 より外
MAG_SPRUE_Y  = 3.4;   // 丸穴の半径 3.1 より外
ROW_GAP  = 16.0;   // 角穴の列と丸穴の列の間隔

function mag_od(i)  = MAG_SET[i]  + 2 * (WALL0 + WALL_UP * i);
function reed_od(i) = REED_SET[i] + 2 * (WALL0 + WALL_UP * i);

// 🔴 2026-08-17、**この点は読めなかった。** φ1.0 × 高さ0.5 の突起を白いレジンで刷ると、
//    実物でも写真でも見分けがつかない。番号を聞かれた側が答えられない。
//    ⚠ 「番号は文字ではなく点の数」という作法（冒頭）は、この寸法では成立していない。
//    次に作るときは **切り欠き（外形を V に欠く）か、突起なら φ2 × 1.0 以上**にする。
//    🔒 いまのゲージで番号を復元する手は「外形の大小」だけ（いちばん小さい駒＝点1）
module dot() { cylinder(d = 1.0, h = 0.5); }

// 印の点。部品の上面に、i+1 個ならべる
module dots(i, r, h) {
    for (j = [0 : i]) translate([(j - i / 2) * 1.6, -r + 1.3, h]) dot();
}

// ---- 角穴の列（リード本体）----
module reed_chain() {
    for (i = [0 : len(REED_SET) - 1]) {
        cx = i * REED_P;
        o  = reed_od(i);
        difference() {
            translate([cx - o / 2, -o / 2, 0]) cube([o, o, REED_H]);
            translate([cx - REED_SET[i] / 2, -REED_SET[i] / 2, -0.5])
                cube([REED_SET[i], REED_SET[i], REED_H + 1]);
        }
        translate([cx, 0, 0]) dots(i, o / 2, REED_H);
        // 桟は穴の外（+Y 側）を通す。⚠ 中心を通すと穴を塞ぐ
        if (i < len(REED_SET) - 1)
            translate([cx, REED_SPRUE_Y, 0]) cube([REED_P, SPRUE_W, SPRUE_H]);
    }
}

// ---- 丸穴の列（リード用磁石）----
module mag_chain() {
    for (i = [0 : len(MAG_SET) - 1]) {
        cx = i * MAG_P;
        difference() {
            translate([cx, 0, 0]) cylinder(d = mag_od(i), h = MAG_H);
            translate([cx, 0, -0.5]) cylinder(d = MAG_SET[i], h = MAG_H + 1);
        }
        translate([cx, 0, 0]) dots(i, mag_od(i) / 2, MAG_H);
        if (i < len(MAG_SET) - 1)
            translate([cx, MAG_SPRUE_Y, 0]) cube([MAG_P, SPRUE_W, SPRUE_H]);
    }
}

// ---- 立てて入れる溝の列（厚み方向の圧入）----
// 貫通させてあるので、押し込んだ磁石は反対側から押し出せる
module edge_chain() {
    for (i = [0 : len(EDGE_SET) - 1]) {
        w  = EDGE_SET[i];
        cx = i * EDGE_P;
        o  = EDGE_LEN + 2 * (WALL0 + WALL_UP * i);   // 外形も育てる（順番の復元用）
        difference() {
            translate([cx - (w + 3.2) / 2, -o / 2, 0]) cube([w + 3.2, o, EDGE_H]);
            translate([cx - w / 2, -EDGE_LEN / 2, -0.5]) cube([w, EDGE_LEN, EDGE_H + 1]);
        }
        translate([cx, 0, 0]) dots(i, o / 2, EDGE_H);
        if (i < len(EDGE_SET) - 1)
            translate([cx, EDGE_LEN / 2 + 0.4, 0]) cube([EDGE_P, SPRUE_W, SPRUE_H]);
    }
}

// part="all"  … 3列すべて
// part="edge" … 立て溝の列だけ（2026-08-16 に追加した列。下2列は刷り済み）
part = "all";

if (part == "edge") {
    edge_chain();
} else {
    reed_chain();
    translate([1.5, ROW_GAP, 0]) mag_chain();
    translate([1.5, ROW_GAP * 2, 0]) edge_chain();
}

echo(str("角穴 ", REED_SET, " / 外形 ",
         [for (i = [0 : len(REED_SET) - 1]) reed_od(i)]));
echo(str("丸穴 ", MAG_SET, " / 外形 ",
         [for (i = [0 : len(MAG_SET) - 1]) mag_od(i)]));
echo(str("占有 X ", REED_P * 3 + reed_od(3), " × Y ", ROW_GAP + mag_od(3)));
