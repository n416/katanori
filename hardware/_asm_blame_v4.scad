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
