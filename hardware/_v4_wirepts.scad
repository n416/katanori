include <_v4_core.scad>
// 📦 §9 の線の両端を機械で取るための探針（bbox 取り用・手写し防止）。W="none" で使う
P = "";
// 🔴 2026-08-29 ここは ina_frame() の 4 つ目の写しだった。INA_DY が抜け、傾きも PB の THETA を
//   使っていたので、INA から出る線の起点が 3mm ずれていた。写しをやめて ina_frame() を呼ぶ。
module inai2c_probe() ina_frame() ina_hdr_ra();
// 🔒 2026-08-28 USB は L 字に揃えたので、探針は挿さる DuPont そのもの（旧: 直ピン pb_usb_pin_header の頭）
module pbusb_probe()  pbu_hous();
if (P == "xiao")   xiao_hous();
if (P == "oled")   oled_hous();
if (P == "asc")    translate([3, 5, 0]) as_conn();
if (P == "inai2c") inai2c_probe();
if (P == "pbusb")  pbusb_probe();
if (P == "tcbh")   translate([-64.47, IN_Y - 1.70, 0]) rotate([0, 0, -90]) tcb_hous();
if (P == "tgl")    tgl_v4();
if (P == "j2")     rsp_j2_space();
for (id = ["XIAO", "OLED", "AS5600", "BTN2", "REED", "INA", "TOGGLE", "PHIN", "PHOUT", "PWR"])
    echo(id, port_at(id) + [HUB_DX, HUB_DY, 0]);
echo(spk_stub_xz = [KNOB_AT[0] + 3 - SPK_L / 2, IN_Z - spk_th() - 0.2], spk_stub_y = SPK4[1] + SPK_W / 2 - 1.2);
echo(tsw = [BTN4[0], BTN4[1], Z_TSW_BOT]);   // 🔴 2026-08-29 直書きの 14.3 は +2.5 に付いてこなかった
echo(inz = IN_Z, iny = IN_Y, knob_at = KNOB_AT, brg = [BRG_Y0, BRG_Y1, BAT_Z], bat = [BAT_X0, BAT_Y0, BAT_Z, BAT_TOP]);
