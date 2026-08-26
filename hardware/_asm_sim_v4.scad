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
module s_walls()  rounded4() { lwall_v4(); rwall_v4(); }
module s_brg()    { brg_v4(); brg_front(); brg_hw(); }   // brg_hw = 箱へ留める M2×6 とナット 3 組（手順 5 で締める）。前板は先に床の溝へ差す（2026-08-26 に別部品になった）
module s_oled()   oled_at();
module s_bat()    color("#f6ad55") bat_v4();
module s_strap()  straps_v4();
module s_boards() { ina_bat(); pb_bat(); pbl_hous(); pbu_hous(); seat_hw(); }
module s_wpwr()   wires_pwr();
module s_top()    { rounded4() top_v4(); top_group(); }
module s_front()  rounded4() front_v4();
module s_hatch()  { rounded4() hatch_v4(); tgl_v4(TAIL_ANG); tail_at(); door4(0, true); }

// ---- 手順の段（累積）------------------------------------------------------
//  1 床にハブ / 2 ReSpeaker / 3 ハブの口 10 本＋低い車線 / 4 左右の壁＋Type-C（壁と一緒に降ろす）/ 5 ブリッジ
//  🔒 2026-08-26 6 と 7 を入れ替えた。留め帯のツバは横からしか入らず、電池が先に居ると差せない
//  6 留め帯（横から差す）/ 7 電池（後ろから差し込む）/ 8 電流計と PowerBoost / 9 OLED と上の車線と電源系の線
// 10 天面一式 / 11 フロント / 12 ハッチ
module upto(n) {
    if (n >= 1)  { s_floor(); s_hub(); }
    if (n >= 2)  s_rsp();
    if (n >= 3)  { s_plugs(); xiao_hous(); w_low(); }
    if (n >= 4)  { s_walls(); s_tcb(); }   // 🔒 2026-08-25 Type-C は左の壁と一緒に降ろす（CASE-V4-OPEN.md A-13）
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
if (ST == "topsub") s_top();
if (ST == "wires") { core(); s_bat(); s_boards(); s_tcb(); brg_v4(); straps_v4(); tgl_v4(); wires_pwr(); wires_sig(); }

// ---- 入れる軌跡の検査（0 が正。相手は「その手順の直前まで」）------------------
module sweep_z(h = 30) union() for (t = [0 : STEP : h]) translate([0, 0, t]) children();
// ② 反例: ReSpeaker を壁の後に入れようとした場合（0 にならないことを見るための検査）
if (CHK == "rsp_after") intersection() { sweep_z() respeaker_at(); union() { s_floor(); s_hub(); s_walls(); } }
// ④ 左右の壁を上から降ろす（相手 = 手順③まで）
if (CHK == "walls")   intersection() { sweep_z() { lwall_v4(); rwall_v4(); } upto(3); }
if (CHK == "wall_l")  intersection() { sweep_z() lwall_v4(); upto(3); }
if (CHK == "wall_r")  intersection() { sweep_z() rwall_v4(); upto(3); }
// ⑤ ブリッジを上から降ろす（相手 = 手順④まで）
if (CHK == "brg")     intersection() { sweep_z() brg_v4(); upto(4); }
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
// 反例: 電池を先に入れてしまった場合、留め帯は横から入らない（0 にならないことを見るための検査）
if (CHK == "strap_bad") intersection() { sweep_x() straps_v4(); union() { upto(5); s_bat(); } }
// 反例: 留め帯を上からかぶせようとした場合（ツバが土手に当たる。0 にならない）
if (CHK == "strap_top") intersection() { sweep_z() straps_v4(); upto(5); }
// ⑧ 電流計と PowerBoost を上から座へ降ろす（相手 = 手順⑦まで）
if (CHK == "boards")  intersection() { sweep_z(25) { ina_bat(); pb_bat(); } upto(7); }
// ⑨ OLED を上から降ろす／上の車線と電源系（静止）↔ 手順⑧まで＋皮
// ⑩ 天面一式を降ろす（相手 = 手順⑨まで）。OLED を L に留めてから一緒に降ろす形も 0（T-2 の調べ）
if (CHK == "top_oled") difference() { intersection() {
    union() for (t = [0 : STEP : 25]) translate([0, 0, t]) { s_top(); s_oled(); oled_hous(); }; upto(8); } rsp_press_zone(); }
if (CHK == "whigh")   intersection() { union() { w_high(); s_wpwr(); } union() { upto(8); s_oled(); oled_hous(); s_top(); s_front(); s_hatch(); } }

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
