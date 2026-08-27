// 柱と E リングの留め方 ①段なし / ②基板の裏で細くする ── 断面の作図
// 2026-08-28。3D を切ると preview の色が潰れるので、**断面そのものを平面の図として描く**。
//   横軸 = 柱の中心からの距離、縦軸 = 高さ（基板の上面 = 0）。左右対称なので mirror で写す。
//   実行: openscad --preview -o post_ering.png --projection=ortho \
//         --camera=0,0.9,0,0,0,0,27 --imgsize=1500,480 hardware/_post_ering_study.scad
$fn = 8;

HOLE   = 3.55;   // ✅ 基板の穴（印刷 φ3.5 が通り 3.6 が通らない・2026-08-28）
PCB_T  = 1.6;
POST_D = 3.5;    // ✅ 穴に合う柱
HDR_X  = 3.98;   // ✅ GPO 角で、柱の中心からヘッダの樹脂までの距離（parts.scad の実物合わせ値から）
HDR_T  = 2.5;    // 樹脂の厚み（基板の裏に密着）
THIN_D = 2.5;    // ② で細くする区間
PIN_BOT = -3.2;  // 柱の下端

R3_OD = 7.0; R3_T = 0.6; R3_GRV = 3.0;   // 呼び3（適用軸 3.2〜4）📄
R2_OD = 5.0; R2_T = 0.4; R2_GRV = 2.0;   // 呼び2（適用軸 2.5〜3.2）📄
STEP_UP = 0.2;   // ② で段を穴の中へ引っ込める量

module box(x0, x1, y0, y1) translate([x0, y0]) square([x1 - x0, y1 - y0]);
module sym() { children(); mirror([1, 0, 0]) children(); }

module fig(thin, grv, ring_od, ring_t) {
    // 基板（緑）
    color("#1f7a4d") linear_extrude(1) sym() box(HOLE / 2, 6.5, -PCB_T, 0);
    // 柱（樹脂）
    color("#c9ced6") linear_extrude(1) sym() difference() {
        union() {
            box(0, POST_D / 2, 0, 5);                                   // 柱（上はずっと φ3.5）
            box(0, POST_D / 2, -(PCB_T - (thin ? STEP_UP : 0)), 0);     // 穴を通る区間
            box(0, (thin ? THIN_D : POST_D) / 2, PIN_BOT,
                   -(PCB_T - (thin ? STEP_UP : 0)));                    // その下
        }
        box(grv / 2, 6.5, -PCB_T - ring_t - 0.1, -PCB_T);                 // E リングの溝
    }
    // ヘッダの樹脂（黒。基板の裏に密着して 2.5mm）
    color("#22272e") linear_extrude(1) sym() box(HDR_X, 6.5, -PCB_T - HDR_T, -PCB_T);
    // E リング（鋼）
    color("#3d4a5c") linear_extrude(1) sym() box(grv / 2, ring_od / 2, -PCB_T - ring_t, -PCB_T);
}

translate([-8.5, 0, 0]) fig(false, R3_GRV, R3_OD, R3_T);   // ① 段なし・呼び3
translate([ 8.5, 0, 0]) fig(true,  R2_GRV, R2_OD, R2_T);   // ② 裏で φ2.5・呼び2
