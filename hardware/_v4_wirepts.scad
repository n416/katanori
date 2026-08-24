include <_v4_core.scad>
// 📦 §9 の線の両端を機械で取るための探針（bbox 取り用・手写し防止）。W="none" で使う
P = "";
module inai2c_probe() translate([INA_DX + BAT_X0 + (lipo_size()[1] - ina_size()[0]) / 2 + ina_size()[0], PAIR_Y0 + ina_size()[1], BAT_TOP + STRAP_T]) rotate([-THETA, 0, 0]) rotate([0, 0, 180]) ina_hdr_ra();
module pbusb_probe()  translate([BAT_X0 + (lipo_size()[1] - PB_L) / 2 + PB_L, PAIR_Y0 + ina_size()[1] + 0.5 + PB_W, BAT_TOP + STRAP_T]) rotate([-THETA, 0, 0]) rotate([0, 0, 180]) pb_usb_pin_header();
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
echo(spk_stub_xz = [KNOB_AT[0] + 3 - SPK_L / 2, IN_Z - spk_th() - 0.2], spk_stub_y = 22.3 - 0.5 - spk_w() / 2 + SPK_W / 2 - 1.2);
echo(tsw = [22, 22.3 - 0.5 - spk_w() / 2, Z_TSW_BOT]);
echo(inz = IN_Z, iny = IN_Y, knob_at = KNOB_AT, brg = [BRG_Y0, BRG_Y1, BAT_Z], bat = [BAT_X0, BAT_Y0, BAT_Z, BAT_TOP]);
