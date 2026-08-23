// ============================================================
// 組み立てシミュレーション（2026-08-23）。筐体の部品ではない・検査だけの道具
//   ユーザー「ちゃんと組めるの？ 線の長さ・手が入るか・ナットを差し入れられるか」
//
//   ST=... で「その手順のときに在る物」を STL に出す（_asm_probe.py が光線を撃つ）
//   WIRES=true で 13 本の実長を echo する
// ============================================================
include <case_v3_fasteners.scad>
part = "none";
CHK  = "none";
ST    = "";
WIRES = false;

module ina_at_() translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module();
module lipo_at_() translate(LIPO_AT) lipo_1000mah();
module top_grp() { top_plate_raw(); oled_brackets(); oled_at();
    translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495();
    translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch();
    translate(KNOB_AT) assembly(show_deck = false); }

// ① 床にハブを留める（床は裏返して机に置く前提。ここは箱の座標のまま）
if (ST == "st_hub")   { floor_v3(); hub_at(); }
// ⑥ 側面構造体を手元で組む。電池の前 / 後
if (ST == "st_manaita") { manaita(); }
if (ST == "st_manaita0") { floor_v3(); hub_at(); respeaker_at(); }
if (ST == "st_lwall") { left_wall_v3(); }
if (ST == "st_walls") { left_wall_v3(); right_wall_v3(); }
if (ST == "st_side")  { left_wall_v3(); right_wall_v3(); bridge_v3(); pb_v3(); ina_at_(); }
if (ST == "st_sideb") { left_wall_v3(); right_wall_v3(); bridge_v3(); pb_v3(); ina_at_(); lipo_at_(); left_wall_extras(); }
// ⑨ まな板に側面構造体を載せた直後（線のハウジング 10 本込み）
if (ST == "st_9")     { manaita(); side_struct(); }
// ⑫ 天面まで載せた
if (ST == "st_12")    { manaita(); side_struct(); top_grp(); }
// ⑬ 全部（フロント・ハッチ・尻尾）
if (ST == "st_all")   { manaita(); side_struct(); top_grp(); front_plate_raw(); front_ears(); hatch(); tail_at(); }
// ④ 天面の小組だけ
if (ST == "st_top")   { top_grp(); }

// ---- 線の実長（口の出口 → 相手の手前 WIRE_TRIM）。r は bundle と同じ ----
function bd_(n) = bundle_d(n);
function wr_(n) = max(5, bd_(n) * 2);
module harness(id, dest, mid = [], n = undef) { if (WIRES) let (nn = is_undef(n) ? port_n(id) : n)
    echo(str("WIRE|", id, "|", nn, "|", wire_len(wire_trim_end(concat([port_out(id)], mid, [dest]), WIRE_TRIM), wr_(nn)),
             "|", port_out(id)[0], ",", port_out(id)[1], ",", port_out(id)[2], "|", dest[0], ",", dest[1], ",", dest[2])); }
module loose(id, pts, n, trim = WIRE_TRIM) { if (WIRES)
    echo(str("WIRE|", id, "|", n, "|", wire_len(wire_trim_end(pts, trim), wr_(n)),
             "|", pts[0][0], ",", pts[0][1], ",", pts[0][2], "|", pts[len(pts)-1][0], ",", pts[len(pts)-1][1], ",", pts[len(pts)-1][2])); }
if (WIRES) { wires_v3();
    echo(str("BOX|", IN_X, "|", IN_Y, "|", IN_Z, "|", Z_TOP));
    for (f = FAST) echo(str("FAST|", f[0], "|", f[1][0], ",", f[1][1], ",", f[1][2], "|", f[2][0], ",", f[2][1], ",", f[2][2],
                            "|", is_undef(f[7]) ? "-" : str(f[7][0], ",", f[7][1], ",", f[7][2])));
}

// ---- 絵: ビスが入らない 2 か所の断面 ----------------------------------
module sec_x(x) { mirror([1, 0]) rotate(90) projection(cut = true) rotate([0, 90, 0]) translate([-x, 0, 0]) children(); }
module slab(c) color(c) linear_extrude(1) children();
module scr_only(f, dz) translate([0, 0, dz]) { shank(f[1], f[2], f[3], f[4]); head(f[1], f[2], f[5], f[6]); }
module lab(y, s) translate([0, y]) linear_extrude(1) text(s, size = 3.4);
if (ST == "pic") {
    // A: X 5（左の棚のビス。ブリッジの上は電池の小部屋）
    translate([0, 0, 0]) {
        slab("#c9d0d8") sec_x(5) left_wall_v3();
        slab("#7d8794") sec_x(5) bridge_v3();
        slab("#9aa5b1") sec_x(5) lipo_at_();
        slab("#e6194b") sec_x(5) scr_only(FAST[8], 0);
        slab("#f7a8b8") sec_x(5) scr_only(FAST[8], 16.3);
        lab(58, "A  X 5 (Y-Z)   bridge screw #8  M2x15");
        lab(53.5, "head seat Z 27.7 / tunnel roof Z 37.2 -> 9.5mm");
        lab(49, "pink = where the screw must start to go in (+16.3)");
    }
    // B: X 83（右の柱のビス。座ぐりの上を PowerBoost の L の立ち上がりが塞ぐ）
    translate([0, -72, 0]) {
        slab("#c9d0d8") sec_x(83) right_wall_v3();
        slab("#7d8794") sec_x(83) bridge_v3();
        slab("#9aa5b1") sec_x(83) pb_v3();
        slab("#e6194b") sec_x(83) scr_only(FAST[9], 0);
        slab("#f7a8b8") sec_x(83) scr_only(FAST[9], 16.3);
        lab(58, "B  X 83 (Y-Z)   bridge screw #9  M2x15");
        lab(53.5, "counterbore is capped at Z 30.3 -> 2.6mm");
        lab(49, "cap = the riser that carries the PowerBoost rear L");
    }
}

// ---- 絵 2: 下から入れたときの道（提案の検証用。形は変えていない） --------
module scr_flip(f, zhead, len, dz) {
    // 同じ軸で上下をひっくり返したビス: 頭の座は zhead、胴は +Z へ len
    translate([f[1][0], f[1][1], zhead + dz]) {
        cylinder(d = f[4], h = len, $fn = 24);
        mirror([0, 0, 1]) cylinder(d = f[5], h = f[6], $fn = 32);
    }
}
if (ST == "pic2") {
    translate([0, 0, 0]) {
        slab("#c9d0d8") sec_x(5) left_wall_v3();
        slab("#7d8794") sec_x(5) bridge_v3();
        slab("#9aa5b1") sec_x(5) lipo_at_();
        slab("#e6194b") sec_x(5) scr_only(FAST[8], 0);
        slab("#f7a8b8") sec_x(5) scr_only(FAST[8], 16.3);
        lab(58, "NOW  bridge screw #8 from above");
        lab(53.5, "9.5mm to the tunnel roof - the screw cannot be stood up");
    }
    translate([0, -72, 0]) {
        slab("#c9d0d8") sec_x(5) left_wall_v3();
        slab("#7d8794") sec_x(5) bridge_v3();
        slab("#9aa5b1") sec_x(5) lipo_at_();
        slab("#2f855a") sec_x(5) scr_flip(FAST[8], 16.5, 8.3, 0);
        slab("#9ae6b4") sec_x(5) scr_flip(FAST[8], 16.5, 8.3, -14);
        lab(58, "FLIPPED  same axis, screw from underneath");
        lab(53.5, "tool run below the ledge: 200mm (side structure on the bench)");
        lab(49, "hub board is 10.9mm below the ledge - head must not stick out that far");
    }
}

// ---- 絵 3: 工具の穴を入れた後（2026-08-23 B 案）--------------------------
if (ST == "pic3") {
    translate([0, 0, 0]) {
        slab("#c9d0d8") sec_x(5) left_wall_v3();
        slab("#7d8794") sec_x(5) bridge_v3();
        slab("#9aa5b1") sec_x(5) lipo_at_();
        slab("#e6194b") sec_x(5) scr_only(FAST[8], 0);
        slab("#f7a8b8") sec_x(5) scr_only(FAST[8], 16.3);
        lab(58, "A  X 5   screw #8 - phi4.0 hole through the tunnel roof");
        lab(53.5, "phi3.2 runs 200mm straight up. tighten BEFORE the battery goes in");
    }
    translate([0, -72, 0]) {
        slab("#c9d0d8") sec_x(83) right_wall_v3();
        slab("#7d8794") sec_x(83) bridge_v3();
        slab("#9aa5b1") sec_x(83) pb_v3();
        slab("#e6194b") sec_x(83) scr_only(FAST[9], 0);
        slab("#f7a8b8") sec_x(83) scr_only(FAST[9], 16.3);
        lab(58, "B  X 83   screw #9 - slot swept -X and +Y through the riser");
        lab(53.5, "the riser that holds the PowerBoost is 2.5 -> 0.90mm thick now");
    }
}

// ---- 絵 4: 立ち上がりを X に伸ばした後（上から見た断面 Z 31.5）------------
module sec_z(z) { projection(cut = true) translate([0, 0, -z]) children(); }
module clip4() intersection() { children(); translate([68, 52]) square([20, 18]); }
if (ST == "pic4") {
    slab("#c9d0d8") clip4() sec_z(31.5) right_wall_v3();
    slab("#7d8794") clip4() sec_z(31.5) bridge_v3();
    slab("#9aa5b1") clip4() sec_z(31.5) pb_v3();
    slab("#e6194b") clip4() sec_z(31.5) scr_only(FAST[9], 0);
    translate([68, 50.4]) linear_extrude(1) text("Z 31.5 seen from above.  X right, Y up.  clip X 68-88 / Y 52-70", size = 0.85);
    translate([68, 48.9]) linear_extrude(1) text("riser now X 76.0-86.0 (was 80.9-86.0).  2.50 thick outside the slot, 1.20 inside", size = 0.85);
}
