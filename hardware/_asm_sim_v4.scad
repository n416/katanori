// ============================================================
// 組み立てシミュレーション v4（2026-08-25）。筐体の部品ではない・マニュアルの挿絵と検算だけの道具
//   ST="st1" 〜 "st12" で「その手順を終えたときに在る物」を出す（番号は hardware/assembly_v4.html と同じ）。
//   CHK="..." でその手順の**入れる軌跡**を当てる（0 が正）。皮の板の軌跡は case_v4.scad の close_* が持つ。
//   実行: openscad --backend=manifold --render -D 'ST="st6"' -o x.png hardware/_asm_sim_v4.scad
//        openscad --backend=manifold -D 'CHK="brg"' -o x.stl hardware/_asm_sim_v4.scad
// ============================================================
include <case_v4.scad>
part = "none";   // case_v4 の描画スイッチを止める（include の後の代入が勝つ）
W    = "none";
ST   = "";
CHK  = "";
WIRELEN = false;

// ---- 線の 2 つの車線 -------------------------------------------------------
//   低い車線（Z 19 以下）: ブリッジの皿（Z 21.4〜23.4・X 13〜53）と壁〜壁の帯（Y 50.5〜62.9・全幅）の**下**を通る。
//     ハブの口がその真下にある束（XIAO・つまみ・BTN2・スピーカー IN/OUT）はブリッジより先に挿して寝かせるしかない。
//   上の車線: 皿や帯の**上**を通る束（OLED・INA の I2C・トグル・リード・充電）。ブリッジを降ろした後に上げる。
//     どれもハブ側の口は左の溝（X<13）か後ろの縦穴（Y>62.9）なので、ブリッジの後でも挿せる。
module w_low()  { w_xiao(); w_as5600(); w_btn2(); w_phin(); w_phout(); }
module w_high() { w_oled(); w_ina_i2c(); w_tgl(); w_reed(); w_chg(); }

// ---- 段ごとの部品のまとまり ------------------------------------------------
module s_floor()  rounded4() floor_v4();
module s_hub()    translate([HUB_DX, HUB_DY, 0]) hub_at();                           // ハブ基板だけ
module s_plugs()  translate([HUB_DX, HUB_DY, 0]) for (id = PLUGGED_9) housing(id);   // ハブの口 10 本に挿した DuPont
module s_rsp()    { respeaker_at(); rsp_j2_space(); }
module s_tcb()    tcb_v4();
module s_seat()   color("#8d99a6") tc_seat4();   // 🆕 2026-08-27（D-1）充電基板の受け。床から出て独立した印刷部品になり、手順 4 の頭で床の枠へ落とす
module s_walls()  rounded4() { lwall_v4(); rwall_v4(); }
module s_brg()    { brg_v4(); brg_front(); brg_hw(); }   // brg_hw = 箱へ留める M2×6 とナット 3 組（手順 5 で締める）。前板は先に床の溝へ差す（2026-08-26 に別部品になった）
module s_oled()   oled_at();
// 🆕 2026-08-27（11 度目の机上の通し）: 電池のコネクタ対は**手順 7 で電池と一緒に入る**。
//   手順 8 で板が載ると、ポケットの真上は板の腹（Z 35.03）で塞がって上から手が入らない（_asm_access.py ⑬）。
//   延長は左の溝へ垂らすだけで、上げて INA へ挿すのは手順 9（s_wpwr）
module s_bat()    { color("#f6ad55") bat_v4(); w_bat_tab(); bat_con(); w_bat_slack(); }
module s_strap()  straps_v4();
module s_boards() { ina_bat(); pb_bat(); pbl_hous(); pbu_hous(); seat_hw(); }
module s_wpwr()   { w_pwr3(); w_bat_ext(); w_batout(); }
//   延長（w_bat_ext）は手順 9。手順 7 では左の溝へ垂らしておくだけで、上げて INA へ挿すのは他の
//   「上の道」の束と同じ段。🔴 ここを手順 7 に入れると、板を降ろす検査（CHK="boards"）が
//   **その板に挿さる自分の線**で 9.1mm³ 止まった（口の真上に線の端が居るため）
module s_top()    { rounded4() top_v4(); top_group(); }
module s_front()  rounded4() front_v4();
module s_hatch()  { rounded4() hatch_v4(); tgl_v4(TAIL_ANG); tail_at(); door4(0, true); }

// ---- 手順の段（累積）------------------------------------------------------
//  1 床にハブ / 2 ReSpeaker / 3 ハブの口 10 本＋低い車線 / 4 受けを落とす＋左右の壁＋Type-C（壁と一緒に降ろす）/ 5 ブリッジ
//  🔒 2026-08-26 6 と 7 を入れ替えた。留め帯のツバは横からしか入らず、電池が先に居ると差せない
//  6 留め帯（横から差す）/ 7 電池（後ろから差し込む）/ 8 電流計と PowerBoost / 9 OLED と上の車線と電源系の線
// 10 天面一式 / 11 フロント / 12 ハッチ
module upto(n) {
    if (n >= 1)  { s_floor(); s_hub(); }
    if (n >= 2)  s_rsp();
    if (n >= 3)  { s_plugs(); xiao_hous(); w_low(); }
    if (n >= 4)  { s_seat(); s_walls(); s_tcb(); }   // 🔒 2026-08-25 Type-C は左の壁と一緒に降ろす（CASE-V4-OPEN.md A-13）。🆕 受けはその前に床の枠へ落とす（D-1）
    if (n >= 5)  s_brg();
    if (n >= 6)  s_strap();
    if (n >= 7)  s_bat();
    if (n >= 8)  s_boards();
    if (n >= 9)  { s_oled(); oled_hous(); w_high(); s_wpwr(); }
    if (n >= 10) s_top();
    if (n >= 11) s_front();
    if (n >= 12) s_hatch();
}
for (n = [1 : 12]) if (ST == str("st", n)) upto(n);

// 中身だけ（線の通り道の全体図。皮は出さない）
// 天面の小組だけ（箱から外した状態。T-2 の「裏返して L にナットを入れる」を測る用）
// 線を除いた「剛体だけ」の段（2026-08-27）。コネクタを挿す道は、**その口に付いている線ごと**動くので、
//   線を障害物に数えると口の真上の自分の線で止まる。挿す道の検査（_asm_access.py の ⑧）はこちらを相手にする。
if (ST == "st9r")  { upto(8); s_oled(); oled_hous(); }              // 手順 9（OLED は立てた・上の車線はまだ）
if (ST == "st10r") { upto(8); s_oled(); oled_hous(); s_top(); }     // 天面を載せた後（線は除く）
// 🆕 2026-08-27 電池の交換の姿: 組み上がりからロックと蓋だけ外した（ハッチ本体は付いたまま）
if (ST == "swap")  { upto(11); rounded4() hatch_v4(); tgl_v4(TAIL_ANG); tail_at(); }
if (ST == "topsub") s_top();
if (ST == "straponly") straps_v4();
if (ST == "tchous") translate([-64.47 + LW_X, IN_Y - 0.50, 0]) rotate([0, 0, -90]) tcb_hous();   // 🆕 2026-08-27 充電の口 2 つ（上下）。頭の Z を手で写さないための出口   // 🆕 2026-08-27 手順 6 の手の道を撃つ用（_asm_access.py が連結成分に割って 3 本の bbox を取る）
if (ST == "wires") { core(); s_bat(); s_boards(); s_tcb(); brg_v4(); straps_v4(); tgl_v4(); wires_pwr(); wires_sig(); }

// ---- 入れる軌跡の検査（0 が正。相手は「その手順の直前まで」）------------------
module sweep_z(h = 30) union() for (t = [0 : STEP : h]) translate([0, 0, t]) children();
// ① ハブ基板を柱（φ7 × 2.5）へ真上から載せる（相手 = 床＋下から通した M3 のビス）。
//   🔴 2026-08-27（10 度目の机上の通し）: ①には工具の道（_asm_access.py）はあったが、**基板を載せる動き**は掃引していなかった
if (CHK == "hub")       intersection() { sweep_z(20) s_hub(); s_floor(); }
// ② ReSpeaker を床の溝へ上から差す（相手 = 手順①まで＝床＋ハブ＋M3 の頭）。
//   🔴 2026-08-27（9 度目の机上の通し）: ここは反例（rsp_after）しか無く、**入れる動きそのもの**は一度も掃引していなかった
if (CHK == "rsp")       intersection() { sweep_z() { respeaker_at(); xiao_hous(); } union() { s_floor(); s_hub(); } }
// ② 反例: ReSpeaker を壁の後に入れようとした場合（0 にならないことを見るための検査）
if (CHK == "rsp_after") intersection() { sweep_z() respeaker_at(); union() { s_floor(); s_hub(); s_walls(); } }
// ④ 手順 4 の**頭**: 充電基板の受け（tc_seat4）を床の枠へ真上から落とす（相手 = 手順③まで＝床・ハブ・ReSpeaker・低い車線）。
//   🔴 2026-08-27（10 度目の机上の通し）: 受けは 🔒 同日に床から出た別部品で、case_v4 に chk_seat_in はあったが
//   既定が SEAT_STAGE="early"（手順①の直後）で、**実際に落とす段（手順③の後）では一度も回していなかった**。
//   マニュアルの検査表にも行が無かった
if (CHK == "seat")      intersection() { sweep_z(20) s_seat(); upto(3); }
// 反例: 受けを Type-C 基板（＝壁）の後に落とそうとした場合（底の座が板の下へ入るので入らない）
if (CHK == "seat_bad")  intersection() { sweep_z(20) s_seat(); union() { upto(3); s_walls(); s_tcb(); } }
// ④ ブリッジを留める棚の M2 ナット 3 個を、**壁を寝かせたまま**横穴へ差す（相手 = その壁の板だけ。箱にはまだ何も無い）。
//   🔴 2026-08-27（10 度目）: 本文は「口の向きは 1 つだけ逆」と向きまで書いてあるのに、差す動きを掃引していなかった。
//   ldg_nut(dy) の dy は差す向き: 左前と右は通路が +Y の面へ抜けているので −Y へ、3 本目（BLU）だけ +Y へ入る
module m2_nut() rotate([0, 0, 30]) hex_pocket_af(4.0, 1.6);
module nut_sweep(dy, d = 6) union() for (t = [0 : STEP : d]) translate([0, dy * t, 0]) children();
LDG_LF = [-1, 30.5, 36.5, 33.5, 30.5, 36.5];
LDG_R  = [ 1, 56.9, 62.9, 59.9, 56.9, 62.9];
module ldg_nut_lf() translate([brg_scr(LDG_LF)[0], LDG_LF[3], brg_slot_z0(LDG_LF) + 0.05]) m2_nut();
module ldg_nut_lb() translate([BLU_SCR[0], BLU_SCR[1], blu_slot_z0() + 0.05]) m2_nut();
module ldg_nut_r()  translate([brg_scr(LDG_R)[0],  LDG_R[3],  brg_slot_z0(LDG_R)  + 0.05]) m2_nut();
if (CHK == "ldgnut_lf") intersection() { nut_sweep(+1) ldg_nut_lf(); lwall_v4(); }
if (CHK == "ldgnut_lb") intersection() { nut_sweep(-1) ldg_nut_lb(); lwall_v4(); }
if (CHK == "ldgnut_r")  intersection() { nut_sweep(+1) ldg_nut_r();  rwall_v4(); }
// 反例: 3 本目を +Y の面から差そうとした場合（通路は −Y の面へしか抜けていない）
if (CHK == "ldgnut_bad") intersection() { nut_sweep(+1) ldg_nut_lb(); lwall_v4(); }
// ④ 左右の壁を上から降ろす（相手 = 手順③まで）
//   🔴 2026-08-27（9 度目）: 受け（tc_seat4）は 🔒 2026-08-27 に床から出て、手順 4 の**頭**で先に落とす部品になった。
//   壁はその後に降りるので、受けは相手に居なければならない。upto(3) には居ないので s_seat() を足した版が下の 2 本
if (CHK == "walls")   intersection() { sweep_z() { lwall_v4(); rwall_v4(); } upto(3); }
if (CHK == "wall_l_seat") intersection() { sweep_z() lwall_v4(); union() { upto(3); s_seat(); } }
if (CHK == "wall_r_seat") intersection() { sweep_z() rwall_v4(); union() { upto(3); s_seat(); } }
// ④ 左の壁が Type-C 基板を**抱いて**降りる本番の動き（相手 = 手順③まで ＋ 先に落とした受け）。
//   🔴 2026-08-27（9 度目）: case_v4 の close_tc は板を tcb_v4_bare（デュポン**抜き**）で掃いていて、相手も
//   core()+floor で**受けが居ない**。手順 4 の本文は 🔒「充電の 2 本は板を手に持っているうちに挿す」なので、
//   降ろすときハウジング 4 個（X 4.524〜7.065）は板に付いている。その姿で当てたのはこの検査が初めて
if (CHK == "tcwall")      intersection() { sweep_z() { lwall_v4(); tcb_v4(); } union() { upto(3); s_seat(); } }
if (CHK == "tcwall_bare") intersection() { sweep_z() { lwall_v4(); tcb_v4_bare(); } union() { upto(3); s_seat(); } }
if (CHK == "wall_l")  intersection() { sweep_z() lwall_v4(); upto(3); }
if (CHK == "wall_r")  intersection() { sweep_z() rwall_v4(); upto(3); }
// ⑤ 🔴 2026-08-27（7 度目の机上の通し）: ブリッジは **2 部品**。前板（brg_front・電池の返し＋前の脚）を
//   先に床の溝へ差してから、ブリッジ本体を真上から降ろす（🔒 2026-08-26 に切り離した・_v4_core.scad の brg_front）。
//   ここまで掃引していたのは本体（brg_v4）だけで、前板を差す動きは一度も当てていなかった
if (CHK == "brgf")    intersection() { sweep_z() brg_front(); upto(4); }
// 反例: 前板をブリッジの後から差そうとした場合（皿の裏の掘り込みが被さっているので入らない）
if (CHK == "brgf_bad") intersection() { sweep_z() brg_front(); upto(5); }
// ⑤ ブリッジ本体を上から降ろす（相手 = 手順④まで ＋ **先に差した前板**。upto(4) に前板は居ないので足す）
if (CHK == "brg")     intersection() { sweep_z() brg_v4(); union() { upto(4); brg_front(); } }
// 反例: 上の車線を先に通してしまった場合（0 にならないことを見るための検査）
if (CHK == "brg_bad") intersection() { sweep_z() brg_v4(); union() { upto(4); w_high(); s_oled(); oled_hous(); } }
// 🔒 2026-08-26 ⑥⑦ は上からではなくなった。⑥ は横（つまみ側から −X へ 2.0）・⑦ は後ろから（−Y へ）
//   向きは右（つまみ側）から。左から差すと帯 A の左足が BTN2 の束を 32.69mm³ 通る（右の XIAO は 20.63mm³ で、
//   右の溝の方が広く束をよけやすい）。どちらも線だけで、剛体との当たりは 0
module sweep_x(d = TAB_L) union() for (t = [0 : STEP : d]) translate([d - t, 0, 0]) children();
module sweep_y(d = 55)    union() for (t = [0 : 1 : d]) translate([0, d - t, 0]) children();
// ⑥ 留め帯 3 本を横から差す（相手 = 手順⑤まで）。ツバが土手の溝へ入る 2.0 の掃引
if (CHK == "strap")     intersection() { sweep_x() straps_v4(); upto(5); }
module upto5_dry() { s_floor(); s_hub(); s_rsp(); s_plugs(); xiao_hous(); s_walls(); s_tcb(); s_brg(); }
if (CHK == "strap_dry") intersection() { sweep_x() straps_v4(); upto5_dry(); }   // 線を除いた剛体だけ（0 が正）
// ⑦ 電池を後ろのハッチ口から差し込む（相手 = 手順⑥まで ＝ 留め帯が既に入っている）
if (CHK == "bat")       intersection() { sweep_y() bat_v4(); upto(6); }
//   🆕 2026-08-27 電池は**素で**差し込む。コネクタを先に嵌めると、電池の尻を押す指の前に
//   コネクタが居る（指 φ12 が通るのは X 14 あたりだけ・_asm_access.py ⑬）。座ってから真上で嵌める。
//   引き抜くときは逆に**繋いだまま**出せる（case_v4 の chk_swap がその姿）
// 反例: 電池を先に入れてしまった場合、留め帯は横から入らない（0 にならないことを見るための検査）
if (CHK == "strap_bad") intersection() { sweep_x() straps_v4(); union() { upto(5); s_bat(); } }
// 反例: 留め帯を上からかぶせようとした場合（ツバが土手に当たる。0 にならない）
if (CHK == "strap_top") intersection() { sweep_z() straps_v4(); upto(5); }
// ⑥ の前半（🆕 2026-08-27）: 押し込む前に、帯を **+2.0 ずらした位置へ上から降ろす**動き。
//   足が皿の縁のレールの外（左足は電池の座の中・右足はレールの右）へ落ちるので、ツバは土手に掛からない
if (CHK == "strap_down") intersection() { translate([TAB_L, 0, 0]) sweep_z() straps_v4(); upto(5); }
// ⑧ 電流計と PowerBoost を上から座へ降ろす（相手 = 手順⑦まで）
if (CHK == "boards")  intersection() { sweep_z(25) { ina_bat(); pb_bat(); } upto(7); }
// ⑨ OLED を上から降ろす（相手 = 手順⑧まで）。🔴 2026-08-27 マニュアルは前からこの CHK の結果 0 を載せていたが、
//   ここに if が無く、打っても**空のモデル**が出るだけだった（＝ 一度も測っていなかった）。書いて回すと 0
if (CHK == "oled")    intersection() { sweep_z() s_oled(); upto(8); }
// ⑨ 上の車線と電源系（静止）↔ 手順⑧まで＋皮
// ⑩ 天面一式を降ろす（相手 = 手順⑨まで）。OLED を L に留めてから一緒に降ろす形も 0（T-2 の調べ）
if (CHK == "top_oled") difference() { intersection() {
    union() for (t = [0 : STEP : 25]) translate([0, 0, t]) { s_top(); s_oled(); oled_hous(); }; upto(8); } rsp_press_zone(); }
if (CHK == "whigh")   intersection() { union() { w_high(); s_wpwr(); } union() { upto(8); s_oled(); oled_hous(); s_top(); s_front(); s_hatch(); } }

// ---- 中身どうしの静止の総当たり（🆕 2026-08-27・9 度目の机上の通し）----------
//   🔴 ここまでの静止の検査は **皮 ↔ 中身**（chk_all ほか）と **1 対 1 の名指し**（chk_tc など）だけで、
//   中身どうしを総当たりで当てたことが一度も無かった。だから「Type-C 基板のデュポン ↔ ハブ基板」の
//   1.169mm³（Z で 0.11 の重なり）が、どの検査にも映らないまま 8 度の机上の通しを素通りした。
//   走らせ方: python hardware/_asm_pairs.py（PAIR_A だけ渡すと「その部品 ↔ 他の全部」）
PAIR_N = 20;
PAIR_A = -1; PAIR_B = -1;
module PAIR_P(i) {
    if (i == 0)  s_floor();
    if (i == 1)  s_hub();
    if (i == 2)  s_plugs();
    if (i == 3)  { respeaker_at(); xiao_hous(); }
    if (i == 4)  s_seat();
    if (i == 5)  lwall_v4();
    if (i == 6)  rwall_v4();
    if (i == 7)  s_tcb();
    if (i == 8)  brg_v4();
    if (i == 9)  brg_front();
    if (i == 10) brg_hw();
    if (i == 11) straps_v4();
    if (i == 12) s_bat();
    if (i == 13) ina_bat();
    if (i == 14) { pb_bat(); pbl_hous(); pbu_hous(); }
    if (i == 15) { s_oled(); oled_hous(); }
    if (i == 16) { top_v4(); top_group(); }
    if (i == 17) front_v4();
    if (i == 18) { hatch_v4(); tgl_v4(); }
    if (i == 19) door4(0, false);
}
if (PAIR_A >= 0 && PAIR_B >= 0) intersection() { PAIR_P(PAIR_A); PAIR_P(PAIR_B); }
if (PAIR_A >= 0 && PAIR_B <  0) intersection() { PAIR_P(PAIR_A); union() for (i = [0 : PAIR_N - 1]) if (i != PAIR_A) PAIR_P(i); }

// ---- 箱と留め具の座標（マニュアルの表の裏取り）------------------------------
if (WIRELEN) {
    echo(str("BOX|", IN_X, "|", IN_Y, "|", IN_Z, "|", LW_X));
    echo(str("FLOORSCREWS|", V4_FLOOR_SCREWS));
    echo(str("HUBHOLES|", HUB_HOLES4));
    echo(str("BOSSES|", BOSSES, "|EAR|", EAR_X));
    echo(str("STRAPS|", STRAP_BANDS, "|THETA|", THETA));
    for (h = ina_holes()) echo(str("SEAT|INA|", h[1], "|", seat_d(h[1]) + ina_size()[2]));
    for (h = pb_mount())  echo(str("SEAT|PB|",  h[1], "|", seat_d(h[1]) + pb_pcb_t()));
}
