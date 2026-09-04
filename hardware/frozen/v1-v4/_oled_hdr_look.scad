// 絵: OLED の I2C ヘッダ（裸のピン＝銀・線の DuPont＝青）と会話ボタン（腕＝赤・バスタブ＝白）・INA226（緑）・電源線（橙）
//   DX でボタンを X へ動かした姿も見る。数字ではなく絵で見るための道具。
include <btn_v3.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN3_SOLO = false;
DX = 0;
SHOW_OLED = false;
module btn_all() translate([BTN4[0] + DX, BTN4[1], Z_TOP]) {
    color("#c0392b") difference() { btn3_station_add(); btn3_station_cut(); }
    color("#f0f0f0") btn3_tub();
    color("#f0f0f0", 0.5) btn3_piston();
}
btn_all();
color("#c8ccd0") at_oled() oled_i2c_header();
color("#2b6cb0", 0.9) at_oled() oled_i2c_housing();
if (SHOW_OLED) color("#444", 0.25) oled_at();
color("#2f855a", 0.9) ina_bat();
color("#dd6b20") wires_pwr();
