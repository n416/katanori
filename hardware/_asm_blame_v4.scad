include <_asm_sim_v4.scad>
part="none"; W="none"; ST=""; CHK=""; WIRELEN=false;
P = "";
module sw_z(h=30) union() for (t=[0:STEP:h]) translate([0,0,t]) children();
module sw_x(d=TAB_L) union() for (t=[0:STEP:d]) translate([d-t,0,0]) children();
// ブリッジ降ろし ↔ 相手を分解
if (P=="brg_rigid") intersection(){ sw_z() brg_v4(); union(){ s_floor(); s_hub(); s_rsp(); s_plugs(); xiao_hous(); s_walls(); s_tcb(); } }
if (P=="brg_xiao")  intersection(){ sw_z() brg_v4(); w_xiao(); }
if (P=="brg_btn2")  intersection(){ sw_z() brg_v4(); w_btn2(); }
if (P=="brg_phout") intersection(){ sw_z() brg_v4(); w_phout(); }
if (P=="brg_phin")  intersection(){ sw_z() brg_v4(); w_phin(); }
if (P=="brg_as")    intersection(){ sw_z() brg_v4(); w_as5600(); }
// 留め帯 ↔ 剛体を分解
if (P=="st_brg")   intersection(){ sw_x() straps_v4(); s_brg(); }
if (P=="st_walls") intersection(){ sw_x() straps_v4(); s_walls(); }
if (P=="st_floor") intersection(){ sw_x() straps_v4(); union(){ s_floor(); s_hub(); s_rsp(); s_plugs(); xiao_hous(); s_tcb(); } }
// 板降ろし ↔ 相手を分解
if (P=="bd_strap") intersection(){ sw_z(25) { ina_bat(); pb_bat(); } s_strap(); }
if (P=="bd_bat")   intersection(){ sw_z(25) { ina_bat(); pb_bat(); } s_bat(); }
if (P=="bd_brg")   intersection(){ sw_z(25) { ina_bat(); pb_bat(); } s_brg(); }
if (P=="bd_wire")  intersection(){ sw_z(25) { ina_bat(); pb_bat(); } union(){ w_low(); } }
if (P=="bd_rest")  intersection(){ sw_z(25) { ina_bat(); pb_bat(); } union(){ s_floor(); s_hub(); s_rsp(); s_plugs(); xiao_hous(); s_walls(); s_tcb(); } }
// ブリッジ ↔ 剛体を 1 つずつ
if (P=="brgR_floor") intersection(){ sw_z() brg_v4(); s_floor(); }
if (P=="brgR_hub")   intersection(){ sw_z() brg_v4(); s_hub(); }
if (P=="brgR_rsp")   intersection(){ sw_z() brg_v4(); s_rsp(); }
if (P=="brgR_plugs") intersection(){ sw_z() brg_v4(); s_plugs(); }
if (P=="brgR_xh")    intersection(){ sw_z() brg_v4(); xiao_hous(); }
if (P=="brgR_walls") intersection(){ sw_z() brg_v4(); s_walls(); }
if (P=="brgR_tcb")   intersection(){ sw_z() brg_v4(); s_tcb(); }
// 留め帯 ↔ 剛体を 1 つずつ
if (P=="stR_floor") intersection(){ sw_x() straps_v4(); s_floor(); }
if (P=="stR_hub")   intersection(){ sw_x() straps_v4(); s_hub(); }
if (P=="stR_rsp")   intersection(){ sw_x() straps_v4(); s_rsp(); }
if (P=="stR_plugs") intersection(){ sw_x() straps_v4(); s_plugs(); }
if (P=="stR_xh")    intersection(){ sw_x() straps_v4(); xiao_hous(); }
if (P=="stR_tcb")   intersection(){ sw_x() straps_v4(); s_tcb(); }
if (P=="brgR_rspbd") intersection(){ sw_z() brg_v4(); respeaker_at(); }
if (P=="brgR_j2")    intersection(){ sw_z() brg_v4(); rsp_j2_space(); }
if (P=="stR_rspbd")  intersection(){ sw_x() straps_v4(); respeaker_at(); }
if (P=="stR_j2")     intersection(){ sw_x() straps_v4(); rsp_j2_space(); }
if (P=="j2box")      rsp_j2_space();
if (P=="brg_static_j2") intersection(){ brg_v4(); rsp_j2_space(); }
if (P=="strap_static_j2") intersection(){ straps_v4(); rsp_j2_space(); }
if (P=="brg_static_rspbd")   intersection(){ brg_v4(); respeaker_at(); }
if (P=="strap_static_rspbd") intersection(){ straps_v4(); respeaker_at(); }
if (P=="rspbd")  respeaker_at();
if (P=="brgonly") brg_v4();
// 当たりの区画にある ReSpeaker の中身を切り出す（X 8.5〜10.6・Y 12〜17.5・Z 20.9〜24）
if (P=="rsp_slice") intersection(){ respeaker_at(); translate([8.5,12,20.9]) cube([2.1,5.5,3.1]); }
if (P=="brg_slab")  intersection(){ brg_v4();      translate([0,12,21.4]) cube([14,6,2.0]); }
if (P=="rsp_slab")  intersection(){ respeaker_at(); translate([0,12,21.4]) cube([14,6,2.0]); }
// 当たりの絵（ブリッジ半透明・ReSpeaker そのまま・重なりを赤）
if (P=="view_j2") {
    color("#dd6b20", 0.25) brg_v4();
    respeaker_at();
    color("#16a085", 0.12) rsp_j2_space();
    color("#e53e3e") intersection(){ brg_v4(); union(){ respeaker_at(); rsp_j2_space(); } }
}
if (P=="brg_mid") intersection(){ brg_v4(); translate([0,25,21.4]) cube([20,20,2.0]); }
if (P=="bat")      bat_v4();
if (P=="brgfront") brg_front();
if (P=="dish")     intersection(){ brg_v4(); translate([0,12.9,21.4]) cube([60,50,2.0]); }
if (P=="echo") echo(BAT_X0=BAT_X0, BAT_DX=BAT_DX, lipo=lipo_size(), LEG_X0=LEG_X0, LW_X=LW_X, RAILL=RAIL_SEG_L[0], j2=respeaker_spk_j2());
// 上から見た当たりの図（皿の高さ Z 21.4〜23.4 の断面だけを平らに見る）
module _slab() translate([-5,5,21.4]) cube([60,25,2.0]);
if (P=="view_top") {
    color("#cbd5e0")            intersection(){ brg_v4();       _slab(); }   // 皿
    color("#f6ad55", 0.55)      intersection(){ bat_v4();       translate([-5,5,23.4]) cube([60,25,0.6]); }  // 電池の footprint
    color("#2f855a", 0.30)      intersection(){ rsp_j2_space(); _slab(); }   // プラグ＋線の確保空間
    color("#1a202c")            intersection(){ respeaker_at(); _slab(); }   // ReSpeaker の実体（J2 ソケット）
    color("#e53e3e")            intersection(){ brg_v4(); union(){ respeaker_at(); rsp_j2_space(); } }
}
if (P=="j2body") intersection(){ respeaker_at(); translate([0,5,14]) cube([12,25,16]); }
module _sl() translate([-2,6,21.4]) cube([26,22,2.0]);
if (P=="view_top2") {
    translate([0,0,-4]) color("#68a688") intersection(){ rsp_j2_space(); _sl(); }        // プラグ＋線の確保空間
                        color("#cbd5e0") intersection(){ brg_v4();       _sl(); }        // 皿（Z 21.4〜23.4）
                        color("#1a202c") intersection(){ respeaker_at(); _sl(); }        // J2 ソケットの実体
    translate([0,0,2])  color("#dd6b20") intersection(){ bat_v4(); translate([11.5,6,23.4]) cube([1.0,22,0.8]); }  // 電池の左端 X 11.5
    translate([0,0,4])  color("#e53e3e") intersection(){ brg_v4(); union(){ respeaker_at(); rsp_j2_space(); } }  // 重なり
}
if (P=="strapfoot") intersection(){ straps_v4(); translate([0,12,23.4]) cube([20,18,2.0]); }
if (P=="raill")     intersection(){ brg_v4();    translate([0,12,23.5]) cube([20,18,3.0]); }
DX = 0;
if (P=="shiftboards") intersection(){ translate([DX,0,0]) union(){ ina_bat(); pb_bat(); pbl_hous(); pbu_hous(); } s_top(); }

// ============================================================
// 天面を降ろす軌跡（part="close_top"）の切り分け — 🔴 2026-08-27（13 度目の机上の通し）
//   close_top が 0 → 30.24mm³ になったので、動く側・相手・束を 1 つずつ当てた。
//   犯人は「AS5600 に挿したデュポンの腹 ↔ XIAO の上段 4 本」だった。
//   使い方: openscad --backend=manifold -D 'P="ct_asconn"' -o x.stl hardware/_asm_blame_v4.scad
// ============================================================
module ct_sw(h = 25) union() for (t = [0 : STEP : h]) translate([0, 0, t]) children();
module ct_stage() { lower_group(); brg_v4(); brg_front(); bat_v4(); pb_bat(); ina_bat(); straps_v4();
                    pbl_hous(); pbu_hous(); wires_pwr(); wires_sig(); floor_v4(); lwall_v4(); rwall_v4(); }
// 動く側を 1 つずつ（相手は close_top と同じ stage_top）
if (P == "ct_shell")  intersection() { ct_sw() top_v4();     ct_stage(); }   // 4.66 ＝ ReSpeaker の押し代（close_top では引かれる）
if (P == "ct_knob")   intersection() { ct_sw() top_knob();   ct_stage(); }
if (P == "ct_asconn") intersection() { ct_sw() top_asconn(); ct_stage(); }   // 🔴 30.24
if (P == "ct_spk")    intersection() { ct_sw() top_spk();    ct_stage(); }
if (P == "ct_btn")    intersection() { ct_sw() top_btn();    ct_stage(); }
// 相手を 1 つずつ（動く側は天面一式）
module ct_mv() ct_sw() { top_v4(); top_group(); }
if (P == "ct_o_lower")  intersection() { ct_mv(); lower_group(); }
if (P == "ct_o_wsig")   intersection() { ct_mv(); wires_sig(); }             // 🔴 30.24
if (P == "ct_o_wpwr")   intersection() { ct_mv(); wires_pwr(); }
if (P == "ct_o_brg")    intersection() { ct_mv(); union() { brg_v4(); brg_front(); } }
if (P == "ct_o_skin")   intersection() { ct_mv(); union() { floor_v4(); lwall_v4(); rwall_v4(); } }
// デュポン ↔ 束を 1 束ずつ／止まった姿でも重なる（13.26mm³）
if (P == "ct_w_xiao")   intersection() { ct_sw() top_asconn(); w_xiao(); }   // 🔴 30.24
if (P == "ct_w_as")     intersection() { ct_sw() top_asconn(); w_as5600(); }
if (P == "ct_static")   intersection() { top_asconn(); wires_sig(); }        // 🔴 13.26（止まった姿）
if (P == "ct_asconn_only") top_asconn();                                     // コネクタの居場所だけ（bbox 取り）
// XIAO の上段の車線に、どれだけ Y の逃げ場があるか。角材 3×3 を Z 27.13 に置いて Y を振る
//   実測（2026-08-27）: Y 29.9 → 13.26 ／ 29.4 → 5.64 ／ 29.0 → 0.15 ／ 28.9 → 0.57 ／ 28.4 → 2.68
//   ＝ 逃げ場は **Y 29.0 の一点だけ**で、向こう側は ReSpeaker の板。空きは束の太さ 3.0mm ちょうど
PY = 29.9;
module ct_lane() translate([55.35, PY - 1.5, 27.13 - 1.5]) cube([68.0 - 55.35, 3.0, 3.0]);
if (P == "ct_lane") intersection() { ct_lane(); union() { respeaker_at(); xiao_hous(); top_knob(); top_asconn(); } }
// 車線の断面を見る（2026-08-27）: Z 25.63〜28.63 の帯を Y 22〜32 まで広げて、何が張り出しているかを出す
if (P == "ct_slab") intersection() {
    translate([55.35, 22, 27.13 - 1.5]) cube([68.0 - 55.35, 10.0, 3.0]);
    union() { respeaker_at(); xiao_hous(); top_knob(); top_asconn(); }
}
if (P == "ct_slab_rsp")  intersection() { translate([55.35, 22, 27.13 - 1.5]) cube([12.65, 10.0, 3.0]); respeaker_at(); }
if (P == "ct_slab_xh")   intersection() { translate([55.35, 22, 27.13 - 1.5]) cube([12.65, 10.0, 3.0]); xiao_hous(); }
if (P == "ct_slab_knob") intersection() { translate([55.35, 22, 27.13 - 1.5]) cube([12.65, 10.0, 3.0]); top_knob(); }
// つまみの 5 本 ↔ 相手を 1 つずつ（2026-08-27 の引き直しの検算）
if (P == "as_hub")   intersection() { w_as5600(); hub_unit(); }
if (P == "as_rsp")   intersection() { w_as5600(); union() { respeaker_at(); xiao_hous(); rsp_j2_space(); } }
if (P == "as_knob")  intersection() { w_as5600(); top_knob(); }
if (P == "as_conn")  intersection() { w_as5600(); top_asconn(); }
if (P == "as_brg")   intersection() { w_as5600(); union() { brg_v4(); brg_front(); straps_v4(); } }
if (P == "as_rest")  intersection() { w_as5600(); union() { bat_v4(); pb_bat(); ina_bat(); tgl_v4(); tcb_v4(); v3_walls_lr(); } }
if (P == "hub_slice") intersection() { hub_unit(); translate([55, 40, 10]) cube([15, 12, 10]); }
if (P == "hub_slice2") intersection() { hub_unit(); translate([50, 38, 4]) cube([35, 30, 14]); }
