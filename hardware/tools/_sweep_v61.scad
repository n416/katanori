// 掃引検査の外部呼び出し口（tools/sweep_chk.py が使う）。case_v6_1.scad は触らない。
//   SW_MODE="mover" → 動かす物を素の位置で出す / "world" → 相手を出す / "hit" → SW_Q の姿勢で交わりを取る
include <../case_v6_1.scad>
SW_MOVER = ""; SW_WORLD = ""; SW_MODE = ""; SW_Q = [0, 0, 0, 0, 0, 0]; SW_C = [0, 0, 0];
SW_D = 0;   // たわみ量（蓋の左の板が口で外へ出る量）。道の 7 つ目から来る
module sw_mover() {
    if (SW_MOVER == "hub")  hub_unit();
    if (SW_MOVER == "rsp")  { one("rsp");  one("riser"); }
    if (SW_MOVER == "oled") { one("oled"); one("oriser"); }
    if (SW_MOVER == "bat")  one("bat");
    if (SW_MOVER == "lid")  { lid_bent(SW_D); lid_units(); }          // 蓋。左の板は SW_D だけたわんだ形
    if (SW_MOVER == "lwall") p_lwall();                               // レジン: 左の板（後ろのねじを支点に開閉）
    if (SW_MOVER == "rwall") p_rwall();
    if (SW_MOVER == "front") { p_front(); one("oled"); }              // レジン: フロント板。OLED を窓に圧入した状態で一緒に入る（⑩）。ライザーは箱に残る
    if (SW_MOVER == "top")   { p_top(); lid_units(); }                // レジン: 天板（小組ごと真上から）
    if (SW_MOVER == "hatch") p_hatch();
}
module sw_units() {       // 先に入っている物だけ（動画が箱と別に描く）
    if (SW_WORLD == "hub")  units_for_hub();
    if (SW_WORLD == "rsp")  units_for_rsp();
    if (SW_WORLD == "oled") units_for_oled();
    if (SW_WORLD == "bat")  units_for_bat();
    if (SW_WORLD == "lid")  units_for_lid();
    if (SW_WORLD == "lwall" || SW_WORLD == "rwall") units_for_wall();
    if (SW_WORLD == "front") units_for_front();
    if (SW_WORLD == "top")   units_for_top();
    if (SW_WORLD == "hatch") { units_for_hatch(); lid_units(); }
}
module sw_world() {
    if (SW_WORLD == "hub")  world_for_hub();
    if (SW_WORLD == "rsp")  world_for_rsp();
    if (SW_WORLD == "oled") world_for_oled();
    if (SW_WORLD == "bat")  world_for_bat();
    if (SW_WORLD == "lid")  world_for_lid();
    if (SW_WORLD == "lwall") world_for_lwall();
    if (SW_WORLD == "rwall") world_for_rwall();
    if (SW_WORLD == "front") world_for_front();
    if (SW_WORLD == "top")   world_for_top();
    if (SW_WORLD == "hatch") world_for_hatch();
}
if (SW_MODE == "mover") sw_mover();
if (SW_MODE == "world") sw_world();
// 箱だけ（動画で半透明に描く）。world_for_* と同じ world_box() を使う（ここで別に書くと必ずずれる）
if (SW_MODE == "wshell") world_box(SW_WORLD);
if (SW_MODE == "wunits") sw_units();   // 先に入っている物だけ（動画で中身として描く）
if (SW_MODE == "hit")   intersection() { at_pose(SW_Q, SW_C) sw_mover(); sw_world(); }
// 道・回す中心・端までの長さ（case_v6_1.scad が唯一の出どころ）
//   ナイロンは 蓋（lid）／レジンは 左右の壁（lwall・rwall）。材料で道が違う
if (SW_MODE == "pose") echo(SWPOSE = concat([["hub",  nylon() ? PATH_HUB : PATH_HUB_R, hub_c(), hub_r()],
                                             ["rsp",  PATH_RSP,  [0, 0, 0], 0],
                                             ["bat",  PATH_BAT,  [0, 0, 0], 0]],
                            nylon() ? [["oled",  PATH_OLED,  [0, 0, 0], 0],
                                       ["lid",   PATH_LID,   [0, 0, 0], 0]]
                                    : [["lwall", PATH_LWALL, lwall_c(), lwall_r()],
                                       ["rwall", PATH_RWALL, rwall_c(), rwall_r()],
                                       ["top",   PATH_TOP,   [0, 0, 0], 0],
                                       ["front", PATH_FRONT, [0, 0, 0], 0],
                                       ["hatch", PATH_HATCH, [0, 0, 0], 0]]));
