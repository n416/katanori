// 支柱を帯に留める案 B（裏から皿ネジ＋支柱の中のナット）/ B'（裏の E リングを本物にする）── 断面の作図
// 2026-09-02。_post_ering_study.scad と同じ作法: 3D を切らず**断面そのものを平面の図として描く**。
//   横軸 = 支柱の中心からの距離、縦軸 = 高さ（帯の裏面 = 電池の上面 = 0）。左右対称なので mirror で写す。
//   実行: openscad --preview -o hardware/_post_fix_study.png --projection=ortho --imgsize=1500,600 hardware/_post_fix_study.scad
//   数字は hardware/_v4_core.scad の実数（STRAP_T 2.0・SPACER_R 2.9・POST_D 2.0・POST_FIT 0.1・POST_KEY_H 0.4・
//   ER_GD 1.5・ER_GW 0.5・ER_OD 4.0・NUT_SLOT_H 1.7・NUT_SLOT_TOP 1.0・NUT_SLOT_FLOOR 0.3）と JIS の値。
//   ⚠ 描いたのは post 3（胴 5.42・PowerBoost 14°）。post 0/1 は胴 1.0 しか無く B のナットは入らない（図の右端に胴 1.0 の線）。
$fn = 8;
$vpr = [0, 0, 0]; $vpt = [0, 1.5, 0]; $vpd = 70;   // 正面・平行投影（--camera を付けない）

STRAP_T = 2.0;    // 帯の天板
BODY_R  = 2.9;    // 胴 φ5.8
PIN_D   = 2.0;    // 軸 φ2.0（帯の穴 2.1）
HOLE_D  = 2.1;
KEY_H   = 0.4;    // D の足が天面へ沈む深さ
BODY_H  = 5.42;   // post 3 の胴（天板の天面 → 板の裏・中心で）
BODY_H_MIN = 1.0; // post 0/1 の胴
PCB_T   = 1.6;
BAT_T   = 1.5;    // 図に描く電池の厚み（実物 6.0）

// ---- B: M2 皿小ねじ（JIS B 1111: dk 3.8・k 1.2・90°）＋ M2 ナット（二面幅 4.0・厚 1.6・溝 4.3 × 1.7）----
CS_DK = 3.8; CS_K = 1.2; SCR_L = 6.0; SCR_D = 2.0;
NUT_AF = 4.0; NUT_T = 1.6; NUT_R = 4.3 / cos(30) / 2;   // 六角の外接半径 2.483
SLOT_H = 1.7; SLOT_TOP = 1.0; SLOT_FLOOR = 0.3;
// ---- B': E 形止め輪 呼び 1.5（JIS B 2804: D 4.0・t 0.4・d2 1.53・m 0.5・n 0.8）----
ER_OD = 4.0; ER_T = 0.4; ER_GD = 1.5; ER_GW = 0.5; ER_N = 0.8; CB_D = 4.4;

module box(x0, x1, y0, y1) translate([x0, y0]) square([x1 - x0, y1 - y0]);
module sym() { children(); mirror([1, 0, 0]) children(); }
module lbl(x, y, s) translate([x, y]) color("#111") linear_extrude(1) text(s, size = 0.5, font = "Liberation Sans");

module battery() color("#e2c07a") linear_extrude(1) box(-9, 9, -BAT_T, 0);   // 電池（柔らかいパウチ・帯の裏に密着）
module pcb(z) color("#1f7a4d") linear_extrude(1) sym() box(1.5, 8, z, z + PCB_T);

// ---- B ----
module fig_B() {
    battery();
    // 帯（橙）: 皿の頭を裏から沈める・天面に D の窪み 0.4
    color("#ed8936") linear_extrude(1) sym() difference() {
        box(0, 9, 0, STRAP_T);
        polygon([[SCR_D / 2, CS_K], [CS_DK / 2, 0], [0, 0], [0, CS_K]]);   // 皿の座（90°）
        box(0, HOLE_D / 2, -0.1, STRAP_T + 0.1);                             // 通し穴 φ2.1
        box(0, BODY_R + 0.15, STRAP_T - KEY_H, STRAP_T + 0.1);               // D の窪み
    }
    // 支柱（水色）: D の足 → 胴 φ5.8（中にナットの横穴）→ 軸 φ2.0
    color("#9ad0ec") linear_extrude(1) sym() difference() {
        union() {
            box(0, BODY_R, STRAP_T - KEY_H, STRAP_T + BODY_H);
            box(0, PIN_D / 2, STRAP_T + BODY_H, STRAP_T + BODY_H + 1.9 + 0.5 + 0.5);
        }
        box(0, 1.25, -0.1, STRAP_T + SLOT_FLOOR + SLOT_H + 1.0 + 0.5);            // ねじの通し穴 φ2.5（先の逃げ込み）
        box(0, NUT_R, STRAP_T + SLOT_FLOOR, STRAP_T + SLOT_FLOOR + SLOT_H);   // ナットの横穴（六角の角まで）
        box(0.75, 8, STRAP_T + BODY_H + 1.9, STRAP_T + BODY_H + 1.9 + ER_GW); // 上の E リング溝（既存）
    }
    // 皿ねじ（鋼・濃灰）
    color("#3d4a5c") linear_extrude(1) sym() union() {
        polygon([[0, 0], [CS_DK / 2, 0], [SCR_D / 2, CS_K], [0, CS_K]]);
        box(0, SCR_D / 2, CS_K, SCR_L);
    }
    // ナット（鋼）: 締めて天井へ上がった位置
    color("#4a5568") linear_extrude(1) sym() box(SCR_D / 2, NUT_AF / 2, STRAP_T + SLOT_FLOOR + SLOT_H - NUT_T, STRAP_T + SLOT_FLOOR + SLOT_H);
    pcb(STRAP_T + BODY_H);
    // post 0/1 の胴の高さ 1.0 の線（比較用・赤）
    color("#c53030") linear_extrude(1) box(3.2, 9, STRAP_T + BODY_H_MIN - 0.03, STRAP_T + BODY_H_MIN + 0.03);
    lbl(-9, -2.2, "B: M2 countersunk below + nut in post (post 3)");
    lbl(-9, -3.0, "strap above head 0.8 - D key 0.4 = 0.4 (lim 0.42)");
    lbl(-9, -3.8, "slot 0.3+1.7+1.0=3.0; body 0/1/2/4 = 1.0/1.0/1.1/1.8");
    lbl(-9, -4.6, "wall at hex corner 0.42 (AF4.3) / 0.53 (AF4.1)");
}
// ---- B' ----
module fig_Bp() {
    battery();
    // 帯: 裏のザグリ φ4.4 × 1.3（つば 0.8 ＋ 溝 0.5）・穴 φ2.1・D の窪み 0.4
    color("#ed8936") linear_extrude(1) sym() difference() {
        box(0, 9, 0, STRAP_T);
        box(0, HOLE_D / 2, -0.1, STRAP_T + 0.1);
        box(0, CB_D / 2, -0.1, ER_N + ER_GW);                       // ザグリ 1.3
        box(0, BODY_R + 0.15, STRAP_T - KEY_H, STRAP_T + 0.1);
    }
    // 支柱: 軸 φ2.0 が帯を貫き、裏で つば 0.8 → 溝 0.5 → 帯の穴の中
    color("#9ad0ec") linear_extrude(1) sym() difference() {
        union() {
            box(0, BODY_R, STRAP_T - KEY_H, STRAP_T + BODY_H);
            box(0, PIN_D / 2, 0, STRAP_T + BODY_H + 1.9 + 0.5 + 0.5);
        }
        box(ER_GD / 2, 8, ER_N, ER_N + ER_GW);                            // 下の溝（つばの上）
        box(0.75, 8, STRAP_T + BODY_H + 1.9, STRAP_T + BODY_H + 1.9 + ER_GW);   // 上の溝（既存）
    }
    // 下の E リング（溝の中・ザグリの天井に当たる）
    color("#3d4a5c") linear_extrude(1) sym() box(ER_GD / 2, ER_OD / 2, ER_N + 0.1, ER_N + 0.1 + ER_T);
    pcb(STRAP_T + BODY_H);
    lbl(-9, -2.2, "B': E-ring 1.5, flange n 0.8 + groove 0.5 = cbore 1.3");
    lbl(-9, -3.0, "strap above cbore 0.7 - D key 0.4 = 0.3 (lim 0.42)");
    lbl(-9, -3.8, "ring lifts on that ledge (annulus 2.1-4.4, 11.7mm2)");
    lbl(-9, -4.6, "tip flush with strap (0 into battery); groove wall 0.235");
}

translate([-12, 0, 0]) fig_B();
translate([ 12, 0, 0]) fig_Bp();
