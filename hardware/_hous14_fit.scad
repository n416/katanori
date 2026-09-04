// ハウジング 14（DUPONT_H）で、挿した線のハウジング＋曲がりが中身の何に当たるか。0 が正。
//   2026-09-05 「ハウジング 10（✅実測）」が誤りと分かった日に作成。chk_all は外皮↔中身しか見ないので、中身どうしはここで見る。
include <btn_v3.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN3_SOLO = false;
S = "hubh";   // hubh（ハブの口 9 本）/ xiaoh（XIAO の線）/ pbh（PowerBoost の線）/ inah（INA226 の線）
W = "brg";    // brg / bat / straps / pb / ina / rspbd / oled / hub / skin
module subj() {
    if (S == "hubh")  translate([HUB_DX, HUB_DY, 0]) for (id = PLUGGED_9) housing(id);
    if (S == "xiaoh") xiao_hous();
    if (S == "pbh")   { pbl_hous(); pbu_hous(); }
}
module partner() {
    if (W == "brg") brg_v4(); if (W == "bat") bat_v4(); if (W == "straps") straps_v4(); if (W == "pb") pb_bat();
    if (W == "ina") ina_bat(); if (W == "rspbd") respeaker_at(); if (W == "oled") oled_at(); if (W == "hub") hub_at();
    if (W == "skin") for (k = SKINS) skin1(k);
}
echo(str("HOUS14 生存確認: S=", S, " W=", W, " HOUS_H=", HOUS_H, " HOUS_R=", HOUS_R));
intersection() { subj(); partner(); }
