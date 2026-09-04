// 箱詰めスタディ ── 候補C: OLED を正面に置く（2026-08-15）
//
// **ユーザーが現物を手で並べて「抜群にかっこいい」と判断した配置。**
// case_pack_study.scad（候補B・OLEDが天面）と比べるために作った。
//
//   openscad -o out.png --viewall --autocenter --camera=0,0,0,60,0,25,0 \
//            hardware/case_pack_front.scad
//
// ---- 🔒 この配置の骨格 ----
//   正面(-Y) から順に:  OLED → ReSpeaker(立てる) → ハブ基板 → 電池/PowerBoost
//   **マイクは OLED の両脇から覗く。**
//   ✅ マイクの内側どうしの間隔 68.3mm に対し OLED は 70.1mm。
//      片側 0.9mm ずつ被るが、ユーザーが現物で「両方空く」を確認済み。
//      ⚠ この 68.3mm は ReSpeaker が決めるので、**箱を広げても変わらない。**
//
// ---- 色 ---- （parts.scad / hub_board.scad と同じ規則）
//   緑=基板 / 🟨黄土=中身未取得の占有 / 🟩緑の柱=マイクの音道 / 🟪紫=線の通り道

use <parts.scad>
use <respeaker_lite.scad>
HUB_EMBEDDED = true;
use <hub_board.scad>

$fn = 48;

OLED_W = 70.1;   // ✅ 実測
OLED_H = 48.1;   // ✅
OLED_T =  8.5;   // ✅ 2026-08-15 着荷・実測

WALL = 2.0;
GAP  = 2.0;

// ハブ基板を立てるか。箱が OLED の 48.1 で背が高くなるので、立てると Y が縮む
HUB_STAND = true;

// ---------------- 正面: OLED ----------------
// 🔴 **スピーカーはマイクより外側にしか置けない**（2026-08-15 に判明）。
//    マイクの間隔(中心間71mm)と OLED の幅(70.1mm)がほぼ同じなので、
//    **OLED はマイクの間に挟まる位置に固定され、左右にずらせない。**
//    → 脇の帯はマイクの外側にしか作れず、スピーカー16mm ぶん箱が広がる。
//    ⚠ AI は最初 IN_X=90 でスピーカーを OLED の裏に置いていた（誤り）。
IN_X    = 100;
OLED_X  = (IN_X - OLED_W) / 2;      // 中央に置く
OLED_Z  = 1.5;
OLED_AT = [OLED_X, 0, OLED_Z];

// ---------------- ReSpeaker: OLED のすぐ裏に立てる ----------------
// rotate([0,0,180]) は回転であって鏡像ではない（respeaker_lite.scad の 🚫）
RSP_MIC_OUT = 1.275;
RSP_DEPTH   = RSP_MIC_OUT + respeaker_T() + 10.0;   // マイク先〜ヘッダ先 ≒13.1
RSP_X       = (IN_X - respeaker_L()) / 2;
RSP_Y       = OLED_T + 1.0;                         // OLED の裏にマイク面を向ける
RSP_Z       = 8.0;

// ---------------- ハブ基板 ----------------
HUB_Y = RSP_Y + RSP_DEPTH + GAP;
HUB_D = HUB_STAND ? hub_stack_h(true) : 52;   // 立てれば厚み、寝かせれば 52

// ---------------- 背面: 電池・PowerBoost ----------------
BACK2_Y = HUB_Y + HUB_D + GAP;

// ---------------- 内寸 ----------------
// 高さ: OLED(48.1) と、立てたハブ基板(52) と、立てた ReSpeaker(34) の最大
IN_Z = max(OLED_Z + OLED_H + 1.5,
           HUB_STAND ? 52 + 2 : 0,
           RSP_Z + 34.007 + 1.5);
IN_Y = BACK2_Y + 10.0 + GAP;        // PowerBoost 10mm 厚を立てて置く帯

// ============================================================
// 描画
// ============================================================
module mic_path(len = 22) {
    for (ref = ["U4", "U5"]) {
        m = cad_part(ref, -1);
        color("#2ecc71", 0.5) face_box(m[2], m[3], m[4], m[5], len, -1);
    }
}

// 正面の OLED（表示面が -Y を向く。oled_242() は +Z 側に部品が出るので寝かせて回す）
translate(OLED_AT) translate([0, OLED_T, 0]) rotate([90, 0, 0]) oled_242();

// ReSpeaker
translate([RSP_X + respeaker_L(), RSP_Y + RSP_MIC_OUT + respeaker_T(), RSP_Z])
    rotate([0, 0, 180]) {
        respeaker_lite();
        color("#f80", 0.20) respeaker_mating_space();
        mic_path();
    }

// ハブ基板
if (HUB_STAND)
    translate([8, HUB_Y + HUB_D, 1]) rotate([90, 0, 0]) {
        hub_board(true);
        hub_corridors(true, "down");
    }
else
    translate([8, HUB_Y, 1 + hub_solder()]) { hub_board(true); hub_corridors(true, "down"); }

// 背面: 電池と PowerBoost（立てて壁に貼る）
translate([4, BACK2_Y, 2]) rotate([90, 0, 0]) translate([0, 0, -5]) lipo_1000mah();
translate([64, BACK2_Y, 2]) rotate([90, 0, 0]) translate([0, 0, -10]) powerboost_1000c();

// スピーカー: OLED の脇（⭐ ここが 90mm に広げた理由）
translate([IN_X - 17.5, 0.5, 14]) rotate([90, 0, 0]) translate([0, 0, -4.6])
    speaker_112495();

// 内寸の枠
color("#39c", 0.10) cube([IN_X, IN_Y, IN_Z]);

// ============================================================
echo(str("=== 候補C: OLED 正面  (ハブ基板を", HUB_STAND ? "立てる" : "寝かせる", ") ==="));
echo(str("内寸  ", IN_X, " x ", IN_Y, " x ", IN_Z));
echo(str("外寸  ", IN_X + WALL*2, " x ", IN_Y + WALL*2, " x ", IN_Z + WALL*2,
         "   = ", (IN_X+WALL*2)*(IN_Y+WALL*2)*(IN_Z+WALL*2)/1000, " cm3"));
echo(str("高さを決めているもの: OLED ", OLED_Z+OLED_H+1.5,
         " / 立てたハブ ", HUB_STAND ? 54 : 0,
         " / 立てたReSpeaker ", RSP_Z+34.007+1.5));
