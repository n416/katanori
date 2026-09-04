// 皿（ブリッジの板）の裏に、どれだけ空間が残っているかを測る用（2026-08-26）。
//   ブリッジ以外の住人を、皿の footprint（X 13〜53）× Y 14.9〜45 × Z 0〜21.4 で切り出す。
//   出てきた塊の一番高い Z が「住人の頭」＝ 21.4 との差が使える厚み。
//   openscad --backend=manifold -o _brg_under.stl -D 'part="none"' hardware/_brg_under.scad
include <case_v4.scad>
intersection() {
    union() {   // innards4 からブリッジと帯だけ抜いたもの
        core(); bat_v4(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); tgl_v4(0); tcb_v4();
        wires_pwr(); wires_sig(); door4(0, false);
    }
    translate([13, 14.9, 0]) cube([40, 30.1, BAT_Z - BRG_T]);
}
