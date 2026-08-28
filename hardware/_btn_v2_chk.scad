include <btn_v2.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN2_SOLO = false;
B2_INA_X1 = -100;   // 逃げを無効にして測る（-D で戻せる）
PART_SEL = "all";   // all / station（天板側だけ）/ sw（スイッチと端子だけ）
// ねじを回す道: 頭の面から −Y へ φ3.4 × 20（🔒 貫通＋ナットなので、回すのは頭側 = −Y）
DRV_DIR = -1;   // -1 = 頭が −Y 側（そこから −Y へ抜く）／ +1 = 頭が +Y 側
// 🔴 2026-08-29 前の模型は頭の位置から**内側へ**円柱を伸ばしていた（＝井戸を貫いて反対側まで）。
//   実際に要るのは**頭から外へ**の空き。向きを直した。角柱で近似（当たり検査には十分・やや厳しめ）。
module btn2_driver() for (sx=[-1,1]) {
    y0 = BTN4[1] + DRV_DIR * (B2_WELL_OY / 2 + 1.2);
    translate([BTN4[0] + sx * msw_hole_p() / 2 - 1.7,
               DRV_DIR > 0 ? y0 : y0 - 20,
               Z_TOP + B2_Z_SW_BOT + B2_SW_HOLE_Z - 1.7]) cube([3.4, 20, 3.4]);
}
module btn2_at() {
    if (PART_SEL == "driver") btn2_driver();
    else {
        if (PART_SEL != "sw") difference() { btn2_at_add(); btn2_at_cut(); }
        if (PART_SEL != "station") { btn2_at_piston(); btn2_at_switch(); btn2_at_screws(); }
    }
}
W = "all";
intersection() { btn2_at();
  if (W=="all") innards4(); else if (W=="bat") bat_v4(); else if (W=="wpwr") wires_pwr();
  else if (W=="wsig") wires_sig(); else if (W=="ina") ina_bat(); else if (W=="brg") brg_v4();
  else if (W=="rsp") respeaker_at(); else if (W=="straps") straps_v4(); else if (W=="pb") { pb_bat(); pbl_hous(); pbu_hous(); }
  else if (W=="v1btn") { translate([BTN4[0], BTN4[1], Z_TSW_BOT]) rotate([0,0,180]) tactswitch(); translate([BTN4[0], BTN4[1], 0]) rotate([0,0,180]) button_cap(); translate([BTN4[0], BTN4[1], 0]) rotate([0,0,180]) btn_plate(); }
  else if (W=="driver") { for (k=SKINS) if (k!="top") skin1(k); rsp_press4(); respeaker_at(); oled_at(); ina_bat(); brg_v4(); straps_v4(); }
  else if (W=="d_rsp") rsp_press4(); else if (W=="d_rspbd") respeaker_at(); else if (W=="d_oled") oled_at();
  else if (W=="d_ina") ina_bat(); else if (W=="d_brg") brg_v4(); else if (W=="d_straps") straps_v4();
  else if (W=="d_skin") { for (k=SKINS) if (k!="top") skin1(k); }
  else if (W=="self_sw") { btn2_at_switch(); }
  else if (W=="skin") { for (k=SKINS) if (k != "top") skin1(k); } }
