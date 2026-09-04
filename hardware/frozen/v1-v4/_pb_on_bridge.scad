include <case_v3.scad>
// 🔍 検討（2026-08-24 深夜・ユーザー「バッテリーの構造体を無くす」）: 電池トンネルと電池を無くし、
//    PowerBoost を**ブリッジの上に平置き**する。部品面が上・8 ピン列とも上向き ⇒ ハウジングは上から挿す（軌跡が自由）
//    板の下は半田の盛り 1.2 を浮かせる。X0/Y0 で位置を振る
X0 = 8; Y0 = 25; ZB = 29.3 + 1.2;
module pbf() translate([X0, Y0, ZB]) { powerboost_1000c(hdr = "front", ra_dir = 1); pb_jst_plug(); }
// 上向きの垂直ピン 3 本（GND/EN/USB）のハウジング＋ USB-A の 4 ピンのハウジング（どれも上へ 10）
module hf() {
    for (i = [3, 4, 7]) { x = 12.83 + i * 2.54; translate([X0 + x - 1.27, Y0 + 1.27 - 1.27, ZB + 1.6 + 2.5]) cube([2.54, 2.54, HOUS_H]); }
    translate([X0 + pb_hdr_x() - 1.27, Y0 + pb_hdr_y0(), ZB + 1.6 + 2.5]) cube([2.54, 4 * 2.54, HOUS_H]);   // ハウジングは樹脂の上面から 10（ピンに被さる）
}
module obst() union() { manaita(); left_wall_v3(); right_wall_v3(); bridge_v3(); one("ina"); top_plate(); front_plate(); hatch(); floor_v3(); }
if (W == "chk") intersection() { union() { pbf(); hf(); } obst(); }
if (W == "who") intersection() { union() { pbf(); hf(); } one(WHO); }
if (W == "tun") intersection() { union() { pbf(); hf(); } union() { translate(LIPO_AT) lipo_1000mah(); } }
if (W == "look") { show_only(["floor", "hub", "rsp", "rwall", "lwall", "bridge", "ina"]); pbf(); color("#f6ad55", 0.6) hf(); }
echo(POS = [X0, Y0, "板", ZB, ZB + 1.6, "部品の頭", ZB + 1.6 + 5.2, "4 ピンのハウジングの頭", ZB + 1.6 + 2.5 + 6.0 + 10]);
