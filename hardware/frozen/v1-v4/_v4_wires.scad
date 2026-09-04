include <_v4_asm.scad>
// ============================================================
// 🔍 v4: 線 13 本を立体で引く（2026-08-24〜）
//   出発点は魚の開き（_v4_sakana.scad・口の役割の正）と、スタディ①②の置き場。
//   v3 の線の経路は読まない（配線が形を決める。前の版の解を写すと前の版の形が再生する）。
//   実行: openscad --backend=manifold -o x.stl -D "WW=\"...\"" hardware/_v4_wires.scad
// ============================================================
part = "none";
W = "none";          // _v4_asm の top-level を全部止める
R = 0; RA = false;   // AS5600 は直立て × R0（はんだ済みの個体の姿・④⑤の筋）
INA_RA = true;       // INA226 は L 字横出し（線は −X へ。X 走査 `inam` と同じ姿）

WW = "look";

// ---- 端点グループの bbox 取り（探針の単体出し）----------------------------
if (WW == "p_xh")   xiao_hous();
if (WW == "p_oh")   oled_hous();
if (WW == "p_asc")  as_conn();
if (WW == "p_ina")  ina_at_x();
if (WW == "p_pbh")  { hous_c(); }
if (WW == "p_pbj")  pose_c() pb_jst_plug();
if (WW == "p_lipo") translate(LIPO_AT) lipo_1000mah();
if (WW == "p_tgl")  toggle_on_hatch();
if (WW == "p_spk")  translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495();
if (WW == "p_btn")  translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch();
if (WW == "p_knob") one("knob");
if (WW == "p_tcb")  tcb_unit();
if (WW == "p_hous") one("hous");
if (WW == "p_j2")   rsp_j2_space();

echo(PORTS = [for (h = HUB_HEADERS) [h[0], port_at(h[0])]]);
echo(RSP_TOP = RSP_TOP, IN = [IN_X, IN_Y, IN_Z]);
echo(LIPO_AT = LIPO_AT, LIPO = [LIPO_L, LIPO_W, LIPO_TH]);
echo(TGL_AT = TGL_AT, BTN_AT = BTN_AT, KNOB_AT = KNOB_AT, Z_TSW_BOT = Z_TSW_BOT);
echo(SPK = [SPK_X, SPK_Y, SPK_L, SPK_W], SPK_C = SPK_C);
echo(OLED = [OLED_X0, OLED_Y1, OLED_Z0], XIAO_HEAD_Y = XIAO_HEAD_Y);
