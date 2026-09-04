// OLED の I2C ヘッダ（＋挿した DuPont）↔ 会話ボタンの受け（バスタブ・耳・天板側のブロック）
include <btn_v3.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN3_SOLO = false;
MODE = "chk";
module at_world() translate([BTN4[0], BTN4[1], Z_TOP]) children();
module hdr()  at_oled() oled_i2c_header();
module hous() at_oled() oled_i2c_housing();
module tub()  at_world() btn3_tub();
module blocks() at_world() for (i = [0, 1]) mirror([i, 0, 0]) translate([0, B3_BLK_DY[i], 0]) btn3_block();
echo(str("hdr world X ", OLED_X0 + OLED_HDR_C[0] - 1.5 * 2.54 - 0.32, "..", OLED_X0 + OLED_HDR_C[0] + 1.5 * 2.54 + 0.32,
         " Z ", OLED_Z0 + OLED_HDR_C[1], " ; block +X outer X ", BTN4[0] + B3_BLK_XO, " inner ", BTN4[0] + B3_BLK_XI,
         " Y ", BTN4[1] + B3_TUB_CY - B3_BLK_W / 2 + B3_BLK_DY[0], "..", BTN4[1] + B3_TUB_CY + B3_BLK_W / 2 + B3_BLK_DY[0],
         " Z ", Z_TOP + B3_EAR_Z1, "..", Z_TOP + B3_Z_LIP_B, " ; ear Z ", Z_TOP + b3_ear_z0(0), "..", Z_TOP + B3_EAR_Z1,
         " ; tub bottom Z ", Z_TOP + B3_Z_TUB_B));
if (MODE == "hdr_tub")   intersection() { hdr(); tub(); }
if (MODE == "hdr_blk")   intersection() { hdr(); blocks(); }
if (MODE == "hous_tub")  intersection() { hous(); tub(); }
if (MODE == "hous_blk")  intersection() { hous(); blocks(); }
if (MODE == "look") { color("#c8ccd0") hdr(); color("#333", 0.5) hous(); tub(); color("#b08080") blocks(); }
