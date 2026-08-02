// つまみ卓上治具 — 全部印刷（可変抵抗は使わない）
//
// 目的: AS5600の同芯 0.25mm を「1つの部品として同じ中心で焼く」ことで出す。
// つまみ・軸・磁石ポケットが一体なので、貼り合わせの誤差が存在しない。
// 軸受けは門形ブリッジの穴。回転の滑らかさより、まず「回して読めるか」を見る治具。
//
// 寸法の根拠（docs/PRINT.md の実測。2026-08-02）:
//   - 磁石ポケット 4.10mm … ゲージで確定（4.2は逆さで落ちる、4.1は落ちない）
//   - 穴は設計値から約0.1mm縮む … 同ゲージの副産物。穴系の設計値に足す
//   - AS5600基板: 23mm角・M2・穴中心間17mm（定規で実測）・チップは4穴の中心
//
// 部品は3つ。全部プレート直置き・サポート不要:
//   knob   つまみ（軸・磁石ポケット一体）。軸を上に向けて刷る
//   bridge 軸受け。門形。デッキを下にして刷り、使うときは裏返して脚を立てる
//   base   底板。基板の座（M2長穴）とブリッジの脚のほぞ穴
//
// 出力:
//   openscad -o knob.stl   -D 'part="knob"'   knob_jig.scad
//   openscad -o bridge.stl -D 'part="bridge"' knob_jig.scad
//   openscad -o base.stl   -D 'part="base"'   knob_jig.scad

part = "all"; // "knob" | "bridge" | "base" | "all"（all は印刷向きで並べ置き）

$fn = 128;

// ---- 実測に基づく共通値 ----
SHRINK = 0.1;           // 穴の縮み（実測）。穴側の設計値に足す

// 磁石（AS5600キット付属・径方向着磁・φ4.0濃厚）
MAG_D = 4.10;           // ポケット内径。ゲージで確定した値そのもの
MAG_POCKET_DEPTH = 2.2; // 磁石厚み2mm想定＋0.2

// 軸と軸受け
SHAFT_D = 6.0;          // 軸の外径（凸側は縮み補正しない）
SHAFT_LEN = 10.0;
BORE_CLEAR = 0.25;      // 軸受けの遊び（直径）。ガタつくなら-0.1、渋いなら+0.1で刷り直す
BORE_D = SHAFT_D + SHRINK + BORE_CLEAR;

// つまみ
KNOB_D = 25.0;          // docs/KNOB-ENCODER.md 段階1の想定
KNOB_H = 12.0;
RIB_N = 24;             // 指がかり（簡易ローレット）
RIB_D = 1.2;

// AS5600 基板
PCB = 23.0;
HOLE_PITCH = 17.0;      // 実測17mm。変種が来たらここだけ変える
M2_D = 2.0 + SHRINK + 0.3;
SLOT_LEN = 2.0;         // 長穴の遊び（±1mm）。AGC を見ながら追い込む
PCB_T = 1.6;
CHIP_H = 1.1;           // SOICパッケージ高さ
CHIP_GAP = 1.5;         // 磁石面とチップ上面の隙間。許容0.5〜3mmの中央寄り

// ベースとブリッジ
BASE_T = 4.0;
BASE_W = 56.0;          // X: ブリッジの脚まで含む
BASE_L = 36.0;
STANDOFF_H = 6.0;       // 基板を浮かせる高さ。裏に出たヘッダの逃げ＋鉄ピンを磁石から離す
STANDOFF_D = 5.0;

DECK_T = 6.0;           // 軸受けの厚み＝軸の掛かり
DECK_W = 14.0;
LEG_W = 5.0;            // 脚の断面（X方向）
LEG_INNER = PCB / 2 + 1.5;   // 脚の内面。基板の縁から1.5mm逃がす
PEG_D = 3.0;            // 脚のほぞ
PEG_H = 2.5;
PEG_HOLE_D = PEG_D + SHRINK + 0.25;

// デッキ上面の高さ（ベース上面=0）: チップ上面 + 隙間 + 軸長
DECK_TOP = STANDOFF_H + PCB_T + CHIP_H + CHIP_GAP + SHAFT_LEN;
LEG_H = DECK_TOP - DECK_T;   // 脚の長さ（デッキ下面まで）
LEG_CX = LEG_INNER + LEG_W / 2;  // 脚の中心X
DECK_LEN = 2 * (LEG_CX + LEG_W / 2) + 4;

// ---- つまみ（軸・磁石ポケット一体）----
module knob() {
    difference() {
        union() {
            cylinder(d = KNOB_D, h = KNOB_H);
            for (i = [0 : RIB_N - 1])
                rotate([0, 0, i * 360 / RIB_N])
                    translate([KNOB_D / 2, 0, 0])
                        cylinder(d = RIB_D, h = KNOB_H);
            translate([0, 0, -SHAFT_LEN])
                cylinder(d = SHAFT_D, h = SHAFT_LEN + 1);
        }
        translate([0, 0, -SHAFT_LEN - 0.01])
            cylinder(d = MAG_D, h = MAG_POCKET_DEPTH);
    }
}

// ---- ブリッジ（門形の軸受け）----
// 使う向きで描く: 脚がベースに刺さり、デッキが基板をまたぐ
module bridge() {
    difference() {
        union() {
            // デッキ
            translate([-DECK_LEN / 2, -DECK_W / 2, LEG_H])
                cube([DECK_LEN, DECK_W, DECK_T]);
            // 脚2本
            for (s = [-1, 1])
                translate([s * LEG_CX - LEG_W / 2, -DECK_W / 2, 0])
                    cube([LEG_W, DECK_W, LEG_H + 1]);
            // ほぞ
            for (s = [-1, 1])
                translate([s * LEG_CX, 0, -PEG_H])
                    cylinder(d = PEG_D, h = PEG_H + 1);
        }
        // 軸受けの穴
        translate([0, 0, LEG_H - 1])
            cylinder(d = BORE_D, h = DECK_T + 2);
    }
}

// ---- ベース ----
module base() {
    difference() {
        union() {
            translate([-BASE_W / 2, -BASE_L / 2, -BASE_T])
                cube([BASE_W, BASE_L, BASE_T]);
            // 基板の座
            for (x = [-1, 1], y = [-1, 1])
                translate([x * HOLE_PITCH / 2, y * HOLE_PITCH / 2, 0])
                    cylinder(d = STANDOFF_D, h = STANDOFF_H);
        }
        // M2 長穴（X方向±1mm）
        for (x = [-1, 1], y = [-1, 1])
            translate([x * HOLE_PITCH / 2, y * HOLE_PITCH / 2, 0])
                hull() {
                    translate([-SLOT_LEN / 2, 0, -BASE_T - 1]) cylinder(d = M2_D, h = STANDOFF_H + BASE_T + 2);
                    translate([ SLOT_LEN / 2, 0, -BASE_T - 1]) cylinder(d = M2_D, h = STANDOFF_H + BASE_T + 2);
                }
        // ブリッジのほぞ穴（貫通させない）
        for (s = [-1, 1])
            translate([s * LEG_CX, 0, -PEG_H - 0.3])
                cylinder(d = PEG_HOLE_D, h = PEG_H + 1);
    }
}

// ---- 出力（それぞれ印刷向き）----
if (part == "knob") {
    rotate([180, 0, 0]) translate([0, 0, -KNOB_H]) knob();       // 軸を上に
} else if (part == "bridge") {
    rotate([180, 0, 0]) translate([0, 0, -DECK_TOP]) bridge();   // デッキを下に
} else if (part == "base") {
    translate([0, 0, BASE_T]) base();
} else {
    translate([-45, 0, 0]) rotate([180, 0, 0]) translate([0, 0, -KNOB_H]) knob();
    translate([45, 0, 0])  rotate([180, 0, 0]) translate([0, 0, -DECK_TOP]) bridge();
    translate([0, 42, 0])  translate([0, 0, BASE_T]) base();
}
