// ============================================================
// 組み立てシミュレーション v5（2026-09-05）。筐体の部品ではない・マニュアルの挿絵だけの道具
//   ST="st1" 〜 "st13" で「その手順を終えたときに在る物」を出す（番号は docs/manual/assembly_v5.html と同じ）。
//   実行: openscad --backend=manifold --render=full -D 'ST="st6"' -o x.png hardware/tools/manual_v5/_asm_sim_v5.scad
// ============================================================
include <../../case_v5.scad>
part = "none";   // case_v5 の描画スイッチを止める（include の後の代入が勝つ）
ST   = "";

// ---- 段ごとの部品のまとまり ------------------------------------------------
module s_floor()  color("#e0a040") p_floor();
module s_hub()    at_hub() hub_board(ra = false);                                // ハブ基板だけ（口はまだ）
module s_rsp()    at_rsp() respeaker_lite();
module s_plugs()  { hub_plugs(); xiao_plugs(); }                                // ハブの口 10 本と XIAO 側の口
module w_low()    { w_xiao(); w_as5600(); w_btn2(); w_phin(); w_phout(); w_oled(); w_pwr(); w_ina(); w_tgl(); }   // 手順 3 でハブ側を挿して寝かせる束（先は宙に浮いたまま）
module s_walls()  { color("#4a90d9") p_lwall(); color("#4a90d9") p_rwall(); panel_ribs("lwall"); panel_ribs("rwall"); }
module s_tc()     { one("tc"); w_chg(); }
module s_brg()    { brg_front(); bridge(); panel_ribs("bridge"); }
module s_straps() straps();
module s_bat()    one("bat");
module s_ina()    { one("ina"); w_bat(); w_batout(); }
module s_topgrp() { one("pb"); one("knob"); one("btn"); one("spk"); }         // 天板に付く小組（天板そのものは s_top）
module s_oled()   one("oled");
module s_top()    { color("#c9d0d8") p_top(); }
module s_front()  { color("#9b59b6") p_front(); panel_ribs("front"); }
module s_hatch()  { color("#27ae60") p_hatch(); panel_ribs("hatch"); one("tgl"); one("hatchplate"); one("shutter"); one("lock"); }

// ---- 手順の段（累積）------------------------------------------------------
//  1 床にハブ / 2 ReSpeaker / 3 ハブの口と XIAO の口・線を寝かせる / 4 Type-C 基板と充電の線（上から・壁より先） / 5 前板とブリッジ（壁より先） / 6 左右の壁（横から・棚が腕を受ける）
//  7 帯 3 本 / 8 電池 / 9 電流計と電源の線 / 10 天板の小組（絵は別）/ 11 OLED / 12 天板とフロント / 13 ハッチ
module upto(n) {
    if (n >= 1)  { s_floor(); s_hub(); }
    if (n >= 2)  s_rsp();
    if (n >= 3)  { s_plugs(); w_low(); }
    if (n >= 4)  s_tc();
    if (n >= 5)  s_brg();
    if (n >= 6)  s_walls();
    if (n >= 7)  s_straps();
    if (n >= 8)  s_bat();
    if (n >= 9)  s_ina();
    if (n >= 10) s_topgrp();
    if (n >= 11) s_oled();
    if (n >= 12) { s_top(); s_front(); }
    if (n >= 13) s_hatch();
}
for (n = [1 : 13]) if (ST == str("st", n)) upto(n);
if (ST == "topsub") { s_top(); s_topgrp(); }                       // 天板の小組（裏から見る）
if (ST == "wires")  { innards(); wires(); }                        // 線の全体
if (ST == "door")   { one("hatchplate"); one("shutter"); one("lock"); }   // 電池の蓋の一式
if (ST == "claw")   { s_floor(); color("#27ae60") p_hatch(); one("tgl"); }   // ハッチの爪と受け
