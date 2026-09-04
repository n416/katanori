include <case_v4.scad>
// のりしろの置き場探し: つばの外側 TAB_REACH までの帯（Y 69.8〜72.0 ＝ 床の板＋縁の厚み）に、何が居るか
//   openscad --backend=manifold --preview -o x.png --camera=33,71,26,90,0,180,160 --projection=o -D 'part="none"' hardware/_hatch_tabs_probe.scad
//   灰 = 空いている帯 / 赤 = 中身・線・基板が居る所 / 青 = ハッチのリブが居る所
TAB_REACH = 4.0;
module tab_zone() sw4_ext(IN_Y - SHUT_BACK, SHUT_BACK) difference() { offset(r = TAB_REACH) sw4_flange_2d(); sw4_flange_2d(); }
module obstacles() { core(); bat_v4(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); tgl_v4(); tcb_v4(); tc_seat4(); brg_v4(); brg_front(); straps_v4(); wires_pwr(); wires_sig(); door4(0); hatch_claws(); }
if (part == "none") {
    color("#c0c0c0") translate([0, -10, 0]) tab_zone();                                   // 帯（外から見る向きで奥 10mm へ引き、当たりが必ず手前に出るように）
    color("#ececec") translate([0, -20, 0]) hatch_v4(false);                            // ハッチの輪郭（さらに奥。向きの目印）
    color("red")  intersection() { tab_zone(); obstacles(); }
    color("blue") intersection() { tab_zone(); panel_ribs("hatch"); }
}
if (part == "tab_hit") intersection() { tab_zone(); obstacles(); }
if (part == "tab_rib") intersection() { tab_zone(); panel_ribs("hatch"); }
// 候補の升 1 個（X x0〜x0+w・Z z0〜z0+h・Y 69.8〜72.0）に、中身・線・基板・リブがどれだけ居るか
//   openscad --backend=manifold -o x.stl -D 'part="tab_probe"' -D PX=10 -D PZ=16.25 -D PW=4 -D PH=3 hardware/_hatch_tabs_probe.scad → 体積 0 なら空き
PX = 0; PZ = 0; PW = 4; PH = 3;
if (part == "tab_probe") intersection() { translate([PX, IN_Y - SHUT_BACK, PZ]) cube([PW, SHUT_BACK, PH]); union() { obstacles(); panel_ribs("hatch"); } }
