// ============================================================
// 用語（部品の呼び名）の絵。筐体の部品ではない・マニュアルの挿絵だけの道具。
//   G="皿" のように呼び名を渡すと、その呼び名が指している物の絵が出る。
//   部品まるごとの呼び名は単体で、「皿」「帯」「腕」のような**部分**の呼び名は、
//   親の部品を灰色で描いて、その部分だけ色を変える。
//   実行は hardware/_asm_gloss.py（マニュアルの絵と同じ _manual_img_v4/ へ g_*.png を書く）。
// ============================================================
include <case_v4.scad>
part = "none";
W    = "none";
G    = "";

BASE = "#c3cbd4";   // 親の部品（灰色）
MARK = "#d2452a";   // その呼び名が指している所

// 親を base、box() の中だけを mark で塗り分ける
module split(box_hi = true) {
    color(BASE) difference() { children(0); children(1); }
    color(MARK)  intersection() { children(0); children(1); }
}
module bx(p0, p1) translate(p0) cube([p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]]);

// ---- 部品まるごと --------------------------------------------------------
if (G == "床")       color(BASE) floor_v4();
if (G == "壁")       color(BASE) { lwall_v4(); rwall_v4(); }
if (G == "ブリッジ") color(BASE) { brg_v4(); brg_front(); }
if (G == "前板")     color(BASE) brg_front();
if (G == "留め帯")   color(BASE) straps_v4();
if (G == "受け")     color(BASE) tc_seat4();
if (G == "ハブ基板") { color(BASE) translate([HUB_DX, HUB_DY, 0]) hub_at();
                       color(MARK) translate([HUB_DX, HUB_DY, 0]) for (id = PLUGGED_9) housing(id); }
if (G == "天面")     color(BASE) { top_v4(); top_group(); }
if (G == "フロント") color(BASE) front_v4();
if (G == "ハッチ")   color(BASE) { hatch_v4(); tgl_v4(TAIL_ANG); door4(0, true); }
if (G == "電池の蓋") color(BASE) door4(0, true);
if (G == "尻尾")     color(BASE) tail_at();

// ---- ブリッジの中の呼び名 -------------------------------------------------
//   皿 = 電池が寝る平らな板 / 帯 = 後ろの横板 / 腕 = 壁の棚へ載る出っ張り / 土手 = 皿の縁の低い壁
if (G == "皿")   split() { brg_v4(); bx([8.9, 0, 0], [49.1, BRG_Y0, BAT_Z]); }
if (G == "帯")   split() { brg_v4(); bx([0, BRG_Y0, 0], [IN_X, IN_Y, 40]); }
if (G == "腕")   split() { brg_v4(); union() { bx([0, 28, 0], [8.9, 39, 40]); bx([49.1, 54, 0], [IN_X, 65, 40]); } }
if (G == "土手") split() { brg_v4(); bx([8.9, 0, BAT_Z], [49.1, BRG_Y0, 40]); }

// ---- 壁の中の呼び名 -------------------------------------------------------
//   棚 = ブリッジの腕を受ける小さな台（中に M2 ナットの横穴）
if (G == "棚") split() { union() { lwall_v4(); rwall_v4(); }
    union() { bx([0, 30.5, 13.0], [9, 36.5, 21.5]);            // 左の前
              bx([0, BLU_Y0, BLU_BOT], [9, BLU_Y1, BLU_TOP]);  // 左の後ろ（3 本目）
              bx([49, 56.9, 13.0], [IN_X + 2, 62.9, 21.5]); } }

// ---- 留め帯の中の呼び名 ---------------------------------------------------
//   ツバ = 足の裏から前後へ張り出した爪（土手を貫く溝に入る）
if (G == "ツバ") split() { straps_v4(); bx([0, 0, BAT_Z], [IN_X, IN_Y, BAT_Z + 2.0]); }

// ---- 天面の中の呼び名 -----------------------------------------------------
//   島 = つまみが乗る台 / L = OLED を留める腕
if (G == "島") split() { top_v4();   // つまみ本体は外して、台だけを見せる
    translate([KNOB4[0], KNOB4[1], IN_Z + 0.6]) cylinder(d = 36, h = 20, $fn = 64); }
if (G == "L")  split() { top_v4(); bx([0, 0, 36], [IN_X, 12, IN_Z]); }
if (G == "耳") split() { union() { front_v4(); top_v4(); }
    union() { bx([-4, -4, 40], [8.0, 11, 60]); bx([76.4, -4, 40], [IN_X + 4, 11, 60]); } }

// ---- 空間の呼び名 ---------------------------------------------------------
//   鞘 = 皿・留め帯の足・留め帯の天板で囲まれた、後ろにだけ開いた筒。電池はここを滑る
if (G == "鞘") { color(BASE) { brg_v4(); straps_v4(); } color(MARK) bat_v4(); }
//   溝と縦穴と 2 階建ての道 = 線が通る隙間。中身を灰色に、**その道を通る線だけ**を色付きで
module michi_base() { core(); brg_v4(); straps_v4(); bat_v4(); ina_bat(); pb_bat(); tcb_v4(); }
module michi_wires() { wires_sig(); wires_pwr(); }
module michi(box_children = true) {
    color(BASE) michi_base();
    color("#9aa3ae") difference()   { michi_wires(); children(); }   // その道を通らない線
    color(MARK)      intersection() { michi_wires(); children(); }   // その道を通る線
}
if (G == "溝")   michi() union() { bx([0, 0, 0], [13.5, IN_Y, IN_Z]); bx([52.5, 0, 0], [IN_X, IN_Y, IN_Z]); }
if (G == "縦穴") michi() bx([0, 62.9, 0], [IN_X, IN_Y, IN_Z]);
//   低い方の道は上の階に隠れるので、上の階（ブリッジ・留め帯・電池・両基板）を外して描く
if (G == "低い道") {
    color(BASE) { floor_v4(); translate([HUB_DX, HUB_DY, 0]) hub_at(); respeaker_at(); tcb_v4(); }
    color("#9aa3ae") difference()   { michi_wires(); bx([0, 0, 0], [IN_X, IN_Y, BRG_ZB]); }
    color(MARK)      intersection() { michi_wires(); bx([0, 0, 0], [IN_X, IN_Y, BRG_ZB]); }
}
if (G == "上の道") michi() bx([0, 0, BRG_ZB], [IN_X, IN_Y, IN_Z]);
//   口 = 線を差し込む所
if (G == "口") { color(BASE) translate([HUB_DX, HUB_DY, 0]) hub_at();
                 color(MARK) translate([HUB_DX, HUB_DY, 0]) for (id = PLUGGED_9) housing(id); }
//   座ぐり = ビスの頭が沈む浅い穴（床の裏の 4 か所）
if (G == "座ぐり") split() { floor_v4(); union() for (h = HUB_HOLES4) translate([h[0], h[1], -1]) cylinder(d = 8.0, h = 4.2, $fn = 40); }
