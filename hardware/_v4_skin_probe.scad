include <_v4_core.scad>
// 皮を描くための座標取りプローブ（使い捨て）。数字は手で写さず bbox で取る
W = "none";
P = "tcnose";
// Type-C の鼻先（ハッチに開ける口）: ユニットの +Y 端 1.5mm ぶんだけ切り出す
if (P == "tcnose") intersection() { tcb_v4(); translate([-10, 71.7, -10]) cube([30, 10, 40]); }
// つまみの島（移動後 +3, +5）の bbox
if (P == "knob") translate([3, 5, 0]) knob_at_v4();
// ハブ（+4 後）のビス穴の位置
if (P == "hub") hub_unit();
echo(HUB_HOLES_V4 = [for (h = HUB_HOLES) [h[0] + HUB_DX, h[1] + HUB_DY]]);
echo(XIAO_PORT_C = XIAO_PORT_C, IN = [IN_X, IN_Y, IN_Z], TGL_AT = TGL_AT);
echo(Z_BTN_PAD = Z_BTN_PAD, Z_TSW_BOT = Z_TSW_BOT, Z_BTN_DISH = Z_BTN_DISH);
echo(EAR_X = EAR_X, BOSSES = BOSSES, BOSSES_B = BOSSES_B, RSP_TOP = RSP_TOP);
echo(SPK = [SPK_L, SPK_W, SPK_DIA], KNOB_AT = KNOB_AT);
